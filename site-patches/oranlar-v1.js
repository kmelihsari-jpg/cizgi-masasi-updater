/* Çizgi Masası · oranlar-v1 — 19 Kasım 2026
   Oyuncu sayfası: (1) iddaa baremi çipleri (seçilince çizgi + oran birlikte gelir), (2) katlanabilir Oranlar tablosu ve
   yanında DK/FD satırı, (3) iddaa baremi olmayan oyuncuda uyarı, oyuncu listesinde soluk gösterim,
   (4) Karne açıklamasındaki Sağlam bandı metni (1.40–1.75).
   Sadece görüntü: Vitrin, Öneriler, Kasa, Karne ve kayıtlara hiçbir şey yazmaz. */
(function(){
  if(window.__cmOL)return;window.__cmOL=1;
  var OPEN=false;
  function $(id){return document.getElementById(id)}
  function X(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function f2(x){return (Math.round(x*100)/100).toFixed(2)}
  function ladder(){try{if(S.pid==null||S.seg!=='G')return [];var a=(lines[S.pid]&&lines[S.pid][S.mk])||[];return a.slice().sort(function(x,y){return x.n-y.n})}catch(e){return []}}
  function selIdx(L){for(var i=0;i<L.length;i++)if(L[i].line===S.line)return i;return -1}
  function defIdx(L){try{var d=lineFor(S.pid,S.mk);if(d)for(var i=0;i<L.length;i++)if(L[i].line===d.line)return i}catch(e){}return 0}

  function pick(l){
    S.line=l.line;S.odds=String(l.odd);S.side='over';
    var a=$('line'),b=$('odds');if(a)a.value=S.line;if(b)b.value=S.odds;
    var sd=$('side');if(sd)sd.querySelectorAll('[data-s]').forEach(function(x){x.setAttribute('aria-pressed',String(x.dataset.s==='over'))});
    renderResults();
  }

  /* ---------- 1) çipler ---------- */
  function host(){
    var b=$('cm-ol');if(b&&b.isConnected)return b;
    var ln=$('line'),row=ln&&ln.closest('.betrow');if(!row)return null;
    b=document.createElement('div');b.id='cm-ol';b.className='cm-ol';
    row.parentNode.insertBefore(b,row);
    b.addEventListener('click',function(e){var c=e.target.closest('[data-k]');if(!c)return;var L=ladder(),l=L[Number(c.dataset.k)];if(l)pick(l)});
    return b;
  }
  function chips(){
    var b=host();if(!b)return;
    if(S.pid==null||S.seg!=='G'){b.innerHTML='';return}
    var L=ladder(),h='';
    if(!L.length){
      var lb=(MK[S.mk]&&MK[S.mk].label)||S.mk;
      b.innerHTML='<div class="cm-ol-no"><b>İddaa baremi yok</b> · '+X(lb)+' için bu oyuncuya iddaa çizgi açmamış. Çizgi sezon ortalamasından tahmin edilir; elle yazarsan sonuç sadece analizdir.</div>';return}
    var si=selIdx(L);
    h+='<div class="cm-ol-lb">İddaa baremleri'+(S.side==='under'?' · iddaa sadece Üst verir':'')+'</div><div class="cm-ol-chips">';
    for(var i=0;i<L.length;i++)h+='<button type="button" class="cm-olc'+(i===si?' on':'')+'" data-k="'+i+'" aria-pressed="'+(i===si)+'">'+L[i].n+'+<small>'+f2(L[i].odd)+'</small></button>';
    if(si<0&&S.line!=null)h+='<span class="cm-olc man" title="Bu çizgi iddaa\'da yok">Elle · '+X(S.line)+'<small>iddaa\'da yok</small></span>';
    b.innerHTML=h+'</div>';
  }

  /* ---------- 2) katlanabilir tablo + DK/FD sütunu ---------- */
  var po=$('pcx-odds'),obs=null;
  function tbl(){
    po=po||$('pcx-odds');if(!po)return;
    var L=ladder();if(!L.length)return;
    var note=po.querySelector('p.note'),noteH=note?note.outerHTML:'';
    var ml=null;try{ml=mktLine(S.pid,S.mk)}catch(e){}
    var bk=ml&&ml.bk?X(ml.bk):'DK/FD',mi=-1;
    if(ml)for(var i=0;i<L.length;i++)if(L[i].line===ml.line)mi=i;
    var si=selIdx(L),vis=[];
    if(OPEN){for(i=0;i<L.length;i++)vis.push(i)}
    else{var a=si>=0?si:defIdx(L);vis.push(a);if(mi>=0&&mi!==a)vis.push(mi);vis.sort(function(x,y){return x-y})}
    var rows='';
    if(ml&&mi<0)rows+='<tr class="cm-ot-mk"><td class="l">'+X(ml.line)+'</td><td>–</td><td>'+f2(ml.o)+(ml.u?'<small> / '+f2(ml.u)+'</small>':'')+'</td></tr>';
    vis.forEach(function(k){var l=L[k],mc='–';
      if(ml&&k===mi)mc=f2(ml.o)+(ml.u?'<small> / '+f2(ml.u)+'</small>':'');
      rows+='<tr class="cm-ot-r'+(k===si?' sel':'')+'" data-k="'+k+'"><td class="l">'+l.n+'+</td><td>'+f2(l.odd)+'</td><td>'+mc+'</td></tr>'});
    var h='<h3 class="pcx-h">Oranlar</h3><table class="pcx-ot cm-ot"><thead><tr><th class="l">Çizgi</th><th>iddaa · Üst</th><th>'+bk+(ml&&ml.u?' · Üst / Alt':' · Üst')+'</th></tr></thead><tbody>'+rows+'</tbody></table>'+
      '<button type="button" class="cm-ot-tg" data-tg="1">'+(OPEN?'Merdiveni kat':'Tüm iddaa basamakları ('+L.length+')')+'</button>'+
      (ml&&mi<0?'<p class="note cm-ot-n">'+bk+' çizgisi '+X(ml.line)+', iddaa merdiveninde bu çizgi yok.</p>':'')+noteH;
    if(obs)obs.disconnect();
    po.innerHTML=h;
    if(obs)obs.observe(po,{childList:true});
  }
  if(po){
    po.addEventListener('click',function(e){
      if(e.target.closest('[data-tg]')){OPEN=!OPEN;tbl();return}
      var r=e.target.closest('tr[data-k]');if(!r)return;var l=ladder()[Number(r.dataset.k)];if(l)pick(l);
    });
    if(window.MutationObserver){obs=new MutationObserver(function(){try{tbl()}catch(e){console.error('cm-ol tbl',e)}});obs.observe(po,{childList:true})}
  }

  /* ---------- 3) oyuncu listesinde iddaa baremi olmayanlar soluk ---------- */
  function dim(){
    try{
      var pl=$('plist');if(!pl||typeof IDDRAW==='undefined'||!IDDRAW||!IDDRAW.rows||!IDDRAW.rows.length)return;
      pl.querySelectorAll('[data-p]').forEach(function(e){
        var m=lines[e.dataset.p],has=m&&Object.keys(m).length>0;
        e.classList.toggle('cm-nolines',!has);
      });
    }catch(e){}
  }

  /* ---------- 4) Karne açıklaması: Sağlam bandı ---------- */
  function fixTxt(root){
    try{
      var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null),n,L=[];
      while((n=w.nextNode()))if(n.nodeValue.indexOf('Sağlam: oran 1.50–1.75')>=0)L.push(n);
      L.forEach(function(t){t.nodeValue=t.nodeValue.replace('Sağlam: oran 1.50–1.75','Sağlam: oran 1.40–1.75')});
    }catch(e){}
  }

  function refresh(){try{chips();tbl();dim()}catch(e){console.error('cm-ol',e)}}
  if(typeof renderResults==='function'){var r0=renderResults;renderResults=function(){var r=r0.apply(this,arguments);refresh();return r}}
  if(typeof renderPlist==='function'){var p0=renderPlist;renderPlist=function(){var r=p0.apply(this,arguments);dim();return r}}
  if(window.MutationObserver&&document.body){
    new MutationObserver(function(ms){
      for(var i=0;i<ms.length;i++){var ad=ms[i].addedNodes;for(var j=0;j<ad.length;j++){var n=ad[j];
        if(n.nodeType===1&&n.textContent&&n.textContent.indexOf('1.50–1.75')>=0)fixTxt(n)}}
    }).observe(document.body,{childList:true,subtree:true});
    fixTxt(document.body);
  }
  window.__cmOLApi={refresh:refresh,pick:pick};
})();
