// Ziyaret sayaci testleri (ag yok). Kullanim: node ziyaret_sayac.test.mjs <repo-koku>
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';

const root = process.argv[2];
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'cm-ziyaret-'));
fs.copyFileSync(path.join(root, 'worker/cizgi-masasi-api.js'), path.join(tmp, 'w.mjs'));
const worker = (await import(path.join(tmp, 'w.mjs'))).default;
const panelHtmlSrc = fs.readFileSync(path.join(root, 'worker/cizgi-masasi-api.js'), 'utf8');

// --- D1 taklidi (gercek SQLite) ---
function makeDb() {
  const db = new DatabaseSync(':memory:');
  db.exec(fs.readFileSync(path.join(root, 'worker/migrations/ziyaret-sayac.sql'), 'utf8'));
  db.exec('CREATE TABLE injuries (id INTEGER PRIMARY KEY AUTOINCREMENT, player_name TEXT, team TEXT, status TEXT, source TEXT, updated_at TEXT)');
  const stmt = (sql, args = []) => ({
    bind: (...a) => stmt(sql, a),
    first: async () => db.prepare(sql).get(...args) ?? null,
    all: async () => ({ results: db.prepare(sql).all(...args) }),
    run: async () => { db.prepare(sql).run(...args); return {}; },
    _run: () => db.prepare(sql).run(...args),
  });
  return { raw: db, prepare: (s) => stmt(s), batch: async (list) => { db.exec('BEGIN'); try { list.forEach((s) => s._run()); db.exec('COMMIT'); } catch (e) { db.exec('ROLLBACK'); throw e; } } };
}

const ORIGIN = 'https://cizgi-masasi.pages.dev';
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1';
const ANDROID = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36';
const WIN_EDGE = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0';
const ping = (env, body, { origin = ORIGIN, ua = IPHONE, cf = { country: 'TR', city: 'Istanbul' } } = {}) => {
  const req = new Request('https://w.test/api/visit', { method: 'POST', body: typeof body === 'string' ? body : JSON.stringify(body), headers: { Origin: origin, 'User-Agent': ua, 'Content-Type': 'text/plain' } });
  Object.defineProperty(req, 'cf', { value: cf });
  return worker.fetch(req, env);
};
const get = (env, p, headers = {}) => worker.fetch(new Request('https://w.test' + p, { headers }), env);
const SID = 'abcdef123456', VID = 'vid1234567890';

let n = 0;
const ok = (name) => console.log('OK', ++n, name);

// 1) cihaz ayristirma + oturum toplama
{
  const env = { DB: makeDb(), PANEL_KEY: 'gizli' };
  let r = await ping(env, { sid: SID, vid: VID, page: 'tab-home', dt: 0, nv: 1, screen: '390x844', lang: 'tr-TR', nick: 'Azra' });
  assert.equal(r.status, 200);
  await ping(env, { sid: SID, vid: VID, page: 'tab-home', dt: 30 });
  await ping(env, { sid: SID, vid: VID, page: 'tab-hit', dt: 20, nv: 1 });
  await ping(env, { sid: SID, vid: VID, page: 'tab-hit', dt: 9999 });          // 65 ile sinirlanir
  const s = env.DB.raw.prepare('SELECT * FROM visit_sessions').all();
  assert.equal(s.length, 1);
  assert.equal(s[0].active_sec, 30 + 20 + 65);
  assert.equal(s[0].hits, 4);
  assert.deepEqual([s[0].device, s[0].os, s[0].browser, s[0].city, s[0].country, s[0].nick, s[0].page], ['iPhone', 'iOS', 'Safari', 'Istanbul', 'TR', 'Azra', 'tab-hit']);
  ok('oturum: sure toplanir, dt 65 ile sinirli, iPhone/Safari ayristirilir');
  // nick sonraki pingte bos gelirse silinmez
  assert.equal(env.DB.raw.prepare('SELECT nick FROM visit_sessions').get().nick, 'Azra');
  const pages = env.DB.raw.prepare('SELECT page, sec, views FROM visit_pages ORDER BY page').all();
  assert.deepEqual(pages.map((p) => [p.page, p.sec, p.views]), [['tab-hit', 85, 1], ['tab-home', 30, 1]]);
  ok('sayfa tablosu: sure ve acilis sayilari dogru, isim korunur');
}

