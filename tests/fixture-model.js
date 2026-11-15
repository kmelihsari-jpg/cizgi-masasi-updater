/* Çizgi Masası · model.js — model: sabitler, expect, olasılık/değer, öneri seçimi (pickScan/pickList/pickSplit), tonightDoc/pickDoc. Klasik betik (global kapsam); index.html'deki sırayla yüklenir. */
/*MODEL-START*/
const MK={PTS:{label:'PTS',c:['pts'],phi:2.2},REB:{label:'REB',c:['reb'],phi:1.3},AST:{label:'AST',c:['ast'],phi:1.4},'3PM':{label:'3PM',c:['fg3m'],phi:1.25},STL:{label:'STL',c:['stl'],phi:1.1},BLK:{label:'BLK',c:['blk'],phi:1.25},RA:{label:'RA',c:['reb','ast'],phi:1.5},SRA:{label:'SRA',c:['pts','reb','ast'],phi:2.6}};
const DVK={pts:'PTS',reb:'REB',ast:'AST',fg3m:'3PM',stl:'STL',blk:'BLK'};
const K_SHRINK=90,DVP_WEIGHT=.5,TRACK_WEIGHT=.25;
// Son maçların ağırlığı: beklenen dakikanın yarısı son 5 maçtan, oranın %30'u son 10 maçtan gelir. 2025-26 sezonunda 65 bin maç-bahis üzerinde test edildi, sezon ortalamasına göre daha isabetli çıktı.
const REC_MIN=.5,REC_RATE=.3;
function sum(a,f){let s=0;for(const x of a){const v=f(x);if(v!=null)s+=v}return s}
function val(g,mk){return MK[mk].c.reduce((s,c)=>s+g[c],0)}
function filterGames(all,f){let g=all.filter(x=>(f.role==='all'||!f.role||x.start==null||(f.role==='st'?x.start:!x.start))&&(f.loc==='all'||!f.loc||(f.loc==='h'?x.home:!x.home))&&(!f.outDates||!f.outDates.has(x.ds??x.d))&&(!f.minM||x.min>=f.minM));if(f.range==='h2h')g=g.filter(x=>x.o===f.opp);else if(f.range&&f.range!=='all')g=g.slice(-Number(f.range));return g}
function dvpFactor(dvp,opp,pos,comp,avgs){const v=dvp?.t?.[opp]?.[pos]?.v?.[DVK[comp]],a=avgs?.[pos]?.[DVK[comp]];if(v==null||!a)return {f:1,v:null,a:null};const f=1+DVP_WEIGHT*(v/a-1);return {f:Math.min(1.25,Math.max(.75,f)),v,a}}
// TeamRankings takım verisi (teamrankings.json): rakip takımın genel savunma/tempo profili, DVP'nin üstüne küçük bir düzeltme. Dosya yoksa f=1.
const TR_WEIGHT=.25,TR_CLAMP=.05,TRSRC={pts:'defensive-efficiency',reb:'opponent-total-rebounds-per-game',ast:'opponent-assists-per-game',fg3m:'opponent-three-pointers-made-per-game',stl:'turnovers-per-game',blk:'field-goals-attempted-per-game'},TRAVG={};
function trVal(team,key,i){const v=TR?.s?.[key]?.t?.[team];return v?v[i??1]:null}
function trAvg(key){if(TRAVG[key]==null){const t=TR?.s?.[key]?.t;const v=t?Object.values(t).map(a=>a[1]).filter(x=>x!=null):[];TRAVG[key]=v.length?v.reduce((a,b)=>a+b,0)/v.length:0}return TRAVG[key]}
function trFactor(opp,comp){const key=TRSRC[comp];if(!TR||!opp||!key)return {f:1};const v=trVal(opp,key),a=trAvg(key);if(v==null||!a)return {f:1};return {f:Math.min(1+TR_CLAMP,Math.max(1-TR_CLAMP,1+TR_WEIGHT*(v/a-1))),v,a}}
function expect(all,sample,mk,opt){
  const minS=sum(sample,x=>x.min),minA=sum(all,x=>x.min)||1;
  const l5=sample.slice(-5),l10=sample.slice(-10),min10=sum(l10,x=>x.min);
  const mins=opt.min??(sample.length?(1-REC_MIN)*minS/sample.length+REC_MIN*sum(l5,x=>x.min)/l5.length:all.length?minA/all.length:0);
  const parts=MK[mk].c.map(c=>{
    const seasonR=sum(all,x=>x[c])/minA;let r=(sum(sample,x=>x[c])+K_SHRINK*seasonR)/(minS+K_SHRINK);const raw=r;if(sample.length>10){const r10=(sum(l10,x=>x[c])+K_SHRINK*seasonR)/(min10+K_SHRINK);r=(1-REC_RATE)*r+REC_RATE*r10}
    if(c==='ast'||c==='reb'){const t=c==='ast'?'pot':'rc';const tk=all.filter(x=>x[t]!=null),ts=sample.filter(x=>x[t]!=null);const trkS=sum(tk,x=>x[t])/(sum(tk,x=>x.min)||1);const trkR=(sum(ts,x=>x[t])+K_SHRINK*trkS)/(sum(ts,x=>x.min)+K_SHRINK);const conv=c==='ast'?opt.lgConv:(sum(tk,x=>x.rc)?sum(tk,x=>x.reb)/sum(tk,x=>x.rc):0);if(trkR&&conv)r=(1-TRACK_WEIGHT)*r+TRACK_WEIGHT*trkR*conv}
    const d=dvpFactor(opt.dvp,opt.opp,opt.pos,c,opt.avgs),tf=trFactor(opt.opp,c);
    return {c,raw,rate:r,dvp:d,tr:tf,mu:r*mins*d.f*tf.f};
  });
  const mu=parts.reduce((s,p)=>s+p.mu,0);
  const vals=sample.map(x=>val(x,mk)),n=vals.length,m=n?vals.reduce((a,b)=>a+b,0)/n:0;
  const obs=n>1&&m>0?vals.reduce((s,v)=>s+(v-m)**2,0)/(n-1)/m:MK[mk].phi;
  const phi=Math.max(1.02,(n*obs+8*MK[mk].phi)/(n+8));
  return {mu,phi,mins,parts,n};
}
function pmf(mu,phi){const out=[];if(mu<=0)return [1];const kmax=Math.ceil(mu+12*Math.sqrt(mu*phi))+12;
  if(phi<=1.02){let p=Math.exp(-mu);out.push(p);for(let k=0;k<kmax;k++){p=p*mu/(k+1);out.push(p)}return out}
  const r=mu/(phi-1),q=1/phi;let lp=r*Math.log(q);let p=Math.exp(lp);out.push(p);for(let k=0;k<kmax;k++){p=p*(k+r)/(k+1)*(1-q);out.push(p)}return out}
