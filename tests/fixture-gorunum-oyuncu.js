/* Çizgi Masası · gorunum-oyuncu.js — oyuncu sayfası görünümü. Klasik betik (global kapsam); index.html'deki sırayla yüklenir. */
const SEGS=[['G','Maç'],['Q1','Q1'],['Q2','Q2'],['Q3','Q3'],['Q4','Q4'],['H1','1. yarı'],['H2','2. yarı']],SEGQ={Q1:[1],Q2:[2],Q3:[3],Q4:[4],H1:[1,2],H2:[3,4]};
function segOf(g){if(S.seg==='G')return g;if(!PERI||g.hist)return null;const e=PERI[S.pid+'|'+g.ds],c=PERI._c;if(!e)return null;const o={...g,min:0,pts:0,reb:0,ast:0,stl:0,blk:0,fg3m:0,fg3a:0,tov:0,pot:null,rc:null,rcon:null,runc:null,rdef:null};let any=false;for(const q of SEGQ[S.seg]){const r=e[q];if(!r)continue;any=true;for(const k of ['min','pts','reb','ast','stl','blk','fg3m','fg3a'])o[k]+=r[c[k]]??0}o.min=Math.round(o.min*10)/10;return any?o:null}
function poolAll(){return (HIST[S.pid]||[]).concat(byP[S.pid]||[])}
function segCur(){return (byP[S.pid]||[]).map(segOf).filter(Boolean)}
function curSample(range){const r=range??S.range;let all=r==='h2h'||r==='20'?poolAll():r==='ls'?(HIST[S.pid]||[]):byP[S.pid]||[];all=all.map(segOf).filter(Boolean);let outDates=null;if(S.outs.length){const h=new Set();S.outs.forEach(id=>{(byP[id]||[]).forEach(x=>h.add(x.ds));(HIST[id]||[]).forEach(x=>h.add(x.ds))});outDates=new Set(all.filter(x=>h.has(x.ds)||x.t!==P[S.pid].team).map(x=>x.ds))}return filterGames(all,{range:r==='ls'?'all':r,role:S.role,loc:S.loc,minM:S.minM,outDates,opp:S.opp})}
function renderSegs(){$('segs').innerHTML=SEGS.map(([k,l])=>`<button class="seg-b" data-seg="${k}" aria-pressed="${S.seg===k}" ${k!=='G'&&!PERI?'disabled title="Çeyrek verisi henüz yüklenmedi"':''}>${l}</button>`).join('')}
function renderSummary(mk,line){const rows=[['3','L3'],['5','L5'],['10','L10'],['all','Sezon'],['ls',histSeason||'Geçen sezon'],['h2h',`${S.opp} ile`]],mks=Object.keys(MK);$('summary').innerHTML=`<table><thead><tr><th class="l">Aralık</th><th>Maç</th><th>Dk</th>${mks.map(m=>`<th class="${m===mk?'sel':''}">${MK[m].label}</th>`).join('')}</tr></thead><tbody>${rows.map(([r,l])=>{const g=curSample(r),n=g.length;const c=m=>n?sum(g,x=>val(x,m))/n:null;return `<tr><td>${esc(l)}</td><td>${n||'–'}</td><td>${n?fmt(sum(g,x=>x.min)/n):'–'}</td>${mks.map(m=>{const v=c(m);return `<td class="${m===mk?'sel '+(v==null?'':v>line?'ok':'ko'):''}">${fmt(v)}</td>`}).join('')}</tr>`}).join('')}</tbody></table>`}
function rmManual(id,mk,n){MAN=MAN.filter(x=>!(x.id===id&&x.mk===mk&&x.n===n));saveMan();applyManual()}
function renderLadder(mk,cur){
  const W=[['5','L5'],['10','L10'],['20','L20'],['all','Sezon'],['ls',histSeason||'Geçen sz.']].map(([r,l])=>[l,curSample(r)]);const l10=W[1][1];if(!l10.length){$('ladder').innerHTML='';return}
  const av=sum(l10,x=>val(x,mk))/l10.length;let lo=Math.max(1,Math.round(av*.5)),hi=Math.round(av*1.4)+1;if(hi-lo>11){lo=Math.max(1,Math.round(av)-7);hi=Math.round(av)+4}
  const e=exp(curSample()),manual=S.seg==='G'?(lines[S.pid]?.[mk]||[]):[];const rows=[];
  for(let n=hi;n>=lo;n--){const line=n-.5,hs=W.map(([,g])=>hitOf(g,mk,line,'over')),l=manual.find(x=>x.n===n),odd=l?.odd??null,h10=hs[1];const ev=odd&&h10.n?h10.p*odd-1:null;rows.push({n,line,hs,odd,ev,model:lineProbs(e.mu,e.phi,line).over})}
  const cand=rows.filter(r=>r.ev!=null&&r.hs[1].n>=5&&r.ev>0).sort((a,b)=>b.ev-a.ev)[0];
  $('ladder').innerHTML=`<h3>Barem merdiveni</h3><p class="note" style="margin:0 0 6px">Her basamağın gerçek hit rate'i. İddaa oranını yazarsan L10'a göre değeri hesaplanır, en değerli basamak işaretlenir. Satıra basınca çizgi o basamağa geçer.</p><div class="tablewrap"><table><thead><tr><th class="l">Barem</th>${W.map(([l])=>`<th>${esc(l)}</th>`).join('')}<th>Model</th><th>Oran</th><th>Gereken</th><th>Değer</th><th></th></tr></thead><tbody>${rows.map(r=>`<tr data-line="${r.line}" class="${r.line===cur?'cur':''} ${r===cand?'best':''}"><td class="l"><b>${r.n}+</b>${r===cand?'<span class="tag-best">EN İYİ</span>':''}</td>${r.hs.map(h=>`<td class="hc ${h.p==null?'':hitCls(h.p)}">${h.p==null?'–':pct(h.p)}<small>${h.n?h.h+'/'+h.n:''}</small></td>`).join('')}<td>${pct(r.model)}</td><td><input class="lodd" data-n="${r.n}" inputmode="decimal" placeholder="oran" value="${r.odd?String(r.odd).replace('.',','):''}" aria-label="${r.n}+ için iddaa oranı"></td><td>${r.odd?pct(1/r.odd):'–'}</td><td class="${r.ev==null?'':r.ev>0?'ok':'ko'}">${r.ev==null?'–':(r.ev>=0?'+':'')+fmt(r.ev*100,0)+'%'}</td><td><button class="addk" data-add="${S.pid}|${mk}|${r.line}|over|${r.odd||''}" aria-label="${r.n}+ kupona ekle">+</button></td></tr>`).join('')}</tbody></table></div>`;
}
// İddaa barem geçmişi: karne belgelerinden (REAL; girişsizlerde karne.json kopyası) seçili oyuncu + bahis türü için, oranı ve baremi olan kayıtlar. Kayıt yoksa kutu gizli. Model/ağ çağrısı yok.
function renderBHist(mk){const el=$('bhist');if(!el)return;el.hidden=true;el.innerHTML='';try{if(!S.pid||!mk||!REAL||!REAL.length||!D||!D.dates)return;
  const seen=new Set(),rows=realRows().filter(r=>String(r.id)===String(S.pid)&&r.mk===mk&&r.odd&&r.n!=null).sort((a,b)=>a.date<b.date?1:a.date>b.date?-1:0).filter(r=>seen.has(r.date)?false:(seen.add(r.date),true)).slice(0,15);
  if(!rows.length)return;const dec=rows.filter(r=>r.res==='hit'||r.res==='miss'),hit=dec.filter(r=>r.res==='hit').length;
  const sum=dec.length>=5?`<p class="note" style="margin:0 0 6px"><b>${dec.length} gecenin ${hit}'${hit===10?'unda':['ında','inde','sinde','ünde','ünde','inde','sında','sinde','inde','unda'][hit%10]}</b> barem tuttu</p>`:'';
  const tag={hit:'<span class="pos">✓ tuttu</span>',miss:'<span class="neg">✗ tutmadı</span>',void:'<span class="note">oynamadı</span>',pending:'<span class="note">bekliyor</span>'};
  el.innerHTML=`<h3>İddaa barem geçmişi</h3>${sum}<div class="tablewrap"><table><thead><tr><th class="l">Gece</th><th>Barem</th><th>Oran</th><th>Sonuç</th><th></th></tr></thead><tbody>${rows.map(r=>`<tr><td class="l">${esc(fmtD(r.date))}</td><td><b>${r.n}+</b></td><td>${Number(r.odd).toFixed(2)}</td><td>${r.real==null?'–':esc(r.real)}</td><td>${tag[r.res]||''}</td></tr>`).join('')}</tbody></table></div>`;el.hidden=false}catch(e){console.error(e)}}