// 2) UA ornekleri
{
  const env = { DB: makeDb() };
  await ping(env, { sid: 'androidsid01', vid: 'androidvid01' }, { ua: ANDROID });
  await ping(env, { sid: 'windowssid01', vid: 'windowsvid01' }, { ua: WIN_EDGE });
  const rows = env.DB.raw.prepare('SELECT sid, device, os, browser FROM visit_sessions ORDER BY sid').all();
  assert.deepEqual(rows.map((r) => [r.device, r.os, r.browser]), [['Android telefon', 'Android', 'Chrome'], ['Masaüstü', 'Windows', 'Edge']]);
  ok('Android (gizlenmis model) ve Windows/Edge ayristirilir');
}

// 3) korumalar
{
  const env = { DB: makeDb() };
  assert.equal((await ping(env, { sid: SID, vid: VID }, { origin: 'https://baska-site.com' })).status, 403);
  assert.equal((await ping(env, { sid: SID, vid: VID }, { origin: '' })).status, 403);
  assert.equal((await ping(env, 'bozuk{json')).status, 400);
  assert.equal((await ping(env, { sid: 'x', vid: VID })).status, 400);
  assert.equal((await ping(env, { sid: "a'; DROP TABLE visit_sessions;--", vid: VID })).status, 400);
  assert.equal(env.DB.raw.prepare('SELECT COUNT(*) AS n FROM visit_sessions').get().n, 0);
  // XSS: isim/sayfadaki < > " ' temizlenir
  await ping(env, { sid: SID, vid: VID, nick: '<img src=x onerror=alert(1)>', page: '"><script>' });
  const row = env.DB.raw.prepare('SELECT nick, page FROM visit_sessions').get();
  assert.ok(!/[<>"']/.test(row.nick + row.page), row.nick + row.page);
  ok('yanlis origin/bozuk veri reddedilir, isim ve sayfa temizlenir');
}

// 4) panel yetkisi ve icerik
{
  const env = { DB: makeDb() };
  assert.equal((await get(env, '/api/panel-data')).status, 503);              // PANEL_KEY yok
  env.PANEL_KEY = 'gizli';
  assert.equal((await get(env, '/api/panel-data')).status, 401);
  assert.equal((await get(env, '/api/panel-data', { Authorization: 'Bearer yanlis' })).status, 401);
  assert.equal((await get(env, '/api/panel-data', { Authorization: 'Bearer gizlj' })).status, 401);
  await ping(env, { sid: SID, vid: VID, page: 'tab-home', dt: 40, nv: 1, nick: 'Deneme', screen: '1920x1080' }, { ua: WIN_EDGE });
  await ping(env, { sid: 'second123456', vid: 'vid2second12', page: 'tab-team', dt: 10, nv: 1 });
  // eski kayit (100 gun once) panel acilinca silinir
  const old = Math.floor(Date.now() / 1000) - 100 * 86400;
  env.DB.raw.prepare("INSERT INTO visit_sessions (sid,vid,started_at,last_seen,active_sec) VALUES ('oldsession01','oldvid123456',?,?,5)").run(old, old);
  env.DB.raw.prepare("INSERT INTO visit_pages (day,page,sec,views) VALUES ('2020-01-01','tab-home',5,1)").run();
  const r = await get(env, '/api/panel-data', { Authorization: 'Bearer gizli' });
  assert.equal(r.status, 200);
  const d = await r.json();
  assert.equal(d.online_count, 2);
  assert.equal(d.today.sessions, 2);
  assert.equal(d.today.visitors, 2);
  assert.equal(d.today.sec, 50);
  assert.equal(d.visitors.length, 2);
  assert.equal(d.days.length, 1);
  assert.deepEqual(d.pages.map((p) => p.page).sort(), ['tab-home', 'tab-team']);
  assert.equal(d.recent.find((x) => x.sid === SID).nick, 'Deneme');
  assert.equal(env.DB.raw.prepare('SELECT COUNT(*) AS n FROM visit_sessions').get().n, 2);
  assert.equal(env.DB.raw.prepare('SELECT COUNT(*) AS n FROM visit_pages').get().n, 2);
  ok('panel: yetki, sayilar, ziyaretci/gun/sayfa listeleri, 90 gun temizligi');
}

// 5) panel sayfasi: HTML gelir, icindeki script soz dizimi gecerli, gizli bilgi yok
{
  const env = { DB: makeDb(), PANEL_KEY: 'gizli' };
  const r = await get(env, '/panel');
  assert.equal(r.status, 200);
  assert.match(r.headers.get('content-type'), /text\/html/);
  assert.match(r.headers.get('x-robots-tag'), /noindex/);
  const html = await r.text();
  assert.ok(!html.includes('gizli'));
  const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
  new vm.Script(script);               // soz dizimi hatasi varsa burada patlar
  ok('/panel HTML sunar, script soz dizimi gecerli, anahtar icinde yok');
}

// 6) eski rotalar bozulmadi
{
  const env = { DB: makeDb() };
  env.DB.raw.prepare("INSERT INTO injuries (player_name) VALUES ('X')").run();
  const h = await (await get(env, '/api/health')).json();
  assert.deepEqual([h.success, h.injury_records], [true, 1]);
  assert.equal((await get(env, '/nope')).status, 404);
  assert.equal((await worker.fetch(new Request('https://w.test/api/health', { method: 'PUT' }), env)).status, 405);
  assert.equal((await worker.fetch(new Request('https://w.test/api/import-nba', { method: 'POST', body: '{}' }), env)).status, 401);
  const root = await (await get(env, '/')).json();
  assert.ok(!JSON.stringify(root).includes('panel'));
  ok('mevcut rotalar (health, 404, 405, import-nba yetkisi) aynen calisir');
}

// 7) tarayici scripti (index.html icindeki)
{
  const html = fs.readFileSync(path.join(root, 'site-patches/index.html'), 'utf8');
  assert.equal((html.match(/id="cm-ziyaret-sayac"/g) || []).length, 1);
  const code = html.match(/<script id="cm-ziyaret-sayac">([\s\S]*?)<\/script>/)[1];
  let t = 1_000_000, visible = 'visible', pressed = 'tab-home';
  const sent = [], timers = [], listeners = {};
  const store = () => { const m = {}; return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); } }; };
  const sandbox = {
    navigator: { doNotTrack: null, language: 'tr-TR' }, screen: { width: 390, height: 844 },
    location: { protocol: 'https:', search: '?ad=Azra' }, URL, crypto: globalThis.crypto,
    localStorage: store(), sessionStorage: store(),
    document: { referrer: '', get visibilityState() { return visible; },
      querySelector: (q) => (q.startsWith('.tab') ? { id: pressed } : null),
      addEventListener: (e, f) => { listeners['d:' + e] = f; } },
    fetch: (url, o) => { sent.push({ url, ...JSON.parse(o.body), headers: o.headers }); return Promise.resolve({}); },
    setInterval: (f) => timers.push(f), Date: { now: () => t },
  };
  sandbox.window = { addEventListener: (e, f) => { listeners['w:' + e] = f; }, localStorage: sandbox.localStorage, sessionStorage: sandbox.sessionStorage };
  vm.runInNewContext(code, sandbox);
  assert.equal(sent.length, 1);
  assert.equal(sent[0].url, 'https://cizgi-masasi-api.k-melihsari.workers.dev/api/visit');
  assert.deepEqual([sent[0].page, sent[0].dt, sent[0].nv, sent[0].nick, sent[0].screen], ['tab-home', 0, 1, 'Azra', '390x844']);
  assert.equal(sent[0].headers['Content-Type'], 'text/plain');
  assert.match(sent[0].sid, /^[a-z0-9]{16}$/);
  assert.match(sent[0].vid, /^[a-z0-9]{16}$/);
  const step = timers[0];
  for (let i = 0; i < 6; i++) { t += 5000; step(); }            // 30 sn gorunur
  assert.equal(sent.length, 2);
  assert.deepEqual([sent[1].page, sent[1].dt, sent[1].nv], ['tab-home', 30, 0]);
  for (let i = 0; i < 2; i++) { t += 5000; step(); }            // 10 sn daha, sonra sekme degisir
  pressed = 'tab-hit'; t += 5000; step();
  assert.deepEqual([sent[2].page, sent[2].dt, sent[2].nv], ['tab-home', 15, 0]);
  assert.deepEqual([sent[3].page, sent[3].dt, sent[3].nv], ['tab-hit', 0, 1]);
  // gizli sekmede sure sayilmaz
  visible = 'hidden';
  for (let i = 0; i < 20; i++) { t += 5000; step(); }
  assert.equal(sent.length, 4);
  // gorunur olunca ve kapaninca kalan sure gonderilir
  visible = 'visible'; listeners['d:visibilitychange'](); t += 5000; step();
  t += 3000; visible = 'hidden'; listeners['d:visibilitychange']();
  assert.equal(sent.at(-2).dt, 5);       // gorunur olunca 5 sn'lik sinyal
  assert.equal(sent.at(-1).page, 'tab-hit');
  assert.equal(sent.at(-1).dt, 3);       // gizlenirken kalan 3 sn
  // DNT acikken hic istek yok
  const sent2 = [];
  vm.runInNewContext(code, { ...sandbox, navigator: { doNotTrack: '1' }, fetch: (u, o) => { sent2.push(o); return Promise.resolve({}); } });
  assert.equal(sent2.length, 0);
  ok('tarayici scripti: ilk ping, 30 sn sinyali, sekme degisimi, gizli sekme sayilmaz, DNT');
}