function lineProbs(mu,phi,line){const d=pmf(mu,phi);let over=0,push=0,under=0;d.forEach((p,k)=>{if(k>line)over+=p;else if(k===line)push+=p;else under+=p});const t=over+push+under||1;return {over:over/t,push:push/t,under:under/t}}
function parseOdds(s){if(s==null)return null;const t=String(s).trim().replace(',','.');if(!t)return null;if(/^[+-]\d{3,}$/.test(t)){const a=Number(t);return a>0?1+a/100:1+100/-a}const n=Number(t);return n>1?n:null}
function assess(probs,side,odds,n){const w=side==='over'?probs.over:probs.under,l=side==='over'?probs.under:probs.over;const fair=w>0?(w+l)/w:Infinity;const pad=n<5?1.1:n<10?1.07:1.05;const minOdds=fair*pad;const out={w,l,push:probs.push,fair,minOdds};if(odds){out.ev=w*(odds-1)-l;out.tag=out.ev>=.05?'go':out.ev>=0?'thin':'no'}return out}
// Oran bilgisini de hesaba katar. Geriye dönük testte modelin %60 üstü tahminleri fazla iyimser çıktı, o yüzden yarı yarıya karıştırılır. 1.19 iddaa'nın çift taraflı marketlerindeki payıdır.
const MARKET_MARGIN=1.19;function blendP(pr,odd){const o=.5*pr.over+.5*(1/odd)/MARKET_MARGIN;return {over:o,push:pr.push,under:Math.max(0,1-o-pr.push)}}
// Çizgi piyasadan (DraftKings/FanDuel) geliyorsa model yüzdesi piyasanın oranından çıkan yüzdeyle yarı yarıya karıştırılır. Model piyasadan çok ayrıştığında genelde piyasa haklıdır.
function mktProb(pr,ml){if(!ml||!ml.o)return pr;const a=1/ml.o,b=ml.u?1/ml.u:null,pi=b?a/(a+b):a/1.05;const o=.5*pr.over+.5*pi;return {over:o,push:pr.push,under:Math.max(0,1-o-pr.push)}}
function guessPos(np,g){const m=sum(g,x=>x.min)||1,r36=sum(g,x=>x.reb)/m*36,a36=sum(g,x=>x.ast)/m*36;const p=np||'';if(p==='C'||p==='C-F')return 'C';if(p==='F-C')return 'PF';if(p==='G')return a36>=5.5?'PG':'SG';if(p==='G-F')return 'SG';if(p==='F-G')return 'SF';if(p==='F')return r36>=7.5?'PF':'SF';return 'SF'}
let D,DVP,ODDS,INJ,byP={},P={},byName={},AVG={},lgConv=.5,teamDates={},slate=[],lines={},evByHome={},RANK={};
const ETZ='America/New_York';
function dayKey(ts){return new Date(ts).toLocaleDateString('en-CA',{timeZone:ETZ})}
function dayList(){return [...new Set(slate.map(s=>dayKey(s.ts)))]}
function mpg(id){const g=byP[id]||[];return g.length?sum(g,x=>x.min)/g.length:0}
function eventFor(team){const g=gameOf(team);if(!g)return null;return (ODDS?.events||[]).find(e=>e.home===g.home&&Math.abs(e.d*1000-g.ts)<6*3600e3)||null}
// Rakibin bir pozisyona verdiği değerin 30 takım içindeki sırası: 1 en çok veren, 30 en az veren.
function rankFor(team,pos,mk){const key=pos+'|'+mk;if(!RANK[key]){const comps=MK[mk].c.map(c=>DVK[c]);const arr=Object.keys(DVP.t).map(t=>[t,comps.reduce((s,k)=>s+(DVP.t[t]?.[pos]?.v?.[k]??0),0)]).sort((a,b)=>b[1]-a[1]);RANK[key]={};arr.forEach(([t],i)=>RANK[key][t]=i+1)}return RANK[key][team]??null}
function rankStat(team,pos,stat){const key='s|'+pos+'|'+stat;if(!RANK[key]){const arr=Object.keys(DVP.t).map(t=>[t,DVP.t[t]?.[pos]?.v?.[stat]??0]).sort((a,b)=>b[1]-a[1]);RANK[key]={};arr.forEach(([t],i)=>RANK[key][t]=i+1)}return RANK[key][team]??null}
function lineFor(id,mk){const a=lines[id]?.[mk];if(a?.length)return a.slice().sort((x,y)=>Math.abs(x.odd-1.85)-Math.abs(y.odd-1.85))[0];return null}
const BKN={draftkings:'DraftKings',fanduel:'FanDuel'};
function mktLine(id,mk){const m=D.mkt?.[String(id)]?.[mk];if(!m||!D.mktAt||Date.now()-Date.parse(D.mktAt)>30*3600e3)return null;return {line:m[0],o:m[1],u:m[2],bk:BKN[m[3]]||m[3]}}
function defaultLine(id,mk,sample){const l=S.seg==='G'?lineFor(id,mk):null;if(l)return l.line;const ml=S.seg==='G'?mktLine(id,mk):null;if(ml)return ml.line;const g=sample?.length?sample:byP[id]||[];const avg=g.length?sum(g,x=>val(x,mk))/g.length:.5;return Math.max(.5,Math.floor(avg)+.5)}
function autoRole(g){const last=g.slice(-3);return last.length===3&&last.every(x=>x.start)&&g.some(x=>!x.start)?'st':'all'}
function exp(sample,mk){mk=mk||S.mk;const e=expect(segCur().length?segCur():byP[S.pid],sample,mk,{min:S.min,opp:S.opp,pos:S.pos,dvp:DVP,avgs:AVG,lgConv});return S.outs.length||S.seg!=='G'?e:adjE(e,P[S.pid],mk)}
function hitOf(sample,mk,line,side){const v=sample.map(x=>val(x,mk));const h=v.filter(x=>side==='over'?x>line:x<line).length;return {h,n:v.length,p:v.length?h/v.length:null}}
function scanRows(){
  const out=[];for(const id in lines){const p=P[id],all=byP[id];if(!p||!all)continue;const pos=posOf(id),role=autoRole(all),sample=filterGames(all,{role});const g=gameOf(p.team);if(!g)continue;const opp=g.away===p.team?g.home:g.away;
    for(const mk in lines[id])for(const l of lines[id][mk]){const e=adjE(expect(all,sample,mk,{opp,pos,dvp:DVP,avgs:AVG,lgConv}),p,mk);const pr=lineProbs(e.mu,e.phi,l.line),a=assess(blendP(pr,l.odd),'over',l.odd,e.n);a.model=pr.over;const l10=all.slice(-10).filter(x=>role==='all'||x.start);const hr=hitOf(l10,mk,l.line,'over');out.push({id:Number(id),p,mk,l,opp,pos,role,n:e.n,mins:e.mins,mu:e.mu,a,hr,pr,adj:e.adj,g,rk:rankFor(opp,pos,mk),inj:injOf(p.name),mis:missedStreak(p),ev:l.ev,big:l.ev?.spread!=null&&Math.abs(l.ev.spread)>=10})}}
  return out;
}
function cheatRows(day,pos,mk){
  const out=[];for(const g of slate.filter(s=>dayKey(s.ts)===day))for(const[team,opp]of[[g.away,g.home],[g.home,g.away]])for(const p of Object.values(P)){
    if(p.team!==team||!byP[p.id]||byP[p.id].length<2||mpg(p.id)<18)continue;const inj=injOf(p.name);if(inj?.[0]==='OUT'||missedStreak(p)>=2)continue;const ELIG={G:['PG','SG'],'G-F':['SG','SF'],'F-G':['SF','SG'],F:['SF','PF'],'F-C':['PF','C'],'C-F':['C','PF'],C:['C']};const po=pos&&!posOv[p.id]&&(ELIG[p.np]||[]).includes(pos)?pos:posOf(p.id);if(pos&&po!==pos)continue;
    const all=byP[p.id],avgOf=a=>a.length?sum(a,x=>val(x,mk))/a.length:null,l10=avgOf(all.slice(-10)),l5=avgOf(all.slice(-5)),h2Pool=(HIST[p.id]||[]).concat(all).filter(x=>x.o===opp),h2=avgOf(h2Pool);const il=lineFor(p.id,mk),line=il?il.line:Math.max(.5,Math.floor(avgOf(all))+.5);const MINL={PTS:8,REB:3,AST:2,'3PM':1,STL:1,BLK:1,RA:5,SRA:12};if(!il&&line<MINL[mk])continue;const rk=rankFor(opp,po,mk);
    out.push({p,opp,po,l10,l5,h2,h2n:h2Pool.length,line,il,rk,inj,trend:minTrend(all),hot:rk!=null&&rk<=10&&l10>line&&l5>line,edge:(l10-line)/Math.max(line,1)})}
  return out.sort((a,b)=>(a.rk??99)-(b.rk??99)||b.edge-a.edge)}
