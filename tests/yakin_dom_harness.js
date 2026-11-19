// node tests/yakin_dom_harness.js <yakin-adaylar-v1.js>
const fs=require('fs'),{JSDOM}=require('jsdom');
const js=fs.readFileSync(process.argv[2],'utf8');
const dom=new JSDOM('<body><div id="h-near" hidden></div><div id="h-oth-head"></div></body>',{runScripts:'outside-only'});
const w=dom.window;
w.eval(`
 var S={hDay:'2026-11-19'};var NOW=Date.now();
 var MK={REB:{label:'REB'},PTS:{label:'PTS'},STL:{label:'STL'}};
 var P={1:{},2:{},3:{},4:{},5:{}};
 var byP={1:new Array(10).fill({}),2:new Array(10).fill({}),3:new Array(3).fill({}),4:new Array(10).fill({}),5:new Array(10).fill({})};
 function mpg(id){return id==4?15:30}
 function dayKey(){return '2026-11-19'}
 function injOf(n){return n=='Out'?'OUT':null} function noBet(i){return i=='OUT'}
 function cmReturnAllowed(){return true}
 function hitOf(){return {p:.7}} function sum(a,f){return a.length*5} function val(){return 5}
 function p25Of(raw,odd){return .75*raw+.25*(1/odd)}
 function tm(){return '04:00'} function esc(s){return s}
 var GOTO=null;function goPlayer(a,b){GOTO=[a,b]}
 var RH=0;function renderHome(){RH++}
 function kasaAll(){return {pass:[{p:{id:5}}]}}
 var G={ts:NOW+36e5,home:'AAA'};
 function R(id,name,mk,n,line,odd,raw,team){return {p:{id:id,name:name,team:team||'AAA'},g:G,opp:'BBB',mk:mk,l:{n:n,line:line,odd:odd},pr:{over:raw},rk:3}}
 var ROWS=[
  R(1,'Aday Bir','REB',7,6.5,2.25,.54),R(1,'Aday Bir','REB',6,5.5,1.71,.50),   // ayni oyuncu: en iyi EV kalir
  R(2,'Aday Iki','PTS',16,15.5,1.7,.59),
  R(2,'Aday Iki','PTS',20,19.5,3.8,.40),                                        // 2.5 ustu: elenir
  R(3,'Az Mac','REB',5,4.5,1.8,.9),                                             // <5 mac
  R(4,'Az Dakika','REB',5,4.5,1.8,.9),                                          // dk<22
  R(5,'Vitrinde','PTS',10,9.5,1.9,.9),                                          // Vitrin'de
  R(6,'Out','PTS',10,9.5,1.9,.9),                                               // sakat
  R(7,'Cok Eksi','STL',2,1.5,1.9,.2)];                                          // EV < -8
 ROWS.forEach(function(r){if(!byP[r.p.id])byP[r.p.id]=new Array(10).fill({});if(!P[r.p.id])P[r.p.id]={}});
 function scanRows(){return ROWS}
`);
w.eval(js);
const q=s=>w.document.querySelectorAll(s);
const out={};
const box=w.document.getElementById('cm-yk');
out.hostAfterNear=w.document.getElementById('h-near').nextSibling===box;
out.visible=!box.hidden;out.rows=q('.cm-yk-r').length;
out.names=[...q('.cm-yk-top b')].map(x=>x.textContent);
out.info=!!w.document.querySelector('.cm-yk-info')&&w.document.querySelector('.cm-yk-info').textContent.includes('Temel kapılar');out.title=w.document.querySelector('.cm-yk-hd h3').textContent;out.firstBet=q('.cm-yk-bet')[0].textContent.replace(/\s+/g,' ');
out.evChips=[...q('.cm-yk-ch span:last-child')].map(x=>x.textContent);
w.eval('renderHome()');out.wrappedCalledOrig=w.eval('RH')===1;out.rowsAfter=q('.cm-yk-r').length;
q('.cm-yk-r')[0].click();out.goto=w.eval('GOTO');
w.eval('ROWS.length=0');w.eval('renderHome()');out.hiddenWhenEmpty=w.document.getElementById('cm-yk').hidden;
w.eval('S.hDay=null');w.eval('renderHome()');out.noDayHidden=w.document.getElementById('cm-yk').hidden;
console.log(JSON.stringify(out));