function bhistRefresh(){try{const v=$('view-player');if(v&&!v.hidden&&S.pid)renderBHist(S.mk)}catch(e){}}
function renderH2H(mk){const a=poolAll().filter(x=>x.o===S.opp).slice(-6).reverse(),sel=new Set(MK[mk].c);const cols=[['pts','PTS'],['reb','REB'],['ast','AST'],['fg3m','3PM'],['stl','STL'],['blk','BLK']];$('h2hbox').innerHTML=`<h3>${S.opp} ile son maçlar</h3>`+(a.length?`<div class="tablewrap"><table><thead><tr><th class="l">Tarih</th><th>Dk</th>${cols.map(([k,l])=>`<th class="${sel.has(k)?'sel':''}">${l}</th>`).join('')}<th>${MK[mk].label}</th></tr></thead><tbody>${a.map(g=>`<tr><td>${fmtG(g)}</td><td>${g.min}</td>${cols.map(([k])=>`<td class="${sel.has(k)?'sel':''}">${g[k]}</td>`).join('')}<td class="${val(g,mk)>(S.line??0)?'ok':'ko'}">${val(g,mk)}</td></tr>`).join('')}</tbody></table></div>`:`<p class="note" style="margin:0">Bu rakiple maçı yok${histSeason?'':' (geçen sezon verisi henüz yüklenmedi)'}.</p>`)}
function shortName(n){return String(n).replace(/\s+(Jr\.?|Sr\.?|II|III|IV)$/,'').split(' ').slice(-1)[0]}
function toggleOut(id){id=String(id);S.outs=S.outs.includes(id)?S.outs.filter(x=>x!==id):[...S.outs,id];S.min=null;renderAll()}
function renderFilters(){
  const activeN=(S.role!=='all')+(S.loc!=='all')+(S.minM>0)+S.outs.length;$('fsum').textContent=activeN?`· ${activeN} aktif`:'';
  const p=P[S.pid],base=curSample('all');const mates=Object.values(P).filter(m=>m.team===p.team&&m.id!==p.id&&byP[m.id]&&mpg(m.id)>=14).sort((a,b)=>mpg(b.id)-mpg(a.id));
  const ch=mates.map(m=>{const on=S.outs.includes(String(m.id)),h=new Set(byP[m.id].map(x=>x.d)),n=base.filter(x=>!h.has(x.d)).length;return (n||on)?`<button class="chip-btn" data-mate="${m.id}" aria-pressed="${on}">${esc(shortName(m.name))}<small>${on?'seçili':n+'M'}</small></button>`:''}).join('');
  $('f-outs').innerHTML=ch||'<span class="note">Bu filtrelerde eksik takım arkadaşlı maç yok.</span>';
  {const q=mates.map(m=>{const on=S.outs.includes(String(m.id)),h=new Set(byP[m.id].map(x=>x.d)),n=(byP[S.pid]||[]).filter(x=>!h.has(x.d)).length,ti=injOf(m.name)?.[0]==='OUT';if(!n&&!on)return '';return `<button class="qchip ${on?'on':''} ${ti?'tout':''}" data-mate="${m.id}" aria-pressed="${on}" title="${ti?'Bu gece OUT · ':''}${n} maç onsuz">${esc(shortName(m.name))}<small>${n}M${ti?' · OUT':''}</small></button>`}).join('');
   $('qouts').innerHTML=q?`<span class="lab">Yokken maçlar</span><div class="qrow">${q}${S.outs.length?'<button class="qchip clr" data-qclr="1">Temizle</button>':''}</div>`:'';}
  const tm8=Object.values(P).filter(m=>m.team===p.team&&byP[m.id]&&mpg(m.id)>=8).sort((a,b)=>mpg(b.id)-mpg(a.id));$('f-tout').innerHTML=tm8.map(m=>{const i=injOf(m.name),o=i?.[0]==='OUT';return `<button class="chip-btn tout ${o?'is-out':''}" data-ij="${esc(norm(m.name))}" aria-pressed="${o}">${esc(shortName(m.name))}${m.id===p.id?' (kendisi)':''}<small>${o?'OUT':i?i[0]:fmt(mpg(m.id),0)+'dk'}</small></button>`}).join('');
  const parts=[];if(S.role!=='all')parts.push(S.role==='st'?'ilk 5':'yedek');if(S.loc!=='all')parts.push(S.loc==='h'?'ev':'deplasman');if(S.minM)parts.push(S.minM+'+ dk');S.outs.forEach(id=>parts.push(shortName(P[id]?.name||'')+' yok'));
  $('f-active').innerHTML=parts.length?`<span class="note"><b>${curSample().length} maç:</b> ${esc(parts.join(' + '))}</span><button class="chip-btn" data-clear="1">Filtreleri temizle</button>`:'';
}
function minTrend(g){if(g.length<4)return null;const l3=g.slice(-3),pr=g.slice(0,-3),a=sum(l3,x=>x.min)/3,b=sum(pr,x=>x.min)/pr.length,diff=a-b;return {l3:a,prior:b,diff,tag:diff>=2?'up':diff<=-2?'down':'flat'}}
function renderMinTrend(sample){
  const el=$('mintrend');if(!sample.length){el.innerHTML='';return}
  const t=minTrend(sample),label=t?{up:'Dakikası artıyor',down:'Dakikası düşüyor',flat:'Dakikası sabit'}[t.tag]:'';
  const head=t?`<span class="mt-tag ${t.tag}">${t.tag==='up'?'↑':t.tag==='down'?'↓':'→'} ${label}</span><span class="note">Son 3 maç ${fmt(t.l3)} dk, önceki maçlar ${fmt(t.prior)} dk</span>${t.tag==='flat'?'':`<button class="chip-btn" data-usemin="${fmt(t.l3)}">Beklenen dakikayı ${fmt(t.l3)} yap</button>`}`:'<span class="note">Trend için en az 4 maç lazım</span>';
  el.innerHTML=`<div class="mt-head"><span class="lab">Dakika</span>${head}</div><div class="mt-strip">${sample.map(g=>`<div class="mt-col" data-tip="${esc(fmtG(g)+' '+g.o+' · '+g.min+' dk')}"><span>${g.min}</span><i style="height:${Math.round(g.min/48*42)}px"></i></div>`).join('')}</div>`;
}
function renderSide(){
  $('days').innerHTML=dayList().map(k=>`<button class="day" data-day="${k}" aria-pressed="${k===S.day}">${esc(dayLabel(k))}</button>`).join('')||'<span class="note">Takvimde maç yok.</span>';
  $('days').onclick=e=>{const b=e.target.closest('[data-day]');if(!b)return;S.day=b.dataset.day;S.game=slate.find(s=>dayKey(s.ts)===S.day)||null;renderSide()};
  const gs=slate.filter(s=>dayKey(s.ts)===S.day);
  $('games').innerHTML=gs.map((g,i)=>`<button class="game" data-g="${i}" aria-pressed="${S.game&&g.ts===S.game.ts&&g.home===S.game.home}"><span>${g.away} @ ${g.home}</span><span>${tm(g.ts)}</span></button>`).join('');
  $('games').onclick=e=>{const b=e.target.closest('[data-g]');if(!b)return;S.game=gs[Number(b.dataset.g)];renderSide()};
  renderPlist();
}
function renderPlist(){
  let list;
  if(S.game){list=Object.values(P).filter(p=>byP[p.id]&&(p.team===S.game.away||p.team===S.game.home));$('plist-title').textContent=`${S.game.away} @ ${S.game.home}`}
  else{list=[];$('plist-title').textContent='Oyuncular'}
  list.sort((a,b)=>mpg(b.id)-mpg(a.id));
  $('plist').innerHTML=list.map(p=>{const i=injOf(p.name);return `<button class="pl pl2" data-p="${p.id}" aria-current="${p.id===S.pid}" title="${esc(p.name)}">${ib(p)}<span class="pl-t"><span class="pl-nm">${esc(p.name)}</span><small>${p.team} · ${fmt(mpg(p.id),0)} dk${i?` · <span class="st ${i[0]}">${i[0]}</span>`:''}</small></span></button>`}).join('')||'<span class="note">Oyuncu bulunamadı.</span>';
  $('plist').onclick=e=>{const b=e.target.closest('[data-p]');if(b){openPlayer(Number(b.dataset.p));if(innerWidth<=860)$('pname').scrollIntoView({block:'start'})}};
}
function openPlayer(id,o={}){
  S.pid=id;S.line=null;S.odds=null;S.min=null;S.outs=[];S.minM=0;S.seg='G';S.range='all';S.loc='all';S.side='over';if(o.mk)S.mk=o.mk;
  const p=P[id],g=byP[id];const g0=gameOf(p.team);S.opp=g0?(g0.away===p.team?g0.home:g0.away):(g.at(-1)?.o||D.teams[0]);S.pos=posOf(id);S.role=autoRole(g);
  store.set('cm-state',{pid:id,mk:S.mk});
  if(g0&&!(S.game&&(S.game.home===p.team||S.game.away===p.team))){S.game=g0;S.day=dayKey(g0.ts);renderSide()}else renderPlist();renderAll();
}
function renderResults(){
  const sample=curSample(),e=exp(sample),mk=S.mk,line=S.line??0,odds=parseOdds(S.odds);
  $('markets').querySelectorAll('[data-mk]').forEach(b=>{const m=b.dataset.mk,on=m===mk;b.setAttribute('aria-pressed',on);const l=on?line:defaultLine(S.pid,m,sample),hr=hitOf(sample,m,l,on?S.side:'over'),bd=b.querySelector('[data-b]');bd.textContent=hr.p==null?'–':pct(hr.p);bd.className='badge '+hitCls(hr.p)});
  const pr=lineProbs(e.mu,e.phi,line),mlq=S.seg==='G'&&!S.outs.length?mktLine(S.pid,mk):null,mkb=!!(mlq&&mlq.o&&mlq.line===line),base=assess(mkb?mktProb(pr,mlq):pr,S.side,null,e.n),adj=odds&&S.side==='over'?blendP(pr,odds):pr,a=assess(adj,S.side,odds,e.n);
  $('side').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.s===S.side));
  const sideW=S.side==='over'?'Üst':'Alt';let cls='',big,sub;
  if(!odds){big=`En az ${fmt(base.minOdds,2)}`;sub='Oranı yaz, net karar vereyim.'}
  else if(a.tag==='go'){cls='go';big='Oynanır';sub=`Düzeltilmiş şans ${pct(a.w)}, değer +${fmt(a.ev*100,0)}%`}
  else if(a.tag==='thin'){cls='thin';big='Sınırda';sub=`Düzeltilmiş şans ${pct(a.w)}, değer +${fmt(a.ev*100,0)}%. Avantaj çok az.`}
  else{cls='no';big='Geç';sub=`Düzeltilmiş şans ${pct(a.w)}, değer ${fmt(a.ev*100,0)}%`}
  $('verdict').className='verdict '+cls;$('verdict').innerHTML=`<b>${big}</b><span>${esc(sub)}${e.n<5?` · ${e.n} maç, örneklem küçük`:''}</span>`;
  const avg=sample.length?sum(sample,x=>val(x,mk))/sample.length:null,avgMin=sample.length?sum(sample,x=>x.min)/sample.length:null;
  $('headkpis').innerHTML=[[pct(a.w),`${sideW} şansı`,1],[fmt(avg),'Grafik ort.'],[fmt(e.mu),'Beklenti'],[fmt(avgMin),'Ort. dakika']].map(([b,s,h])=>`<div class="hk ${h?'hl':''}"><b>${b}</b><span>${s}</span></div>`).join('');
  if(document.activeElement!==$('minutes'))$('minutes').value=S.min!=null?S.min:fmt(e.mins);
  const g0=gameOf(P[S.pid].team),ev=eventFor(P[S.pid].team);const gi=[];
  if(g0)gi.push(`${g0.home===P[S.pid].team?'Ev':'Deplasman'} · ${S.opp}`);
  if(ev?.total!=null)gi.push(`Toplam ${fmt(ev.total)}`);
  if(ev?.spread!=null&&ev.spread!==0)gi.push(`Favori ${ev.spread<0?ev.home:ev.away} -${fmt(Math.abs(ev.spread))}`);
  const rk=rankFor(S.opp,S.pos,mk);if(rk)gi.push(`${S.opp} ${S.pos}'ye ${MK[mk].label}: ${rk}/30`);
  if(g0){const gp=gamePace(g0);if(gp)gi.push(`Tempo ${fmt(gp.p)} · ${gp.tag}`)}
  {const ml=mktLine(S.pid,mk);if(ml)gi.push(`Piyasa (${ml.bk}): ${ml.line} · Ü ${fmt(ml.o,2)}${ml.u?' / A '+fmt(ml.u,2):''}`)}
  $('gameinfo').innerHTML=gi.map(x=>`<span class="gi">${esc(x)}</span>`).join('');
  renderChart(sample,mk,line,avg);renderMinTrend(sample);renderWins(mk,line);renderOddsChips(mk,line);
  const pushT=pr.push>.005?` · iade ${pct(pr.push)}`:'';
  $('kpis').innerHTML=[[pct(base.w),`${mkb?'Model + piyasa şansı':'Model şansı'}${pushT}`],[odds&&S.side==='over'?pct(a.w):'–','Oranla düzeltilmiş'],[fmt(base.fair,2),'Modele göre adil oran'],[fmt(base.minOdds,2),'Modele göre en az oran']].map(([b,s])=>`<div class="kpi"><b>${b}</b><span>${esc(s)}</span></div>`).join('');
  renderSummary(mk,line);renderLadder(mk,line);renderBHist(mk);renderMatchup(mk);renderH2H(mk);renderTiers(mk,line);renderShots(mk);renderZones(mk);renderHow(sample,e);renderTable(sample,mk);renderPHead();try{renderPCX(sample,e,base,mk,line)}catch(err){console.error(err)}
}
function renderOddsChips(mk,line){
  const a=S.seg==='G'?(lines[S.pid]?.[mk]||[]):[];
  $('oddschips').innerHTML=a.length?a.map(l=>`<button class="oc" data-l="${l.line}" data-o="${l.odd}" aria-pressed="${l.line===line}">${l.n}+<b>${fmt(l.odd,2)}</b></button>`).join(''):'<span class="note">Bu türde kayıtlı barem yok. Çizgi ve oranı yazıp ekleyebilirsin.</span>';
}
function renderMatchup(mk){
  const t=S.opp,pos=S.pos,sel=new Set(MK[mk].c.map(c=>DVK[c]));const d=DVP.t[t]?.[pos];
  if(!d){$('matchup').innerHTML='<p class="note">Bu rakip için veri yok.</p>';return}
  const tile=(lab,key,opt={})=>{const v=d.v[key],r=rankStat(t,pos,key);const cls=opt.neutral?'':rkCls(r);return `<div class="tile ${cls} ${sel.has(key)?'sel':''}"><small>${lab}</small><b>${fmt(v)}${opt.pct?'%':''}</b><i>${rkB(r)}</i></div>`};
  const combo=(lab,m)=>{const v=MK[m].c.reduce((s,c)=>s+d.v[DVK[c]],0),r=rankFor(t,pos,m);return `<div class="tile ${rkCls(r)} ${mk===m?'sel':''}"><small>${lab}</small><b>${fmt(v)}</b><i>${rkB(r)}</i></div>`};
  $('matchup').innerHTML=`<div class="mtitle">${t} savunması: ${pos}'ye verdiği</div>
  <div class="mgroup"><h4>Skor</h4><div class="tiles">${tile('PTS','PTS')}${tile('FG%','FG',{pct:1})}${tile('FT%','FT',{pct:1})}${tile('3PM','3PM')}</div></div>
  <div class="mgroup"><h4>Ribaunt ve oyun kurma</h4><div class="tiles">${tile('REB','REB')}${tile('AST','AST')}${tile('TO','TO',{neutral:1})}${combo('RA','RA')}${combo('SRA','SRA')}</div></div>
  <div class="mgroup"><h4>Savunma</h4><div class="tiles">${tile('STL','STL')}${tile('BLK','BLK')}</div></div>
  <p class="note">48 dakikaya göre. # 30 takım içindeki sıra: 1 en çok veren, 30 en az veren. Yeşil rakip bu alanda zayıf, kırmızı sert.</p>`;
}
function renderHow(sample,e){
  const n=sample.length;const avg=f=>n?sum(sample,f)/n:null;const pg=sample.filter(x=>x.pot!=null),rg=sample.filter(x=>x.rc!=null);const potA=pg.length?sum(pg,x=>x.pot)/pg.length:null,rcA=rg.length?sum(rg,x=>x.rc)/rg.length:null,astA=pg.length?sum(pg,x=>x.ast)/pg.length:null,rebA=rg.length?sum(rg,x=>x.reb)/rg.length:null,a3=avg(x=>x.fg3a),m3=sum(sample,x=>x.fg3m),at3=sum(sample,x=>x.fg3a);
  const dv=e.parts.map(p=>p.dvp.v==null?'':`<div class="row"><span>${DVK[p.c]} rakip etkisi</span><span class="${p.dvp.f>1.005?'pos':p.dvp.f<.995?'neg':''}">${p.dvp.f>=1?'+':''}${fmt((p.dvp.f-1)*100,0)}%</span></div>`).join('');
  const TRL={pts:'rakip savunma verimliliği',reb:'rakibe verilen ribaund',ast:'rakibe verilen asist',fg3m:'rakibe verilen 3\'lük',stl:'rakip top kaybı',blk:'rakip şut denemesi'};
  const tv=e.parts.map(p=>!p.tr||p.tr.v==null?'':`<div class="row"><span>${DVK[p.c]} takım verisi <small>(${TRL[p.c]} ${fmt(p.tr.v,p.c==='pts'?2:1)}, lig ${fmt(p.tr.a,p.c==='pts'?2:1)})</small></span><span class="${p.tr.f>1.005?'pos':p.tr.f<.995?'neg':''}">${p.tr.f>=1?'+':''}${fmt((p.tr.f-1)*100,0)}%</span></div>`).join('');
  const lastNo=n&&sample[n-1].pot==null;$('how').innerHTML=`<h3>Tracking</h3>${lastNo?'<p class="note" style="margin:0 0 4px">Son maçın tracking verisi nba.com\'da henüz yayınlanmadı. Ortalamalar verisi olan maçlardan hesaplanır.</p>':''}
  <div class="row"><span>Potential assists</span><span>${fmt(potA)} · AST'ye dönüş ${potA?pct(astA/potA):'–'} (lig ${pct(lgConv)})</span></div>
  <div class="row"><span>Rebound chances</span><span>${fmt(rcA)} · REB'e dönüş ${rcA?pct(rebA/rcA):'–'}</span></div>
  ${(()=>{const cg=sample.filter(x=>x.rcon!=null),cc=cg.length,cn=sum(cg,x=>x.rcon),un=sum(cg,x=>x.runc),df=sum(cg,x=>x.rdef);if(!cc||cn+un===0)return '';const n2=cc;return `<div class="row"><span>Çekişmeli / serbest REB</span><span>${fmt(cn/n2)} / ${fmt(un/n2)} · çekişmeli ${pct(cn/(cn+un))}${lgContest!=null?` (lig ${pct(lgContest)})`:''}</span></div><div class="row"><span>Arkadaşına bıraktığı şans</span><span>${fmt(df/n2)}</span></div>`})()}
  <div class="row"><span>3PA</span><span>${fmt(a3)} · isabet ${at3?pct(m3/at3):'–'}</span></div>
  <h3 style="margin-top:7px">Tahmin</h3>${dv}${tv}
  <div class="row"><span>Beklenti</span><span><b>${fmt(e.mu)}</b> · ${fmt(e.mins,1)} dk · ${e.n} maç</span></div>`;
}
function renderTable(sample,mk){
  $('tbl-title').textContent=`Maçlar (${sample.length})`;
  const sel=new Set(MK[mk].c);const cols=[['pts','PTS'],['reb','REB'],['ast','AST'],['fg3m','3PM'],['stl','STL'],['blk','BLK']];
  const h=`<tr><th class="l">Tarih</th><th class="l">Rakip</th><th>Dk</th>${cols.map(([k,l])=>`<th class="${sel.has(k)?'sel':''}">${l}</th>`).join('')}<th class="${mk==='RA'?'sel':''}">RA</th><th class="${mk==='SRA'?'sel':''}">SRA</th><th>Pot. AST</th><th>Rib. şansı</th><th>Çekişmeli</th><th>Serbest</th><th>3PA</th><th>Fark</th></tr>`;
  const rows=[...sample].reverse().map(g=>`<tr><td>${fmtG(g)}</td><td class="l">${g.home?'':'@ '}${g.o} ${g.start?'<span class="s5t" title="İlk beşte başladı">ilk 5</span>':''}</td><td>${g.min}</td>${cols.map(([k])=>`<td class="${sel.has(k)?'sel':''}">${g[k]}</td>`).join('')}<td class="${mk==='RA'?'sel':''}">${g.reb+g.ast}</td><td class="${mk==='SRA'?'sel':''}">${g.pts+g.reb+g.ast}</td><td>${g.pot??'–'}</td><td>${g.rc??'–'}</td><td>${g.rcon??'–'}</td><td>${g.runc??'–'}</td><td>${g.fg3a}</td><td>${g.margin>0?'+':''}${g.margin??'–'}</td></tr>`).join('');
  $('table').innerHTML=`<table><thead>${h}</thead><tbody>${rows}</tbody></table>`;
}
// ---- Savunma seviyesine göre
function renderTiers(mk,line){const el=$('tierbox');if(!el)return;const pool=(HIST[S.pid]||[]).concat(byP[S.pid]||[]).slice(-82);const T=[['Zayıf savunma','en çok veren 10 takım',r=>r<=10],['Orta','11-20',r=>r>10&&r<=20],['Güçlü savunma','en az veren 10 takım',r=>r>20]];
  const rows=T.map(([n,s,f])=>{const g=pool.filter(x=>{const r=x.hist?rankHist(x.o,S.pos,mk):rankFor(x.o,S.pos,mk);return r!=null&&f(r)});const h=g.filter(x=>val(x,mk)>line).length;return {n,s,f,g:g.length,v:g.length?sum(g,x=>val(x,mk))/g.length:null,m:g.length?sum(g,x=>x.min)/g.length:null,h}});
  const rk=rankFor(S.opp,S.pos,mk);
  el.innerHTML=`<h3>Rakip savunmasına göre</h3><p class="note" style="margin:0 0 6px">${S.pos} pozisyonunda ${MK[mk].label} savunma sıralamasına göre son ${pool.length} maç (bu ve geçen sezon). Her maç kendi sezonunun savunma sıralamasıyla gruplanır: bu sezon Hashtag verisi, geçen sezon 2025-26 maçlarından hesaplanan sıralama.</p><div class="tablewrap"><table><thead><tr><th class="l">Rakip</th><th>Maç</th><th>Dk</th><th>${MK[mk].label} ort.</th><th>${line+.5}+ hit</th></tr></thead><tbody>${rows.map(r=>`<tr class="${rk!=null&&r.f(rk)?'cur':''}"><td class="l"><b>${r.n}</b> <span class="note">${r.s}${rk!=null&&r.f(rk)?` · bu gece ${S.opp} ${rkB(rk)}`:''}</span></td><td>${r.g||'–'}</td><td>${r.m!=null?fmt(r.m):'–'}</td><td>${fmt(r.v)}</td><td class="${r.g?hitCls(r.h/r.g):''}">${r.g?pct(r.h/r.g)+` <small>${r.h}/${r.g}</small>`:'–'}</td></tr>`).join('')}</tbody></table></div>`}
