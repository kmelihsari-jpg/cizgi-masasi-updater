// node tests/donen_oyuncu_dom_harness.js <donen-oyuncu-v1.js>
const fs=require('fs'),{JSDOM}=require('jsdom');
const js=fs.readFileSync(process.argv[2],'utf8');
const html='<body><table><tbody>'+
 '<tr class="click" data-p="2" data-m="PTS"><td><b>Wagler</b></td></tr>'+
 '<tr class="click" data-p="3" data-m="PTS"><td><b>Lopez</b></td></tr>'+
 '<tr class="click" data-p="4" data-m="PTS"><td><b>Baska Takim</b></td></tr>'+
 '<tr class="click" data-p="1" data-m="PTS"><td><b>Ingram</b></td></tr></tbody></table>'+
 '<button class="hbtn" data-p="2" data-m="PTS">Oyuncuya git</button></body>';
const dom=new JSDOM(html,{runScripts:'outside-only'});
const w=dom.window;
w.eval(`
 var P={1:{id:1,name:'Brandon Ingram',team:'LAC'},2:{id:2,name:'Keaton Wagler',team:'LAC'},3:{id:3,name:'Brook Lopez',team:'LAC'},4:{id:4,name:'X Y',team:'BOS'},5:{id:5,name:'Beal',team:'LAC'}};
 var byP={2:[{}],3:[{}],4:[{}]};
 var lines={1:{PTS:[{n:2}]},2:{PTS:[{n:1}]},3:{PTS:[{n:1}]},4:{PTS:[{n:1}]}};
 function gameOf(t){return t=='LAC'||t=='BOS'?{ts:1}:null}
 function injOf(n){return n=='Beal'?'OUT':null} function noBet(i){return i=='OUT'}
`);
w.eval(js);
const q=s=>[...w.document.querySelectorAll(s)];
const out={};
setTimeout(()=>{
  out.badges=q('.cm-do').length;
  out.rowsWithBadge=q('tr[data-cmdo]').map(x=>x.getAttribute('data-p'));
  out.text=q('.cm-do')[0]&&q('.cm-do')[0].textContent;
  out.btnClean=!w.document.querySelector('.hbtn').hasAttribute('data-cmdo');
  // yeniden cizim: yeni satir eklenir, eskiler tekrar etiketlenmez
  w.document.querySelector('tbody').insertAdjacentHTML('beforeend','<tr data-p="3" data-m="REB"><td><b>Lopez</b></td></tr>');
  setTimeout(()=>{
    out.badgesAfter=q('.cm-do').length;
    // iddaa baremi yoksa etiket yok
    w.eval('lines[1]={}');
    w.document.querySelector('tbody').insertAdjacentHTML('beforeend','<tr data-p="2" data-m="AST"><td><b>Wagler</b></td></tr>');
    setTimeout(()=>{out.noLineNoBadge=q('tr[data-p="2"][data-m="AST"] .cm-do').length===0;console.log(JSON.stringify(out));process.exit(0)},150);
  },150);
},150);
