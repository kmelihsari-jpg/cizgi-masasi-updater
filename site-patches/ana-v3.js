/* Çizgi Masası · ana-v3 "Masa" — 21 Kasım 2026
   Melih'in onayladığı ana sayfa: Maçlar (M4: geniş vitrin şeridi; 24 Kasım), Gecenin vitrini aynen (diğer bahislerin
   satırlarında "neden" açıklaması her zaman görünür), Merdiven Altı (Kâğıt üstünde ve "Oran düşük ama değerli"
   buraya katıldı; düz satırlar, model/iddaa çubuğu, barem bekleyenler katlanır), Revir raporu (V1: her yeni OUT için kart, iki tablonun ilk 3 satırı, Takım sayfasına tek düğme), Yükselenler ve Günün alt önerileri kapalı çekmece.
   Karne: yeni dönemde Tribün (shadow) kaydı Merdiven Altı'nın SADECE oranlı adaylarıdır (tonightDoc sarmalayıcı;
   karne_automation.py başsız tarayıcıda aynı fonksiyonu çağırır). Barem bekleyenler karneye yazılmaz.
   Vitrin (Kasa) seçimi, Vitrin kartı, Karne kayıt kuralları ve Barem Geçmişi değişmez. */
(function(){
  if(window.__cmAnaV3)return;window.__cmAnaV3=1;
  var CFG={oMin:1.30,oMax:2.50,evMin:-.08,max:12,wait:8};
  var TILT=[-1,.8,-.6,.7,-.8,.5];
  var LAST={sp:null,day:null,it:null,oday:null,outs:null};
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
      var c={p:p,mk:r.mk,n:r.l.n,line:line,odd:odd,raw:raw,ev:ev,sup:sup,g:g,opp:r.opp,rk:r.rk,mu:r.mu,po:r.pos,h10:h10,a10:a10,nl:l10.length},o=best[p.id];
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
      seen[c.p.id]=1;out.push({p:c.p,mk:c.mk,n:Math.floor(c.line)+1,line:Math.floor(c.line)+.5,g:c.g,opp:c.opp,rk:c.rk,h10:c.h10,a10:c.a10,po:c.po,model:c.model!=null?c.model:(c.pr?c.pr.over:null),need:need});
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

  /* ---- Maçlar (N2): iki sütun liste, takım kodu kendi renginde etiket, derece, önerilen bahis ---- */
  function outsOf(day){if(LAST.oday!==day){LAST.oday=day;try{LAST.outs=day?outBoost(day):[]}catch(e){LAST.outs=[]}}return LAST.outs||[]}
  function lum(h){var m=/^#?([0-9a-f]{6})$/i.exec(String(h||''));if(!m)return 0;var n=parseInt(m[1],16);return (.299*(n>>16&255)+.587*(n>>8&255)+.114*(n&255))/255}
  function tag(t){var c=col(t);return '<span class="cm3n-t" style="background:'+c+';color:'+(lum(c)>.62?'#14181D':'#fff')+'">'+X(t)+'</span>'}
  /* M4 (24 Kasım): her maç geniş vitrin şeridi: solda saat+takımlar, ortada öne çıkan bahis ve haplar, sağda son 10 çubukları. */
  /* Takım kodu yazısı (24 Kasım): siyah zeminde okunur, her takım kendi markasına yakın BİRİNCİL renkle gösterilir; aynı maçtaki iki takımın rengi
     birbirine yakınsa (ör. iki mavi, iki kırmızı) ikinci renge geçilir. TC/TC2 yalnız tabloda olmayan kod için yedektir. */
  /*TXT_BASLA*/
  var TXT={ATL:['#FF4E50','#C8E000'],BOS:['#2FCB6E','#FFFFFF'],BKN:['#F2F2F2','#9CA3AF'],CHA:['#1FC8D6','#A78BFA'],CHI:['#FF2E2E','#FFFFFF'],
    CLE:['#E85A7C','#FDBB30'],DAL:['#4DA3FF','#C7CED6'],DEN:['#FFC72C','#6EA8FF'],DET:['#FF4D5A','#5B8CFF'],GSW:['#3E8BFF','#FFD23F'],
    HOU:['#FF3B5C','#C8CED3'],IND:['#FFC72C','#4C8DFF'],LAC:['#FF5470','#4AA0FF'],LAL:['#9D6BE8','#FDB927'],MEM:['#7C9BD6','#FFD23F'],
    MIA:['#F0476A','#FFB04A'],MIL:['#3CC36A','#F3E6C8'],MIN:['#3AA6E0','#7BD389'],NOP:['#D8B66A','#4DA3FF'],NYK:['#FF8A2B','#4C8DFF'],
    OKC:['#35B0FF','#FF8A2B'],ORL:['#4C8DFF','#E5E7EB'],PHI:['#3B82F6','#FF4D6A'],PHX:['#FF7A2B','#A77BF0'],POR:['#FF4040','#D9DEE3'],
    SAC:['#A56AE8','#E5E7EB'],SAS:['#C8D0D6','#FFFFFF'],TOR:['#EC4569','#C5CAD1'],UTA:['#A78BFA','#FFD23F'],WAS:['#5C80E0','#FF3B5C']};
  function rgbOf(h){var m=/^#?([0-9a-f]{6})$/i.exec(String(h||''));if(!m)return null;var n=parseInt(m[1],16);return [n>>16&255,n>>8&255,n&255]}
  function cdist(a,b){var x=rgbOf(a),y=rgbOf(b);if(!x||!y)return 999;var dr=x[0]-y[0],dg=x[1]-y[1],db=x[2]-y[2];return Math.sqrt(2*dr*dr+4*dg*dg+3*db*db)}
  var TXT_MIN=120;
  function pairColors(a,h){
    var A=TXT[a],H=TXT[h];
    if(!A||!H)return [tcol(a),tcol(h)];
    var combos=[[A[0],H[0]],[A[0],H[1]],[A[1],H[0]],[A[1],H[1]]],best=combos[0],bd=-1;
    for(var i=0;i<combos.length;i++){var d=cdist(combos[i][0],combos[i][1]);if(d>=TXT_MIN)return combos[i];if(d>bd){bd=d;best=combos[i]}}
    return best;
  }
  /*TXT_BITIR*/
  function tcol(t){
    var c=col(t),c2=col(t,true);
    if(lum(c)>=.45)return c;
    if(lum(c2)>=.45)return c2;
    var m=/^#?([0-9a-f]{6})$/i.exec(String(c||''));if(!m)return '#d0d0d6';
    var n=parseInt(m[1],16),r=n>>16&255,g=n>>8&255,b=n&255,k=.6;
    return 'rgb('+Math.round(r+(255-r)*k)+','+Math.round(g+(255-g)*k)+','+Math.round(b+(255-b)*k)+')';
  }
  function bars10(pid,mk,n,h){
    var g=[];try{g=(byP[pid]||[]).slice(-10)}catch(e){}
    if(!g.length)return '';
    var v=g.map(function(x){try{return +val(x,mk)||0}catch(e){return 0}}),mx=Math.max.apply(null,v.concat([n]))*1.1||1,hit=0;
    var bs=v.map(function(x){var ok=x>=n;if(ok)hit++;return '<i class="'+(ok?'h':'x')+'" style="height:'+Math.max(4,Math.round(x/mx*100))+'%" title="'+x+'"></i>'}).join('');
    return '<div class="cm4-bars" style="height:'+h+'px">'+bs+'<u style="bottom:'+((n-.5)/mx*100).toFixed(0)+'%"></u></div><div class="cm4-bl"><span>son '+v.length+'</span><span>'+hit+'/'+v.length+'</span></div>';
  }
  if(typeof cmGameCard==='function'){
    cmGameCard=function(g,picks){
      var k=dayKey(g.ts),top=(picks||[]).find(function(c){return c.g===g}),ev=null,gp=null;
      try{if(typeof cmEv==='function')ev=cmEv(g)}catch(e){}
      try{gp=gamePace(g)}catch(e){}
      var pc2=pairColors(g.away,g.home);
      function side(t,tc){var rc=null,ri=null;try{rc=teamRecord(t)}catch(e){}try{ri=restInfo(t,k)}catch(e){}
        return '<div class="cm4g-t"><b class="cm4g-c" style="color:'+tc+'">'+X(t)+'</b>'+(rc?'<small>'+rc.w+'-'+rc.l+'</small>':'')+(ri&&ri.b2b?'<em>B2B</em>':'')+'</div>'}
      var sub=[];
      try{if(ev&&ev.spread!=null&&ev.spread!==0)sub.push(X(ev.spread<0?g.home:g.away)+' -'+f1(Math.abs(ev.spread)))}catch(e){}
      if(gp&&gp.tag)sub.push(X(gp.tag)+(gp.p!=null?' '+f1(gp.p):''));
      var mid,rgt='';
      if(top){
        var pr=top.a&&top.a.w!=null?top.a.w:top.model,nn=top.il?top.il.n:(top.line!=null?Math.floor(top.line)+1:null);
        mid='<div class="cm4g-n">'+X(shortName(top.p.name))+' <small>'+X(lbl(top.mk))+(nn!=null?' '+nn+'+':'')+'</small></div><div class="cm4g-h">'+
          (pr!=null?'<span class="cm4h s">model %'+pc(pr)+'</span>':'')+(top.il&&top.il.odd?'<span class="cm4h">iddaa '+top.il.odd.toFixed(2)+'</span>':'')+'</div>';
        if(nn!=null)rgt=bars10(top.p.id,top.mk,nn,40);
      }else mid='<div class="cm4g-n mu">öne çıkan bahis yok</div>';
      return '<button class="gcard cm4g" data-home="'+X(g.home)+'" aria-label="'+X(g.away)+' @ '+X(g.home)+' '+X(tm(g.ts))+'">'+
        '<span class="cm4g-l"><span class="cm4-k">'+X(tm(g.ts))+(sub.length?' · '+sub.join(' · '):'')+'</span>'+side(g.away,pc2[0])+side(g.home,pc2[1])+'</span>'+
        '<span class="cm4g-m">'+mid+'</span><span class="cm4g-r">'+rgt+'</span></button>';
    };
  }
  function tabelaHead(){var hg=$('h-games');if(hg&&hg.querySelector('.cm4g'))hg.classList.add('cm4-list')}

  /* ---- Revir raporu (V1, 24 Kasım): her yeni OUT için bir kart; "Kim artıyor" ve "Yokken baremler" tablolarının ilk 3 satırı + Takım sayfasına tek düğme ---- */
  function sgn(x){var v=Math.round(x*10)/10;return (v>0?'+':v<0?'−':'')+Math.abs(v).toFixed(1)}
  function dcl(x){return x>0.04?'up':x<-0.04?'dn':''}
  function wobTop(o){
    var out=[];
    try{
      if(window.CM_WOB&&window.CM_WOB.rows){
        var rs=window.CM_WOB.rows(o.team,{m:o.m},false)||[];
        for(var i=0;i<rs.length&&out.length<3;i++)if(rs[i].n>=3)out.push(rs[i]);
      }
    }catch(e){console.error('cm-v4 wob',e)}
    return out;
  }
  function wobRowHtml(r){
    var cls=r.pr>=.6?'g':r.pr>=.45?'a':'r',v=r.v.slice(-10),mx=Math.max(r.li.line*1.6,Math.max.apply(null,v),1);
    return '<tr data-p="'+r.p.id+'" data-m="'+X(r.mk)+'" role="button" tabindex="0"><td><b>'+X(r.p.name)+'</b></td><td class="cm5v-mu">'+X(lbl(r.mk))+' '+X(r.li.txt)+(r.li.odd?' · '+r.li.odd.toFixed(2):'')+(r.li.src==='ort'?' <em>tahmini</em>':'')+'</td>'+
      '<td class="cm5v-h '+cls+'">'+r.h+'/'+r.n+' · %'+pc(r.pr)+'</td><td><span class="cm5v-b">'+v.map(function(x){return '<i class="'+(x>r.li.line?'w':'l')+'" style="height:'+Math.max(3,Math.round(x/mx*20))+'px"></i>'}).join('')+'</span></td></tr>';
  }
  if(typeof renderOuts==='function'){
    renderOuts=function(day){
      var wrap=$('h-outs-wrap'),el=$('h-outs');if(!wrap||!el)return;
      var R=day?outsOf(day):[];
      var C=[];
      R.forEach(function(o){
        var ben=[];
        (o.rows||[]).forEach(function(r){var bb=cmObBest(r);if(!bb)return;ben.push({r:r,b:bb,w:bb.v*({PTS:1,REB:2.2,AST:2.6}[bb.mk]||1)})});
        if(!ben.length)return;
        ben.sort(function(a,b){return b.w-a.w});
        C.push({o:o,ben:ben.slice(0,3),best:ben[0].w,n:Math.max.apply(null,ben.map(function(x){return x.r.n||0}))});
      });
      wrap.hidden=!C.length;if(!C.length){el.innerHTML='';return}
      C.sort(function(a,b){return b.best-a.best});
      el.innerHTML='<div class="cm5v-w">'+C.map(function(c){
        var o=c.o,a='';try{a=pav(o.m,'pav-s')}catch(e){}
        var t1='<table class="cm5v-t"><thead><tr><th>Kim artıyor</th><th>Dk</th><th>PTS</th><th>REB</th><th>AST</th></tr></thead><tbody>'+c.ben.map(function(x){var r=x.r,pa='';try{pa=pav(r.p,'pav-s')}catch(e){}
          return '<tr data-p="'+r.p.id+'" data-m="'+X(x.b.mk)+'" role="button" tabindex="0"><td>'+pa+'<b>'+X(r.p.name)+'</b></td><td class="'+dcl(r.dm)+'">'+sgn(r.dm)+'</td><td class="'+dcl(r.dp)+'">'+sgn(r.dp)+'</td><td class="'+dcl(r.dr)+'">'+sgn(r.dr)+'</td><td class="'+dcl(r.da)+'">'+sgn(r.da)+'</td></tr>'}).join('')+'</tbody></table>';
        var W=wobTop(o),t2=W.length?'<table class="cm5v-t cm5v-wb"><thead><tr><th>Yokken baremler</th><th>Bahis</th><th>Onsuz hit</th><th></th></tr></thead><tbody>'+W.map(wobRowHtml).join('')+'</tbody></table>':'';
        return '<div class="cm5v" style="border-top-color:'+col(o.team)+'"><div class="cm5v-hd">'+a+'<s>'+X(o.m.name)+'</s><em>OUT</em><span>'+X(o.team)+' '+(o.g&&o.g.home===o.team?'vs':'@')+' '+X(o.opp)+' · '+X(tm(o.g.ts))+' · onsuz '+c.n+' maç</span></div>'+
          t1+t2+'<button type="button" class="cm5v-go" data-team="'+X(o.team)+'" data-wk="'+o.m.id+'">Tam tabloları gör ›</button></div>'}).join('')+'</div>';
      el.onclick=function(e){
        var g=e.target.closest('.cm5v-go');
        if(g){S.team=g.dataset.team;S.woKey=Number(g.dataset.wk);S.cmWob=Number(g.dataset.wk);S.woBoth=false;setView('team');try{window.scrollTo(0,0)}catch(x){}return}
        var b=e.target.closest('[data-p]');if(b)goPlayer(Number(b.dataset.p),b.dataset.m)};
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

  /* ---- 4A Merdiven Altı ---- */
  function merdiven(day){
    var near=$('h-near');if(near){near.hidden=true;near.innerHTML=''}
    var oh=$('h-oth-head'),ot=$('h-others');if(oh)oh.hidden=true;if(ot){ot.innerHTML='';var pb=ot.closest('.paperbox');if(pb)pb.hidden=true}
    var y=$('cm-yk');if(y){y.hidden=true;y.innerHTML=''}
    var b=$('cm3-yk');
    if(!b){var anchor=y||near||$('h-picks');if(!anchor||!anchor.parentNode)return;b=document.createElement('div');b.id='cm3-yk';anchor.parentNode.insertBefore(b,anchor.nextSibling)}
    if(!b.__cm3){b.__cm3=1;b.addEventListener('click',function(e){if(e.target.closest('summary,[data-add],.cm-yk-info'))return;var t=e.target.closest('[data-p]');if(t&&P[t.dataset.p])goPlayer(Number(t.dataset.p),t.dataset.m)})}
    var L=[],W=[],vit={};try{(LAST.it||[]).forEach(function(o){var id=o.c?o.c.p.id:(o.x&&o.x.d?o.x.d.id:null);if(id)vit[id]=1})}catch(e){}
    try{if(day)L=cand(day).filter(function(c){return !vit[c.p.id]})}catch(e){console.error('cm-v3',e)}
    var taken=Object.assign({},vit);L.forEach(function(c){taken[c.p.id]=1});
    try{if(day)W=waiting(day,taken)}catch(e){}
    if(!L.length&&!W.length){b.hidden=true;b.innerHTML='';return}
    var INFO='<details class="cm-yk-info"><summary>Bu liste nasıl seçildi, kartlar ne demek?</summary><div class="cm-yk-ib">'+
      '<p>Vitrin\'e girmeyen ama Vitrin\'in temel kapılarını geçen bahisler: oyuncunun en az 5 maçı ve maç başına 22+ dakikası var, sakatlık listesinde "oynamaz" görünmüyor, en az bir destek sinyali var (rakip bu istatistikte ilk 10, son 10 maçın %60\'ında geçmiş ya da son 10 ortalaması çizginin üstünde), iddaa oranı 1.30–2.50 ve beklenen getiri −%8\'den kötü değil. Oyuncu başına iddaa merdivenindeki en iyi basamak gösterilir.</p>'+
      '<p><b>Eşleşme</b>: rakibin o istatistiği o pozisyona verme sırası. 1–10 güçlü, 11–20 orta, 21–30 zayıf (zayıf = rakip az veriyor, bahis zor). Çubuklar son 10 maç, kesik çizgi barem; yeşil çizgiyi geçen maç.</p>'+
      '<p><b>Barem bekliyor</b> satırları modelin sevdiği ama iddaa\'nın henüz açmadığı bahisler; barem gelince oranıyla üst satırlara geçer.</p>'+
      '<p>Karne bu listenin sadece iddaa baremi olan bahislerini maç öncesi kaydeder; günün son kaydında hâlâ baremi olmayanlar karneye girmez (kasa birimine katılmaz, ayrı defter).</p>'+
      '<p class="cm-yk-warn">Bunlar öneri değil, izleme listesi. Oynamadan önce sakatlığı, kadroyu ve oranı kendin kontrol et.</p></div></details>';
    var h='<div class="cm-yk-box"><div class="cm-yk-hd"><span class="cm-yk-lamp" aria-hidden="true"></span><h3>Merdiven Altı</h3><span class="cm3-stamp">RUHSATSIZ</span><span class="cm3-side">Vitrin\'e giremeyen, sınırdaki bahisler · ayrı defter · ✓/✗ şartlar, çubuklar son 10 maç</span></div>'+
      INFO+'<div class="cm3mr-l">';
    function why(c){var w=[];
      if(c.rk!=null&&c.rk<=10)w.push(X(c.opp)+(c.po?', '+X(c.po)+'\'ye':'')+' '+X(lbl(c.mk))+' vermede '+c.rk+'. sırada');
      if(c.h10&&c.h10.n)w.push('son '+c.h10.n+' maçın '+(c.h10.h!=null?c.h10.h:Math.round(c.h10.p*c.h10.n))+'\'inde '+c.n+'+ yaptı');
      else if(c.h10&&c.h10.p!=null)w.push('son 10 maçın %'+pc(c.h10.p)+'\'inde geçti');
      if(c.a10!=null&&isFinite(c.a10))w.push('son 10 ort. '+f1(c.a10));
      return w.join(' · ')}
    function av(p){try{return pav(p,'pav-s')}catch(e){return ''}}
    /* S2: şart listesi. Eşleşme = rakibin bu istatistiği o pozisyona verme sırası (1 = en çok veren, oyuncuya iyi). */
    function gates(c){
      var ip=pc(1/c.odd),L=[];
      L.push([c.ev>=0?'ok':'no',c.ev>=0?'✓':'✗',(c.ev>=0?'Değer var':'Değer yok')+' <span class="mu">· model %'+pc(c.raw)+', iddaa %'+ip+' · getiri '+sg(c.ev)+'%</span>']);
      if(c.rk==null)L.push(['mid','•','Eşleşme verisi yok']);
      else{
        var t=c.rk<=10?['ok','✓','Eşleşme güçlü']:c.rk<=20?['mid','~','Eşleşme orta']:['no','✗','<b class="cm4s-weak">Eşleşme zayıf</b>'];
        L.push([t[0],t[1],t[2]+' <span class="mu">· '+X(c.opp)+(c.po?', '+X(c.po)+'\'ye':'')+' '+X(lbl(c.mk))+' vermede #'+c.rk+'</span>']);
      }
      var hp=c.h10&&c.h10.p!=null?c.h10.p:null,hn=c.h10&&c.h10.n?c.h10.n:null,hh=c.h10&&c.h10.h!=null?c.h10.h:(hp!=null&&hn?Math.round(hp*hn):null);
      if(hp!=null)L.push([hp>=.6?'ok':'no',hp>=.6?'✓':'✗','Form <span class="mu">· son '+(hn||10)+' maçın '+(hh!=null?hh:Math.round(hp*10))+'\'inde '+c.n+'+'+(c.a10!=null&&isFinite(c.a10)?' · ort. '+f1(c.a10):'')+'</span>']);
      try{var dn=typeof cmDonusAd==='function'?cmDonusAd(c.p):null;if(dn)L.push(['mid','!','<b>'+X(shortName(dn))+' dönüyor olabilir</b> <span class="mu">· son maçlardaki payı o yokken şişmiş olabilir, Vitrin\'e almıyoruz</span>'])}catch(e){}
      return '<div class="cm4s-w">'+L.map(function(r){return '<div><span class="'+r[0]+'">'+r[1]+'</span><span>'+r[2]+'</span></div>'}).join('')+'</div>';
    }
    if(L.length)h+='<div class="cm4s-g">';
    L.forEach(function(c,i){
      h+='<div class="cm4s" data-p="'+c.p.id+'" data-m="'+X(c.mk)+'" role="button" tabindex="0">'+
        '<div class="cm4-k">'+vs(c.p,c.g)+' '+X(c.opp)+' · '+X(tm(c.g.ts))+'</div>'+
        '<div class="cm4s-hd">'+av(c.p)+'<b class="cm4s-n">'+X(c.p.name)+'</b><span class="cm4s-bet">'+X(lbl(c.mk))+' '+X(c.n)+'+</span><span class="cm4s-o">'+c.odd.toFixed(2)+'</span></div>'+
        gates(c)+bars10(c.p.id,c.mk,c.n,44)+
        '<span class="cm3mr-k cm4s-k" role="button" tabindex="0" aria-label="Kupona ekle" data-add="'+c.p.id+'|'+X(c.mk)+'|'+X(c.line)+'|over|'+c.odd+'">+ Kupon</span></div>';
    });
    if(L.length)h+='</div>';
    if(W.length){
      h+='<details class="cm3mr-wd"><summary>Barem bekleyen '+W.length+' bahis: '+W.slice(0,3).map(function(c){return X(shortName(c.p.name))+' '+X(lbl(c.mk))+' '+c.n+'+'}).join(', ')+(W.length>3?'…':'')+' ▾</summary>';
      W.forEach(function(c){
        h+='<div class="cm3mr w" data-p="'+c.p.id+'" data-m="'+X(c.mk)+'" role="button" tabindex="0">'+av(c.p)+
          '<div class="cm3mr-m"><div class="cm3mr-t"><b>'+X(c.p.name)+'</b><span class="cm3mr-bet">'+X(lbl(c.mk))+' '+X(c.n)+'+</span><small>'+vs(c.p,c.g)+' '+X(c.opp)+(c.g?' · '+X(tm(c.g.ts)):'')+'</small></div>'+
          '<div class="cm3mr-w">'+why(c)+'</div></div><div></div>'+
          '<div class="cm3mr-r"><span class="cm3mr-o mu">barem yok</span><small>'+(c.model!=null?'model %'+pc(c.model):'')+(c.need&&isFinite(c.need)?' · en az '+c.need.toFixed(2):'')+'</small></div><span></span></div>';
      });
      h+='</details>';
    }
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

  /* ---- Yükselenler ve Günün alt önerileri: kapalı çekmeceler ---- */
  function drawer(id,name,sumFn){
    var w=$(id);if(!w)return;var hd=w.querySelector('.mini-head'),h3=hd&&hd.querySelector('h3');if(!h3)return;
    w.classList.add('cm3-dr');if(!w.__cm3){w.__cm3=1;w.classList.add('closed');
      hd.addEventListener('click',function(e){if(e.target.closest('.sd-i'))return;w.classList.toggle('closed')})}
    var t=h3.firstChild;if(t&&t.nodeType===3)t.nodeValue=name;
    var s=hd.querySelector('.cm3-dr-s');if(!s){s=document.createElement('span');s.className='cm3-dr-s';h3.appendChild(s)}
    s.textContent=sumFn();
  }
  function drawers(day){
    drawer('h-risers-wrap','Yükselenler',function(){var R=[];try{R=day?risers(day):[]}catch(e){}return R.slice(0,3).map(function(r){return shortName(r.p.name)+' '+(r.startUp?'İlk 5':Math.round(r.mp)+'→'+Math.round(r.m2)+' dk')}).join(', ')});
    drawer('h-unders-wrap','Günün alt önerileri',function(){var U=[];try{U=day?underList(day):[]}catch(e){}return U.slice(0,2).map(function(c){return shortName(c.p.name)+' '+lbl(c.mk)+' '+c.line+' alt'}).join(', ')+(U.length>2?' +'+(U.length-2):'')});
    var oh=document.querySelector('#h-outs-wrap .mini-head h3');if(oh&&oh.firstChild&&oh.firstChild.nodeType===3)oh.firstChild.nodeValue='Revir raporu';
    var ph=document.querySelector('#view-home .picks .sec-head');if(ph&&!ph.querySelector('.cm3-side')){var n=document.createElement('span');n.className='cm3-side';n.textContent='Vitrin · değerli bahisler · Kasa defteri';ph.appendChild(n)}
  }

  function after(){
    var day=(typeof S!=='undefined'&&S.hDay)||null;
    try{merdiven(day)}catch(e){console.error('cm-v3 merdiven',e)}
    try{tabelaHead()}catch(e){}
    try{drawers(day)}catch(e){console.error('cm-v3 drawer',e)}
    try{watch('view-card');watch('h-karne');watch('h-chg')}catch(e){}
  }
  if(typeof renderHome==='function'){var r0=renderHome;renderHome=function(){LAST.it=null;LAST.oday=null;var r=r0.apply(this,arguments);after();return r}}
  window.cmAnaV3After=after;
  try{after()}catch(e){}
})();