// ---- Şut hacmi
function renderShots(mk){const el=$('shotbox');if(!el)return;if(!['PTS','3PM','SRA'].includes(mk)){el.innerHTML='';return}
  const all=byP[S.pid]||[];if(all.length<3){el.innerHTML='';return}const hasF=all.some(x=>x.fga!=null);
  const W=[['L3',all.slice(-3)],['L5',all.slice(-5)],['L10',all.slice(-10)],['Sezon',all]];const av=(a,k)=>{const b=a.filter(x=>x[k]!=null);return b.length?sum(b,x=>x[k])/b.length:null};const p3=a=>{const m=sum(a,x=>x.fg3m),t=sum(a,x=>x.fg3a);return t?m/t:null};
  const R=W.map(([l,a])=>({l,fga:av(a,'fga'),fg3a:av(a,'fg3a'),fta:av(a,'fta'),p3:p3(a),pts:av(a,'pts'),min:av(a,'min')}));const L3=R[0],SZ=R[3];const sig=[];
  if(SZ.fg3a>=1.5){const dv=L3.fg3a/SZ.fg3a-1;if(dv>=.15&&L3.p3!=null&&SZ.p3!=null&&L3.p3<SZ.p3-.05)sig.push(['ok',`Son 3 maçta üçlük denemesi %${fmt(dv*100,0)} arttı ama isabeti %${fmt(L3.p3*100,0)}'e düştü (sezon %${fmt(SZ.p3*100,0)}). Hacim yüksek, isabet normale dönerse üçlükler gelir.`]);else if(dv>=.15)sig.push(['ok',`Üçlük denemesi artıyor: son 3 maç ${fmt(L3.fg3a)}, sezon ${fmt(SZ.fg3a)}.`]);else if(dv<=-.2)sig.push(['ko',`Üçlük denemesi düşüyor: son 3 maç ${fmt(L3.fg3a)}, sezon ${fmt(SZ.fg3a)}.`]);else if(L3.p3!=null&&SZ.p3!=null&&L3.p3>SZ.p3+.12)sig.push(['ko',`Son 3 maçta isabeti çok yüksek (%${fmt(L3.p3*100,0)}, sezon %${fmt(SZ.p3*100,0)}). Bu sıcaklık sürmeyebilir.`])}
  if(hasF&&SZ.fga){const dv=(L3.fga+.44*(L3.fta||0))/(SZ.fga+.44*(SZ.fta||0))-1;if(dv>=.12)sig.push(['ok',`Şut hacmi (FGA + serbest atış) son 3 maçta %${fmt(dv*100,0)} yukarıda.`]);else if(dv<=-.15)sig.push(['ko',`Şut hacmi son 3 maçta %${fmt(-dv*100,0)} aşağıda.`])}
  el.innerHTML=`<h3>Şut hacmi</h3><div class="tablewrap"><table><thead><tr><th class="l">Aralık</th><th>Dk</th>${hasF?'<th>FGA</th>':''}<th>3PA</th><th>3P%</th>${hasF?'<th>FTA</th>':''}<th>PTS</th></tr></thead><tbody>${R.map(r=>`<tr><td class="l">${r.l}</td><td>${fmt(r.min)}</td>${hasF?`<td>${fmt(r.fga)}</td>`:''}<td>${fmt(r.fg3a)}</td><td>${r.p3==null?'–':'%'+fmt(r.p3*100,0)}</td>${hasF?`<td>${fmt(r.fta)}</td>`:''}<td>${fmt(r.pts)}</td></tr>`).join('')}</tbody></table></div>${sig.map(([c,t])=>`<div class="warnline ${c==='ko'?'':'okline'}">${esc(t)}</div>`).join('')}${hasF?'':'<p class="note" style="margin:4px 0 0">FGA ve serbest atış verisi akşamki güncellemeyle gelecek.</p>'}`}

