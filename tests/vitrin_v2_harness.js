// node tests/vitrin_v2_harness.js <model.js> : Vitrin V2 kapilarini sentetik verilerle dener.
const vm=require('vm'),fs=require('fs');
const src=fs.readFileSync(process.argv[2],'utf8');
const ctx=vm.createContext({console,Date,Math,JSON,Object,Array,Number,String,Set,Map,window:{},fmt:x=>String(x)});
vm.runInContext(`
var noBet=()=>false,injOf=()=>null,missedStreak=()=>0,minTrend=()=>null,restInfo=()=>null,adjE=e=>e,posOf=()=>'SF';`,ctx);
vm.runInContext(src,ctx);
const out=vm.runInContext(`(function(){
  const G={home:'AAA',away:'BBB',ts:Date.now()+3600e3},day=dayKey(G.ts),res={};
  const mkGames=(v,mins)=>Array.from({length:10},(_,i)=>({pts:v,reb:5,ast:3,stl:1,blk:1,fg3m:2,min:mins?mins[i]:34,start:true}));
  function player(id,v,mins){P[id]={id,name:'P'+id,team:'AAA',np:'F'};byP[id]=mkGames(v,mins)}
  function row(id,line,odd,mu,mk){mk=mk||'PTS';const p=P[id],pr=lineProbs(mu,1.5,line),a=assess(blendP(pr,odd),'over',odd,10);a.model=pr.over;return {id,p,mk,l:{line,odd,n:line+.5},opp:'BBB',pos:'SF',role:'st',n:10,mins:34,mu,a,hr:null,pr,adj:null,g:G,rk:3}}
  function run(rows){D={mkt:{},mktAt:new Date().toISOString(),dates:[]};scanRows=()=>rows;const r=kasaAll(day,Date.now());return {pass:r.pass.map(c=>c.p.id+'|'+c.mk+'|'+c.tag),cap:(r.cap||[]).map(c=>c.p.id+'|'+c.mk+'|'+!!c.capMk)}}
  // 1) Rol dususu: son 2 mac 20 ve 18 dk (sezon ortalamasi 22+): Vitrin'e girmez; ayni oyuncu normal dakikada girer
  player(1,26,[30,30,30,30,30,30,30,30,20,18]);player(2,26);
  res.rolDus=run([row(1,19.5,1.6,27)]);res.rolOk=run([row(2,19.5,1.6,27)]);
  // 1b) Son 3 mac ortalamasi sezonun %85'inin altinda (31,31,31,31,31,31,31,24,24,24 -> l2=24 ok, l3=24 < .85*29.9? 25.4) -> girmez
  player(3,26,[32,32,32,32,32,32,32,24,24,24]);res.rolL3=run([row(3,19.5,1.6,27)]);
  // 1c) Tek kotu mac (28,28,...,23,30) girer
  player(4,26,[34,34,34,34,34,34,34,34,23,30]);res.rolTek=run([row(4,19.5,1.6,27)]);
  // 2) secim yolu: 1.9 oran, model ~%62 (Saglam/Deger degil) ; mu taramasi
  player(5,26);const tags={};for(let mu=19;mu<=24;mu+=.25){const r=row(5,19.5,1.9,mu),c=kasaCand(r,day,Date.now());D={mkt:{},mktAt:new Date().toISOString(),dates:[]};if(c)tags[c.tag]=(tags[c.tag]||0)+1}
  res.tagTara=tags;
  // 3) AST/STL: dusuk model reddedilir, yuksek model girer
  player(6,26);const lo=row(6,5.5,1.55,6.0,'AST'),hi=row(6,2.5,1.55,6.0,'AST');
  res.astLo=[lo.pr.over,!!kasaCand(lo,day,Date.now())];res.astHi=[hi.pr.over,!!kasaCand(hi,day,Date.now())];
  // 4) Market cesitliligi: ayni macta 3 Saglam PTS -> Vitrin'de 2, biri capMk ile Merdiven Alti'na
  player(7,26);player(8,26);player(9,26);
  res.mkCap=run([row(7,19.5,1.6,27),row(8,19.5,1.6,27.2),row(9,19.5,1.6,27.4)]);
  // 5) Farkli market: 2 PTS + 1 REB -> hepsi girer
  player(10,26);const rr=row(10,3.5,1.6,6.5,'REB');
  res.mkMix=run([row(7,19.5,1.6,27),row(8,19.5,1.6,27.2),rr]);
  // 6) Donus kapisi: ayni takimda 25+ dk'lik bir oyuncu son 2+ maci kacirmis ve OUT/D degil -> takim arkadasi Vitrin'e girmez
  player(50,26);P[50].name='Star';
  missedStreak=p=>p.id===50?3:0;injOf=n=>n==='Star'?['AVAILABLE']:null;
  res.donusAvail=run([row(2,19.5,1.6,27)]);
  injOf=n=>n==='Star'?['Q']:null;res.donusQ=run([row(2,19.5,1.6,27)]);
  injOf=n=>n==='Star'?['OUT']:null;res.donusOut=run([row(2,19.5,1.6,27)]);   // hala OUT: model adj zaten isliyor, kapi yok
  injOf=n=>n==='Star'?['D']:null;res.donusD=run([row(2,19.5,1.6,27)]);
  missedStreak=p=>p.id===50?1:0;injOf=n=>n==='Star'?['AVAILABLE']:null;res.donusTek=run([row(2,19.5,1.6,27)]);   // tek mac kacirdi: kapi yok
  missedStreak=p=>0;injOf=()=>null;delete P[50];delete byP[50];res.donusYok=run([row(2,19.5,1.6,27)]);
  return res})()`,ctx);
console.log(JSON.stringify(out));
