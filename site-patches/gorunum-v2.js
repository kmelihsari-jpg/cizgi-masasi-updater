/* Çizgi Masası · gorunum-v2 — 19 Kasım 2026
   1A Oyuncu: "Bu geceki senaryo" kartı (bu gece OUT olan takım arkadaşı otomatik seçili, karşılaştırma).
   8A Oyuncu: Eşleşme özeti kutuları sekme olur; alttaki tekrar eden sekme satırı gizlenir (CSS).
   9A Oyuncu: maç kadrosu yan listesi (arama, takım sekmesi, İlk 5 / Yedek / Oynamayacak, bahis rozeti).
   6B Sorgu: cümle kurucu; takıma ve rakip oyuncuya karşı (oyuncu takım değiştirse de).
   7C Karne: seçilen gün "kupon fişi".
   Sadece görüntü: Vitrin, Öneriler, Kasa, Karne kayıtları ve iddaa arşivine hiçbir şey yazmaz. */
(function(){
  if(window.__cmV2)return;window.__cmV2=1;
  function E(x){try{return esc(x)}catch(e){return String(x==null?'':x)}}
  function F(x,d){try{return fmt(x,d)}catch(e){return x==null?'–':String(x)}}
  function safe(name,fn){return function(){try{return fn.apply(this,arguments)}catch(err){console.error('cm-v2 '+name,err)}}}
  function sname(n){try{return shortName(n)}catch(e){return String(n||'')}}
  function injS(p){try{var i=injOf(p.name);return i&&i[0]!=='AVAILABLE'&&i[0]!=='P'?i[0]:null}catch(e){return null}}
  function hcl(p){return p==null?'':p>=.6?'g':p>=.45?'a':'r'}
  function pc(p){return p==null?'–':'%'+Math.round(p*100)}

  /* =================== 1A · Bu geceki senaryo =================== */
  var AUTO_KEY='cm-senaryo-oto';
  function autoOn(){try{return localStorage.getItem(AUTO_KEY)!=='0'}catch(e){return true}}
  function setAuto(on){try{localStorage.setItem(AUTO_KEY,on?'1':'0')}catch(e){}}
  function matesOf(p){return Object.values(P).filter(function(m){return m.team===p.team&&m.id!==p.id&&byP[m.id]&&mpg(m.id)>=14}).sort(function(a,b){return mpg(b.id)-mpg(a.id)})}
  function playDates(id){var s=new Set();(byP[id]||[]).forEach(function(x){s.add(x.ds)});(HIST[id]||[]).forEach(function(x){s.add(x.ds)});return s}
  function onsuzN(pid,m){var h=new Set((byP[m.id]||[]).map(function(x){return x.d}));return (byP[pid]||[]).filter(function(x){return !h.has(x.d)}).length}
  function autoOuts(pid){
    var p=P[pid];if(!p||!byP[pid])return [];if(injS(p)==='OUT')return [];if(!gameOf(p.team))return [];
    var c=matesOf(p).filter(function(m){return injS(m)==='OUT'&&onsuzN(pid,m)>=3});
    /* Örneklem en az 5 maç kalacak şekilde ekle (önce çok dakika alan); hiçbiri tutmazsa en çok onsuz maçı olan tek oyuncu (3+). */
    var chosen=[],union=new Set(),own=byP[pid]||[],cnt=function(u){return own.filter(function(x){return x.t===p.team&&!u.has(x.ds)}).length};
    c.forEach(function(m){var u=new Set(union);playDates(m.id).forEach(function(x){u.add(x)});if(cnt(u)>=5){chosen.push(m.id);union=u}});
    if(!chosen.length&&c.length){var best=null,bn=0;c.forEach(function(m){var n=cnt(playDates(m.id));if(n>bn){bn=n;best=m}});if(best&&bn>=3)chosen.push(best.id)}
    return chosen.map(String);
  }
  if(typeof openPlayer==='function'){var _op=openPlayer;openPlayer=function(id){window.__cmSc=Number(id);return _op.apply(this,arguments)}}
  if(typeof renderAll==='function'){var _ra=renderAll;renderAll=function(){
    try{if(window.__cmSc!=null&&window.__cmSc===S.pid){window.__cmSc=null;S.cmAuto=[];if(autoOn()){var a=autoOuts(S.pid);if(a.length){S.outs=a.slice();S.cmAuto=a.slice();S.min=null}}}}catch(e){console.error('cm-v2 auto',e)}
    return _ra.apply(this,arguments)}}

  function sampleWith(o){var keep={outs:S.outs,loc:S.loc,minM:S.minM};try{if('outs' in o)S.outs=o.outs;if('loc' in o)S.loc=o.loc;if('minM' in o)S.minM=o.minM;return curSample()}finally{S.outs=keep.outs;S.loc=keep.loc;S.minM=keep.minM}}
  function stat(sample){var mk=S.mk,l=S.line==null?0:S.line,side=S.side||'over',n=sample.length;if(!n)return {n:0,p:null,avg:null};
    var v=sample.map(function(x){return val(x,mk)}),h=v.filter(function(x){return side==='over'?x>l:x<l}).length;return {n:n,p:h/n,avg:v.reduce(function(a,b){return a+b},0)/n,h:h}}
  function restTxt(t,k){try{var r=restInfo(t,k);if(!r)return '';if(r.b2b)return t+' B2B (dün de oynadı)';if(r.rest>=2)return t+' '+r.rest+' gün dinlendi';if(r.rest===1)return t+' 1 gün dinlendi';return ''}catch(e){return ''}}
  function scHtml(){
    var p=P[S.pid];if(!p||!byP[S.pid])return '';
    var g0=gameOf(p.team),mates=matesOf(p),on=autoOn(),own=injS(p);
    var chips=[],shown=0;
    var ranked=mates.map(function(m){var n=onsuzN(S.pid,m),st=injS(m);return {m:m,n:n,st:st,sel:S.outs.indexOf(String(m.id))>=0}})
      .filter(function(x){return x.n>0||x.sel});
    ranked.sort(function(a,b){var ia=(a.st==='OUT'?2:a.st?1:0),ib2=(b.st==='OUT'?2:b.st?1:0);return (b.sel-a.sel)||(ib2-ia)||(mpg(b.m.id)-mpg(a.m.id))});
    var extra=[];
    ranked.forEach(function(x){
      var t='<button type="button" class="cmsc-c'+(x.sel?' on':'')+(x.st==='OUT'?' out':x.st?' q':'')+'" data-mate="'+x.m.id+'" aria-pressed="'+x.sel+'">'+E(sname(x.m.name))+' yokken<small>'+x.n+'M'+(x.st?' · '+E(x.st):'')+'</small></button>';
      if(x.sel||x.st||shown<4){chips.push(t);shown++}else extra.push(t)});
    if(g0){var home=g0.home===p.team,lk=home?'h':'a',ln=(byP[S.pid]||[]).filter(function(x){return home?x.home:!x.home}).length,lon=S.loc===lk;
      chips.push('<button type="button" class="cmsc-c'+(lon?' on':'')+'" data-scloc="'+lk+'" aria-pressed="'+lon+'">'+(home?'Ev':'Deplasman')+'<small>'+ln+'M</small></button>')}
    if(extra.length)chips.push('<details class="cmsc-more"><summary>+'+extra.length+'</summary><div>'+extra.join('')+'</div></details>');
    var active=S.outs.length||S.loc!=='all'||S.minM>0;
    var base=stat(sampleWith({outs:[],loc:'all',minM:0})),cur=stat(curSample());
    var lab=(MK[S.mk]?MK[S.mk].label:S.mk)+' '+(S.side==='under'?'alt ':'')+F(S.line);
    var cmp='<div class="cmsc-cmp"><div class="cmsc-b"><span class="lbl">Tüm maçlar</span><b class="'+hcl(base.p)+'">'+pc(base.p)+'</b><small>ort '+F(base.avg)+' · '+base.n+' maç</small></div>'+
      '<span class="cmsc-ar">→</span><div class="cmsc-b'+(active?' act':'')+'"><span class="lbl">'+(active?'Senaryo':'Senaryo (filtre yok)')+'</span><b class="'+hcl(cur.p)+'">'+pc(cur.p)+'</b><small>ort '+F(cur.avg)+' · '+cur.n+' maç</small></div></div>';
    var ctx=[];
    if(g0){var k=dayKey(g0.ts),r1=restTxt(p.team,k),r2=restTxt(S.opp,k);if(r1)ctx.push(r1);if(r2)ctx.push(r2);
      var ho=Object.values(P).filter(function(m){return m.team===S.opp&&byP[m.id]&&mpg(m.id)>=15&&injS(m)==='OUT'}).sort(function(a,b){return mpg(b.id)-mpg(a.id)});
      if(ho.length)ctx.unshift('Rakipte OUT: '+ho.slice(0,3).map(function(m){return sname(m.name)}).join(', ')+(ho.length>3?' +'+(ho.length-3):''))}
    var warn=active&&cur.n<5?'<div class="cmsc-w">Örneklem küçük ('+cur.n+' maç). Sonucu temkinli oku.</div>':'';
    var autoNote=S.cmAuto&&S.cmAuto.length&&S.cmAuto.every(function(id){return S.outs.indexOf(id)>=0})?'<span class="cmsc-an">bu gecenin OUT\'ları otomatik seçildi</span>':'';
    return '<div class="cmsc"><div class="cmsc-h"><span class="lbl or">Bu geceki senaryo · '+E(lab)+'</span>'+autoNote+
      '<button type="button" class="cmsc-tog'+(on?' on':'')+'" data-sctog="1" title="Bu gece OUT olan takım arkadaşlarını oyuncu açılınca otomatik seç" aria-pressed="'+on+'"><span>otomatik</span><i></i></button></div>'+
      (own==='OUT'?'<div class="cmsc-w">Oyuncu bu gece OUT.</div>':'')+
      '<div class="cmsc-chips">'+(chips.join('')||'<span class="note">Takım arkadaşı yokken oynadığı maç yok.</span>')+'</div>'+cmp+warn+
      (ctx.length?'<div class="cmsc-ctx">'+ctx.map(E).join(' · ')+'</div>':'')+
      '<div class="cmsc-ft"><button type="button" data-scmore="1">Diğer filtreler ▸</button>'+(active?'<button type="button" data-scclr="1">Sıfırla</button>':'')+'<button type="button" data-scoutt="1" aria-expanded="false">OUT işaretle ▾</button></div><div class="cmsc-outs" hidden></div></div>';
  }
  var scRender=safe('senaryo',function(){
    var box=document.getElementById('qouts');if(!box||!S.pid||!P[S.pid])return;
    var keep=box.querySelector('.cmsc-outs'),wasOpen=keep&&!keep.hidden,row=document.querySelector('#injbox .outrow')||(keep&&keep.querySelector('.outrow'));
    box.innerHTML=scHtml();box.classList.add('cmsc-on');
    var slot=box.querySelector('.cmsc-outs');if(slot&&row){slot.appendChild(row);if(wasOpen){slot.hidden=false;var b=box.querySelector('[data-scoutt]');if(b)b.setAttribute('aria-expanded','true')}}
    if(!box.__cmsc){box.__cmsc=1;box.addEventListener('click',function(e){
      var t=e.target.closest('[data-sctog]');if(t){var on=!autoOn();setAuto(on);S.min=null;if(on){var a=autoOuts(S.pid);S.outs=a;S.cmAuto=a.slice()}else{if(S.cmAuto&&S.cmAuto.length)S.outs=S.outs.filter(function(x){return S.cmAuto.indexOf(x)<0});S.cmAuto=[]}renderAll();return}
      var l=e.target.closest('[data-scloc]');if(l){S.loc=S.loc===l.dataset.scloc?'all':l.dataset.scloc;S.min=null;renderAll();return}
      if(e.target.closest('[data-scclr]')){S.outs=[];S.loc='all';S.minM=0;S.cmAuto=[];S.min=null;renderAll();return}
      if(e.target.closest('[data-scmore]')){var d=document.querySelector('#view-player details.fbox');if(d){d.open=true;d.scrollIntoView({block:'nearest',behavior:'smooth'})}return}
      var o=e.target.closest('[data-scoutt]');if(o){var s=box.querySelector('.cmsc-outs');if(s){s.hidden=!s.hidden;o.setAttribute('aria-expanded',String(!s.hidden))}}})}
  });
  /* Sakatlık kutusundaki tekrarlar (önerilen filtre, rakipte, dinlenmiş) karta taşındı. */
  if(typeof renderInj==='function'){var _ri=renderInj;renderInj=function(){try{document.querySelectorAll('#qouts .cmsc-outs .outrow').forEach(function(x){x.remove()})}catch(e){}var r=_ri.apply(this,arguments);try{
    var b=document.getElementById('injbox');if(b){b.querySelectorAll(':scope > .chips').forEach(function(x){x.remove()});
      b.querySelectorAll(':scope > .note').forEach(function(x){if(/^Rakipte:/.test(x.textContent.trim()))x.remove()});
      b.querySelectorAll(':scope > .warnline.okline').forEach(function(x){x.remove()})}}catch(e){console.error('cm-v2 inj',e)}return r}}
  if(typeof renderResults==='function'){var _rr=renderResults;renderResults=function(){var r=_rr.apply(this,arguments);scRender();return r}}

  /* =================== 9A · Maç kadrosu yan listesi =================== */
  var BETC={k:null,m:{}};
  function betMap(day){
    var key=day+'|'+(typeof INJV!=='undefined'?INJV:0)+'|'+(typeof lines!=='undefined'&&lines?Object.keys(lines).length:0);if(BETC.k===key)return BETC.m;
    var m={};try{var sp=pickSplit(day);(sp.bets||[]).concat(sp.others||[]).forEach(function(c){if(c&&c.p&&!m[c.p.id])m[c.p.id]={mk:c.mk,kasa:(sp.bets||[]).indexOf(c)>=0}})}catch(e){}
    BETC={k:key,m:m};return m;
  }
  function starters(list){var st=list.filter(function(p){var g=(byP[p.id]||[]).slice(-3);return g.length&&g.filter(function(x){return x.start}).length>=2});
    st.sort(function(a,b){return mpg(b.id)-mpg(a.id)});return st.slice(0,5)}
  function plItem(p,bm){var st=injS(p),b=bm[p.id];
    return '<button class="pl pl2 cm-pl-i'+(st==='OUT'?' is-out':'')+'" data-p="'+p.id+'" aria-current="'+(p.id===S.pid)+'" title="'+E(p.name)+'">'+ib(p)+
      '<span class="pl-t"><span class="pl-nm">'+E(p.name)+'</span><small>'+F(mpg(p.id),0)+' dk'+(st?' · <span class="st '+E(st)+'">'+E(st)+'</span>':'')+'</small></span>'+
      (b&&st!=='OUT'?'<span class="cm-pl-b'+(b.kasa?' k':'')+'" title="Bu gece öne çıkan bahis">'+E(MK[b.mk]?MK[b.mk].label:b.mk)+'</span>':'')+'</button>'}
  function plBody(){
    var g=S.game;if(!g)return '<span class="note">Bir maç seç.</span>';
    var bm=betMap(dayKey(g.ts)),q=norm(S.cmPlQ||'');
    var all=Object.values(P).filter(function(p){return byP[p.id]&&(p.team===g.away||p.team===g.home)});
    if(q){var r=all.filter(function(p){return norm(p.name).indexOf(q)>=0}).sort(function(a,b){return mpg(b.id)-mpg(a.id)});
      return r.length?r.map(function(p){return plItem(p,bm)}).join(''):'<span class="note">Bu maçta “'+E(S.cmPlQ)+'” yok.</span>'}
    var t=S.cmPlT,list=all.filter(function(p){return p.team===t}).sort(function(a,b){return mpg(b.id)-mpg(a.id)});
    var out=list.filter(function(p){var s=injS(p);return s==='OUT'||s==='D'}),ok=list.filter(function(p){return out.indexOf(p)<0});
    var st5=starters(ok),bench=ok.filter(function(p){return st5.indexOf(p)<0}),bMain=bench.filter(function(p){return mpg(p.id)>=6}),bLow=bench.filter(function(p){return mpg(p.id)<6});
    var h='';
    if(st5.length)h+='<div class="cm-pl-g">İlk 5</div>'+st5.map(function(p){return plItem(p,bm)}).join('');
    if(bMain.length)h+='<div class="cm-pl-g">Yedek</div>'+bMain.map(function(p){return plItem(p,bm)}).join('');
    if(bLow.length)h+='<details class="cm-pl-more"><summary>Az süre alanlar ('+bLow.length+')</summary>'+bLow.map(function(p){return plItem(p,bm)}).join('')+'</details>';
    if(out.length)h+='<div class="cm-pl-g">Oynamayacak</div>'+out.map(function(p){return plItem(p,bm)}).join('');
    return h||'<span class="note">Oyuncu bulunamadı.</span>';
  }
  function plTabs(){var g=S.game;if(!g)return '';return [g.away,g.home].map(function(t){var on=t===S.cmPlT,c=TC[t]||'#555';
    return '<button type="button" class="cm-pl-tab'+(on?' on':'')+'" data-plt="'+t+'" aria-pressed="'+on+'" style="--tc:'+c+'">'+t+'<small>'+(t===g.home?'ev':'dep')+'</small></button>'}).join('')}
  var _rpl=typeof renderPlist==='function'?renderPlist:null;
  renderPlist=function(){
    try{
      var box=$('plist'),title=$('plist-title');if(!box)return;
      if(!S.game){if(_rpl)return _rpl.apply(this,arguments);return}
      var g=S.game,gk=g.ts+'|'+g.home;
      var inG=P[S.pid]&&(P[S.pid].team===g.away||P[S.pid].team===g.home);
      if(S.cmPlG!==gk){S.cmPlG=gk;S.cmPlQ='';S.cmPlT=inG?P[S.pid].team:g.away}
      else if(inG&&S.cmPlPid!==S.pid)S.cmPlT=P[S.pid].team;
      S.cmPlPid=S.pid;
      title.textContent=g.away+' @ '+g.home;
      if(!box.querySelector('.cm-pl-q')){
        box.classList.add('cm-pl');
        box.innerHTML='<input class="cm-pl-q" type="search" placeholder="Bu maçta ara…" aria-label="Bu maçta oyuncu ara" autocomplete="off"><div class="cm-pl-tabs"></div><div class="cm-pl-body"></div>';
        var inp=box.querySelector('.cm-pl-q');inp.addEventListener('input',function(){S.cmPlQ=inp.value;box.querySelector('.cm-pl-body').innerHTML=plBody();box.querySelector('.cm-pl-tabs').hidden=!!inp.value.trim()});
        box.onclick=function(e){var t=e.target.closest('[data-plt]');if(t){S.cmPlT=t.dataset.plt;box.querySelector('.cm-pl-tabs').innerHTML=plTabs();box.querySelector('.cm-pl-body').innerHTML=plBody();return}
          var b=e.target.closest('[data-p]');if(b){openPlayer(Number(b.dataset.p));if(innerWidth<=860){var pn=$('pname');if(pn)pn.scrollIntoView({block:'start'})}}};
      }
      var q=box.querySelector('.cm-pl-q');if(document.activeElement!==q)q.value=S.cmPlQ||'';
      var tb=box.querySelector('.cm-pl-tabs');tb.innerHTML=plTabs();tb.hidden=!!(S.cmPlQ||'').trim();
      box.querySelector('.cm-pl-body').innerHTML=plBody();
    }catch(err){console.error('cm-v2 plist',err);if(_rpl){try{$('plist').innerHTML='';_rpl()}catch(e){}}}
  };
  /* Oyuncu değişince seçili oyuncunun takımına geç. */
  if(typeof renderPHead==='function'){var _rph=renderPHead;renderPHead=function(){var r=_rph.apply(this,arguments);try{
    var b=$('plist');if(b&&b.querySelector('.cm-pl-body')){b.querySelectorAll('[data-p]').forEach(function(x){x.setAttribute('aria-current',String(Number(x.dataset.p)===S.pid))})}}catch(e){}return r}}

  /* =================== 6B+ · Sorgu: cümle kurucu =================== */
  var QS={init:false,pid:null,mk:'PTS',ln:'',ss:'both',vsT:'',vsP:[],mates:[],lc:'all',st:'all',b2:'all',rg:'0'};
  var ROWI=null;
  function rowIdx(){var key=Object.keys(HIST).length+'|'+Object.keys(byP).length;if(ROWI&&ROWI.key===key)return ROWI;var m={};
    function add(id,g){(m[id]||(m[id]={}))[g.ds]=g}
    for(var id in byP)byP[id].forEach(function(g){add(id,g)});for(var id2 in HIST)HIST[id2].forEach(function(g){add(id2,g)});ROWI={key:key,m:m};return ROWI}
  function pidOf(v){if(!v)return null;var k=norm(v);var id=byName[(typeof ALIAS!=='undefined'&&ALIAS[k])||k];return id||null}
  function qName(id){return P[id]?P[id].name:'#'+id}
  function szLbl(z){if(z==='cur')return "26-27";var m=String(histSeason||'').match(/(\d{2})(\d{2})-(\d{2})/);return m?m[2]+'-'+m[3]:'geçen'}
  function qGames(pid){var all=[];
    if(QS.ss!=='last')(byP[pid]||[]).forEach(function(g){all.push(Object.assign({},g,{sz:'cur'}))});
    if(QS.ss!=='cur')(HIST[pid]||[]).forEach(function(g){all.push(Object.assign({},g,{sz:'last'}))});
    all.forEach(function(g){g.sv=g.start!=null?g.start:(g.gs!=null?g.gs:null)});
    return all.filter(function(g){return g.min>0}).sort(function(a,b){return a.ds<b.ds?-1:a.ds>b.ds?1:0})}
  function onCourt(B,g,x){var r=B.ros[g.o+'|'+g.ds];return !!(r&&r.has(Number(x)))}
  function xTeamThen(B,g,x){var z=qryZ(g.ds),s=B.span[z+'|'+g.o+'|'+Number(x)];return !!(s&&g.ds>=s.a&&g.ds<=s.b)}
  function qBase(pid,cols){var B=qryBuild(),noStart=0;
    var f=qGames(pid).filter(function(g){
      if(QS.st!=='all'){if(g.sv==null){noStart++;return false}if(QS.st==='s'&&g.sv!==1)return false;if(QS.st==='b'&&g.sv===1)return false}
      if(QS.lc==='h'&&g.home!==1)return false;if(QS.lc==='a'&&g.home===1)return false;
      if(QS.b2!=='all'){var was=teamDS(g.t).has(dayAdd(g.ds,-1));if(QS.b2==='b2b'&&!was)return false;if(QS.b2==='rest'&&was)return false}
      if(qryVal(g,cols)==null)return false;
      for(var i=0;i<QS.mates.length;i++){var c=QS.mates[i],z=qryZ(g.ds),s=B.span[z+'|'+g.t+'|'+c.id];if(!s||g.ds<s.a||g.ds>s.b)return false;var r=B.ros[g.t+'|'+g.ds],pl=!!(r&&r.has(c.id));if((c.mode==='with')!==pl)return false}
      return true});
    return {f:f,B:B,noStart:noStart}}
  function rg(f){var r=QS.rg;return r==='l5'?f.slice(-5):r==='l10'?f.slice(-10):r==='l20'?f.slice(-20):f}
  function sumUp(f,cols,line){var n=f.length;if(!n)return {n:0};var v=f.map(function(g){return qryVal(g,cols)}),avg=v.reduce(function(a,b){return a+b},0)/n,s=v.slice().sort(function(a,b){return a-b}),med=n%2?s[(n-1)/2]:(s[n/2-1]+s[n/2])/2;
    var o={n:n,avg:avg,med:med};if(isFinite(line)){o.h=v.filter(function(x){return x>line}).length;o.p=o.h/n}return o}
  function qOpts(){return Object.keys(MK).map(function(k){return '<option value="'+k+'"'+(k===QS.mk?' selected':'')+'>'+MK[k].label+'</option>'}).join('')}
  function qInit(){
    if(QS.init)return;QS.init=true;
    var v=$('view-qry');if(!v)return;
    v.querySelectorAll('.qpanel,.qres,.qcmp,.qk,.qchart,#q-tab').forEach(function(x){x.hidden=true;x.style.display='none'});
    var w=document.createElement('div');w.id='cmq';
    var teams=(D.teams||[]).slice().sort();
    w.innerHTML='<div class="cmq-s">'+
      '<input id="cmq-pl" class="cmq-in cmq-pl" list="cmq-pll" placeholder="Oyuncu" autocomplete="off" aria-label="Oyuncu">'+
      '<span class="cmq-vs" id="cmq-vsc"></span>'+
      '<input id="cmq-vs" class="cmq-in cmq-vsin" list="cmq-vsl" placeholder="+ takıma / oyuncuya karşı" autocomplete="off" aria-label="Takıma ya da oyuncuya karşı">'+
      '<select id="cmq-mk" class="cmq-ch" aria-label="Bahis türü">'+qOpts()+'</select>'+
      '<input id="cmq-ln" class="cmq-in cmq-ln" inputmode="decimal" placeholder="çizgi" aria-label="Çizgi (üstü)">'+
      '<span class="cmq-w">üstü yaptı mı,</span>'+
      '<select id="cmq-ss" class="cmq-ch" aria-label="Sezon"><option value="both">son 2 sezon</option><option value="cur">bu sezon</option><option value="last">geçen sezon</option></select>'+
      '<select id="cmq-add" class="cmq-ch cmq-plus" aria-label="Koşul ekle"></select></div>'+
      '<div class="cmq-cond" id="cmq-cond"></div><div class="cmq-sug" id="cmq-sug"></div><div id="cmq-out"></div>'+
      '<datalist id="cmq-pll">'+Object.values(P).map(function(p){return p.name}).sort().map(function(n){return '<option value="'+E(n)+'"></option>'}).join('')+'</datalist>'+
      '<datalist id="cmq-vsl">'+teams.map(function(t){return '<option value="'+t+' (takım)"></option>'}).join('')+Object.values(P).filter(function(p){return byP[p.id]&&mpg(p.id)>=10}).map(function(p){return p.name}).sort().map(function(n){return '<option value="'+E(n)+'"></option>'}).join('')+'</datalist>';
    var head=v.querySelector('.qhead');if(head){head.after(w);var nt=head.querySelector('.note');if(nt)nt.textContent='Cümleyi kur: oyuncu, kime karşı (takım ya da rakip oyuncu), bahis ve çizgi. Rakip oyuncu seçersen o oyuncunun sahada olduğu maçlar sayılır; takım değiştirdiyse eski takımındaki maçlar da gelir. Bu ve geçen sezonun maçları.'}else v.prepend(w);
    if(S.pid&&P[S.pid]){QS.pid=S.pid;$('cmq-pl').value=P[S.pid].name;QS.mk=S.mk||'PTS';$('cmq-mk').value=QS.mk;if(S.line!=null)$('cmq-ln').value=S.line}
    $('cmq-pl').addEventListener('change',function(){var id=pidOf(this.value);QS.pid=id;QS.mates=[];QS.vsP=QS.vsP.filter(function(x){return x!==id});renderQry()});
    $('cmq-pl').addEventListener('input',function(){var id=pidOf(this.value);if(id&&id!==QS.pid){QS.pid=id;QS.mates=[];renderQry()}});
    $('cmq-vs').addEventListener('change',function(){var s=this.value.trim();this.value='';if(!s)return;var m=s.match(/^([A-Za-z]{2,3})(\s*\(takım\))?$/);
      if(m&&(D.teams||[]).indexOf(m[1].toUpperCase())>=0){QS.vsT=m[1].toUpperCase()}else{var id=pidOf(s);if(id&&id!==QS.pid&&QS.vsP.indexOf(id)<0)QS.vsP.push(id)}renderQry()});
    $('cmq-mk').addEventListener('change',function(){QS.mk=this.value;renderQry()});
    $('cmq-ln').addEventListener('input',function(){QS.ln=this.value;renderQry()});
    $('cmq-ss').addEventListener('change',function(){QS.ss=this.value;renderQry()});
    $('cmq-add').addEventListener('change',function(){var x=this.value;this.value='';if(!x)return;var k=x.split(':');
      if(k[0]==='tm'){var id=Number(k[1]);if(!QS.mates.some(function(c){return c.id===id}))QS.mates.push({id:id,mode:'out'})}else QS[k[0]]=k[1];renderQry()});
    w.addEventListener('click',function(e){
      var x=e.target.closest('[data-qx]');if(x){var k=x.dataset.qx,a=k.split(':');
        if(a[0]==='vsT')QS.vsT='';else if(a[0]==='vsP')QS.vsP=QS.vsP.filter(function(i){return i!==Number(a[1])});
        else if(a[0]==='tm')QS.mates=QS.mates.filter(function(c){return c.id!==Number(a[1])});
        else QS[a[0]]=a[0]==='rg'?'0':'all';renderQry();return}
      var m=e.target.closest('[data-qmode]');if(m){var c=QS.mates.find(function(c){return c.id===Number(m.dataset.qmode)});if(c){c.mode=c.mode==='out'?'with':'out';renderQry()}return}
      var s=e.target.closest('[data-qsug]');if(s){var v2=s.dataset.qsug;if(/^[A-Z]{3}$/.test(v2))QS.vsT=QS.vsT===v2?'':v2;else{var id=Number(v2);var i=QS.vsP.indexOf(id);if(i>=0)QS.vsP.splice(i,1);else QS.vsP.push(id)}renderQry();return}
      var r=e.target.closest('tr[data-qd]');if(r&&QS.pid){try{goPlayer(QS.pid,QS.mk)}catch(_){}}});
  }
  function qAddOpts(){
    var o='<option value="">+ koşul</option><optgroup label="Yer"><option value="lc:h">evde</option><option value="lc:a">deplasmanda</option></optgroup>'+
      '<optgroup label="Rol"><option value="st:s">ilk 5 iken</option><option value="st:b">yedekken</option></optgroup>'+
      '<optgroup label="Dinlenme"><option value="b2:b2b">B2B (dün de oynadı)</option><option value="b2:rest">dinlenmiş</option></optgroup>'+
      '<optgroup label="Aralık"><option value="rg:l5">son 5 maç</option><option value="rg:l10">son 10 maç</option><option value="rg:l20">son 20 maç</option></optgroup>';
    if(QS.pid){try{var gr=qryMates(QS.pid,QS.ss),taken=new Set(QS.mates.map(function(c){return c.id}));
      gr.forEach(function(g){var l=g.list.filter(function(x){return !taken.has(x.id)}).slice(0,14);if(l.length)o+='<optgroup label="Takım arkadaşı yokken · '+E(g.label)+'">'+l.map(function(x){return '<option value="tm:'+x.id+'">'+E(qName(x.id))+' ('+x.n+' maç)</option>'}).join('')+'</optgroup>'})}catch(e){}}
    return o}
  function qCondHtml(){var c=[],L={lc:{h:'evde',a:'deplasmanda'},st:{s:'ilk 5 iken',b:'yedekken'},b2:{b2b:'B2B',rest:'dinlenmiş'},rg:{l5:'son 5 maç',l10:'son 10 maç',l20:'son 20 maç'}};
    ['lc','st','b2','rg'].forEach(function(k){var v=QS[k];if(v&&v!=='all'&&v!=='0')c.push('<span class="cmq-c">'+L[k][v]+'<button type="button" data-qx="'+k+'" aria-label="Kaldır">✕</button></span>')});
    QS.mates.forEach(function(m){c.push('<span class="cmq-c"><button type="button" class="cmq-mode" data-qmode="'+m.id+'" title="yokken / oynarken">'+E(sname(qName(m.id)))+' '+(m.mode==='out'?'yokken':'oynarken')+' ⇄</button><button type="button" data-qx="tm:'+m.id+'" aria-label="Kaldır">✕</button></span>')});
    return c.join('')}
  function qVsHtml(){var c=[];if(QS.vsT)c.push('<span class="cmq-c cmq-vt" style="--tc:'+(TC[QS.vsT]||'#555')+'">vs '+QS.vsT+'<button type="button" data-qx="vsT" aria-label="Kaldır">✕</button></span>');
    QS.vsP.forEach(function(id){var p=P[id];c.push('<span class="cmq-c cmq-vp">'+(p?ib(p):'')+E(qName(id))+' sahada<button type="button" data-qx="vsP:'+id+'" aria-label="Kaldır">✕</button></span>')});return c.join('')}
  function qSugHtml(){var p=P[QS.pid];if(!p)return '';var g=gameOf(p.team);if(!g)return '';var opp=g.home===p.team?g.away:g.home;
    var top=Object.values(P).filter(function(m){return m.team===opp&&byP[m.id]&&injS(m)!=='OUT'}).sort(function(a,b){return mpg(b.id)-mpg(a.id)}).slice(0,5);
    return '<span class="lbl">Bu gece</span><button type="button" class="cmq-sb'+(QS.vsT===opp?' on':'')+'" data-qsug="'+opp+'">vs '+opp+'</button>'+top.map(function(m){var on=QS.vsP.indexOf(m.id)>=0;return '<button type="button" class="cmq-sb'+(on?' on':'')+'" data-qsug="'+m.id+'">'+ib(m)+E(sname(m.name))+'</button>'}).join('')}
  function rowTr(lab,s,hasLine,cls){if(!s.n)return '<tr class="'+(cls||'')+'"><td>'+lab+'</td><td class="n">0</td><td class="n">–</td><td class="n">–</td><td></td></tr>';
    var w=hasLine?Math.round(s.p*100):0;return '<tr class="'+(cls||'')+'"><td>'+lab+'</td><td class="n">'+s.n+'</td><td class="n">'+F(s.avg)+'</td><td class="n '+(hasLine?hcl(s.p):'')+'">'+(hasLine?s.h+'/'+s.n+' · '+pc(s.p):'–')+'</td><td class="cmq-bc">'+(hasLine?'<div class="cmq-bar"><i class="'+hcl(s.p)+'" style="width:'+w+'%"></i></div>':'')+'</td></tr>'}
  var _rq=typeof renderQry==='function'?renderQry:null;
  renderQry=function(){
    try{
      qInit();try{qryStarts()}catch(e){}
      var out=$('cmq-out');if(!out)return _rq&&_rq();
      $('cmq-vsc').innerHTML=qVsHtml();$('cmq-cond').innerHTML=qCondHtml();$('cmq-add').innerHTML=qAddOpts();$('cmq-sug').innerHTML=qSugHtml();
      $('cmq-ss').value=QS.ss;$('cmq-mk').value=QS.mk;
      var pid=QS.pid;if(!pid||!P[pid]){out.innerHTML='<p class="note">Listeden bir oyuncu seç.</p>';return}
      var cols=MK[QS.mk].c,line=parseFloat(String(QS.ln).replace(',','.')),hasLine=isFinite(line);
      var qb=qBase(pid,cols),B=qb.B,base=qb.f;
      var isVsT=function(g){return !QS.vsT||g.o===QS.vsT},isVsP=function(g){return QS.vsP.every(function(x){return onCourt(B,g,x)})};
      var main=rg(base.filter(function(g){return isVsT(g)&&isVsP(g)}));
      var S0=sumUp(rg(base),cols,line),SM=sumUp(main,cols,line);
      var vsLab=[];if(QS.vsT)vsLab.push('vs '+QS.vsT);QS.vsP.forEach(function(x){vsLab.push(sname(qName(x))+' sahada')});
      var lab=vsLab.length?vsLab.join(' + '):'Seçili maçlar';
      var trs=[rowTr('Genel',S0,hasLine,'')];
      if(vsLab.length)trs.push(rowTr('<b>'+E(lab)+'</b>',SM,hasLine,'cmq-main'));
      if(QS.vsT&&QS.vsP.length)trs.push(rowTr('vs '+E(QS.vsT)+' (hepsi)',sumUp(rg(base.filter(function(g){return g.o===QS.vsT})),cols,line),hasLine,''));
      QS.vsP.forEach(function(x){var nm=sname(qName(x));
        if(QS.vsT||QS.vsP.length>1)trs.push(rowTr(E(nm)+' sahada',sumUp(rg(base.filter(function(g){return onCourt(B,g,x)})),cols,line),hasLine,''));
        trs.push(rowTr(E(nm)+' yokken (takımına karşı)',sumUp(rg(base.filter(function(g){return xTeamThen(B,g,x)&&!onCourt(B,g,x)})),cols,line),hasLine,''))});
      var big=hasLine&&SM.n?'<b class="cmq-big '+hcl(SM.p)+'">'+SM.h+' / '+SM.n+'</b><span>'+pc(SM.p)+' · ort '+F(SM.avg)+' · medyan '+F(SM.med)+'</span>':SM.n?'<b class="cmq-big">'+F(SM.avg)+'</b><span>ort '+MK[QS.mk].label+' · medyan '+F(SM.med)+' · '+SM.n+' maç</span>':'<b class="cmq-big">0</b><span>Bu koşullarda maç yok</span>';
      var delta=hasLine&&vsLab.length&&S0.n&&SM.n?'<div class="cmq-d">genel <b>'+pc(S0.p)+'</b> → '+E(lab)+' <b class="'+hcl(SM.p)+'">'+pc(SM.p)+'</b></div>':'';
      var shown=main.slice(-30),mx=Math.max.apply(null,shown.map(function(g){return qryVal(g,cols)}).concat(hasLine?[line]:[1]));
      var bars=shown.length?'<div class="cmq-bars">'+(hasLine?'<div class="cmq-ln2" style="bottom:'+(line/mx*100)+'%"><span>'+F(line)+'</span></div>':'')+shown.map(function(g){var v=qryVal(g,cols);return '<i class="'+(hasLine?(v>line?'o':'u'):'')+'" style="height:'+Math.max(3,v/mx*100)+'%" title="'+E(g.ds+' · '+(g.home?'':'@')+g.o+' · '+v)+'"></i>'}).join('')+'</div><div class="cmq-bl"><span>'+E(fmtD(shown[0].ds))+" '"+shown[0].ds.slice(2,4)+'</span><span>'+E(fmtD(shown[shown.length-1].ds))+" '"+shown[shown.length-1].ds.slice(2,4)+'</span></div>':'';
      var RI=rowIdx().m,cs=[['pts','PTS'],['reb','REB'],['ast','AST'],['fg3m','3PM'],['stl','STL'],['blk','BLK']];
      var th='<tr><th class="l">Tarih</th><th>Sezon</th><th class="l">Maç</th>'+QS.vsP.map(function(x){return '<th>'+E(sname(qName(x)))+' dk</th>'}).join('')+'<th>Rol</th><th>Dk</th>'+cs.map(function(c){return '<th'+(cols.indexOf(c[0])>=0?' class="sel"':'')+'>'+c[1]+'</th>'}).join('')+(cols.length>1?'<th class="sel">'+MK[QS.mk].label+'</th>':'')+(hasLine?'<th>Çizgi</th>':'')+'</tr>';
      var trs2=main.slice().reverse().slice(0,120).map(function(g){var v=qryVal(g,cols);
        return '<tr data-qd="'+g.ds+'"><td class="l">'+g.ds+'</td><td><span class="cmq-sz">'+szLbl(g.sz)+'</span></td><td class="l">'+g.t+' '+(g.home?'vs':'@')+' <span style="color:'+(TC[g.o]||'inherit')+'">'+g.o+'</span></td>'+
          QS.vsP.map(function(x){var r=(RI[x]||{})[g.ds];return '<td>'+(r?Math.round(r.min):'–')+'</td>'}).join('')+
          '<td>'+(g.sv==null?'–':g.sv===1?'<span class="qp s">İlk 5</span>':'<span class="qp b">Yedek</span>')+'</td><td>'+Math.round(g.min)+'</td>'+
          cs.map(function(c){return '<td'+(cols.indexOf(c[0])>=0?' class="sel"':'')+'>'+(g[c[0]]==null?'–':g[c[0]])+'</td>'}).join('')+(cols.length>1?'<td class="sel">'+v+'</td>':'')+
          (hasLine?'<td><span class="qp '+(v>line?'o':'u')+'">'+(v>line?'Üst':'Alt')+'</span></td>':'')+'</tr>'}).join('');
      var note=qb.noStart?'<p class="note">Geçen sezonun '+qb.noStart+' maçında ilk 5 bilgisi yok; rol koşuluna girmedi.</p>':'';
      out.innerHTML='<div class="cmq-res"><div class="cmq-card"><span class="lbl">Cevap</span>'+big+delta+'</div>'+
        '<div class="cmq-card cmq-tbl"><span class="lbl">Karşılaştırma'+(hasLine?' · '+MK[QS.mk].label+' '+F(line)+' üstü':'')+'</span><table><thead><tr><th class="l">Durum</th><th class="n">Maç</th><th class="n">Ort</th><th class="n">Hit</th><th></th></tr></thead><tbody>'+trs.join('')+'</tbody></table></div>'+
        '<div class="cmq-card"><span class="lbl">'+E(lab)+' · son '+shown.length+' maç</span>'+(bars||'<p class="note">Maç yok.</p>')+'</div></div>'+note+
        (main.length?'<div class="tablewrap cmq-tab"><table><thead>'+th+'</thead><tbody>'+trs2+'</tbody></table></div>':'<div class="qempty">Bu koşullarla maç yok.</div>');
    }catch(err){console.error('cm-v2 sorgu',err);if(_rq)try{_rq()}catch(e){}}
  };

  /* =================== 7C · Karne gün fişi =================== */
  function gameTime(r){try{var g=slate.find(function(s){return dayKey(s.ts)===r.date&&(s.home===r.team||s.away===r.team)});return g?tm(g.ts):null}catch(e){return null}}
  function dayLong(k){var a=k.split('-').map(Number);return new Date(Date.UTC(a[0],a[1]-1,a[2],12)).toLocaleDateString('tr-TR',{day:'numeric',month:'long',weekday:'long',timeZone:'UTC'})}
  function fisRow(r){
    var p=P[r.id],bet=(MK[r.mk]?MK[r.mk].label:r.mk)+' '+(r.n?r.n+'+':'~'+r.line);
    var tag=r.kind==='kasa'&&r.tag&&r.tag!=='deger'?' <em class="ktag '+E(r.tag)+'">'+E((typeof KTAG!=='undefined'&&KTAG[r.tag])||r.tag)+'</em>':'';
    var right='';
    if(r.res==='hit')right='<b class="pos">'+E(r.real)+' ✓</b>';
    else if(r.res==='miss'){var need=(r.n||Math.floor(r.line)+1),gap=need-r.real;right='<b class="neg">'+E(r.real)+' ✗</b>'+(gap>0&&gap<=1?'<small>'+gap+' eksik</small>':'')}
    else if(r.res==='void')right='<span class="mu">oynamadı</span>';
    else{var t=gameTime(r);right='<span class="mu">⏳ '+(t||'bekliyor')+'</span>'}
    var un=r.kind==='old'||!r.odd?'':r.res==='hit'?'+'+F(r.odd-1,2):r.res==='miss'?'−1':r.res==='void'?'0':'';
    return '<button class="kf-r '+E(r.res)+'" data-p="'+r.id+'" data-m="'+E(r.mk)+'">'+(p?pav(p,'pav-s'):'<span class="kf-av"></span>')+
      '<span class="kf-who"><b>'+E(r.name)+'</b><small>'+E(r.team||'')+(r.opp?' – '+E(r.opp):'')+tag+'</small></span>'+
      '<span class="kf-bet"><b>'+E(bet)+'</b><small>'+(r.odd?'iddaa '+F(r.odd,2):'oransız')+'</small></span>'+
      '<span class="kf-res">'+right+'</span><span class="kf-u">'+un+'</span></button>'}
  var fisRender=safe('karne',function(){
    var el=$('r-list');if(!el||!KV||!KV.d)return;
    var Z=realStats(),rows=kRows(Z.rows,KV.v),DD=kDays(rows),x=DD[KV.d];if(!x)return;
    var stamp,cls;
    if(x.p&&!x.n){stamp='AÇIK';cls='open'}else if(x.un){stamp=(x.u>=0?'+':'−')+F(Math.abs(x.u),1);cls=x.u>=0?'win':'loss'}else{stamp=x.h+'/'+x.n;cls=x.h*2>=x.n?'win':'loss'}
    var info=x.all.length+' seçim · '+x.h+'/'+x.n+' tuttu'+(x.p?' · '+x.p+' bekliyor':'')+(x.v?' · '+x.v+' iade':'');
    var order={hit:0,miss:1,void:2,pending:3},list=x.all.slice().sort(function(a,b){return (order[a.res]-order[b.res])});
    el.innerHTML='<div class="kf"><div class="kf-h"><div><b class="kf-d">'+E(dayLong(KV.d))+'</b><small>'+E(info)+'</small></div><span class="kf-st '+cls+'">'+E(stamp)+'</span></div>'+
      '<div class="kf-l">'+list.map(fisRow).join('')+'</div><div class="kf-f"><span>'+(KV.v==='kasa'?'Kasa defteri':'Kâğıt üstünde')+' · her bahis 1 birim</span><span>Çizgi Masası</span></div></div>';
  });
  if(typeof renderCard==='function'){var _rc=renderCard;renderCard=function(){var r=_rc.apply(this,arguments);fisRender();return r}}
})();