// ---- Şut bölgeleri
const ZN=['Pota altı','Boya (pota altı dışı)','Orta mesafe','Sol köşe üçlük','Sağ köşe üçlük','Tepeden üçlük'];
let ZLG=null;
function zoneLeague(){if(ZLG)return ZLG;const T=Object.values(D.zones?.t||{});const a=Array(6).fill(0),m=Array(6).fill(0);for(const r of T)for(let z=0;z<6;z++){a[z]+=r[z];m[z]+=r[6+z]}
  const rk=[];for(let z=0;z<6;z++){const arr=Object.entries(D.zones.t).map(([t,r])=>[t,r[z]?r[6+z]/r[z]:0]).sort((x,y)=>y[1]-x[1]);const o={};arr.forEach(([t],i)=>o[t]=i+1);rk.push(o)}
  return ZLG={pct:a.map((v,z)=>v?m[z]/v:null),rk}}
const ZCOL=['#E5605A','#F08A47','#E8B348','#4C8DF6','#7AA8FF','#3CBF84'];
function renderZones(mk){const el=$('zonebox');if(!el)return;if(!D.zones?.p){el.innerHTML='';return}
  const pz=D.zones.p[String(S.pid)],oz=S.opp?D.zones.t[S.opp]:null;const nm=esc(shortName(P[S.pid]?.name||''));const H3='<h3 class="zh">Şut haritası</h3>';
  if(!pz){el.innerHTML=H3+`<p class="note">${nm} için bu sezon şut bölgesi verisi yok.</p>`;return}
  const fga=pz.slice(0,6),fgm=pz.slice(6),tot=fga.reduce((a,b)=>a+b,0);if(tot<20){el.innerHTML=H3+`<p class="note">${nm} bu sezon henüz ${tot} şut attı, harita için en az 20 şut gerekiyor.</p>`;return}
  const L=zoneLeague(),gp=Math.max(1,(byP[S.pid]||[]).length);let edge=0;
  const rows=ZN.map((n,z)=>{const sh=fga[z]/tot,pp=fga[z]?fgm[z]/fga[z]:null,op=oz&&oz[z]?oz[6+z]/oz[z]:null,rk=oz?L.rk[z][S.opp]:null,d=op!=null&&L.pct[z]!=null?op-L.pct[z]:0;edge+=sh*d;const mkr=op==null?'n':d>=.02?'up':d<=-.02?'dn':'n';return {n,z,sh,pp,op,rk,d,lg:L.pct[z],mkr,pg:fga[z]/gp}});
  const mx=Math.max(...rows.map(r=>r.sh));const tint=r=>`rgba(240,138,71,${(.012+.17*Math.pow(r.sh/mx,1.2)).toFixed(3)})`;const SY={up:'▲',dn:'▼',n:'●'};
  const B=420,cy=B-52.5,a3=`M30,${B} L30,${B-140} A237.5,237.5 0 0 1 470,${B-140} L470,${B}`,ra=`M210,${B} L210,${cy} A40,40 0 0 1 290,${cy} L290,${B}`;
  const lab=(r,x,y,t,anc,noOpp)=>`<g class="zl ${r.mkr}" text-anchor="${anc||'middle'}"><text x="${x}" y="${y}" class="zn">${t}</text><text x="${x}" y="${y+19}" class="zv">${SY[r.mkr]} ${r.pp==null?'–':'%'+fmt(r.pp*100,0)}</text>${oz&&!noOpp?`<text x="${x}" y="${y+35}" class="zo">%${fmt(r.sh*100,0)} şut · ${S.opp} #${r.rk??'–'}</text>`:''}</g>`;
  const fill=(d,r)=>`<path d="${d}" class="cbg"/><path d="${d}" fill="${tint(r)}"/>`;
  const svg=`<svg class="court2" viewBox="0 0 500 ${B}" role="img" aria-label="Şut haritası: bölgelere göre isabet ve rakip savunması">
<rect width="500" height="${B}" class="cbg"/><rect width="500" height="${B}" fill="${tint(rows[5])}"/>${fill(a3+' Z',rows[2])}${fill(`M0,${B-140} H30 V${B} H0 Z`,rows[3])}${fill(`M470,${B-140} H500 V${B} H470 Z`,rows[4])}${fill(`M170,${B-190} H330 V${B} H170 Z`,rows[1])}${fill(ra+' Z',rows[0])}
<g class="cl2"><path d="${a3}"/><rect x="170" y="${B-190}" width="160" height="190"/><path d="${ra}"/><path d="M190,${B-190} A60,60 0 0 1 310,${B-190}"/><path d="M190,${B-190} A60,60 0 0 0 310,${B-190}" stroke-dasharray="5 6"/><line x1="220" y1="${B-40}" x2="280" y2="${B-40}"/><circle cx="250" cy="${cy}" r="7.5"/><line x1="0" y1="${B-.5}" x2="500" y2="${B-.5}"/><rect x=".5" y=".5" width="499" height="${B-1}" rx="10"/></g>
${lab(rows[5],250,42,'ÜÇLÜK · TEPE')}${lab(rows[2],250,148,'ORTA MESAFE')}${lab(rows[1],250,244,'BOYA','middle',1)}${lab(rows[0],250,304,'POTA ALTI','middle',1)}${lab(rows[3],38,304,'SOL KÖŞE','start')}${lab(rows[4],462,304,'SAĞ KÖŞE','end')}</svg>`;
  // donut
  const R=70,C=2*Math.PI*R;let acc=0;const segs=rows.map((r,i)=>{const len=r.sh*C,mid=(acc+len/2)/C*2*Math.PI-Math.PI/2;const s=`<circle cx="100" cy="100" r="${R}" fill="none" stroke="${ZCOL[i]}" stroke-width="30" stroke-dasharray="${Math.max(0,len-2).toFixed(1)} ${C.toFixed(1)}" stroke-dashoffset="${(-acc).toFixed(1)}" transform="rotate(-90 100 100)"/>`+(r.sh>=.07?`<text x="${(100+R*Math.cos(mid)).toFixed(1)}" y="${(104+R*Math.sin(mid)).toFixed(1)}" class="dl">%${fmt(r.sh*100,0)}</text>`:'');acc+=len;return s}).join('');
  const donut=`<svg class="donut" viewBox="0 0 200 200" role="img" aria-label="Şut dağılımı">${segs}<text x="100" y="98" class="dc">${fmt(tot/gp,1)}</text><text x="100" y="116" class="dcs">ŞUT / MAÇ</text></svg>`;
  const sum1=oz?`${S.opp}, ${nm}'in şut attığı bölgelerde lig ortalamasından <b class="${edge>=.01?'pos':edge<=-.01?'neg':''}">${fmt(Math.abs(edge*100),1)} puan ${edge>=0?'daha yüksek':'daha düşük'}</b> isabet izni veriyor.`:'Rakip seçilince bölge savunması da eşleşir.';
  el.innerHTML=`<div class="zg2"><div class="zcard"><div class="zhead"><h3 class="zh">Şut haritası</h3><span class="note">${oz?nm+' vs '+S.opp:nm}</span></div><p class="note zsum">${sum1}</p>${svg}<div class="zleg2"><span class="up">▲ Oyuncu avantajlı</span><span class="n">● Nötr</span><span class="dn">▼ Savunma avantajlı</span></div><p class="note zfoot">Savunma sırasına göre ağırlıklı şut payı · renk koyuluğu oyuncunun o bölgeden şut payı · sıra 1 en kötü savunma</p></div>
  <div class="zcard"><div class="zhead"><h3 class="zh">Şut profili</h3><span class="note">bu sezon · ${gp} maç</span></div><div class="dwrap">${donut}</div>
  <div class="tablewrap"><table class="ztab"><thead><tr><th class="l">Bölge</th><th>Şut/maç</th><th>% şut</th><th>İsabet</th><th>Rakip sırası</th></tr></thead><tbody>${rows.map((r,i)=>`<tr><td class="l"><i class="zdot" style="background:${ZCOL[i]}"></i>${['Pota altı','Boya','Orta mesafe','Sol köşe 3','Sağ köşe 3','Tepeden 3'][i]}</td><td>${fmt(r.pg,1)}</td><td>%${fmt(r.sh*100,0)}</td><td>${r.pp==null?'–':'%'+fmt(r.pp*100,0)}</td><td class="zr ${r.mkr}">${oz?`${{up:'▲',dn:'▼',n:'●'}[r.mkr]} #${r.rk??'–'}`:'–'}</td></tr>`).join('')}</tbody></table></div></div></div>`}
