/* Çizgi Masası · donen-oyuncu-v1 — 24 Kasım 2026
   Bir takımda bu sezon hiç maç satırı olmayan ama bu gece iddaa baremi açık (ve sakat listesinde OUT olmayan) bir oyuncu
   varsa (ör. sezona yeni dönen yıldız), o takımın takım arkadaşlarının kartlarına "dönüyor · örnek yok" etiketi koyar.
   Neden: takım arkadaşlarının örnekleri o oyuncusuz maçlardan oluşuyor; onunla oynadıkları örnek yok, dağılım değişebilir.
   Sadece görüntü: Vitrin, Öneriler, Kasa, Karne ve kayıtlara hiçbir şey yazmaz, öneri mantığına dokunmaz. */
(function(){
  if(window.__cmDO)return;window.__cmDO=1;
  var T=0;
  function X(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function has(o){if(!o)return false;for(var k in o){if(o[k]&&o[k].length)return true}return false}
  function sur(n){var a=String(n||'').trim().split(/\s+/);return a[a.length-1]||''}
  function retMap(){
    var m={};
    try{
      Object.keys(P).forEach(function(id){
        var p=P[id];if(!p||!p.team)return;
        if(byP[id]&&byP[id].length)return;
        if(!has(lines[id]))return;
        if(!gameOf(p.team))return;
        try{if(noBet(injOf(p.name)))return}catch(e){}
        (m[p.team]=m[p.team]||[]).push({id:String(id),name:p.name||''});
      });
    }catch(e){}
    return m;
  }
  function scan(){
    var m=retMap();if(!Object.keys(m).length)return;
    var els=document.querySelectorAll('[data-p][data-m]:not([data-cmdo])');
    for(var i=0;i<els.length;i++){
      var el=els[i];
      if(el.classList.contains('hbtn'))continue;
      var id=el.getAttribute('data-p'),p=P[id];
      if(!p||!m[p.team])continue;
      var r=m[p.team].filter(function(x){return x.id!==String(id)});
      if(!r.length)continue;
      var b=el.querySelector('b');if(!b)continue;
      el.setAttribute('data-cmdo','1');
      var who=r.map(function(x){return sur(x.name)}).join(' / ');
      var full=r.map(function(x){return x.name}).join(', ');
      b.insertAdjacentHTML('afterend','<em class="cm-do" title="'+X(full)+' bu sezon hiç oynamadı ama bu gece iddaa baremi açık. Bu oyuncunun örnekleri onsuz maçlara dayanıyor; onunla dağılım değişebilir.">↩ '+X(who)+' dönüyor · örnek yok</em>');
    }
  }
  function later(){if(T)return;T=setTimeout(function(){T=0;try{scan()}catch(e){}},60)}
  try{new MutationObserver(later).observe(document.body,{childList:true,subtree:true})}catch(e){}
  later();
})();
