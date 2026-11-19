// node tests/oran_kademe_harness.js <model.js> : yamali model.js'te oran kademesi davranisini sentetik verilerle dener.
const vm=require('vm'),fs=require('fs');
const src=fs.readFileSync(process.argv[2],'utf8');
const ctx=vm.createContext({console,Date,Math,JSON,Object,Array,Number,String,Set,Map,window:{},fmt:x=>String(x)});
vm.runInContext(`
var noBet=()=>false,injOf=()=>null,missedStreak=()=>0,minTrend=()=>null,restInfo=()=>null,adjE=e=>e,posOf=()=>'SF';`,ctx);
vm.runInContext(src,ctx);
const out=vm.runInContext(`(function(){
  const G={home:'AAA',away:'BBB',ts:Date.now()+3600e3},day=dayKey(G.ts),res={};
  const mkGames=v=>Array.from({length:10},(_,i)=>({pts:v,reb:5,ast:3,stl:1,blk:1,fg3m:2,min:34,start:true}));
  function player(id,v){P[id]={id,name:'P'+id,team:'AAA',np:'F'};byP[id]=mkGames(v)}
  function row(id,line,odd,mu){const p=P[id],pr=lineProbs(mu,1.5,line),a=assess(blendP(pr,odd),'over',odd,10);a.model=pr.over;return {id,p,mk:'PTS',l:{line,odd,n:line+.5},opp:'BBB',pos:'SF',role:'st',n:10,mins:34,mu,a,hr:null,pr,adj:null,g:G,rk:3}}
  ORANPAT=[];
  function run(rows,mkt){D={mkt:mkt||{},mktAt:new Date().toISOString(),dates:[]};scanRows=()=>rows;const r=kasaAll(day,Date.now());return {pass:r.pass.map(c=>c.p.id+'|'+c.tag+'|'+c.il.odd),cap:r.cap.length}}
  // 1) Bir oyuncu, merdiven: 1.6 / 2.2 / 4.0 / 15
  player(1,26);
  res.ladder=run([row(1,19.5,1.6,27),row(1,24.5,2.2,27),row(1,29.5,4.0,27),row(1,39.5,15,27)]);
  // 2) Tek basamak 15 oran -> girmez
  res.long=run([row(1,39.5,15,27)]);
  // 3) Surpriz: sadece 3.5 oran; DK ana baremi model ile uyumlu / uyumsuz / yok
  const agree={1:{PTS:[26.5,1.9,1.9,'draftkings']}};
  const disagree={1:{PTS:[26.5,1.2,4.5,'draftkings']}};
  res.surAgree=run([row(1,27.5,3.5,27)],agree);
  res.surDis=run([row(1,27.5,3.5,27)],disagree);
  res.surNoMkt=run([row(1,27.5,3.5,27)],{});
  // 4) Iki oyuncuda surpriz -> en fazla 1
  player(2,26);P[2].team='AAA';
  const m2={1:{PTS:[26.5,1.9,1.9,'draftkings']},2:{PTS:[26.5,1.9,1.9,'draftkings']}};
  res.twoSur=run([row(1,27.5,3.5,27),row(2,27.5,3.2,27)],m2);
  // 5) Oyuncunun normal bahsi varsa surpriz eklenmez (oyuncu basina tek bahis)
  res.sameP=run([row(1,19.5,1.6,27),row(1,27.5,3.5,27)],agree);
  return res})()`,ctx);
console.log(JSON.stringify(out));