function setPTab(t,noScroll){const el=document.getElementById('pane-'+t);if(!el)return;document.querySelectorAll('#ptabs [data-pt]').forEach(b=>b.setAttribute('aria-selected',b.dataset.pt===t));if(!noScroll){const y=el.getBoundingClientRect().top+scrollY-($('ptabs').offsetHeight+(innerWidth>860?($('phead')?.offsetHeight||0):0)+70);scrollTo({top:y,behavior:'smooth'})}}
function renderPHead(){const p=P[S.pid];if(!p)return;const b=$('ph-badge');b.textContent=p.team;b.style.setProperty('--tc',TC[p.team]||'var(--muted)');b.style.boxShadow=`inset 0 -4px 0 ${TC2[p.team]||'transparent'}`;b.style.color=ibLum(TC[p.team]||'#5A6470')>.62?'#14181D':'#fff';const line=S.line??0,v=$('verdict');
  $('ph-bet').innerHTML=`<span class="pb-mk">${MK[S.mk].label} ${S.side==='over'?(line+.5)+'+':line+' alt'}</span><span class="pb-v ${v.className.replace('verdict','').trim()}">${esc(v.querySelector('b')?.textContent||'')}</span>`;
  const n=$('injbox').querySelectorAll('.warnline').length,a=$('pt-alert');a.hidden=!n;a.textContent=n}