// pickScan: eski pickList döngüsü. "no" etiketli öneriler elenmek yerine c.no=true ile işaretlenir (pickList onları yine eler).
function pickScan(day){
  const out=[];for(const g of slate.filter(s=>dayKey(s.ts)===day))for(const[team,opp]of[[g.away,g.home],[g.home,g.away]])for(const p of Object.values(P)){
    if(p.team!==team||!byP[p.id]||byP[p.id].length<5||mpg(p.id)<22)continue;const inj=injOf(p.name);if(noBet(inj)||missedStreak(p)>=1)continue;
    const all=byP[p.id],po=posOf(p.id),role=autoRole(all),sample=filterGames(all,{role});let best=null,bestBet=null,bestNo=null;
    for(const mk of Object.keys(MK)){const MINL={PTS:8,REB:3,AST:2,'3PM':1,STL:1,BLK:1,RA:5,SRA:12};const il=lineFor(p.id,mk),ml=il?null:mktLine(p.id,mk),seasonAvg=sum(sample,x=>val(x,mk))/(sample.length||1),line=il?il.line:ml?ml.line:Math.max(.5,Math.floor(seasonAvg)+.5);if(!il&&!ml&&line<MINL[mk])continue;
      const rk=rankFor(opp,po,mk);if(rk==null||rk>10)continue;const l10=all.slice(-10),l5=all.slice(-5),h10=hitOf(l10,mk,line,'over');const a10=sum(l10,x=>val(x,mk))/l10.length,a5=sum(l5,x=>val(x,mk))/l5.length;if(a10<=line||a5<=line||h10.p<.6)continue;
      const e=adjE(expect(all,sample,mk,{opp,pos:po,dvp:DVP,avgs:AVG,lgConv}),p,mk);if(e.mu<=line)continue;const pr=mktProb(lineProbs(e.mu,e.phi,line),ml);let a=null;if(il){a=assess(blendP(pr,il.odd),'over',il.odd,e.n)}
      const tr=minTrend(all);const ri=restInfo(team,day),gp=gamePace(g);const score=(e.mu-line)/Math.sqrt(e.mu*e.phi)+(11-rk)*.035+h10.p*.6+(tr?.tag==='up'?.2:tr?.tag==='down'?-.2:0)+(a?.tag==='go'?.5:0)+(ri?.b2b?-.15:0)+(gp&&['PTS','REB','AST','RA','SRA'].includes(mk)?Math.max(-.15,Math.min(.15,gp.d*.04)):0);const c={p,mk,opp,po,line,il,ml,rk,a,mu:e.mu,model:pr.over,h10,a10,a5,tr,inj,score,g,adj:e.adj,ri,gp,pr,en:e.n};if(a&&a.tag==='no'){c.no=true;if(!bestNo||score>bestNo.score)bestNo=c;continue}if(il&&(!bestBet||score>bestBet.score))bestBet=c;if(!best||score>best.score)best=c}
    if(best){best.old=true;out.push(best)}if(bestBet&&bestBet!==best){bestBet.extra=true;out.push(bestBet)}if(!best&&bestNo)out.push(bestNo)}
  return out.sort((x,y)=>y.score-x.score)}