// 8) isim sorusu YOK; bot/Linux/headless girisleri hic gonderilmez (istemci) ve kaydedilmez (Worker)
{
  const html = fs.readFileSync(path.join(root, 'site-patches/index.html'), 'utf8');
  const code = html.match(/<script id="cm-ziyaret-sayac">([\s\S]*?)<\/script>/)[1];
  assert.ok(!code.includes('cm-ad-ov') && !code.includes('Adın ne') && !code.includes('cm_ad_asked'), 'isim sorusu kalmamali');
  const run = (nav) => {
    const sent = [], timeouts = [];
    const store = () => { const m = {}; return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); } }; };
    const sb = {
      navigator: { doNotTrack: null, language: 'tr-TR', ...nav }, screen: { width: 390, height: 844 },
      location: { protocol: 'https:', search: '' }, URL, crypto: globalThis.crypto,
      localStorage: store(), sessionStorage: store(),
      document: { referrer: '', readyState: 'complete', visibilityState: 'visible', querySelector: () => null, addEventListener() {}, body: { appendChild() {} }, createElement: () => ({ setAttribute() {}, appendChild() {} }) },
      fetch: (u, o) => { sent.push(JSON.parse(o.body)); return Promise.resolve({}); },
      setInterval() {}, setTimeout: (f) => timeouts.push(f), Date: { now: () => 1_000_000 },
    };
    sb.window = { addEventListener() {}, localStorage: sb.localStorage, sessionStorage: sb.sessionStorage, top: null, self: null };
    vm.runInNewContext(code, sb);
    timeouts.forEach((f) => f());
    return sent;
  };
  const WIN = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
  const LINUX = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
  const HEADLESS = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/126.0.0.0 Safari/537.36';
  assert.equal(run({ userAgent: WIN }).length, 1, 'Windows sayilir');
  assert.equal(run({ userAgent: ANDROID }).length, 1, 'Android (UA icinde Linux var) sayilir');
  assert.equal(run({ userAgent: IPHONE }).length, 1, 'iPhone sayilir');
  assert.equal(run({ userAgent: LINUX }).length, 0, 'Linux masaustu sayilmaz');
  assert.equal(run({ userAgent: HEADLESS }).length, 0, 'headless sayilmaz');
  assert.equal(run({ userAgent: WIN, webdriver: true }).length, 0, 'webdriver (otomasyon) sayilmaz');
  // Worker tarafi: Linux/headless/bos UA hic satir yazmaz, mobil ve masaustu yazar
  const env = { DB: makeDb(), PANEL_KEY: 'gizli' };
  const send = (ua, i) => ping(env, { sid: 'sid' + String(i).padStart(9, '0'), vid: 'vid' + String(i).padStart(9, '0'), page: 'tab-home', dt: 0, nv: 1 }, { ua });
  for (const [i, ua] of [LINUX, HEADLESS, 'curl/8.0', 'Googlebot/2.1', ''].entries()) {
    const r = await send(ua, i);
    assert.equal(r.status, 200);
    assert.equal((await r.json()).ignored, true, 'yok sayilmali: ' + ua);
  }
  assert.equal(env.DB.raw.prepare('SELECT COUNT(*) c FROM visit_sessions').get().c, 0);
  for (const [i, ua] of [WIN, ANDROID, IPHONE].entries()) assert.equal((await send(ua, 10 + i)).status, 200);
  const rows = env.DB.raw.prepare('SELECT os FROM visit_sessions ORDER BY os').all().map((x) => x.os);
  assert.deepEqual(rows, ['Android', 'Windows', 'iOS']);
  ok('isim sorusu yok; Linux/headless/webdriver/bot sayilmaz (istemci + Worker), Android/iPhone/Windows sayilir');
}