// ---- Oyuncu sayfası (Props.Cash tarzı)
function pcxLum(hex){const h=String(hex||'').replace('#','');if(h.length<6)return .3;const r=parseInt(h.slice(0,2),16)/255,g=parseInt(h.slice(2,4),16)/255,b=parseInt(h.slice(4,6),16)/255;return .2126*r+.7152*g+.0722*b}
function pcxSeasonLbl(r){if(r==='all')return '26/27';if(r==='ls'){const m=String(histSeason||'').match(/(\d{2})(\d{2})?-(\d{2})/);return m?`${String(histSeason).slice(2,4)}/${m[3]}`:'Geçen sz'}return r}
function pcxGrade(p,rk,side){if(p==null)return {g:'–',c:''};let sc=p+(rk==null?0:(side==='over'?(15.5-rk):(rk-15.5))/30*.04);const T=[[.70,'A+'],[.65,'A'],[.61,'A-'],[.58,'B+'],[.55,'B'],[.52,'B-'],[.49,'C+'],[.46,'C'],[.43,'C-'],[.39,'D']];for(const[t,g]of T)if(sc>=t)return {g,c:g[0]==='A'?'g':g[0]==='B'?'g2':g[0]==='C'?'a':'r'};return {g:'F',c:'r'}}
function pcxRing(p,cls,label){const R=34,C=2*Math.PI*R,f=Math.max(0,Math.min(1,p||0));return `<svg viewBox="0 0 84 84" class="pcx-ring ${cls}" aria-hidden="true"><circle cx="42" cy="42" r="${R}" class="trk"/><circle cx="42" cy="42" r="${R}" class="arc" stroke-dasharray="${(C*f).toFixed(1)} ${C.toFixed(1)}" transform="rotate(-90 42 42)"/><text x="42" y="49" text-anchor="middle">${label}</text></svg>`}
const PCXSC={};
function pcxTeamGames(t){if(PCXSC[t])return PCXSC[t];const own={},opp={},oppT={},win={};for(const id in byP)for(const g of byP[id]){if(g.t===t){own[g.ds]=(own[g.ds]||0)+(g.pts||0);oppT[g.ds]=g.o;win[g.ds]=g.win}}
  for(const id in byP)for(const g of byP[id]){if(g.o===t&&oppT[g.ds]===g.t)opp[g.ds]=(opp[g.ds]||0)+(g.pts||0)}
  return PCXSC[t]=Object.keys(own).sort().reverse().map(ds=>({ds,o:oppT[ds],a:own[ds],b:opp[ds]??null,w:!!win[ds]}))}