// pickList: eskisiyle aynı sonuç (sadece "no" olmayanlar, oyuncu başına en iyi). picks.js bunu kullanır, davranışı değişmez.
function pickList(day){return pickScan(day).filter(c=>c.old)}
// Kasa'nın başladığı gece. Bundan önceki karne belgeleri "eski kayıt, oransız" sayılır (Tribün'e taşınır, birim hesabına girmez).
const MILAT='2026-11-10';
// Kasa için gereken en düşük iddaa oranı: assess'in "go" etiketine çıktığı (beklenen getiri %5+) ilk oran, 0.01 adımla. (13 Kasım'a kadar ev>=0 eşiğiydi.)
function needOdds(c){if(!c.il||!c.pr)return null;for(let o=Math.round(c.il.odd*100)+1;o<=1000;o++){const x=o/100;if(assess(blendP(c.pr,x),'over',x,c.en).tag==='go')return x}return null}
// ---- Kasa (13 Kasım): adaylar o gecenin bütün iddaa baremleri (scanRows).
// Şart: değer etiketi "go" (beklenen getiri %5+), oyuncu OUT/D/Q değil (noBet), son maçı kaçırmamış, en az 5 maç ve 22 dk ortalama,
// destek sinyallerinden (rakip ilk 10 · L10 isabet %60+ · L10 ortalaması çizginin üstünde) en az biri. Oyuncu başına tek bahis (en yüksek getiri). Sabit günlük sınır yok.
// Sıra: beklenen getiri, eşitlikte destek sayısı (sonra id/bahis/çizgi; açılış sırasından bağımsız).
const KASA_SUP={rk:'rakip ilk 10',h10:'L10 isabet %60+',a10:'L10 ort. çizgi üstü'};
// Etiketler: 'saglam' (oran 1.50–1.75, ham model >=%70, %25 iddaa karışımlı olasılık >= 1/oran+0.03, >=2 destek) ve 'deger' (assess "go", >=1 destek). Sabit günlük sınır yok.
const SAG={lo:1.5,hi:1.75,raw:.70,m:.03,w:.25,sup:2},GAP_MAX=.15;
function p25Of(raw,odd){return (1-SAG.w)*raw+SAG.w*((1/odd)/MARKET_MARGIN)}
// Değer seçiminde model–iddaa farkı >%15 ise veri hatası kontrolü: boş liste = temiz, doluysa Kâğıt üstüne düşer (why 'kontrol').
function dataChk(r,p,all){const w=[];try{if(typeof LIVE!=='undefined'&&(!LIVE||!LIVE.ts||Date.now()-LIVE.ts>6*3600e3))w.push('sakatlık listesi 6 saatten eski');
  const l5=all.slice(-5);if(r.mins!=null&&l5.length){const m5=sum(l5,x=>x.min)/l5.length;if(m5>0&&Math.abs(r.mins-m5)/m5>.15)w.push(`dakika tahmini ${fmt(r.mins,0)} (L5 ${fmt(m5,0)})`)}
  for(const m of Object.values(P)){if(m.id===p.id||(m.team!==p.team&&m.team!==r.opp)||!byP[m.id]||mpg(m.id)<20||missedStreak(m)<1||injOf(m.name))continue;w.push(`${m.name} son maçı kaçırmış, sakatlık kaydı yok`);break}
  if(r.adj&&r.adj.f>=1.15&&r.adj.n<4)w.push('sakatlık düzeltmesi az örnekle');if(r.n<8)w.push(`örnek az (${r.n})`)}catch(e){}return w}
function kasaCand(r,day,now){const p=r.p,g=r.g,all=byP[p.id];if(!g||dayKey(g.ts)!==day||(now!=null&&g.ts<=now))return null;if(!all||all.length<5||mpg(p.id)<22)return null;
  const inj=injOf(p.name);if(noBet(inj)||missedStreak(p)>=1)return null;const mk=r.mk,line=r.l.line,odd=r.l.odd,l10=all.slice(-10),l5=all.slice(-5),h10=hitOf(l10,mk,line,'over'),a10=sum(l10,x=>val(x,mk))/l10.length,a5=sum(l5,x=>val(x,mk))/l5.length;
  const sup=[];if(r.rk!=null&&r.rk<=10)sup.push('rk');if(h10.p>=.6)sup.push('h10');if(a10>line)sup.push('a10');if(!sup.length)return null;
  const raw=r.pr.over,p25=p25Of(raw,odd),sag=odd>=SAG.lo&&odd<=SAG.hi&&raw>=SAG.raw&&p25>=1/odd+SAG.m&&sup.length>=SAG.sup,deg=r.a.tag==='go';if(!sag&&!deg)return null;
  const tag=sag?'saglam':'deger',ev=sag?p25*(odd-1)-(1-p25):r.a.ev,gap=raw-(1/odd);const chk=!sag&&gap>GAP_MAX?dataChk(r,p,all):[];
  const tr=minTrend(all),ri=restInfo(p.team,day),gp=gamePace(g);const score=(r.mu-line)/Math.sqrt(r.mu*Math.max(1.02,MK[mk].phi))+(r.rk!=null?(11-Math.min(r.rk,30))*.035:0)+h10.p*.6+.5;
  return {p,mk,opp:r.opp,po:r.pos,line,il:r.l,ml:null,rk:r.rk,a:r.a,mu:r.mu,model:r.a.model,h10,a10,a5,tr,inj,score,g,adj:r.adj,ri,gp,pr:r.pr,en:r.n,sup,kasa:true,tag,ev,pm:p25,gap,chk}}
