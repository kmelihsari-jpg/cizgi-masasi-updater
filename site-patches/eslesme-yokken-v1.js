/* Çizgi Masası · eslesme-yokken-v1 — 18 Kasım 2026
   1) Oyuncu sayfası: sekmelerin üstünde 8 kategorilik "Eşleşme özeti" kutusu (hit rate + rakip savunma sırası).
   2) Takım sekmesi: "Kim yokken kim artıyor" altında seçili oyuncu yokken takım arkadaşlarının barem isabeti.
   Sadece görüntü: Vitrin, Öneriler, Kasa, Karne ve kayıtlara hiçbir şey yazmaz. */
(function(){
  if(window.__cmEY)return;window.__cmEY=1;
  var MKS=['PTS','REB','AST','3PM','STL','BLK','RA','SRA'];
  var FALLBACK_MK={PTS:1,REB:1,AST:1,'3PM':1};
  function hcls(p){return p==null?'':p>=.6?'g':p>=.45?'a':'r'}
  function rcol(r){try{return r==null?'#555':rkCol(r)}catch(e){return '#555'}}
  function avgOf(a,mk){return a.length?a.reduce(function(s,x){return s+val(x,mk)},0)/a.length:null}
  function lnTxt(l){return (Math.round(l*10)/10).toString()}

  /* ---------- 1) Oyuncu sayfası: Eşleşme özeti ---------- */
  function eoHtml(){
    var sample=curSample(),cur=S.mk,out='';
    for(var i=0;i<MKS.length;i++){var m=MKS[i];if(!MK[m])continue;
      var on=m===cur,l=on?(S.line==null?0:S.line):defaultLine(S.pid,m,sample),side=on?S.side:'over';
      var hr=hitOf(sample,m,l,side),r=null;try{r=rankFor(S.opp,S.pos,m)}catch(e){}
      var idd=S.seg==='G'?lineFor(S.pid,m):null,lt=idd&&idd.line===l?idd.n+'+':(side==='under'?'alt ':'')+lnTxt(l);
      var a10=avgOf(sample.slice(-10),m);
      out+='<button type="button" class="cm-eo-t'+(on?' on':'')+'" data-eo="'+m+'" aria-pressed="'+on+'">'+
        '<span class="cm-eo-h"><b>'+MK[m].label+'</b>'+(r!=null?'<i style="--c:'+rcol(r)+'" title="Rakibin bu pozisyona verdiği sıra">#'+r+'</i>':'')+'</span>'+
        '<span class="cm-eo-p '+hcls(hr.p)+'">'+(hr.p==null?'–':pct(hr.p))+'</span>'+
        '<small>çizgi '+lt+' · L10 '+fmt(a10)+'</small></button>';
    }
    return out;
  }
  function eoRender(){
    try{
      var mk=document.getElementById('markets');if(!mk||!S.pid||!byP[S.pid])return;
      var box=document.getElementById('cm-eo');
      if(!box){box=document.createElement('div');box.id='cm-eo';box.className='cm-eo';box.setAttribute('aria-label','Eşleşme özeti');
        mk.parentNode.insertBefore(box,mk);
        box.addEventListener('click',function(e){var b=e.target.closest('[data-eo]');if(!b)return;S.mk=b.dataset.eo;S.line=null;S.odds=null;renderAll()})}
      box.innerHTML=eoHtml();
    }catch(err){console.error('cm-eo',err);var b=document.getElementById('cm-eo');if(b)b.innerHTML=''}
  }
  if(typeof renderResults==='function'){var _rr=renderResults;renderResults=function(){var r=_rr.apply(this,arguments);eoRender();return r}}

  /* ---------- 2) Takım sekmesi: yokken barem isabeti ---------- */
  function lineInfo(id,mk){
    var l=lineFor(id,mk);if(l)return {line:l.line,txt:l.n+'+',odd:l.odd,src:'iddaa'};
    var m=mktLine(id,mk);if(m)return {line:m.line,txt:lnTxt(m.line)+' üst',odd:m.o,src:m.bk};
    if(!FALLBACK_MK[mk])return null;
    var g=byP[id]||[];if(g.length<3)return null;var a=avgOf(g,mk);if(a==null||a<1)return null;
    var ln=Math.floor(a)+.5;return {line:ln,txt:lnTxt(ln)+' üst',odd:null,src:'ort'};
  }
  function wobRows(t,key,both){
    var src=function(id){return both?(HIST[id]||[]).concat(byP[id]||[]):(byP[id]||[])};
    var mg=src(key.m.id).filter(function(x){return x.t===t});if(!mg.length)return [];
    var md=new Set(mg.map(function(x){return x.ds}));
    var span=mg.map(function(x){return x.ds}).sort(),lo=span[0],tl=Array.from(teamDS(t)).sort().pop(),hi=tl&&tl>span[span.length-1]?tl:span[span.length-1];
    var rows=[];
    Object.values(P).forEach(function(p){
      if(p.team!==t||p.id===key.m.id||!byP[p.id]||mpg(p.id)<10)return;
      var wo=src(p.id).filter(function(x){return x.t===t&&x.ds>=lo&&x.ds<=hi&&!md.has(x.ds)}).sort(function(a,b){return a.ds<b.ds?-1:1});
      if(!wo.length)return;
      MKS.forEach(function(mk){var li=lineInfo(p.id,mk);if(!li)return;
        var v=wo.map(function(x){return val(x,mk)}),h=v.filter(function(x){return x>li.line}).length;
        rows.push({p:p,mk:mk,li:li,v:v,h:h,n:v.length,pr:h/v.length,inj:injOf(p.name)})});
    });
    rows.sort(function(a,b){return b.pr-a.pr||b.n-a.n||(a.li.src==='ort')-(b.li.src==='ort')||b.h-a.h});
    return rows;
  }
  function bars(r){
    var v=r.v.slice(-10),mx=Math.max(r.li.line*1.6,Math.max.apply(null,v),1);
    return '<span class="cm-wob-bars" title="'+v.map(function(x){return fmt(x,0)}).join(' · ')+'">'+v.map(function(x){
      var h=Math.max(3,Math.round(x/mx*22));return '<i class="'+(x>r.li.line?'w':'l')+'" style="height:'+h+'px"></i>'}).join('')+'</span>';
  }
  function rowHtml(r){
    var o=r.li.odd?' · <b>'+fmt(r.li.odd,2)+'</b>':'',srcT=r.li.src==='ort'?' <em title="Barem yok; sezon ortalamasından kurulan çizgi">tahmini</em>':r.li.src!=='iddaa'?' <em>'+esc(r.li.src)+'</em>':'';
    var st=r.inj&&r.inj[0]!=='AVAILABLE'?' <span class="st '+r.inj[0]+'">'+r.inj[0]+'</span>':'';
    return '<div class="cm-wob-r" data-eob="'+r.p.id+'" data-eobm="'+r.mk+'" role="button" tabindex="0">'+
      '<span class="cm-wob-who">'+esc(r.p.name)+st+'</span>'+
      '<span class="cm-wob-ln">'+MK[r.mk].label+' '+r.li.txt+o+srcT+'</span>'+
      '<span class="cm-wob-hr '+hcls(r.pr)+'">'+r.h+'/'+r.n+' · '+pct(r.pr)+'</span>'+bars(r)+'</div>';
  }
  function wobHtml(){
    var t=S.team;if(!t)return '';var both=!!S.woBoth,W=withoutTable(t,both);if(!W.length)return '';
    var key=W.find(function(x){return x.m.id===S.woKey})||W.find(function(x){return x.inj&&x.inj[0]==='OUT'})||W[0];
    var rows=wobRows(t,key,both);
    var head='<div class="cm-wob-h"><b>'+esc(key.m.name)+' yokken baremler</b><span>Bu gecenin baremi, '+esc(key.m.name.split(' ').slice(-1)[0])+' oynamadığı maçlarda kaç kez geçildi. Barem iddaa, yoksa DK/FD; ikisi de yoksa sezon ortalamasından tahmini çizgi.</span></div>';
    if(!rows.length)return '<div class="cm-wob">'+head+'<p class="note">Bu oyuncu yokken oynamış takım arkadaşı ya da barem yok.</p></div>';
    var first=rows.slice(0,10),rest=rows.slice(10);
    return '<div class="cm-wob">'+head+'<div class="cm-wob-l">'+first.map(rowHtml).join('')+'</div>'+
      (rest.length?'<details class="tv-more"><summary>'+rest.length+' satır daha</summary><div class="cm-wob-l">'+rest.map(rowHtml).join('')+'</div></details>':'')+'</div>';
  }
  function wobRender(){
    var box=document.getElementById('t-wo');if(!box)return;
    try{var h=wobHtml();if(h)box.insertAdjacentHTML('beforeend',h)}catch(err){console.error('cm-wob',err)}
    if(!window.__cmWobBound){window.__cmWobBound=1;var go=function(e){var r=e.target.closest('[data-eob]');if(!r)return;e.stopPropagation();goPlayer(Number(r.dataset.eob),r.dataset.eobm)};
      box.addEventListener('click',go);box.addEventListener('keydown',function(e){if(e.key==='Enter')go(e)})}
  }
  if(typeof renderTeam==='function'){var _rt=renderTeam;renderTeam=function(){var r=_rt.apply(this,arguments);wobRender();return r}}
})();