function renderChart(sample,mk,line,avg){
  const el=$('chart');const H=220;
  if(!sample.length){el.style.minWidth='';el.innerHTML='<div class="note" style="padding:90px 0;text-align:center">Bu filtrede maç yok. Tahmin sezon verisinden geliyor.</div>';return}
  const vals=sample.map(x=>val(x,mk));const att=mk==='3PM'?sample.map(x=>x.fg3a!=null&&x.fg3a!==''?Number(x.fg3a):null):null;const showAtt=att&&att.some(a=>a!=null);const top=Math.max(line,...vals,...(showAtt?att.filter(a=>a!=null):[]),1);const stepRaw=top/4,step=stepRaw<=1?1:stepRaw<=2?2:stepRaw<=5?5:stepRaw<=10?10:20;const axis=Math.ceil(top/step)*step||1;const y=v=>v/axis*H;
  const grids=[];for(let v=0;v<=axis;v+=step)grids.push(`<div class="pcb-gl" style="bottom:${y(v)}px">${Math.abs(y(v)-y(line))<14?'':`<span>${v}</span>`}</div>`);
  const bars=sample.map((g,i)=>{const v=vals[i],cl=g.min===0?'zero':v===line?'push':(S.side==='over'?v>line:v<line)?'hit':'miss';const r=rankFor(g.o,S.pos,mk);const t=`${fmtG(g)} ${g.home?'vs':'@'} ${g.o} · ${g.min} dk${g.start?' · ilk 5':''}<br>PTS ${g.pts} · REB ${g.reb} · AST ${g.ast} · 3PM ${g.fg3m} · STL ${g.stl} · BLK ${g.blk}<br>Pot. AST ${g.pot??'–'} · Rib. şansı ${g.rc??'–'}<br>Maç farkı ${g.margin>0?'+':''}${g.margin??'–'}${r?`<br>Rakip sırası ${r}/30`:''}`;const h=Math.max(4,Math.round(y(v)));
    const a=showAtt?att[i]:null,ah=a!=null&&a>0?Math.round(y(a)):0;return `<button class="pcb ${cl}" data-tip="${esc(t+(a!=null?`<br>Üçlük: ${v}/${a}${a?` (%${Math.round(v/a*100)})`:''}`:''))}" aria-label="${esc(t.replace(/<br>/g,', '))}">${ah?`<span class="pcb-att" style="height:${ah}px"><i>${v}/${a}</i></span>`:''}<span class="pcb-bar" style="height:${h}px"><em class="${h<24?'out':''}">${v}</em></span><span class="pcb-x">${fmtG(g)}<br>${g.home?'':'@'}${g.o}</span></button>`}).join('');
  el.style.minWidth=Math.max(0,sample.length*40+40)+'px';
  el.innerHTML=`<div class="pcb-plot" style="height:${H}px">${grids.join('')}<div class="pcb-line" style="bottom:${y(line)}px"><span>${line}</span></div>${avg!=null?`<div class="pcb-avg" style="bottom:${y(avg)}px"><span>ort ${fmt(avg)}</span></div>`:''}<div class="pcb-bars">${bars}</div></div>${showAtt?'<p class="note pcb-leg"><span class="pcb-legbox"></span> Çerçeve: üçlük denemesi · dolu çubuk: isabet · üstteki rakam isabet/deneme</p>':''}`;
}
function renderWins(mk,line){
  const opts=[['all',pcxSeasonLbl('all')],['ls',pcxSeasonLbl('ls')],['h2h','H2H'],['3','L3'],['5','L5'],['10','L10'],['20','L20']];
  $('wins').innerHTML=opts.map(([r,l])=>{const s=curSample(r),h=hitOf(s,mk,line,S.side);const av=s.length?sum(s,x=>val(x,mk))/s.length:null;return `<button class="pcw ${hitCls(h.p)}" data-r="${r}" aria-pressed="${S.range===r}" title="${h.n?`${h.h}/${h.n} · ort ${fmt(av)}`:'maç yok'}"><small>${l}</small><b>${h.p==null?'–':'%'+Math.round(h.p*100)}</b></button>`}).join('');
}
function renderPCX(sample,e,base,mk,line){
  const p=P[S.pid];if(!p)return;const g0=gameOf(p.team),opp=S.opp,pos=S.pos,side=S.side;
  const b=$('ph-badge');const tc=TC[p.team]||'#5b6670';b.className='pcx-badge pav';b.removeAttribute('style');b.outerHTML=pav(p,'').replace('<span ','<span id="ph-badge" ');
  $('phead').style.setProperty('--tc',tc);try{kkBox(mk)}catch(e){console.error(e)}
  $('psub').textContent=`${p.team} · ${pos}`+(g0?` · ${g0.home===p.team?'vs':'@'} ${g0.home===p.team?g0.away:g0.home} · ${dayLabel(dayKey(g0.ts))} ${tm(g0.ts)}`:' · bu hafta maçı yok');
  const all=(byP[S.pid]||[]).map(segOf).filter(Boolean),l10=all.slice(-10),a10=l10.length?sum(l10,x=>val(x,mk))/l10.length:null,h10=hitOf(l10,mk,line,side),rk=rankFor(opp,pos,mk);
  const up=a10!=null&&(side==='over'?a10>line:a10<line);const hcl=hitCls(h10.p);
  const K=[['L10 ORT.',a10==null?'–':`<i class="${up?'pos':'neg'}">${up?'▲':'▼'}</i> ${fmt(a10)}`],['ÇİZGİ',side==='over'?`${line+.5}+`:`${line} alt`],['BAHİS',`${MK[mk].label} · ${side==='over'?'Üst':'Alt'}`],['HIT RATE',h10.p==null?'–':`<i class="${hcl==='g'?'pos':hcl==='r'?'neg':''}">${hcl==='g'?'▲':hcl==='r'?'▼':'●'}</i> %${Math.round(h10.p*100)}`],['POZ. SIRASI',rk==null?'–':rkB(rk)],['RAKİP',g0?`${g0.home===p.team?'vs':'@'} ${opp} · ${tm(g0.ts)}`:opp?`${opp} (seçili)`:'–']];
  $('pcx-kpis').innerHTML=K.map(([l,v])=>`<div><small>${l}</small><b>${v}</b></div>`).join('');
  const G=pcxGrade(base.w,rk,side);$('pcx-grade').innerHTML=`${pcxRing(base.w,G.c,G.g)}<span>Eşleşme</span><small>Model %${base.w==null?'–':Math.round(base.w*100)}</small>`;
  // insight
  const n=all.length;if(n>=8){const l5=all.slice(-5),pr=all.slice(-30,-5),a=sum(l5,x=>x.min)/5,bm=pr.length?sum(pr,x=>x.min)/pr.length:null;const d=bm==null?0:a-bm;$('pcx-ins').innerHTML=bm==null?'':`<small>İÇGÖRÜ</small>${esc(shortName(p.name))} son 5 maçta <b>${fmt(a)} dk</b> ortalıyor, önceki ${pr.length} maçtaki ${fmt(bm)} dk'dan ${Math.abs(d)<1.5?'pek farklı değil':d>0?'<b class="pos">yüksek</b>':'<b class="neg">düşük</b>'}.`}else $('pcx-ins').innerHTML=n?`<small>İÇGÖRÜ</small>Bu sezon ${n} maç oynadı, trend için örneklem küçük.`:'';
  // matchup hero
  const otc=opp?tcIn(opp,P[S.pid]?.team):'#3a4350',rec=opp?teamRecord(opp):{w:0,l:0},pg=opp?pcxTeamGames(opp).slice(0,4):[];
  $('pcx-mhero').style.setProperty('--oc',otc);
  $('pcx-mhero').innerHTML=opp?`<div class="mh-top"><div><small>EŞLEŞME</small><h3>${opp}</h3><p>${rec.w}-${rec.l} bu sezon${g0?` · ${g0.home===opp?'ev sahibi':'deplasmanda'}`:''}</p></div><span class="mh-badge" style="background:${otc};color:${pcxLum(otc)>.55?'#111':'#fff'}">${opp}</span></div>${pg.length?`<small class="mh-lab">SON MAÇLARI</small><div class="mh-games">${pg.map(x=>`<div class="mh-g"><span>${fmtG({ds:x.ds,d:null,...x})}</span><b>${opp} ${x.a}</b><b>${x.o} ${x.b??'–'}</b><i class="${x.w?'w':'l'}">${x.w?'G':'M'}</i></div>`).join('')}</div>`:''}`:'<p class="note">Rakip seçili değil.</p>';
  // favourability
  const d=DVP.t[opp]?.[pos];const MS=['PTS','REB','AST','3PM','STL','BLK','RA','SRA'];
  const pAvg=all.length?sum(all,x=>val(x,mk))/all.length:null;const oAl=d?MK[mk].c.reduce((s,c)=>s+(d.v[DVK[c]]||0),0):null;
  $('pcx-fav').innerHTML=d?`<h3 class="pcx-h">Eşleşme özeti</h3><div class="fv-vs"><div><span class="pcx-mini" style="background:${tc};color:${pcxLum(tc)>.55?'#111':'#fff'}">${p.team}</span><b>${esc(shortName(p.name))}</b><small>${fmt(pAvg)} ${MK[mk].label}/maç</small></div><em>vs</em><div class="r"><span class="pcx-mini" style="background:${otc};color:${pcxLum(otc)>.55?'#111':'#fff'}">${opp}</span><b>${opp} → ${pos}</b><small>${fmt(oAl)} ${MK[mk].label} veriyor (48 dk)</small></div></div><small class="mh-lab">EŞLEŞME UYGUNLUĞU · ${pos}</small>${MS.map(m=>{const r=rankFor(opp,pos,m);if(r==null)return '';return `<div class="fv-row2 ${m===mk?'on':''}"><span class="fv-k">${MK[m].label}</span><div class="fv-tr"><i class="rkf" style="background:${rkCol(r)};width:${Math.max(6,Math.round((31-r)/30*100))}%"></i></div><span class="fv-w">${rkW(r)}</span>${rkB(r)}</div>`}).join('')}${dvpDrill({opp,po:pos,mk,p})}<div class="fv-lg"><span>#1</span><i class="rkgrad"></i><span>#30</span><span>zayıf savunma → sert savunma</span><span class="note">Çubuk uzunsa rakip bu pozisyona çok veriyor, oyuncu için iyi.</span></div>`:'<h3 class="pcx-h">Eşleşme özeti</h3><p class="note">Bu rakip için savunma verisi yok.</p>';
  // rest
  if(g0&&opp){const k=dayKey(g0.ts),ri=restInfo(opp,k),me=restInfo(p.team,k);let n8=0;for(let i=1;i<=8;i++)if(playedOn(opp,dayAdd(k,-i)))n8++;const gp=gamePace(g0);const lvl=ri?.b2b?1:ri?.rest>=2?4:ri?.rest===1?3:2;
    $('pcx-rest').hidden=false;$('pcx-rest').innerHTML=`<div class="rs-t"><small>RAKİP KONDİSYONU</small><p>${opp} ${ri?.b2b?'<b>dün gece de oynadı (B2B)</b>':ri?.rest!=null?`${ri.rest} gün dinlenip geliyor`:'dinlenme bilgisi yok'}, son 8 günde ${n8} maç oynadı.${me?.b2b?` ${p.team} de B2B'de.`:''}${gp?` Beklenen tempo ${fmt(gp.p)} (${gp.tag}).`:''}</p></div><div class="rs-bat" aria-hidden="true">${[1,2,3,4].map(i=>`<i class="${i<=lvl?'on':''} l${lvl}"></i>`).join('')}</div>`}else{$('pcx-rest').hidden=true}
  // odds
  const ml=mktLine(S.pid,mk),il=S.seg==='G'?lineFor(S.pid,mk):null,ia=S.seg==='G'?(lines[S.pid]?.[mk]||[]):[];
  $('pcx-odds').innerHTML=`<h3 class="pcx-h">Oranlar</h3><table class="pcx-ot"><thead><tr><th class="l">Kaynak</th><th>Çizgi</th><th>Üst</th><th>Alt</th></tr></thead><tbody>${ml?`<tr><td class="l">${esc(ml.bk)}</td><td>${ml.line}</td><td>${fmt(ml.o,2)}</td><td>${ml.u?fmt(ml.u,2):'–'}</td></tr>`:''}${ia.map(l=>`<tr><td class="l">iddaa</td><td>${l.n}+</td><td>${fmt(l.odd,2)}</td><td>–</td></tr>`).join('')}${!ml&&!ia.length?`<tr><td class="l" colspan="4"><span class="note">Bu bahis için kayıtlı oran yok. iddaa oranını çizgi altındaki "Oran" kutusuna yazabilirsin.</span></td></tr>`:''}</tbody></table>${base.fair?`<p class="note" style="margin:6px 0 0">Modele göre adil oran ${fmt(base.fair,2)} · en az ${fmt(base.minOdds,2)}</p>`:''}`;
}