// 9) panel: ayni isimli cihazlar tek kisi altinda, farkli cihazlar alt satir olur
{
  const env = { DB: makeDb(), PANEL_KEY: 'gizli' };
  const html = await (await get(env, '/panel')).text();
  const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
  const els = {};
  const el = (id) => (els[id] ||= { id, innerHTML: '', textContent: '', hidden: false, addEventListener() {}, value: '' });
  const rowsIn = [
    { vid: 'v1', nick: 'Azra', device: 'iPhone', os: 'iOS', browser: 'Safari', city: 'Istanbul', country: 'TR', sessions: 3, sec: 600, first_seen: 100, last_seen: 500 },
    { vid: 'v2', nick: 'azra', device: 'Masaüstü', os: 'Windows', browser: 'Chrome', city: 'Istanbul', country: 'TR', sessions: 1, sec: 60, first_seen: 200, last_seen: 900 },
    { vid: 'v3', nick: 'Melih', device: 'Mac', os: 'macOS', browser: 'Safari', city: 'Ankara', country: 'TR', sessions: 2, sec: 120, first_seen: 50, last_seen: 400 },
    { vid: 'v4', nick: '', device: 'Android telefon', os: 'Android', browser: 'Chrome', city: '', country: 'TR', sessions: 1, sec: 30, first_seen: 10, last_seen: 20 },
    { vid: 'v5', nick: '', device: 'iPad', os: 'iPadOS', browser: 'Safari', city: '', country: '', sessions: 1, sec: 5, first_seen: 5, last_seen: 6 },
    { vid: 'v6', nick: '<i>x</i>', device: 'Mac', os: 'macOS', browser: 'Chrome', city: '', country: '', sessions: 1, sec: 5, first_seen: 1, last_seen: 2 },
  ];
  const data = { success: true, now: 1000, online_count: 0, today: {}, online: [], days: [], recent: [], visitors: rowsIn, pages: [] };
  const sandbox = {
    document: { getElementById: el }, localStorage: { getItem: () => 'gizli', setItem() {}, removeItem() {} },
    fetch: async () => ({ status: 200, json: async () => data }), setInterval: () => 1, Date, Math, Set, Map, String, Array, Number,
  };
  vm.runInNewContext(script, sandbox);
  await new Promise((r) => setTimeout(r, 20));
  const t = els['t-vis'].innerHTML;
  const person = (t.match(/<tr class="person">/g) || []).length;
  const subs = (t.match(/<tr class="sub">/g) || []).length;
  assert.equal(person, 5, 'Azra(2 cihaz) + Melih + 2 isimsiz + <i>x</i> = 5 kisi satiri');
  assert.equal(subs, 2, 'sadece Azra icin 2 alt satir');
  assert.ok(t.includes('2 cihaz'));
  assert.ok(t.indexOf('Azra') < t.indexOf('Melih'), 'son gorulmeye gore: Azra (900) once');
  assert.equal((t.match(/\(isimsiz\)/g) || []).length, 2, 'isimsizler birlestirilmez');
  assert.ok(!t.includes('<i>x</i>') && t.includes('&lt;i&gt;x&lt;/i&gt;'), 'isim HTML olarak yorumlanmaz');
  // toplamlar: Azra 3+1 oturum, 660 sn = 11 dk
  assert.ok(/<td>4<\/td><td>11 dk<\/td>/.test(t), t);
  ok('panel: ayni isim (buyuk/kucuk harf fark etmez) tek kisi, cihazlar alt satir, isimsizler ayri, HTML kacisli');
}


