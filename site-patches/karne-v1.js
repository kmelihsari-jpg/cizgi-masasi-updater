/* Cizgi Masasi V1: yeni Karne donemi ve Vitrin durum ozeti. */
(function(){'use strict';
  const START='2026-11-15';
  // Eski kayıtlar arşivdir; yeni 100 birim hesabına dahil edilmez.
  if(typeof realRows==='function'){
    const base=realRows;
    realRows=function(){return base().filter(x=>x.date>=START)};
  }
  function fmt2(x){return Number(x).toLocaleString('tr-TR',{minimumFractionDigits:1,maximumFractionDigits:1})}
  function render(){
    const el=document.getElementById('cm-v1-vitrin');if(!el)return;
    let z;try{z=realStats()}catch(_){return}
    const k=z.kasa||{},rows=(z.rows||[]).filter(x=>x.kind==='kasa');
    const n=rows.filter(x=>x.res==='hit'||x.res==='miss').length;
    const hits=rows.filter(x=>x.res==='hit').length;
    const bal=Number.isFinite(k.bal)?k.bal:100;
    const a=typeof IDDRAW!=='undefined'&&IDDRAW ? IDDRAW : null;
    const age=a?.ts?(Date.now()-a.ts)/3600000:Infinity;
    const active=(a?.rows||[]).filter(s=>Number(String(s).split('|')[4])*1000>Date.now()).length;
    const ts=a?.updated ? new Date(a.updated).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}):'henüz yok';
    const oddsStatus=age<=6&&active>0?`${active} aktif barem · ${ts}`:(active>0?'Barem verisi eskidi · yeni seçim kapalı':'Yeni barem bekleniyor');
    el.innerHTML='<div class="cmv-top"><strong>ÇİZGİ MASASI <span>VİTRİN</span></strong><small>Yeni Karne dönemi · 15 Kasım 2026</small></div>'+
      '<div class="cmv-grid"><div><span>Kasa</span><b>'+fmt2(bal)+'</b><small>100 birim başlangıç</small></div>'+
      '<div><span>Karne</span><b>'+hits+'/'+n+'</b><small>Sonuçlanan tahminler</small></div>'+
      '<div><span>ROI</span><b>'+(k.staked?((k.roi||0)*100).toFixed(1)+'%':'—')+'</b><small>Oranlı ve sonuçlanan</small></div>'+
      '<div><span>İddaa baremleri</span><b>'+active+'</b><small>'+oddsStatus+'</small></div></div>'+
      '<p class="cmv-note">Öneriler yalnızca maç öncesinde kayıt altına alınır. Kayıt yoksa sonuç sonradan oluşturulmaz. Model yüzdeleri garanti değildir.</p>';
  }
  const originalRenderHome=typeof renderHome==='function'?renderHome:null;
  if(originalRenderHome)renderHome=function(){const v=originalRenderHome.apply(this,arguments);render();return v};
  const originalRenderCard=typeof renderCard==='function'?renderCard:null;
  if(originalRenderCard)renderCard=function(){const v=originalRenderCard.apply(this,arguments);render();return v};
  document.addEventListener('DOMContentLoaded',()=>{render();setInterval(()=>{if(!document.hidden)render()},60000)});
})();
