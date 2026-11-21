// node tests/ana_v3_harness.js <ana-v3.js>   (jsdom gerekir)
const fs=require('fs'),{JSDOM}=require('jsdom');
const js=fs.readFileSync(process.argv[2],'utf8');
const dom=new JSDOM(`<body><div id="view-home"><div class="injbar"><button id="inj-up">ESPN</button></div>
<details id="cm-live-source"><summary>NBA</summary></details><div id="inj-panel"></div>
<div id="h-games"></div><section class="picks"><div class="sec-head"><h3>Gecenin bahisleri</h3></div><div id="h-hero"></div><div id="h-picks"></div><div id="h-near"><p>eski</p></div>
<div class="paperbox"><div id="h-oth-head"></div><div id="h-others"><p>kagit</p></div></div></section>
<section id="h-outs-wrap"><div class="mini-head"><h3>Yeni OUT → öne çıkanlar</h3></div><div id="h-outs"></div></section><section id="h-risers-wrap"><div class="mini-head"><h3>Yükselenler</h3></div><div class="mlist" id="h-risers"></div></section>
<section id="h-unders-wrap"><div class="mini-head"><h3>Günün alt önerileri</h3></div><div class="mlist" id="h-unders"></div></section><button id="h-karne">Kasa 100 · Tribün 98</button><div id="h-chg"></div></div>
<div id="view-card"><h3>Kâğıt üstünde</h3></div></body>`,{runScripts:'outside-only'});
const w=dom.window;
w.eval(`
 var NOW=Date.now();var S={hDay:'2026-11-21'};
 var MK={REB:{label:'REB'},PTS:{label:'PTS'},AST:{label:'AST'},RA:{label:'RA'}};
 var TC={MIL:'#00471B',PHI:'#006BB6',SAS:'#C4CED4',NOP:'#0C2340'},TC2={MIL:'#EEE1C6',PHI:'#ED174C',SAS:'#000',NOP:'#C8102E'};
 var G1={ts:NOW+36e5,home:'PHI',away:'MIL'},G2={ts:NOW+72e5,home:'SAS',away:'NOP'};
 var slate=[G1,G2];
 function mkP(id,name,team){return {id:id,name:name,team:team}}
 function pav(p){return '<span class="pav" data-i="'+p.id+'"></span>'}
 var P={};var byP={};
 [[1,'Aday Bir','PHI'],[2,'Aday Iki','SAS'],[3,'Vitrin Uc','SAS'],[4,'Bekleyen Dort','MIL'],[5,'Out Bes','PHI'],[6,'Fayda Alti','PHI'],[7,'Fayda Yedi','PHI']].forEach(function(a){P[a[0]]=mkP(a[0],a[1],a[2]);byP[a[0]]=new Array(10).fill({})});
 function mpg(){return 30} function dayKey(){return '2026-11-21'} function injOf(){return null} function noBet(i){return i==='OUT'}
 function cmReturnAllowed(){return true} function hitOf(){return {p:.7}} function sum(a){return a.length*7} function val(){return 7}
 function p25Of(raw,odd){return .75*raw+.25*(1/odd)} function tm(){return '04:00'} function esc(s){return s} function shortName(n){return n.split(' ')[1]||n}
 function teamRecord(t){return {w:10,l:5}} function restInfo(t){return t==='NOP'?{b2b:true}:null} function gamePace(g){return {p:99.1,tag:'orta'}}
 function lineFor(){return null} function assess(){return {minOdds:1.41}}
 var GOTO=null;function goPlayer(a,b){GOTO=[a,b]}
 function kasaAll(){return {pass:[{p:P[3]}]}}
 function R(id,mk,n,odd,raw,g){return {p:P[id],g:g||G1,opp:'MIL',mk:mk,l:{n:n,line:n-.5,odd:odd},pr:{over:raw},rk:3,mu:n+.4,pos:'SF'}}
 var ROWS=[R(1,'REB',7,2.0,.55),R(1,'REB',6,1.6,.60),R(2,'PTS',16,1.7,.58,G2),R(3,'AST',6,1.55,.75,G2)];
 function scanRows(){return ROWS}
 var VITC={p:P[3],mk:'AST',il:{n:6,odd:1.55},a:{ev:.16},ev:.16,model:.75,g:G2,opp:'NOP',line:5.5};
 var VIT2={p:P[2],mk:'PTS',il:{n:16,odd:1.7},a:{ev:.09},ev:.09,model:.66,g:G2,opp:'NOP',line:15.5};
 var OTHERS=[{p:P[4],mk:'RA',why:'nobarem',line:11.5,g:G1,opp:'PHI',model:.73,pr:{over:.73}},{p:P[1],mk:'REB',why:'value',line:6.5,g:G1,model:.6}];var BETS=[VITC,VIT2];
 function pickSplit(day,now){return {bets:BETS,others:OTHERS}}
 function homeItems(day,bets){return BETS.map(function(c){return {c:c}})}
 function outBoost(){return [{m:P[5],team:'PHI',opp:'MIL',g:G1,rows:[{p:P[6],n:13,dm:6,dp:4.2,dr:0,da:0},{p:P[7],n:9,dm:5,dp:0,dr:0,da:1.6}]},{m:mkP(9,'Bos Dokuz','PHI'),team:'PHI',opp:'MIL',g:G1,rows:[]}]}
 function cmObBest(r){var c=[['PTS',r.dp,1],['REB',r.dr,2.2],['AST',r.da,2.6]].filter(function(x){return x[1]>0});if(!c.length)return null;c.sort(function(a,b){return b[1]*b[2]-a[1]*a[2]});return {mk:c[0][0],v:c[0][1]}}
 function risers(){return [{p:P[6],g:G1,startUp:true,d:12,mp:10,m2:22,sp:{pts:4,reb:1,ast:0},s2:{pts:5,reb:2,ast:1},outs:[]}]}
 function underList(){return [{p:P[7],g:G1,opp:'MIL',mk:'AST',line:5.5,mu:3.9,a10:4.7,a5:4.4,rk:30,model:.77,ri:{b2b:true}}]}
 function cmGameCard(){return 'ESKI'} function renderOuts(){} function renderRisers(){} function renderUnders(){}
 function keepOrder(old,nw){return nw} function gTs(){return NOW+36e5} function pickDoc(day,b){return {date:day,picks:b.map(function(c){return {id:c.p.id}})}}
 function tonightDoc(day,old,now){var sp=pickSplit(day,now);return {date:day,picks:sp.bets.map(function(c){return {id:c.p.id,mk:c.mk}}),shadow:[{id:4,mk:'RA',why:'nobarem'}]}}
 var RH=0;function renderHome(){RH++;var sp=pickSplit(S.hDay);homeItems(S.hDay,sp.bets);
   document.getElementById('h-games').innerHTML=slate.map(function(g){return cmGameCard(g,sp.bets)}).join('');
   renderOuts(S.hDay);renderRisers(S.hDay);renderUnders(S.hDay);
   document.getElementById('h-picks').innerHTML='<table>eski</table>';}
`);
w.eval(js);
w.eval('renderHome()');
const d=w.document,q=s=>[...d.querySelectorAll(s)],out={};
out.rh=w.eval('RH');
// Tabela
out.games=q('#h-games .gcard.cm3t').length;out.board=d.getElementById('h-games').classList.contains('cm3-board');out.head=!!d.querySelector('#h-games .cm3t-h');
out.durum=q('#h-games .cm3t .cm3f.rd,#h-games .cm3t .cm3f.ye').map(x=>x.textContent);
// sakatlık çipleri yok, injbar yerinde
out.noChips=!d.getElementById('cm3-outs');
// Vitrin tablosu aynen
out.vitCards=q('.cm3v-c').length;out.tableKept=!!d.querySelector('#h-picks table');out.side=(d.querySelector('.picks .sec-head .cm3-side')||{}).textContent;
// Merdiven Altı
out.nearHidden=d.getElementById('h-near').hidden;out.paperHidden=d.querySelector('.paperbox').hidden;
out.vitrinNotInMerdiven=!q('#cm3-yk .cm3mr .cm3mr-t b').some(x=>x.textContent==='Aday Iki');
out.merdiven=q('#cm3-yk .cm3mr:not(.w) .cm3mr-t b').map(x=>x.textContent);
out.waiting=q('#cm3-yk .cm3mr.w .cm3mr-t b').map(x=>x.textContent);
out.merdivenBet=q('#cm3-yk .cm3mr:not(.w) .cm3mr-bet').map(x=>x.textContent);
out.gauge=q('#cm3-yk .cm3g2').length;out.why=q('#cm3-yk .cm3mr:not(.w) .cm3mr-w').map(x=>x.textContent);
// Revir
out.revir=q('.cm3rv-c .cm3rv-h b').map(x=>x.textContent);out.revirBen=q('.cm3rv-b b').map(x=>x.textContent);out.revirTitle=d.querySelector('#h-outs-wrap h3').firstChild.nodeValue;
// Asansör / Bodrum
out.drawers=['h-risers-wrap','h-unders-wrap'].map(id=>{const w=d.getElementById(id);return w.querySelector('h3').firstChild.nodeValue+'|'+w.classList.contains('closed')});
out.risers=q('.cm3r').length;out.unders=q('.cm3u-d').map(x=>x.textContent);
d.querySelector('#h-risers-wrap .mini-head').click();out.openAfterClick=!d.getElementById('h-risers-wrap').classList.contains('closed');
// relabel
out.karne=d.querySelector('#view-card h3').textContent;out.kstrip=d.getElementById('h-karne').textContent;
// karne shadow
const doc=w.eval("tonightDoc('2026-11-21',null,NOW)");
out.shadow=doc.shadow.map(s=>s.name+'|'+s.mk+'|'+s.n+'|'+s.odd+'|'+s.why);out.picksKept=doc.picks.length;
out.shadowNoVitrin=!doc.shadow.some(s=>s.id===3);
// tıklama
q('#cm3-yk .cm3mr')[0].click();out.goto=w.eval('GOTO');
// boşken
w.eval('ROWS.length=0;OTHERS.length=0;BETS.length=0;renderHome()');
out.emptyHidden=d.getElementById('cm3-yk').hidden;
const doc2=w.eval("tonightDoc('2026-11-21',null,NOW)");out.emptyDocShadow=doc2?doc2.shadow.length:null;
console.log(JSON.stringify(out));