function kasaAll(day,now){const cmp=(x,y)=>y.ev-x.ev||y.sup.length-x.sup.length||x.p.id-y.p.id||(x.mk<y.mk?-1:x.mk>y.mk?1:0)||x.line-y.line,best=new Map(),flag=new Map();
  for(const r of scanRows()){const c=kasaCand(r,day,now);if(!c)continue;const m=c.chk.length?flag:best,o=m.get(c.p.id);if(!o||cmp(c,o)<0)m.set(c.p.id,c)}
  for(const id of flag.keys())if(best.has(id))flag.delete(id);
  return {pass:[...best.values()].sort(cmp),flag:[...flag.values()].sort(cmp)}}
function kasaList(day,now){return kasaAll(day,now).pass}
// Kasa/Kâğıt üstü ayrımı (sayfa ve picks.js → tonightDoc aynı fonksiyonu kullanır). bets = kasaList. others = eski yöntemin (pickScan: rakip ilk 10, L10/L5 ort. çizgi üstü, L10 %60+, oyuncu başına en iyi) seçip Kasa'ya girmeyenler:
// why 'value' (oranda %5 getiri yok, need = gereken en düşük oran), 'nobarem' (iddaa baremi yok), 'limit' (değerli ama Kasa dolu), 'player' (oyuncunun başka bahsi Kasa'da).
function pickSplit(day,now){const ka=kasaAll(day,now),bets=ka.pass,inK=new Set(bets.map(c=>c.p.id+'|'+c.mk)),kp=new Set(bets.map(c=>c.p.id)),fl=new Map(ka.flag.map(c=>[c.p.id+'|'+c.mk,c]));
  const all=pickScan(day).filter(c=>now==null||c.g.ts>now),old=[],seen=new Set();
  for(const c of all)if(c.il&&!c.no){old.push(c);seen.add(c.p.id)}
  for(const c of all){if(seen.has(c.p.id))continue;seen.add(c.p.id);old.push(c)}
  const others=[],done=new Set();for(const c of old){const k=c.p.id+'|'+c.mk;if(inK.has(k))continue;const f=fl.get(k);if(f){others.push(Object.assign(f,{why:'kontrol'}));done.add(k);continue}if(!c.il)c.why='nobarem';else if(c.a?.tag!=='go'){c.why='value';c.need=needOdds(c)}else c.why=kp.has(c.p.id)?'player':'filter';others.push(c)}
  for(const [k,f] of fl)if(!done.has(k)&&!kp.has(f.p.id)){f.why='kontrol';others.push(f)}
  return {bets,others}}
// Tek bir (oyuncu, bahis) için iddaa baremindeki değerlendirme (seçim filtreleri uygulanmadan). Barem yoksa null. a.tag==='no' ise c.why='value', c.need=gereken en düşük oran.
function pickEval(id,mk){const p=P[id],all=byP[id];if(!p||!all||!MK[mk])return null;const il=lineFor(id,mk),g=gameOf(p.team);if(!il||!g)return null;
  const opp=g.home===p.team?g.away:g.home,po=posOf(id),sample=filterGames(all,{role:autoRole(all)}),line=il.line,e=adjE(expect(all,sample,mk,{opp,pos:po,dvp:DVP,avgs:AVG,lgConv}),p,mk),pr=mktProb(lineProbs(e.mu,e.phi,line),null),a=assess(blendP(pr,il.odd),'over',il.odd,e.n);
  const c={p,g,mk,opp,po,line,il,ml:null,rk:rankFor(opp,po,mk),a,mu:e.mu,model:pr.over,pr,en:e.n};if(a.tag==='no'){c.why='value';c.need=needOdds(c)}return c}
