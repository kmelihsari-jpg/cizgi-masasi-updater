/* Çizgi Masası · yakin-adaylar-v1 — 19 Kasım 2026
   Ana sayfada "Yakın adaylar" kutusu: Vitrin'e girmeyen ama temel kapıları geçen (≥22 dk, sakat değil, en az 1 destek
   sinyali, oran 1.30–2.50) oyuncuların iddaa merdivenindeki en iyi baremi. Sıralama: piyasa karışımlı EV. En çok 12.
   Sadece görüntü ve izleme: Vitrin, Öneriler, Kasa, Karne ve kayıtlara hiçbir şey yazmaz. */
(function(){
  if(window.__cmYK)return;window.__cmYK=1;
  var TILT=[-1,.8,-.6,.7,-.8,.5];
  var CFG={oMin:1.30,oMax:2.50,evMin:-.08,max:12};
  function $(id){return document.getElementById(id)}
  function X(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function pc(x){return Math.round(x*100)}
  function sg(x){var v=Math.round(x*1000)/10;return v>0?'+'+v.toFixed(1):v<0?'−'+Math.abs(v).toFixed(1):'0.0'}

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
    var INFO='<details class="cm-yk-info"><summary>Bu liste nasıl seçildi, kartlar ne demek?</summary><div class="cm-yk-ib">'+
      '<h4>Temel kapılar</h4><p>Bir bahis bu listeye girmek için hepsini geçer:</p><ul>'+
      '<li>Oyuncunun sezonda en az 5 maçı var ve maç başına ortalama en az 22 dakika oynuyor.</li>'+
      '<li>Sakatlık listesinde "oynamaz" görünmüyor.</li>'+
      '<li>En az bir destek sinyali var: rakip savunma bu istatistikte ilk 10 içinde, oyuncu son 10 maçın %60 ve fazlasında bu çizgiyi geçmiş ya da son 10 maç ortalaması çizginin üstünde.</li>'+
      '<li>İddaa baremi var ve oran 1.30 ile 2.50 arasında.</li>'+
      '<li>Beklenen getiri −%8\'den kötü değil.</li>'+
      '<li>Bahis zaten Vitrin\'de değil. Oyuncu başına iddaa merdivenindeki en iyi barem gösterilir, en fazla 12 kart.</li></ul>'+
      '<h4>Kart nasıl okunur</h4><ul>'+
      '<li><b>REB 7+ @2.25</b>: oyuncu 7 ve üstü ribaund yaparsa bahis kazanır; iddaa oranı 2.25.</li>'+
      '<li><b>Bizim model %54</b>: modelin bu bahsin tutma ihtimali.</li>'+
      '<li><b>İddaa\'nın oranı %44 diyor</b>: oranın ima ettiği ihtimal (oran 2.25 ise 1 ÷ 2.25 ≈ %44; 2.00 ise %50).</li>'+
      '<li><b>Beklenen getiri +%11.8</b>: bu bahsi aynı koşullarda tekrar tekrar oynasan 100 TL başına ortalama kazancın. Hesapta modelin %75\'i, iddaa\'nın ihtimalinin %25\'i karıştırılır. Eksi ise oran modele göre düşük, yani değer yok.</li></ul>'+
      '<p class="cm-yk-warn">Bunlar öneri değil, izleme listesi. Oynamadan önce sakatlığı, kadroyu ve oranı kendin kontrol et.</p></div></details>';
    var h='<div class="cm-yk-box"><div class="cm-yk-hd"><span class="cm-yk-lamp" aria-hidden="true"></span><h3>Merdiven Altı</h3><span class="cm-yk-tag">ruhsatsız · oynamadan önce düşün</span></div>'+
      '<p class="note">Vitrin\'e giremeyen ama temel kapıları geçen bahisler. İddaa marjı yüzünden çoğu modele göre sınırda ya da hafif eksidir.</p>'+INFO+'<div class="cm-yk-grid">';
    L.forEach(function(c,i){
      var lb=(MK[c.mk]&&MK[c.mk].label)||c.mk,pos=c.ev>=.03;
      h+='<button type="button" class="cm-yk-r" style="--tilt:'+TILT[i%6]+'deg" data-p="'+c.p.id+'" data-m="'+X(c.mk)+'">'+
        '<span class="cm-yk-top"><b>'+X(c.p.name)+'</b><small>'+X(c.p.team)+' '+(c.g.home===c.p.team?'vs':'@')+' '+X(c.opp)+' · '+X(tm(c.g.ts))+'</small></span>'+
        '<span class="cm-yk-bet">'+X(lb)+' '+X(c.n)+'+ <small>@'+c.odd.toFixed(2)+'</small></span>'+
        '<span class="cm-yk-ch"><span>Bizim model %'+pc(c.raw)+'</span><span>İddaa\'nın oranı %'+pc(1/c.odd)+' diyor</span><span class="'+(pos?'cm-yk-p':'cm-yk-n')+'">Beklenen getiri '+sg(c.ev)+'%</span></span></button>';
    });
    b.innerHTML=h+'</div></div>';b.hidden=false;
  }

  if(typeof renderHome==='function'){var r0=renderHome;renderHome=function(){var r=r0.apply(this,arguments);try{draw()}catch(e){console.error('cm-yk',e)}return r}}
  try{draw()}catch(e){}
})();