// 11) Worker: "Melih" kaydedilmez, o cihazin eski kayitlari silinir
{
  const env = { DB: makeDb() };
  await ping(env, { sid: 'oldsess00001', vid: 'melihvid0001', page: 'tab-home', dt: 30, nv: 1 });          // isimsizken kaydedilmisti
  await ping(env, { sid: 'friend000001', vid: 'friendvid001', page: 'tab-home', dt: 30, nv: 1, nick: 'Azra' });
  assert.equal(env.DB.raw.prepare('SELECT COUNT(*) AS n FROM visit_sessions').get().n, 2);
  const r = await ping(env, { sid: 'newsess00001', vid: 'melihvid0001', page: 'tab-home', dt: 0, nick: 'Melih' });
  assert.equal(r.status, 200);
  assert.equal((await r.json()).ignored, true);
  const left = env.DB.raw.prepare('SELECT vid FROM visit_sessions').all().map((x) => x.vid);
  assert.deepEqual(left, ['friendvid001'], 'Melih cihazinin eski ve yeni kaydi kalmamali, arkadas kalmali');
  // yazim varyantlari da sayilmaz
  for (const nick of ['melih', 'MELIH', 'MELİH', 'Melıh', '  melih  ', 'Mélih']) {
    const x = await ping(env, { sid: 'varsess00001', vid: 'varvid000001', page: 'tab-home', dt: 5, nick });
    assert.equal((await x.json()).ignored, true, nick);
  }
  assert.equal(env.DB.raw.prepare("SELECT COUNT(*) AS n FROM visit_sessions WHERE vid='varvid000001'").get().n, 0);
  // benzer ama farkli isimler normal kaydedilir
  for (const nick of ['Melihan', 'Melis', 'Emel']) {
    const x = await ping(env, { sid: 'ok' + nick.toLowerCase() + '01', vid: 'okvid' + nick.toLowerCase() + '1', page: 'tab-home', dt: 5, nick });
    assert.equal((await x.json()).ignored, undefined, nick);
  }
  assert.equal(env.DB.raw.prepare('SELECT COUNT(*) AS n FROM visit_sessions').get().n, 4);
  ok('Worker: Melih (her yazimi) kaydedilmez ve cihazinin eski kayitlari silinir; Melihan/Melis/Emel normal kaydedilir');
}