function pickWhy(c){const parts=[];const key=MK[c.mk].c.map(k=>DVK[k]);const v=key.reduce((s,k)=>s+(DVP.t[c.opp]?.[c.po]?.v?.[k]??0),0);parts.push(`${c.opp}, ${c.po}'ye ${MK[c.mk].label} vermede ${c.rk}. sırada (48 dakikada ${fmt(v)}).`);parts.push(`Son ${c.h10.n} maçın ${c.h10.h} tanesinde bu çizgiyi geçti.`);if(c.tr?.tag==='up')parts.push(`Dakikası artıyor: son 3 maç ${fmt(c.tr.l3,0)} dk.`);if(c.adj&&c.adj.f>1.005)parts.push(`${c.adj.outs.map(m=>shortName(m.name)).join(', ')} yok: beklenti +%${fmt((c.adj.f-1)*100,0)}${c.adj.n?` (o yokken ${c.adj.n} maç)`:''}.`);if(c.gp&&c.gp.tag!=='orta')parts.push(`Maç temposu ${c.gp.tag} (${fmt(c.gp.p)}).`);if(c.ri?.b2b)parts.push('Dikkat: takımı dün gece de oynadı (B2B).');{const tf=MK[c.mk].c.map(k=>trFactor(c.opp,k).f),tm=tf.reduce((a,b)=>a+b,0)/tf.length;if(Math.abs(tm-1)>=.02)parts.push(`${c.opp} takım verisi (TeamRankings) beklentiyi ${tm>1?'+':''}%${fmt((tm-1)*100,0)} değiştiriyor.`)}if(c.inj)parts.push(`Durumu: ${c.inj[0]}.`);return parts.join(' ')}
function pickBase(day,cur){const doc=REAL.find(x=>x.date===day);if(doc?.first?.length)return doc.first;if(doc?.picks?.length)return doc.picks;let b=store.get('cm-pbase');if(!b||b.day!==day){b={day,items:cur};store.set('cm-pbase',b)}return b.items}
// Öneri kartı. tri=true: Diğer öneriler (Tribün) kartı, sebep satırıyla.
function triWhy(c){if(c.il&&c.why==='kontrol')return `iddaa ${fmt(c.il.odd,2)} · model–iddaa farkı büyük, veri kontrolü: ${(c.chk||[]).join('; ')}`;if(c.il&&c.why==='player')return `iddaa ${fmt(c.il.odd,2)} · oyuncunun başka bahsi Kasa'da`;if(c.il&&c.why!=='value')return `iddaa ${fmt(c.il.odd,2)} · modelin form filtresinden geçmedi`;if(c.why==='value'&&c.il)return c.need?`iddaa ${fmt(c.il.odd,2)} · değer için en az ${fmt(c.need,2)}`:`iddaa ${fmt(c.il.odd,2)} · bu oranda değer yok`;return 'iddaa baremi yok'}
// ---- Dinlenme / B2B
let TDS=null;
function teamDS(t){if(!TDS){TDS={};for(const id in byP)for(const g of byP[id])(TDS[g.t]??=new Set()).add(g.ds);for(const id in HIST)for(const g of HIST[id])(TDS[g.t]??=new Set()).add(g.ds)}return TDS[t]||new Set()}
function dayAdd(k,n){const[y,m,d]=k.split('-').map(Number);const t=new Date(Date.UTC(y,m-1,d+n,12));return t.toISOString().slice(0,10)}
function playedOn(t,k){return teamDS(t).has(k)||slate.some(s=>dayKey(s.ts)===k&&(s.home===t||s.away===t))}
function restInfo(t,k){if(!k)return null;const y=dayAdd(k,-1);if(!(D.dates.at(-1)>=y||slate.some(s=>dayKey(s.ts)===y)))return null;const b2b=playedOn(t,dayAdd(k,-1));let n3=0;for(let i=1;i<=3;i++)if(playedOn(t,dayAdd(k,-i)))n3++;let rest=null;for(let i=1;i<=7;i++)if(playedOn(t,dayAdd(k,-i))){rest=i-1;break}return {b2b,three:n3>=2,rest}}
function restTag(t,k){const r=restInfo(t,k);if(!r)return '';if(r.b2b)return '<span class="rtag b2b" title="Takım dün gece de oynadı">B2B</span>';return ''}
function b2bSplit(id,mk){const pool=(HIST[id]||[]).concat(byP[id]||[]);const A=[],B=[];for(const x of pool){(teamDS(x.t).has(dayAdd(x.ds,-1))?A:B).push(x)}const f=a=>a.length?{n:a.length,v:sum(a,x=>val(x,mk))/a.length,m:sum(a,x=>x.min)/a.length}:null;return {b:f(A),r:f(B)}}
// ---- Tempo
function paceOf(t){const p=D.pace?.[t];if(!p)return null;const a=p[0],b=p[1];return a!=null&&b!=null?(a+b)/2:(a??b)}
function lgPace(){const v=Object.keys(D.pace||{}).map(paceOf).filter(x=>x!=null);return v.length?sum(v,x=>x)/v.length:null}
function gamePace(g){const a=paceOf(g.home),b=paceOf(g.away),L=lgPace();if(a==null||b==null||!L)return null;const p=a+b-L;return {p,d:p-L,tag:p-L>=1.8?'hızlı':p-L<=-1.8?'yavaş':'orta'}}
// ---- Geçen sezon savunma sıralaması (history.json'dan hesaplanır)
let HRK=null;
function buildHRank(){const acc={},gm={};for(const id in HIST){if(!P[id])continue;const po=posOf(Number(id));for(const x of HIST[id]){if(!x.o)continue;(gm[x.o]??=new Set()).add(x.ds);const a=((acc[x.o]??={})[po]??={pts:0,reb:0,ast:0,stl:0,blk:0,fg3m:0});for(const k in a)a[k]+=x[k]||0}}
  HRK={};const teams=Object.keys(acc);for(const po of ['PG','SG','SF','PF','C'])for(const mk of Object.keys(MK)){const arr=teams.map(t=>[t,MK[mk].c.reduce((s,c)=>s+(acc[t][po]?.[c]||0),0)/(gm[t].size||1)]).sort((a,b)=>b[1]-a[1]);arr.forEach(([t],i)=>{HRK[t+'|'+po+'|'+mk]=i+1})}}
function rankHist(t,po,mk){if(!HRK){if(!Object.keys(HIST).length)return null;buildHRank()}return HRK[t+'|'+po+'|'+mk]??null}

// ---- Yükselenler (rol değişikliği)
function risers(day){const out=[];const kn=g=>g.pot!=null||g.rc!=null;
  for(const g of slate.filter(s=>dayKey(s.ts)===day))for(const[team,opp]of[[g.away,g.home],[g.home,g.away]])for(const p of Object.values(P)){
    if(p.team!==team)continue;const all=(byP[p.id]||[]).filter(x=>x.t===team);if(all.length<5)continue;const inj=injOf(p.name);if(inj?.[0]==='OUT'||inj?.[0]==='D'||missedStreak(p)>=1)continue;
    const l2=all.slice(-2),pv=all.slice(0,-2);const m2=sum(l2,x=>x.min)/2,mp=sum(pv,x=>x.min)/pv.length;const pk=pv.filter(kn);
    const st2=l2.every(kn)&&l2.every(x=>x.start),stp=pk.length>=3?pk.filter(x=>x.start).length/pk.length:null;
    const startUp=st2&&stp!=null&&stp<=.3,minUp=m2-mp>=7&&m2>=20;if(!startUp&&!minUp)continue;
    const av=(a,k)=>sum(a,x=>x[k])/a.length;const outs=freshOuts(p);
    out.push({p,opp,g,m2,mp,startUp,d:m2-mp,s2:{pts:av(l2,'pts'),reb:av(l2,'reb'),ast:av(l2,'ast')},sp:{pts:av(pv,'pts'),reb:av(pv,'reb'),ast:av(pv,'ast')},outs,score:(m2-mp)+(startUp?6:0)})}
  return out.sort((a,b)=>b.score-a.score).slice(0,6)}
