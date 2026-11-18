// Cizgi Masasi API - ESPN + NBA Official
const ESPN_URL = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries';
const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type' };
const json = (data, status = 200) => Response.json(data, { status, headers: cors });

async function getEspn() {
  const response = await fetch(ESPN_URL, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error('ESPN HTTP ' + response.status);
  const data = await response.json();
  if (!Array.isArray(data.injuries)) throw new Error('ESPN veri formati beklenenden farkli');
  const players = [];
  for (const team of data.injuries) {
    for (const item of team.injuries || []) {
      const name = item.athlete?.displayName?.trim();
      if (!name) continue;
      const raw = String(item.status || '').toLowerCase();
      const note = String(item.shortComment || '');
      let status = 'DTD';
      if (/\bout\b|suspend/.test(raw)) status = 'OUT';
      else if (/doubtful/.test(raw)) status = 'D';
      else if (/questionable|game.time/.test(raw)) status = 'Q';
      else if (/probable/.test(raw)) status = 'P';
      else if (/available/.test(raw)) status = 'AVAILABLE';
      players.push({ name, team: team.displayName || team.team?.displayName || '', status, note });
    }
  }
  if (players.length === 0) throw new Error('ESPN hic oyuncu dondurmedi');
  return players;
}

async function saveInjuries(env, players) {
  const unique = [...new Map(players.map(p => [p.name + '|' + p.team, p])).values()];
  const statements = [env.DB.prepare('DELETE FROM injuries WHERE source = ?').bind('ESPN')];
  for (const p of unique) {
    statements.push(env.DB.prepare(`INSERT INTO injuries
      (player_name, team, status, source, updated_at)
      VALUES (?, ?, ?, 'ESPN', CURRENT_TIMESTAMP)`)
      .bind(p.name, p.team, p.status));
  }
  await env.DB.batch(statements);
  return unique.length;
}

async function syncEspn(env) {
  let status = 'success';
  let count = 0;
  let message = 'Oyuncu verileri kaydedildi';
  try {
    const players = await getEspn();
    count = await saveInjuries(env, players);
  } catch (error) {
    status = 'error';
    message = String(error?.message || error);
  }
  await env.DB.prepare(`INSERT INTO sync_log
    (source, status, player_count, message)
    VALUES (?, ?, ?, ?)`)
    .bind('ESPN', status, count, message).run();
  return { status, count, message };
}

// Public refresh endpoint. The database's successful refresh timestamp is
// used as a shared cooldown across all visitors. The scheduled sync is unchanged.
async function refreshEspnNow(env) {
  const last = await env.DB.prepare(`SELECT checked_at FROM sync_log
    WHERE source='ESPN' AND status='success' ORDER BY id DESC LIMIT 1`).first();
  if (last?.checked_at) {
    const checked = Date.parse(String(last.checked_at).replace(' ', 'T') + 'Z');
    if (Number.isFinite(checked) && Date.now() - checked < 5 * 60 * 1000) {
      return json({ success:true, refreshed:false, skipped:true,
        message:'ESPN son 5 dakika icinde zaten kontrol edildi',last_check:last.checked_at });
    }
  }
  const result=await syncEspn(env);
  if(result.status !== 'success') return json({success:false,refreshed:false,error:result.message},502);
  return json({success:true,refreshed:true,count:result.count,
    message:'ESPN yeniden sorgulandi',checked_at:new Date().toISOString()});
}

async function importNba(request, env) {
  const authorization = request.headers.get('Authorization') || '';
  if (!env.NBA_IMPORT_TOKEN || authorization !== `Bearer ${env.NBA_IMPORT_TOKEN}`) {
    return json({ success: false, error: 'Unauthorized' }, 401);
  }
  let input;
  try { input = await request.json(); }
  catch { return json({ success: false, error: 'Invalid JSON' }, 400); }
  const { report_url, report_key, report_date, players, not_submitted_teams } = input || {};
  if (typeof report_url !== 'string' ||
      !/^https:\/\/ak-static\.cms\.nba\.com\/referee\/injury\/Injury-Report_/.test(report_url) ||
      !/^\d{4}-\d{2}-\d{2}_\d{4}$/.test(report_key || '') ||
      typeof report_date !== 'string' || report_date.length > 60 ||
      !Array.isArray(players) || players.length < 1 || players.length > 500 ||
      !Array.isArray(not_submitted_teams) || not_submitted_teams.length > 30 ||
      not_submitted_teams.some(t => typeof t !== 'string' || t.length > 80)) {
    return json({ success: false, error: 'Invalid payload' }, 400);
  }
  const allowed = new Set(['OUT', 'QUESTIONABLE', 'DOUBTFUL', 'PROBABLE', 'AVAILABLE']);
  for (const p of players) {
    if (!p || typeof p.player_name !== 'string' || !p.player_name.trim() || p.player_name.length > 120 ||
        typeof p.team !== 'string' || !p.team.trim() || p.team.length > 80 ||
        !allowed.has(p.status) || typeof p.reason !== 'string' || p.reason.length > 500) {
      return json({ success: false, error: 'Invalid player row' }, 400);
    }
  }
  const previous = await env.DB.prepare('SELECT report_key FROM nba_official_meta WHERE id = 1').first();
  if (previous && previous.report_key >= report_key) {
    return json({ success: true, skipped: true, report_key, reason: 'Same or older report' });
  }
  const statements = [env.DB.prepare('DELETE FROM nba_official_injuries')];
  for (const p of players) {
    statements.push(env.DB.prepare(`INSERT INTO nba_official_injuries
      (player_name, team, status, reason, report_key, report_url, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)`)
      .bind(p.player_name, p.team, p.status, p.reason, report_key, report_url));
  }
  statements.push(env.DB.prepare(`INSERT INTO nba_official_meta
    (id, report_key, report_date, report_url, player_count, not_submitted_json, updated_at)
    VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(id) DO UPDATE SET
      report_key=excluded.report_key,
      report_date=excluded.report_date,
      report_url=excluded.report_url,
      player_count=excluded.player_count,
      not_submitted_json=excluded.not_submitted_json,
      updated_at=CURRENT_TIMESTAMP`)
    .bind(report_key, report_date, report_url, players.length, JSON.stringify(not_submitted_teams)));
  await env.DB.batch(statements);
  return json({ success: true, stored: players.length, report_key });
}

async function listNba(env) {
  const { results } = await env.DB.prepare(`SELECT player_name, team, status, reason, report_key, updated_at
    FROM nba_official_injuries ORDER BY team, player_name`).all();
  const report = await env.DB.prepare('SELECT * FROM nba_official_meta WHERE id = 1').first();
  return json({ success: true, report: report || null, players: results || [] });
}


// Public read-only ESPN snapshot. updated_at is OUR COLLECTION TIME,
// not ESPN's publication time; never treat it as an official news timestamp.
async function listEspn(env) {
  const data = await env.DB.prepare(`SELECT player_name, team, status, updated_at
    FROM injuries WHERE source='ESPN' ORDER BY team, player_name`).all();
  const rows = data.results || [];
  const last = await env.DB.prepare(`SELECT checked_at, player_count FROM sync_log
    WHERE source='ESPN' AND status='success' ORDER BY id DESC LIMIT 1`).first();
  return json({success:true,source:'ESPN',timestamp_type:'collected_at',
    last_check:last?.checked_at || null, count:rows.length, players:rows});
}

// ---------------------------------------------------------------------------
// Ziyaret sayaci + kontrol paneli (sadece EKLENDI; yukaridaki kod degismedi)
// Tablolar: visit_sessions, visit_pages (migrations/ziyaret-sayac.sql).
// IP adresi saklanmaz. Panel anahtari: Worker secret PANEL_KEY.
// ---------------------------------------------------------------------------
const SITE_ORIGINS = new Set(['https://cizgi-masasi.pages.dev']);
const ID_RE = /^[a-z0-9]{8,40}$/;
const istDay = (ts) => new Date((ts + 10800) * 1000).toISOString().slice(0, 10);
const clean = (v, n) => String(v ?? '').replace(/[\u0000-\u001f<>"'`]/g, '').trim().slice(0, n);

function parseUa(uaRaw) {
  const ua = String(uaRaw || '');
  let os = 'Bilinmiyor', device = 'Masaüstü';
  if (/iPhone/.test(ua)) { os = 'iOS'; device = 'iPhone'; }
  else if (/iPad/.test(ua)) { os = 'iPadOS'; device = 'iPad'; }
  else if (/Android/.test(ua)) {
    os = 'Android';
    device = /Mobile/.test(ua) ? 'Android telefon' : 'Android tablet';
    const m = ua.match(/Android [\d.]+; ([^;)]+)/);
    const model = m ? m[1].trim() : '';
    if (model && model !== 'K' && !/^(Mobile|wv)$/.test(model) && !/Build/.test(model)) device = model.slice(0, 40);
  }
  else if (/Windows/.test(ua)) { os = 'Windows'; }
  else if (/Macintosh|Mac OS X/.test(ua)) { os = 'macOS'; device = 'Mac'; }
  else if (/CrOS/.test(ua)) { os = 'ChromeOS'; }
  else if (/Linux/.test(ua)) { os = 'Linux'; }
  let browser = 'Diğer';
  if (/Instagram/.test(ua)) browser = 'Instagram';
  else if (/FBAN|FBAV/.test(ua)) browser = 'Facebook';
  else if (/Edg\//.test(ua)) browser = 'Edge';
  else if (/OPR\/|Opera/.test(ua)) browser = 'Opera';
  else if (/SamsungBrowser/.test(ua)) browser = 'Samsung Internet';
  else if (/Firefox\/|FxiOS/.test(ua)) browser = 'Firefox';
  else if (/Chrome\/|CriOS/.test(ua)) browser = 'Chrome';
  else if (/Safari\//.test(ua)) browser = 'Safari';
  return { os, device, browser };
}

async function visitPing(request, env) {
  const origin = request.headers.get('Origin') || '';
  if (!SITE_ORIGINS.has(origin)) return json({ success: false, error: 'Forbidden' }, 403);
  let b;
  try { b = JSON.parse(await request.text()); }
  catch { return json({ success: false, error: 'Invalid JSON' }, 400); }
  if (!b || typeof b !== 'object' || !ID_RE.test(String(b.sid || '')) || !ID_RE.test(String(b.vid || ''))) {
    return json({ success: false, error: 'Invalid ids' }, 400);
  }
  const now = Math.floor(Date.now() / 1000);
  const dt = Math.max(0, Math.min(65, Math.round(Number(b.dt) || 0)));
  const page = clean(b.page, 40) || 'tab-home';
  const nick = clean(b.nick, 30);
  const ua = parseUa(request.headers.get('User-Agent'));
  const cf = request.cf || {};
  await env.DB.batch([
    env.DB.prepare(`INSERT INTO visit_sessions
      (sid, vid, started_at, last_seen, active_sec, hits, device, os, browser, screen, country, city, lang, nick, page, ref)
      VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(sid) DO UPDATE SET
        last_seen = excluded.last_seen,
        active_sec = visit_sessions.active_sec + excluded.active_sec,
        hits = visit_sessions.hits + 1,
        page = excluded.page,
        nick = CASE WHEN excluded.nick <> '' THEN excluded.nick ELSE visit_sessions.nick END`)
      .bind(b.sid, b.vid, now, now, dt, ua.device, ua.os, ua.browser,
        clean(b.screen, 16), clean(cf.country, 4), clean(cf.city, 40), clean(b.lang, 12), nick, page, clean(b.ref, 80)),
    env.DB.prepare(`INSERT INTO visit_pages (day, page, sec, views) VALUES (?, ?, ?, ?)
      ON CONFLICT(day, page) DO UPDATE SET sec = visit_pages.sec + excluded.sec, views = visit_pages.views + excluded.views`)
      .bind(istDay(now), page, dt, b.nv ? 1 : 0),
  ]);
  return json({ success: true });
}

function panelAuthorized(request, env) {
  const key = env.PANEL_KEY;
  if (!key) return 'missing';
  const got = request.headers.get('Authorization') || '';
  const want = `Bearer ${key}`;
  if (got.length !== want.length) return 'no';
  let diff = 0;
  for (let i = 0; i < want.length; i++) diff |= got.charCodeAt(i) ^ want.charCodeAt(i);
  return diff === 0 ? 'ok' : 'no';
}

async function panelData(request, env) {
  const auth = panelAuthorized(request, env);
  if (auth === 'missing') return json({ success: false, error: 'PANEL_KEY tanimli degil' }, 503);
  if (auth !== 'ok') return json({ success: false, error: 'Unauthorized' }, 401);
  const now = Math.floor(Date.now() / 1000);
  const todayStart = Math.floor((now + 10800) / 86400) * 86400 - 10800;
  const db = env.DB;
  // 90 gunden eski kayitlar silinir.
  await db.batch([
    db.prepare('DELETE FROM visit_sessions WHERE last_seen < ?').bind(now - 90 * 86400),
    db.prepare('DELETE FROM visit_pages WHERE day < ?').bind(istDay(now - 90 * 86400)),
  ]);
  const one = (sql, ...p) => db.prepare(sql).bind(...p).first();
  const all = async (sql, ...p) => (await db.prepare(sql).bind(...p).all()).results || [];
  const [onlineRow, todayRow, online, days, recent, visitors, pages] = await Promise.all([
    one('SELECT COUNT(*) AS n FROM visit_sessions WHERE last_seen > ?', now - 90),
    one(`SELECT COUNT(*) AS sessions, COUNT(DISTINCT vid) AS visitors, COALESCE(SUM(active_sec),0) AS sec
         FROM visit_sessions WHERE started_at >= ?`, todayStart),
    all(`SELECT sid, vid, nick, device, os, browser, city, country, page, active_sec, last_seen
         FROM visit_sessions WHERE last_seen > ? ORDER BY last_seen DESC LIMIT 50`, now - 90),
    all(`SELECT strftime('%Y-%m-%d', started_at + 10800, 'unixepoch') AS day, COUNT(*) AS sessions,
           COUNT(DISTINCT vid) AS visitors, COALESCE(SUM(active_sec),0) AS sec
         FROM visit_sessions WHERE started_at >= ? GROUP BY day ORDER BY day DESC`, todayStart - 13 * 86400),
    all(`SELECT sid, vid, nick, device, os, browser, screen, city, country, page, started_at, last_seen, active_sec
         FROM visit_sessions ORDER BY last_seen DESC LIMIT 60`),
    all(`SELECT vid, MAX(nick) AS nick, MAX(device) AS device, MAX(os) AS os, MAX(browser) AS browser,
           MAX(city) AS city, COUNT(*) AS sessions, COALESCE(SUM(active_sec),0) AS sec,
           MIN(started_at) AS first_seen, MAX(last_seen) AS last_seen
         FROM visit_sessions GROUP BY vid ORDER BY MAX(last_seen) DESC LIMIT 300`),
    all(`SELECT page, COALESCE(SUM(sec),0) AS sec, COALESCE(SUM(views),0) AS views
         FROM visit_pages WHERE day >= ? GROUP BY page ORDER BY sec DESC`, istDay(now - 6 * 86400)),
  ]);
  return json({ success: true, now, online_count: onlineRow?.n || 0, today: todayRow || {},
    online, days, recent, visitors, pages });
}

const PANEL_HTML = `<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>Çizgi Masası · Ziyaret Paneli</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}
body{margin:0;font:14px/1.45 system-ui,Segoe UI,Roboto,sans-serif;background:#0f1419;color:#e6edf3;padding:16px;max-width:1100px;margin:auto}
h1{font-size:20px;margin:0 0 4px}h2{font-size:15px;margin:22px 0 8px;color:#9fb3c8}
.sub{color:#7d8b99;font-size:12px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.card{background:#171e26;border:1px solid #24303c;border-radius:10px;padding:12px}
.card b{display:block;font-size:24px}.card span{color:#7d8b99;font-size:12px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#3fb950;margin-right:6px}
.wrap{overflow-x:auto;background:#171e26;border:1px solid #24303c;border-radius:10px}
table{border-collapse:collapse;width:100%;min-width:560px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid #202a35;white-space:nowrap}
th{color:#7d8b99;font-weight:600;font-size:12px}tr:last-child td{border-bottom:0}
input,button{font:inherit;padding:8px 10px;border-radius:8px;border:1px solid #2b3a48;background:#0f1419;color:inherit}
button{background:#1f6feb;border-color:#1f6feb;cursor:pointer}
#login{max-width:340px;margin:20vh auto;text-align:center}#err{color:#f85149;margin-top:8px}
.muted{color:#7d8b99}
tr.sub td{color:#9fb3c8;font-size:13px;background:#141b22}tr.sub td:first-child{padding-left:24px;color:#7d8b99}
tr.person td:first-child{font-weight:600}
</style></head><body>
<div id="login"><h1>Ziyaret Paneli</h1><p class="sub">Panel anahtarını gir</p>
<form id="f"><input id="k" type="password" autocomplete="current-password" placeholder="anahtar" style="width:100%;margin:8px 0"><button style="width:100%">Aç</button></form><div id="err"></div></div>
<div id="app" hidden>
<h1>Çizgi Masası · Ziyaret Paneli</h1><div class="sub" id="upd"></div>
<div class="cards" id="cards"></div>
<h2>Şu an sitede</h2><div class="wrap"><table id="t-online"></table></div>
<h2>Son 14 gün</h2><div class="wrap"><table id="t-days"></table></div>
<h2>Kişiler ve cihazları</h2><div class="wrap"><table id="t-vis"></table></div>
<h2>Son oturumlar</h2><div class="wrap"><table id="t-rec"></table></div>
<h2>Sayfalar (son 7 gün)</h2><div class="wrap"><table id="t-pages"></table></div>
<p class="sub">Süre = sayfa açıkken ve ekranda görünürken geçen süre. IP adresi saklanmaz; 90 günden eski kayıtlar silinir.
Siteye ilk girişte herkese bir kez isim sorulur. Aynı ismi yazan cihazlar tek kişi altında toplanır. İstersen
<b>siteadresi/?ad=Azra</b> linkiyle de isim verilebilir.</p>
</div>
<script>
const PAGES={'tab-home':'Ana sayfa','tab-player':'Oyuncu','tab-hit':'Hit rate','tab-sak':'Sakatlar','tab-team':'Takım','tab-cheat':'Cheat sheet','tab-qry':'Sorgu','tab-scan':'İddaa tarama','tab-card':'Karne'};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const mins=s=>{s=Math.round(s||0);return s<60?s+' sn':Math.floor(s/60)+' dk'+(s%60?' '+(s%60)+' sn':'')};
const dt=t=>t?new Date(t*1000).toLocaleString('tr-TR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'-';
const who=r=>esc(r.nick||'(isimsiz)');const dev=r=>esc([r.device,r.os,r.browser].filter(Boolean).join(' · '));
const place=r=>esc([r.city,r.country].filter(Boolean).join(', '));
const page=p=>esc(PAGES[p]||p);
function tbl(id,head,rows){document.getElementById(id).innerHTML='<tr>'+head.map(h=>'<th>'+h+'</th>').join('')+'</tr>'+
 (rows.length?rows.map(r=>{const o=Array.isArray(r)?{c:r}:r;return '<tr'+(o.cls?' class="'+o.cls+'"':'')+'>'+o.c.map(c=>'<td>'+c+'</td>').join('')+'</tr>'}).join(''):'<tr><td class="muted" colspan="'+head.length+'">Kayıt yok</td></tr>')}
function groupPeople(rows){
  const m=new Map();
  for(const r of rows){
    const nm=String(r.nick||'').trim();
    const key=nm?'n:'+nm.toLowerCase():'v:'+r.vid;
    let g=m.get(key);
    if(!g){g={name:nm,devices:[],sessions:0,sec:0,first:r.first_seen,last:r.last_seen};m.set(key,g)}
    g.devices.push(r);g.sessions+=r.sessions;g.sec+=r.sec;
    g.first=Math.min(g.first,r.first_seen);g.last=Math.max(g.last,r.last_seen);
  }
  const out=[...m.values()];
  out.forEach(g=>g.devices.sort((a,b)=>b.last_seen-a.last_seen));
  return out.sort((a,b)=>b.last-a.last);
}
function peopleRows(rows){
  const out=[];
  for(const g of groupPeople(rows)){
    const d0=g.devices[0],name=esc(g.name||'(isimsiz)');
    if(g.devices.length===1){out.push({cls:'person',c:[name,dev(d0),place(d0),g.sessions,mins(g.sec),dt(g.first),dt(g.last)]});continue}
    const cities=[...new Set(g.devices.map(place).filter(Boolean))].join(' / ');
    out.push({cls:'person',c:[name,g.devices.length+' cihaz',cities,g.sessions,mins(g.sec),dt(g.first),dt(g.last)]});
    for(const d of g.devices)out.push({cls:'sub',c:['↳',dev(d),place(d),d.sessions,mins(d.sec),dt(d.first_seen),dt(d.last_seen)]});
  }
  return out;
}
let key=localStorage.getItem('cm_panel_key')||'',timer=null;
async function load(){
 const r=await fetch('/api/panel-data',{headers:{Authorization:'Bearer '+key},cache:'no-store'});
 if(r.status===401||r.status===503){const j=await r.json().catch(()=>({}));localStorage.removeItem('cm_panel_key');
  document.getElementById('app').hidden=true;document.getElementById('login').hidden=false;
  document.getElementById('err').textContent=r.status===503?'Worker\\'da PANEL_KEY tanımlı değil':'Anahtar yanlış';return false}
 const d=await r.json();document.getElementById('login').hidden=true;document.getElementById('app').hidden=false;
 const t=d.today||{};
 document.getElementById('cards').innerHTML=
  '<div class="card"><b><span class="dot"></span>'+d.online_count+'</b><span>şu an sitede</span></div>'+
  '<div class="card"><b>'+(t.visitors||0)+'</b><span>bugün cihaz</span></div>'+
  '<div class="card"><b>'+(t.sessions||0)+'</b><span>bugün oturum</span></div>'+
  '<div class="card"><b>'+mins(t.sec)+'</b><span>bugün toplam süre</span></div>'+
  '<div class="card"><b>'+(t.sessions?mins(t.sec/t.sessions):'-')+'</b><span>oturum başı ortalama</span></div>';
 tbl('t-online',['Kim','Cihaz','Yer','Şu an','Süre'],d.online.map(r=>[who(r),dev(r),place(r),page(r.page),mins(r.active_sec)]));
 tbl('t-days',['Gün','Cihaz','Oturum','Toplam süre'],d.days.map(r=>[esc(r.day),r.visitors,r.sessions,mins(r.sec)]));
 tbl('t-vis',['Kim','Cihaz','Yer','Oturum','Toplam süre','İlk görülme','Son görülme'],peopleRows(d.visitors));
 tbl('t-rec',['Kim','Cihaz','Ekran','Başladı','Süre','Son sayfa'],d.recent.map(r=>[who(r),dev(r),esc(r.screen),dt(r.started_at),mins(r.active_sec),page(r.page)]));
 tbl('t-pages',['Sayfa','Toplam süre','Açılış'],d.pages.map(r=>[page(r.page),mins(r.sec),r.views]));
 document.getElementById('upd').textContent='Son güncelleme: '+new Date().toLocaleTimeString('tr-TR')+' · 30 sn\\'de bir yenilenir';
 return true}
function start(){load().then(ok=>{if(ok&&!timer)timer=setInterval(load,30000)}).catch(()=>{document.getElementById('err').textContent='Bağlantı hatası'})}
document.getElementById('f').addEventListener('submit',e=>{e.preventDefault();key=document.getElementById('k').value.trim();
 localStorage.setItem('cm_panel_key',key);start()});
if(key)start();
</script></body></html>`;

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    try {
      if (path === '/api/import-nba' && request.method === 'POST') return await importNba(request, env);
      if (path === '/api/refresh-espn' && request.method === 'POST') return await refreshEspnNow(env);
      if (path === '/api/visit' && request.method === 'POST') return await visitPing(request, env);
      if (request.method !== 'GET') return json({ success: false, error: 'Method not allowed' }, 405);
      if (path === '/panel') return new Response(PANEL_HTML, { headers: {
        'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' } });
      if (path === '/api/panel-data') return await panelData(request, env);
      if (path === '/api/nba-injuries') return await listNba(env);
      if (path === '/api/espn-injuries') return await listEspn(env);
      if (path === '/api/health') {
        const row = await env.DB.prepare('SELECT COUNT(*) AS total FROM injuries').first();
        return json({ success: true, database: 'connected', injury_records: row?.total || 0 });
      }
      if (path === '/api/sync-status') {
        const row = await env.DB.prepare('SELECT * FROM sync_log ORDER BY id DESC LIMIT 1').first();
        return json({ success: true, last_check: row || null });
      }
      if (path === '/api/test-espn') {
        const players = await getEspn();
        return json({ success: true, count: players.length, sample: players.slice(0, 5) });
      }
      if (path === '/api/test-nba') {
        const page = await fetch('https://official.nba.com/nba-injury-report-2026-27-season/');
        const html = await page.text();
        const urls = [...html.matchAll(/https:\/\/ak-static\.cms\.nba\.com\/referee\/injury\/Injury-Report_[^"'<>\s]+?\.pdf/g)].map(m => m[0]);
        return json({ success: page.ok, page_status: page.status, reports_found: urls.length, sample: urls.slice(0, 3) });
      }
      if (path === '/') return json({ success: true, service: 'Cizgi Masasi API', routes: ['/api/health', '/api/sync-status', '/api/nba-injuries', '/api/espn-injuries'] });
      return json({ success: false, error: 'Not found' }, 404);
    } catch (error) {
      console.error('API error:', error);
      return json({ success: false, error: String(error?.message || error) }, 500);
    }
  },
  async scheduled(controller, env, ctx) {
    const result = await syncEspn(env);
    console.log('Sakatlik guncelleme:', result);
    if (result.status !== 'success') throw new Error(result.message);
  }
};
