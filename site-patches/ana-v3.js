/* Çizgi Masası · ana-v3 — 21 Kasım 2026
   Melih'in seçimleri: 1B sakatlık bandı (yeni OUT çipleri), 2A sade maç kartı (takım renkleri),
   3C Vitrin'deki diğer bahisler kart sırası, 4A tek Merdiven Altı (Kâğıt üstünde ve "Oran düşük ama
   değerli" kalkar, barem bekleyenler soluk kart), 6B Yeni OUT fırsat şeridi, 7A Yükselenler dakika çubuğu,
   8B Günün alt önerileri fark kartları.
   Karne: yeni dönemde Tribün (shadow) kaydı Kâğıt üstünde yerine Merdiven Altı'nın oranlı adaylarıdır
   (tonightDoc sarmalayıcı; karne_automation.py başsız tarayıcıda aynı fonksiyonu çağırır).
   Vitrin (Kasa) seçimi, Vitrin kartı, Karne kayıt kuralları ve Barem Geçmişi değişmez. */
(function(){
  if(window.__cmAnaV3)return;window.__cmAnaV3=1;
  var CFG={oMin:1.30,oMax:2.50,evMin:-.08,max:12,wait:8};
  var TILT=[-1,.8,-.6,.7,-.8,.5];
  var LAST={sp:null,day:null,it:null};
  function $(id){return document.getElementById(id)}
  function X(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function pc(x){return Math.round(x*100)}
  function f1(x){return (Math.round(x*10)/10).toFixed(1)}
  function sg(x){var v=Math.round(x*1000)/10;return v>0?'+'+v.toFixed(1):v<0?'−'+Math.abs(v).toFixed(1):'0.0'}
  function lbl(mk){return (typeof MK!=='undefined'&&MK[mk]&&MK[mk].label)||mk}
  function col(t,two){try{var c=two?TC2[t]:TC[t];return c||(two?'#555':'#777')}catch(e){return '#777'}}
  function vs(p,g){return X(p.team)+' '+(g&&g.home===p.team?'vs':'@')}

  /* ---- veriyi yakala (aynı hesap tekrar yapılmasın) ---- */
  if(typeof pickSplit==='function'){var ps0=pickSplit;pickSplit=function(day){var r=ps0.apply(this,arguments);if(arguments.length<2||arguments[1]==null){LAST.sp=r;LAST.day=day}return r}}
  if(typeof homeItems==='function'){var hi0=homeItems;homeItems=function(){var r=hi0.apply(this,arguments);LAST.it=r;return r}}

  /* ---- Merdiven Altı adayları (yakin-adaylar-v1 kapıları) ---- */
  function cand(day,now){
    now=now||Date.now();var best={},vit={};
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
      var c={p:p,mk:r.mk,n:r.l.n,line:line,odd:odd,raw:raw,ev:ev,sup:sup,g:g,opp:r.opp,rk:r.rk,mu:r.mu,po:r.pos},o=best[p.id];
      if(!o||c.ev>o.ev)best[p.id]=c;
    }
    var L=Object.keys(best).map(function(k){return best[k]});
    L.sort(function(a,b){return b.ev-a.ev||b.sup-a.sup||a.p.id-b.p.id});
    return L.slice(0,CFG.max);
  }
  window.cmMerdivenAday=cand;

  // Barem bekleyenler: modelin sevdiği, iddaa'nın henüz açmadığı bahisler (sadece görüntü, karneye yazılmaz).
  function waiting(day,taken){
    var sp=(LAST.day===day&&LAST.sp)||null,now=Date.now(),out=[],seen={};
    if(!sp)return out;
    (sp.others||[]).forEach(function(c){
      if(!c||!c.p||c.why!=='nobarem'||taken[c.p.id]||seen[c.p.id])return;
      if(c.g&&c.g.ts<=now)return;
      try{if(noBet(c.inj||injOf(c.p.name)))return}catch(e){}
      var need=null;try{need=c.pr?assess(c.pr,'over',null,c.en||10).minOdds:null}catch(e){}
      seen[c.p.id]=1;out.push({p:c.p,mk:c.mk,n:Math.floor(c.line)+1,g:c.g,opp:c.opp,model:c.model!=null?c.model:(c.pr?c.pr.over:null),need:need});
    });
    out.sort(function(a,b){return (b.model||0)-(a.model||0)});
    return out.slice(0,CFG.wait);
  }

  /* ---- Karne: Tribün kaydı = Merdiven Altı (oranlı) ---- */
  function mShadow(day,now){
    return cand(day,now).map(function(c){return {id:c.p.id,name:c.p.name,team:c.p.team,opp:c.opp,pos:c.po||null,mk:c.mk,line:c.line,n:c.n,odd:c.odd,
      ev:Math.round(c.ev*1000)/1000,rk:c.rk!=null?c.rk:null,mu:c.mu!=null?Math.round(c.mu*10)/10:null,model:Math.round(c.raw*1000)/1000,est:false,why:'merdiven',need:null}});
  }
  window.cmMerdivenShadow=mShadow;
  if(typeof tonightDoc==='function'){
    var td0=tonightDoc;
    tonightDoc=function(day,old,now){
      var d=td0.apply(this,arguments),sh=[];
      try{sh=mShadow(day,now)}catch(e){console.error('cm-v3 shadow',e)}
      if(!d){
        if(old)d=Object.assign({},old);
        else if(!sh.length)return null;
        else{try{d=Object.assign({},pickDoc(day,[]),{picks:[]})}catch(e){d={date:day,picks:[]}}}
      }
      d.picks=d.picks||[];
      var pk={};d.picks.concat(d.injPicks||[]).forEach(function(c){pk[c.id]=1});sh=sh.filter(function(c){return !pk[c.id]});
      var t=now==null?Date.now():now,started=function(c){try{return gTs(c.team,day)<=t}catch(e){return false}};
      try{d.shadow=keepOrder((old&&old.shadow)||[],sh,started).slice(0,15)}catch(e){d.shadow=sh.slice(0,15)}
      if(!d.picks.length&&!d.shadow.length)return null;
      if(old&&JSON.stringify(old.picks||[])===JSON.stringify(d.picks)&&JSON.stringify(old.shadow||[])===JSON.stringify(d.shadow))return null;
      return d;
    };
  }

  /* ---- 2A maç kartı ---- */
  if(typeof cmGameCard==='function'){
    cmGameCard=function(g,picks){
      var k=dayKey(g.ts),gp=null,top=null;try{gp=gamePace(g)}catch(e){}top=(picks||[]).find(function(c){return c.g===g});
      function side(t,home){var rc={w:'',l:''},ri=null;try{rc=teamRecord(t)}catch(e){}try{ri=restInfo(t,k)}catch(e){}
        return '<span class="cm3g-t'+(home?' r':'')+'"><i style="background:'+col(t)+';box-shadow:0 0 0 1.5px '+col(t,1)+'"></i><b>'+X(t)+'</b><small>'+rc.w+'-'+rc.l+'</small>'+(ri&&ri.b2b?'<em>B2B</em>':'')+'</span>'}
      var pr=top?(top.a&&top.a.w!=null?top.a.w:top.model):null;
      var bot=top?'<span class="mu">Öne çıkan</span> <b>'+X(shortName(top.p.name))+' '+X(lbl(top.mk))+(top.il?' '+top.il.n+'+':'')+'</b>'+(pr!=null?' <span class="cm3g-p">%'+pc(pr)+'</span>':''):'<span class="mu">Öne çıkan bahis yok</span>';
      var tag=gp?gp.tag:'';
      return '<button class="gcard cm3g" data-home="'+X(g.home)+'" aria-label="'+X(g.away)+' @ '+X(g.home)+' '+X(tm(g.ts))+'">'+
        '<span class="cm3g-s" aria-hidden="true"><i style="background:'+col(g.away)+'"></i><i style="background:'+col(g.home)+'"></i></span>'+
        '<span class="cm3g-r1"><span class="cm3g-tm">'+X(tm(g.ts))+'</span><span class="cm3g-pc'+(tag==='hızlı'?' f':tag==='yavaş'?' s':'')+'">'+(gp?'tempo '+X(f1(gp.p))+' · '+X(tag):'')+'</span></span>'+
        '<span class="cm3g-r2">'+side(g.away,0)+'<span class="cm3g-at">@</span>'+side(g.home,1)+'</span>'+
        '<span class="cm3g-pk">'+bot+'</span></button>';
    };
  }

  /* ---- 6B Yeni OUT fırsat şeridi ---- */
  if(typeof renderOuts==='function'){
    renderOuts=function(day){
      var wrap=$('h-outs-wrap'),el=$('h-outs');if(!wrap||!el)return;
      var R=[];try{R=day?outBoost(day):[]}catch(e){}
      var F=[];R.forEach(function(o){(o.rows||[]).forEach(function(r){var b=cmObBest(r);if(b)F.push({o:o,r:r,b:b,w:b.v*({PTS:1,REB:2.2,AST:2.6}[b.mk]||1)})})});
      F.sort(function(a,b){return b.w-a.w});
      wrap.hidden=!R.length;if(!R.length){el.innerHTML='';return}
      function row(x){var il=null;try{il=lineFor(x.r.p.id,x.b.mk)}catch(e){}
        return '<button type="button" class="cm3o" data-p="'+x.r.p.id+'" data-m="'+x.b.mk+'"><span class="cm3o-l"><small>'+X(shortName(x.o.m.name))+' OUT →</small><b>'+X(x.r.p.name)+' <em>'+X(lbl(x.b.mk))+'</em></b>'+
          '<small>onsuz '+x.r.n+' maç: '+(x.b.v>=0?'+':'')+f1(x.b.v)+' '+X(lbl(x.b.mk))+' · '+(Math.round(x.r.dm)>=0?'+':'')+Math.round(x.r.dm)+' dk'+(x.r.inj&&['AVAILABLE','P'].indexOf(x.r.inj[0])<0?' · '+X(x.r.inj[0]):'')+'</small></span>'+
          '<span class="cm3o-r"><b>'+(x.b.v>=0?'+':'')+f1(x.b.v)+'</b>'+(il?'<small>iddaa '+il.n+'+ · '+il.odd.toFixed(2)+'</small>':'')+'</span></button>'}
      var top=F.slice(0,3),rest=F.slice(3),none=R.filter(function(o){return !(o.rows||[]).length});
      var h=top.length?top.map(row).join(''):'<p class="note">Yeni OUT var ama onsuz oynanmış yeterli maç yok.</p>';
      if(rest.length||none.length){
        h+='<details class="cm3o-all"><summary>Tüm OUT\'lar ve faydalananlar ('+(F.length+none.length)+')</summary>'+rest.map(row).join('')+
          (none.length?'<p class="note">'+none.map(function(o){return X(shortName(o.m.name))}).join(', ')+': onsuz oynanmış yeterli maç yok.</p>':'')+'</details>';
      }
      el.innerHTML='<div class="cm3o-w">'+h+'</div>';
      el.onclick=function(e){var b=e.target.closest('[data-p]');if(b)goPlayer(Number(b.dataset.p),b.dataset.m)};
    };
  }

  /* ---- 7A Yükselenler: dakika çubuğu ---- */
  if(typeof renderRisers==='function'){
    renderRisers=function(day){
      var el=$('h-risers');if(!el)return;var R=[];try{R=day?risers(day):[]}catch(e){}
      $('h-risers-wrap').hidden=!R.length;
      var mx=Math.max(40,Math.max.apply(null,R.map(function(r){return r.m2||0}).concat([0])));
      el.innerHTML='<div class="cm3r-w">'+R.slice(0,5).map(function(r){
        var a=Math.max(0,Math.min(100,r.mp/mx*100)),b=Math.max(0,Math.min(100-a,(r.m2-r.mp)/mx*100));
        return '<button type="button" class="cm3r" data-p="'+r.p.id+'" data-m="PTS"><span class="cm3r-h"><b>'+X(r.p.name)+'</b><small>'+X(r.p.team)+' · '+X(tm(r.g.ts))+'</small><em>'+(r.startUp?'İlk 5':'+'+Math.round(r.d)+' dk')+'</em></span>'+
          '<span class="cm3r-bar"><i style="width:'+a.toFixed(0)+'%"></i><i class="up" style="left:'+a.toFixed(0)+'%;width:'+b.toFixed(0)+'%"></i></span>'+
          '<span class="cm3r-f"><span>'+Math.round(r.mp)+' → <b>'+Math.round(r.m2)+' dk</b>'+(r.outs&&r.outs.length?' · '+X(r.outs.map(function(m){return shortName(m.name)}).join(', '))+' OUT':'')+'</span>'+
          '<span>S/R/A '+Math.round(r.sp.pts)+'/'+Math.round(r.sp.reb)+'/'+Math.round(r.sp.ast)+' → <b>'+Math.round(r.s2.pts)+'/'+Math.round(r.s2.reb)+'/'+Math.round(r.s2.ast)+'</b></span></span></button>'}).join('')+'</div>';
      el.onclick=function(e){var b=e.target.closest('[data-p]');if(b)goPlayer(Number(b.dataset.p),b.dataset.m)};
    };
  }

  /* ---- 8B Günün alt önerileri: fark kartları ---- */
  if(typeof renderUnders==='function'){
    renderUnders=function(day){
      var el=$('h-unders');if(!el)return;var U=[];try{U=day?underList(day):[]}catch(e){}
      $('h-unders-wrap').hidden=!U.length;
      el.innerHTML='<div class="cm3u-w">'+U.slice(0,6).map(function(c){var d=c.mu-c.line;
        return '<div class="cm3u" data-p="'+c.p.id+'" data-m="'+X(c.mk)+'" role="button" tabindex="0"><b class="cm3u-n">'+X(c.p.name)+(c.ri&&c.ri.b2b?' <em>B2B</em>':'')+'</b>'+
          '<span class="cm3u-b">'+X(lbl(c.mk))+' '+X(c.line)+' alt</span><span class="cm3u-d">'+(d<0?'−':'+')+f1(Math.abs(d))+'</span>'+
          '<small>beklenti '+f1(c.mu)+' · L10 '+f1(c.a10)+' · rakip #'+X(c.rk)+' · model %'+pc(c.model)+'</small>'+
          '<span class="cm3u-k" role="button" tabindex="0" data-add="'+c.p.id+'|'+X(c.mk)+'|'+X(c.line)+'|under|">+ Kupon</span></div>'}).join('')+'</div>';
      el.onclick=function(e){if(e.target.closest('[data-add]'))return;var b=e.target.closest('[data-p]');if(b)goPlayer(Number(b.dataset.p),b.dataset.m)};
    };
  }

  /* ---- 1B Sakatlık bandı: yeni OUT çipleri, düğmeler altta ---- */
  function injBand(day){
    var bar=document.querySelector('#view-home .injbar'),ban=$('cm-live-source');if(!bar)return;
    var row=$('cm3-outs');
    if(!row){row=document.createElement('div');row.id='cm3-outs';row.className='cm3-outs';
      row.addEventListener('click',function(e){var b=e.target.closest('[data-p]');if(b&&P[b.dataset.p])goPlayer(Number(b.dataset.p))})}
    var host=ban||bar;
    if(row.previousElementSibling!==host)host.insertAdjacentElement('afterend',row);
    if(ban&&row.nextElementSibling!==bar)row.insertAdjacentElement('afterend',bar);
    var R=[];try{R=day?outBoost(day):[]}catch(e){}
    if(!R.length){row.hidden=true;row.innerHTML='';return}
    row.hidden=false;
    row.innerHTML='<span class="cm3-ol">Yeni OUT</span>'+R.slice(0,6).map(function(o){return '<button type="button" class="cm3-oc" data-p="'+o.m.id+'">'+X(shortName(o.m.name))+' <small>'+X(o.team)+'</small></button>'}).join('')+(R.length>6?'<span class="cm3-oc">+'+(R.length-6)+'</span>':'');
  }

  /* ---- 3C Vitrin'deki diğer bahisler + 4A Merdiven Altı ---- */
  function vitrinOthers(){
    var el=$('h-picks');if(!el)return;var IT=LAST.it||[];
    if(IT.length<2)return;
    var L=IT.slice(1).map(function(o){return o.c?{p:o.c.p,mk:o.c.mk,bet:o.c.il?o.c.il.n+'+':'~'+o.c.line,odd:o.c.il?o.c.il.odd:null,ev:o.c.il&&o.c.a?(o.c.ev!=null?o.c.ev:o.c.a.ev):null,model:o.c.model,g:o.c.g,opp:o.c.opp,line:o.c.line,lock:false}:
      (o.x&&o.x.d?{p:o.x.p||{id:o.x.d.id,name:o.x.d.name,team:o.x.d.team},mk:o.x.d.mk,bet:o.x.d.n?o.x.d.n+'+':'~'+o.x.d.line,odd:o.x.d.odd,ev:o.x.d.ev,model:o.x.d.model,g:null,opp:o.x.d.opp,line:o.x.d.line,lock:true}:null)}).filter(Boolean);
    el.innerHTML='<div class="cm3v-h">Vitrin\'deki diğer bahisler</div><div class="cm3v">'+L.map(function(c){
      return '<div class="cm3v-c" data-p="'+c.p.id+'" data-m="'+X(c.mk)+'" role="button" tabindex="0"><span class="cm3v-t"><b>'+X(c.p.name)+'</b><span class="cm3v-o">'+(c.odd?c.odd.toFixed(2):'–')+'</span></span>'+
        '<span class="cm3v-b">'+X(lbl(c.mk))+' '+X(c.bet)+'</span><span class="cm3v-f">'+(c.ev!=null?'<span class="'+(c.ev>=0?'up':'dn')+'">değer '+(c.ev>=0?'+':'')+Math.round(c.ev*100)+'%</span>':'<span></span>')+
        (c.model!=null?'<span class="mu">model %'+pc(c.model)+'</span>':'')+'</span>'+(c.lock?'<small class="mu">maç başladı, kilitli</small>':
        '<span class="cm3v-k" role="button" tabindex="0" data-add="'+c.p.id+'|'+X(c.mk)+'|'+X(c.line)+'|over|'+(c.odd||'')+'">+ Kupona ekle</span>')+'</div>'}).join('')+'</div>';
    el.onclick=function(e){if(e.target.closest('[data-add]'))return;var b=e.target.closest('[data-p]');if(b&&P[b.dataset.p])goPlayer(Number(b.dataset.p),b.dataset.m)};
  }
  function merdiven(day){
    var near=$('h-near');if(near){near.hidden=true;near.innerHTML=''}
    var oh=$('h-oth-head'),ot=$('h-others');if(oh)oh.hidden=true;if(ot){ot.innerHTML='';var pb=ot.closest('.paperbox');if(pb)pb.hidden=true}
    var y=$('cm-yk');if(y){y.hidden=true;y.innerHTML=''}
    var b=$('cm3-yk');
    if(!b){var anchor=y||near||$('h-picks');if(!anchor||!anchor.parentNode)return;b=document.createElement('div');b.id='cm3-yk';anchor.parentNode.insertBefore(b,anchor.nextSibling)}
    if(!b.__cm3){b.__cm3=1;b.addEventListener('click',function(e){if(e.target.closest('summary,[data-add]'))return;var t=e.target.closest('[data-p]');if(t&&P[t.dataset.p])goPlayer(Number(t.dataset.p),t.dataset.m)})}
    var L=[],W=[],vit={};try{(LAST.it||[]).forEach(function(o){var id=o.c?o.c.p.id:(o.x&&o.x.d?o.x.d.id:null);if(id)vit[id]=1})}catch(e){}
    try{if(day)L=cand(day).filter(function(c){return !vit[c.p.id]})}catch(e){console.error('cm-v3',e)}
    var taken=Object.assign({},vit);L.forEach(function(c){taken[c.p.id]=1});
    try{if(day)W=waiting(day,taken)}catch(e){}
    if(!L.length&&!W.length){b.hidden=true;b.innerHTML='';return}
    var INFO='<details class="cm-yk-info"><summary>Bu liste nasıl seçildi, kartlar ne demek?</summary><div class="cm-yk-ib">'+
      '<p>Vitrin\'e girmeyen ama Vitrin\'in temel kapılarını geçen bahisler: oyuncunun en az 5 maçı ve maç başına 22+ dakikası var, sakatlık listesinde "oynamaz" görünmüyor, en az bir destek sinyali var (rakip bu istatistikte ilk 10, son 10 maçın %60\'ında geçmiş ya da son 10 ortalaması çizginin üstünde), iddaa oranı 1.30–2.50 ve beklenen getiri −%8\'den kötü değil. Oyuncu başına iddaa merdivenindeki en iyi basamak gösterilir.</p>'+
      '<p><b>Çubuk</b>: yeşil kısım modelin tutma ihtimali. <b>Barem bekliyor</b> kartları modelin sevdiği ama iddaa\'nın henüz açmadığı bahisler; barem gelince normal karta döner.</p>'+
      '<p>Karne bu listenin oranlı bahislerini maç öncesi kaydeder (kasa birimine katılmaz, ayrı defter).</p>'+
      '<p class="cm-yk-warn">Bunlar öneri değil, izleme listesi. Oynamadan önce sakatlığı, kadroyu ve oranı kendin kontrol et.</p></div></details>';
    var h='<div class="cm-yk-box"><div class="cm-yk-hd"><span class="cm-yk-lamp" aria-hidden="true"></span><h3>Merdiven Altı</h3><span class="cm-yk-tag">ruhsatsız · oynamadan önce düşün</span></div>'+
      '<p class="note">Vitrin\'e giremeyen bahisler. İddaa marjı yüzünden çoğu modele göre sınırda ya da hafif eksidir.</p>'+INFO+'<div class="cm-yk-grid">';
    L.forEach(function(c,i){
      var pos=c.ev>=0;
      h+='<button type="button" class="cm-yk-r cm3m" style="--tilt:'+TILT[i%6]+'deg" data-p="'+c.p.id+'" data-m="'+X(c.mk)+'">'+
        '<span class="cm-yk-top"><b>'+X(c.p.name)+'</b><small>'+vs(c.p,c.g)+' '+X(c.opp)+' · '+X(tm(c.g.ts))+'</small></span>'+
        '<span class="cm-yk-bet">'+X(lbl(c.mk))+' '+X(c.n)+'+ <small>@'+c.odd.toFixed(2)+'</small></span>'+
        '<span class="cm3m-mi">model %'+pc(c.raw)+' · iddaa %'+pc(1/c.odd)+'</span><span class="cm3m-bar"><i style="width:'+pc(c.raw)+'%"></i></span>'+
        '<span class="cm3m-ev '+(pos?'p':'n')+'">getiri '+sg(c.ev)+'%</span></button>';
    });
    W.forEach(function(c,j){
      h+='<button type="button" class="cm-yk-r cm3m w" style="--tilt:'+TILT[(L.length+j)%6]+'deg" data-p="'+c.p.id+'" data-m="'+X(c.mk)+'">'+
        '<span class="cm-yk-top"><b>'+X(c.p.name)+'</b><small>'+vs(c.p,c.g)+' '+X(c.opp)+(c.g?' · '+X(tm(c.g.ts)):'')+'</small></span>'+
        '<span class="cm-yk-bet">'+X(lbl(c.mk))+' '+X(c.n)+'+ <small>barem bekliyor</small></span>'+
        '<span class="cm-yk-ch">'+(c.model!=null?'<span>model %'+pc(c.model)+'</span>':'')+(c.need&&isFinite(c.need)?'<span>en az '+c.need.toFixed(2)+'</span>':'')+'</span></button>';
    });
    b.innerHTML=h+'</div></div>';b.hidden=false;
  }

  /* ---- Karne ve Kasa şeridinde ad değişikliği: Kâğıt üstünde / Tribün → Merdiven Altı ---- */
  var REP=[[/Kâğıt üstüne/g,'Merdiven Altı\'na'],[/Kâğıt üstünde/g,'Merdiven Altı'],[/Kâğıt üstü/g,'Merdiven Altı'],[/Tribün/g,'Merdiven Altı']];
  function relabel(root){
    if(!root)return;var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null),n,L=[];
    while((n=w.nextNode()))if(/Kâğıt üstü|Tribün/.test(n.nodeValue))L.push(n);
    L.forEach(function(t){var v=t.nodeValue;REP.forEach(function(r){v=v.replace(r[0],r[1])});if(v!==t.nodeValue)t.nodeValue=v});
  }
  function watch(id){var r=$(id);if(!r||r.__cm3w)return;r.__cm3w=1;relabel(r);
    try{new MutationObserver(function(){relabel(r)}).observe(r,{childList:true,subtree:true,characterData:true})}catch(e){}}

  function after(){
    var day=(typeof S!=='undefined'&&S.hDay)||null;
    try{injBand(day)}catch(e){console.error('cm-v3 inj',e)}
    try{vitrinOthers()}catch(e){console.error('cm-v3 vitrin',e)}
    try{merdiven(day)}catch(e){console.error('cm-v3 merdiven',e)}
    try{watch('view-card');watch('h-karne');watch('h-chg')}catch(e){}
    var hg=$('h-games');if(hg)hg.classList.add('cm3-games');
  }
  if(typeof renderHome==='function'){var r0=renderHome;renderHome=function(){LAST.it=null;var r=r0.apply(this,arguments);after();return r}}
  window.cmAnaV3After=after;
  try{after()}catch(e){}
})();
