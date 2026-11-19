// node tests/oranlar_dom_harness.js <oranlar-v1.js> : jsdom ile iddaa merdiveni / DK satiri / katlanma davranisini dener.
const fs=require('fs'),{JSDOM}=require('jsdom');
const js=fs.readFileSync(process.argv[2],'utf8');
const dom=new JSDOM(`<body><div id="plist"><button data-p="1">A</button><button data-p="2">B</button></div><section><div class="betrow"><div id="side"><button data-s="over" aria-pressed="true">Üst</button><button data-s="under" aria-pressed="false">Alt</button></div><input id="line"><input id="odds"></div></section><div id="pcx-odds"></div><p class="note" id="kn">Kasa defteri. Sağlam: oran 1.50–1.75, ham model %70+</p></body>`,{runScripts:'outside-only'});
const w=dom.window;
let calls=0;
w.eval(`
 var S={pid:1,mk:'STL',seg:'G',line:null,odds:null,side:'over'};
 var MK={STL:{label:'STL'},PTS:{label:'PTS'}};
 var lines={1:{STL:[{n:1,line:.5,odd:1.17},{n:2,line:1.5,odd:1.95},{n:3,line:2.5,odd:4.8},{n:4,line:3.5,odd:12}]},2:{}};
 var IDDRAW={rows:['x']};
 var DKML=null;function mktLine(){return DKML}
 function lineFor(id,mk){var a=lines[id]&&lines[id][mk];return a&&a.length?a.slice().sort((x,y)=>Math.abs(x.odd-1.85)-Math.abs(y.odd-1.85))[0]:null}
 var RCALLS=0;function renderResults(){RCALLS++}
 function renderPlist(){}
 function esc(s){return s}
 var ORIG='<h3 class="pcx-h">Oranlar</h3><table class="pcx-ot"><tbody><tr><td>orig</td></tr></tbody></table><p class="note">Modele göre adil oran 2.38 · en az 2.50</p>';
`);
w.eval(js);
const q=(s)=>w.document.querySelectorAll(s);
const out={};
const render=()=>{w.eval('document.getElementById("pcx-odds").innerHTML=ORIG');return new Promise(r=>setTimeout(r,20))};
(async()=>{
  // 1) varsayilan: iddaa 1.85'e yakin satir secili, tablo kapali
  w.eval('S.line=1.5;S.odds="1.95"');
  w.eval('renderResults()');await render();
  out.chips=q('.cm-olc').length;out.chipSel=[...q('.cm-olc.on')].map(x=>x.textContent);
  out.rowsClosed=q('.cm-ot-r').length;out.noteKept=!!w.document.querySelector('#pcx-odds p.note');
  out.toggleLabel=w.document.querySelector('.cm-ot-tg').textContent;
  // 2) DK ana barem iddaa'daki 2.5 cizgisi ile ayni: kapaliyken DK satiri da gorunur
  w.eval('DKML={line:2.5,o:4.2,u:1.2,bk:"DraftKings"}');await render();
  out.dkMatchRows=q('.cm-ot-r').length;out.dkHead=w.document.querySelector('#pcx-odds thead').textContent;out.dkCell=[...q('.cm-ot-r')].map(r=>r.textContent);
  // 3) DK cizgisi merdivende yok -> ayri satir + aciklama
  w.eval('DKML={line:1.0,o:1.4,u:2.9,bk:"FanDuel"}');await render();
  out.dkExtra=q('.cm-ot-mk').length;out.dkExtraNote=q('.cm-ot-n').length;
  // 4) tabloyu ac
  w.document.querySelector('.cm-ot-tg').click();out.rowsOpen=q('.cm-ot-r').length;
  // 5) satira basinca cizgi+oran gelir
  const before=w.eval('RCALLS');
  q('.cm-ot-r')[2].click();
  out.picked=w.eval('[S.line,S.odds,S.side]');out.renderCalled=w.eval('RCALLS')>before;out.inputs=[w.document.getElementById('line').value,w.document.getElementById('odds').value];
  // 6) cip tiklama
  q('.cm-olc')[0].click();out.chipPick=w.eval('[S.line,S.odds]');
  // 7) elle cizgi (iddaa'da yok)
  w.eval('S.line=3.0;S.odds="";renderResults()');out.manual=q('.cm-olc.man').length;
  // 8) iddaa baremi olmayan oyuncu
  w.eval('S.pid=2;S.line=null;renderResults()');out.noLadder=!!w.document.querySelector('.cm-ol-no');out.noChips=q('.cm-olc').length;
  w.eval('DKML=null');await render();out.origUntouched=w.document.querySelector('#pcx-odds table').textContent.includes('orig');
  // 9) segment (Q1...) -> cip yok, uyari yok
  w.eval('S.pid=1;S.seg="Q1";renderResults()');out.segEmpty=w.document.getElementById('cm-ol').innerHTML==='';
  // 10) oyuncu listesi
  out.dimmed=[...q('#plist .cm-nolines')].map(x=>x.dataset.p);
  // 11) karne metni
  out.karne=w.document.getElementById('kn').textContent;
  const n=w.document.createElement('p');n.textContent='Sağlam: oran 1.50–1.75 yeni';w.document.body.appendChild(n);
  await new Promise(r=>setTimeout(r,30));out.karneDyn=n.textContent;
  console.log(JSON.stringify(out));
})().catch(e=>{console.error(e);process.exit(1)});