// ---- Yeni OUT → öne çıkanlar
function outBoost(day){const res=[],seen=new Set();
  for(const g of slate.filter(s=>dayKey(s.ts)===day))for(const team of[g.away,g.home]){
    if(seen.has(team))continue;seen.add(team);const opp=team===g.away?g.home:g.away;
    const outs=freshOuts({id:-1,team}).sort((a,b)=>mpg(b.id)-mpg(a.id));
    const src=id=>(HIST[id]||[]).concat(byP[id]||[]);
    for(const m of outs){
      const mg=src(m.id).filter(x=>x.t===team),md=new Set(mg.map(x=>x.ds)),span=mg.map(x=>x.ds).sort(),lo=span[0],hi=span.at(-1),rows=[];
      for(const p of Object.values(P)){
        if(p.team!==team||p.id===m.id||!byP[p.id]||mpg(p.id)<10||missedStreak(p)>=2)continue;
        const inj=injOf(p.name);if(inj&&(inj[0]==='OUT'||inj[0]==='D'))continue;
        const pool=src(p.id).filter(x=>x.t===team&&x.ds>=lo&&x.ds<=hi),w=pool.filter(x=>md.has(x.ds)),wo=pool.filter(x=>!md.has(x.ds));
        if(wo.length<2||w.length<3)continue;
        const a=(arr,k)=>sum(arr,x=>x[k])/arr.length,dm=a(wo,'min')-a(w,'min'),dp=a(wo,'pts')-a(w,'pts'),dr=a(wo,'reb')-a(w,'reb'),da=a(wo,'ast')-a(w,'ast');
        if(dm<1.5&&dp<2)continue;
        let bm=null,bf=1;for(const mk of['PTS','REB','AST','3PM']){const f=outAdj(p,mk).f;if(Math.abs(f-1)>Math.abs(bf-1)){bf=f;bm=mk}}
        rows.push({p,inj,n:wo.length,dm,dp,dr,da,bm,bf})}
      rows.sort((x,y)=>(y.dm+y.dp)-(x.dm+x.dp));
      res.push({m,g,team,opp,rows:rows.slice(0,4)})}}
  return res.sort((x,y)=>mpg(y.m.id)-mpg(x.m.id)).slice(0,6)}
// ---- Günün alt önerileri
function underList(day){const out=[];const MKS=['PTS','REB','AST','3PM','RA','SRA'],MINL={PTS:8,REB:3,AST:2,'3PM':1,RA:5,SRA:12};
  for(const g of slate.filter(s=>dayKey(s.ts)===day))for(const[team,opp]of[[g.away,g.home],[g.home,g.away]])for(const p of Object.values(P)){
    if(p.team!==team||!byP[p.id]||byP[p.id].length<5||mpg(p.id)<22)continue;const inj=injOf(p.name);if(noBet(inj)||missedStreak(p)>=1)continue;
    const all=byP[p.id],po=posOf(p.id),role=autoRole(all),sample=filterGames(all,{role});let best=null;
    for(const mk of MKS){const ml=mktLine(p.id,mk),seasonAvg=sum(sample,x=>val(x,mk))/(sample.length||1),line=ml?ml.line:Math.floor(seasonAvg)+.5;if(!ml&&line<MINL[mk])continue;
      const rk=rankFor(opp,po,mk);if(rk==null||rk<21)continue;const l10=all.slice(-10),l5=all.slice(-5),h10=hitOf(l10,mk,line,'under');const a10=sum(l10,x=>val(x,mk))/l10.length,a5=sum(l5,x=>val(x,mk))/l5.length;if(a10>=line||a5>=line||h10.p<.6)continue;
      const e=adjE(expect(all,sample,mk,{opp,pos:po,dvp:DVP,avgs:AVG,lgConv}),p,mk);if(e.mu>=line||(e.adj&&e.adj.f>1.03))continue;const pr=mktProb(lineProbs(e.mu,e.phi,line),ml);
      const tr=minTrend(all),ri=restInfo(team,day),gp=gamePace(g);const score=(line-e.mu)/Math.sqrt(e.mu*e.phi)+(rk-20)*.035+h10.p*.6+(tr?.tag==='down'?.25:tr?.tag==='up'?-.25:0)+(ri?.b2b?.15:0)+(gp?Math.max(-.15,Math.min(.15,-gp.d*.04)):0);
      const c={p,mk,opp,po,line,ml,rk,mu:e.mu,model:pr.under,h10,a10,a5,tr,inj,score,g,ri,gp};if(!best||score>best.score)best=c}
    if(best)out.push(best)}
  return out.sort((x,y)=>y.score-x.score).slice(0,6)}