// 12) tarayici: nick Melih ise tek temizlik sinyali, sonra hic istek yok
{
  const html = fs.readFileSync(path.join(root, 'site-patches/index.html'), 'utf8');
  const code = html.match(/<script id="cm-ziyaret-sayac">([\s\S]*?)<\/script>/)[1];
  const mkStore = (o) => ({ getItem: (k) => (k in o ? o[k] : null), setItem: (k, v) => { o[k] = String(v); } });
  const local = {}, session = {};
  function run(search) {
    const sent = [], timers = [];
    let t = 1_000_000;
    const sandbox = {
      navigator: { doNotTrack: null, language: 'tr-TR' }, screen: { width: 1, height: 1 }, location: { protocol: 'https:', search }, URL,
      crypto: globalThis.crypto, localStorage: mkStore(local), sessionStorage: mkStore(session),
      document: { referrer: '', readyState: 'complete', visibilityState: 'visible', querySelector: () => ({ id: 'tab-home' }), addEventListener() {} },
      fetch: (u, o) => { sent.push(JSON.parse(o.body)); return Promise.resolve({}); },
      setInterval: (f) => timers.push(f), setTimeout() {}, Date: { now: () => t },
    };
    sandbox.window = { addEventListener() {}, localStorage: sandbox.localStorage, sessionStorage: sandbox.sessionStorage };
    vm.runInNewContext(code, sandbox);
    for (let i = 0; i < 20; i++) { t += 5000; timers[0](); }       // 100 sn ekranda
    return sent;
  }
  let sent = run('?ad=MELİH');
  assert.equal(sent.length, 1, 'tek bir temizlik sinyali gitmeli');
  assert.deepEqual([sent[0].nick, sent[0].dt], ['MELİH', 0]);
  assert.equal(local.cm_self, '1');
  sent = run('');                                                    // ayni cihaz tekrar acildi: hic istek yok
  assert.equal(sent.length, 0, 'Melih cihazi bir daha hic istek atmamali');
  // ismi baska bir sey yaparsa normal sayilir ve tekrar gonderilir
  local.cm_ad = 'Azra';
  sent = run('');
  assert.ok(sent.length > 1 && sent.every((x) => x.nick === 'Azra'));
  assert.equal(local.cm_self, '0');
  ok('tarayici: Melih ise tek temizlik sinyali sonra sessiz; isim degisirse normal calisir');
}

console.log('TUM TESTLER GECTI:', n);
fs.rmSync(tmp, { recursive: true, force: true });
