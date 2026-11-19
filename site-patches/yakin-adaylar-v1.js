/* Çizgi Masası · yakin-adaylar-v1 — 19 Kasım 2026
   Ana sayfada "Yakın adaylar" kutusu: Vitrin'e girmeyen ama temel kapıları geçen (≥22 dk, sakat değil, en az 1 destek
   sinyali, oran 1.30–2.50) oyuncuların iddaa merdivenindeki en iyi baremi. Sıralama: piyasa karışımlı EV. En çok 12.
   Sadece görüntü ve izleme: Vitrin, Öneriler, Kasa, Karne ve kayıtlara hiçbir şey yazmaz. */
(function(){
  if(window.__cmYK)return;window.__cmYK=1;
  var CFG={oMin:1.30,oMax:2.50,evMin:-.08,max:12};
  function $(id){return document.getElementById(id)}
  function X(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function pc(x){return Math.round(x*100)}
  function sg(x){var v=Math.round(x*1000)/10;return (v>0?'+':'')+v.toFixed(1)}

  function cand(day){
    var now=Date.now(),best={},vit={};
    try{kasaAll(day,now).pass.forEach(function(c){vit[c.p.id]=1})}catch(e){}
    var rows=scanRows();
    for(var i=0;i<rows.length;i++){
      var r=rows[i],p=r.p,g=r.g,all=byP[p.id];
      if(!g||dayKey(g.ts)!==day||g.ts<=now||vit[p.id])continue;
      var odd=r.l&&r.l.odd;if(!odd||odd<CFG.oMin||odd>CFG.oMax)continue;
      if(!all||all.length<5||mpg(p.id)<22)continue;
      if(noBet(injOf(p.name))||!cmReturnAllowed(p,day))continue;
      var line=r.l.line,l10=all.slice(-10),h10=hitOf(l10,r.mk,line,'over'),a10=sum(l10,function(x){return val(x,r.mk)})/l10.length;
      var sup=0;if(r.rk!=null&&r.rk<=10)sup++;if(h10.p>=.6)sup++;if(a10>line)sup++;if(!sup)continue;
      var raw=r.pr.over,p25=p25Of(raw,odd),ev=p25*(odd-1)-(1-p25);
      if(ev<CFG.evMin)continue;
      var c={p:p,mk:r.mk,n:r.l.n,line:line,odd:odd,raw:raw,mk25:p25,ev:ev,sup:sup,g:g,opp:r.opp},o=best[p.id];
      if(!o||c.ev>o.ev)best[p.id]=c;
    }
    var L=Object.keys(best).map(function(k){return best[k]});
    L.sort(function(a,b){return b.ev-a.ev||b.sup-a.sup||a.p.id-b.p.id});
    return L.slice(0,CFG.max);
  }

  function host(){
    var b=$('cm-yk');if(b&&b.isConnected)return b;
    var n=$('h-near');if(!n||!n.parentNode)return null;
    b=document.createElement('div');b.id='cm-yk';b.hidden=true;
    n.parentNode.insertBefore(b,n.nextSibling);
    b.addEventListener('click',function(e){var t=e.target.closest('[data-p]');if(t&&P[t.dataset.p])goPlayer(Number(t.dataset.p),t.dataset.m)});
    return b;
  }

  function draw(){
    var b=host();if(!b)return;
    var day=(typeof S!=='undefined'&&S.hDay)||null,L=[];
    try{if(day)L=cand(day)}catch(e){console.error('cm-yk',e)}
    if(!L.length){b.hidden=true;b.innerHTML='';return}
    var h='<div class="cm-yk-box"><div class="cm-yk-hd"><h3>Yakın adaylar</h3><span class="cm-yk-tag">izleme listesi · önerilmiş bahis değil</span></div>'+
      '<p class="note">Vitrin\'e girmeyen ama temel kapıları (≥22 dk, sakat değil, en az 1 destek sinyali) geçen bahisler; oyuncu başına iddaa merdivenindeki en iyi barem. '+
      'iddaa marjı yüzünden çoğu modele göre sınırda ya da hafif eksidir. Oynamadan önce kendin değerlendir.</p><div class="cm-yk-grid">';
    L.forEach(function(c){
      var lb=(MK[c.mk]&&MK[c.mk].label)||c.mk,pos=c.ev>=.03;
      h+='<button type="button" class="cm-yk-r" data-p="'+c.p.id+'" data-m="'+X(c.mk)+'">'+
        '<span class="cm-yk-top"><b>'+X(c.p.name)+'</b><small>'+X(c.p.team)+' '+(c.g.home===c.p.team?'vs':'@')+' '+X(c.opp)+' · '+X(tm(c.g.ts))+'</small></span>'+
        '<span class="cm-yk-bet">'+X(lb)+' '+X(c.n)+'+ <small>@'+c.odd.toFixed(2)+'</small></span>'+
        '<span class="cm-yk-ch"><span>model %'+pc(c.raw)+'</span><span>piyasa %'+pc(1/c.odd)+'</span><span class="'+(pos?'cm-yk-p':'cm-yk-n')+'">EV '+sg(c.ev)+'%</span></span></button>';
    });
    b.innerHTML=h+'</div></div>';b.hidden=false;
  }

  if(typeof renderHome==='function'){var r0=renderHome;renderHome=function(){var r=r0.apply(this,arguments);try{draw()}catch(e){console.error('cm-yk',e)}return r}}
  try{draw()}catch(e){}
})();