function underWhy(c){const parts=[`${c.opp}, ${c.po}'ye ${MK[c.mk].label} vermede en cimrilerden (${c.rk}. sırada).`,`Son ${c.h10.n} maçın ${c.h10.h} tanesinde ${c.line} altında kaldı.`];if(c.tr?.tag==='down')parts.push(`Dakikası düşüyor: son 3 maç ${fmt(c.tr.l3,0)} dk.`);if(c.ri?.b2b)parts.push('Takımı dün gece de oynadı (B2B).');if(c.gp?.tag==='yavaş')parts.push(`Yavaş tempo bekleniyor (${fmt(c.gp.p)}).`);return parts.join(' ')}
// ---- Takım sayfası
function teamRecord(t){const ds={};for(const id in byP)for(const g of byP[id])if(g.t===t)ds[g.ds]=g.win;const v=Object.values(ds);return {w:v.filter(x=>x).length,l:v.filter(x=>!x).length}}
function pickDoc(day,list){return {date:day,saved:new Date().toISOString(),dataUpdated:D.updated,picks:list.map(c=>({id:c.p.id,name:c.p.name,team:c.p.team,opp:c.opp,pos:c.po,mk:c.mk,line:c.line,n:c.il?c.il.n:null,odd:c.il?c.il.odd:null,ev:c.ev!=null?Math.round(c.ev*1000)/1000:c.a?Math.round(c.a.ev*1000)/1000:null,rk:c.rk,mu:Math.round(c.mu*10)/10,model:Math.round(c.model*1000)/1000,est:!c.il,tag:c.tag||'deger',pm:c.pm!=null?Math.round(c.pm*1000)/1000:null}))}}
// Tribün (shadow) kaydı: pickDoc ile aynı alanlar + why ('value': oranı değer taşımıyor, 'nobarem': iddaa baremi yok) ve gereken en düşük oran (need).
function shadowDoc(list){return list.slice(0,15).map(c=>({id:c.p.id,name:c.p.name,team:c.p.team,opp:c.opp,pos:c.po,mk:c.mk,line:c.line,n:c.il?c.il.n:null,odd:c.il?c.il.odd:null,ev:c.a?Math.round(c.a.ev*1000)/1000:null,rk:c.rk,mu:Math.round(c.mu*10)/10,model:Math.round(c.model*1000)/1000,est:!c.il,why:c.why,need:c.need||null,...(c.chk&&c.chk.length?{chk:c.chk}:{})}))}
function gTs(team,day){const g=slate.find(s=>dayKey(s.ts)===day&&(s.home===team||s.away===team));return g?g.ts:0}
// Gecenin karne belgesini üretir (saveTonight ve picks.js ortak kullanır). picks = Kasa (kasaList, sabit sınır yok; başlamış kilitliler dahil), shadow = Tribün/Kâğıt üstü (eski yöntemin Kasa'ya girmeyenleri). Başlamış maçların kayıtları kilitli kalır, başlamamışlar son sakatlık/barem verisiyle yenilenir. "first" ilk kaydedilen listedir (Kasa+Tribün, son dakika karşılaştırması için). Değişiklik yoksa null.
// Sıra sabit kalır: eski listedeki öneri yerinde durur (başladıysa kilitli, başlamadıysa güncel değerleriyle), listeden düşen çıkar, yeniler sona eklenir.
function keepOrder(old,fresh,started){const kk=x=>x.id+'|'+x.mk,F=new Map(fresh.map(x=>[kk(x),x])),out=[],seen=new Set();for(const o of old){const k=kk(o);if(started(o)){out.push(o);seen.add(k)}else if(F.has(k)){out.push(F.get(k));seen.add(k)}}for(const x of fresh)if(!seen.has(kk(x)))out.push(x);return out}
function tonightDoc(day,old,now){const started=c=>gTs(c.team,day)<=now,kk=x=>x.id+'|'+x.mk,sp=pickSplit(day,now);
  const nd=pickDoc(day,sp.bets);const picks=keepOrder(old?.picks||[],nd.picks,started);
  const wasK=new Set((old?.picks||[]).map(kk)),wasF=new Set((old?.shadow||[]).filter(x=>x.fell).map(kk));
  const sh=shadowDoc(sp.others).map(x=>x.why!=='nobarem'&&(wasK.has(kk(x))||wasF.has(kk(x)))?{...x,fell:true}:x);
  const shadow=keepOrder(old?.shadow||[],sh,started).slice(0,15);
  if(!picks.length&&!shadow.length)return null;
  if(old&&JSON.stringify(old.picks)===JSON.stringify(picks)&&JSON.stringify(old.shadow||[])===JSON.stringify(shadow))return null;
  const first=old?.first||(old?.picks?.length||old?.shadow?.length?(old.picks||[]).concat(old.shadow||[]):picks.concat(shadow)).map(c=>({id:c.id,mk:c.mk,name:c.name,team:c.team}));
  return {...nd,picks,shadow,first,...(old&&old.injPicks?{injPicks:old.injPicks}:{})}}

// ---- Sakatlık fırsatı: ev={id,name,team} yeni OUT olduysa takım arkadaşlarının baremlerini yeniden değerlendirir (without-player düzeltmesi scanRows→adjE içinde). Oyuncu başına en iyi bahis, getiri (%25 karışımlı) >=%8.
function injOppItems(ev,now,news){const best=new Map();for(const r of scanRows()){const p=r.p;if(p.team!==ev.team||p.id===ev.id||!r.g||r.g.ts<=now||r.g.ts-now>36*3600e3)continue;
    const all=byP[p.id];if(!all||all.length<5||mpg(p.id)<15||noBet(injOf(p.name))||missedStreak(p)>=1)continue;
    if(!r.adj||!(r.adj.outs||[]).some(o=>o.id===ev.id)||r.adj.f<1.05||r.adj.n<3)continue;
    const odd=r.l.odd,raw=r.pr.over,p25=p25Of(raw,odd),e25=p25*(odd-1)-(1-p25);if(e25<.08||r.mu<=r.l.line)continue;
    const o=best.get(p.id);if(!o||e25>o.ev)best.set(p.id,{id:p.id,name:p.name,team:p.team,opp:r.opp,pos:r.pos,mk:r.mk,line:r.l.line,n:r.l.n,odd,ev:Math.round(e25*1000)/1000,rk:r.rk,mu:Math.round(r.mu*10)/10,model:Math.round(raw*1000)/1000,pm:Math.round(p25*1000)/1000,tag:'inj',news,oddAt:new Date(now).toISOString(),gt:r.g.ts,f:Math.round(r.adj.f*100)/100,wn:r.adj.n,est:false})}
  return [...best.values()].sort((a,b)=>b.ev-a.ev)}
