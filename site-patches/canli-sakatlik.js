/* Cizgi Masasi - NBA Official canli sakatlik baglantisi.
   GitHub -> Cloudflare D1 -> herkese acik salt-okunur API.
   NBA kaynagi guncel degilse eski rapor tahminlere uygulanmaz.
   ESPN snapshot API ile okunur; resmî NBA önceliği korunur. */
(function () {
  'use strict';
  var API = 'https://cizgi-masasi-api.k-melihsari.workers.dev/api/nba-injuries';
  var ESPN_API = 'https://cizgi-masasi-api.k-melihsari.workers.dev/api/espn-injuries';
  var ESPN_REFRESH_API = 'https://cizgi-masasi-api.k-melihsari.workers.dev/api/refresh-espn';
  var PERIOD_MS = 2 * 60 * 1000;
  var MAX_AGE_MS = 24 * 60 * 60 * 1000;
  var fetching = false;
  var lastKey = '';
  var ready = false;
  var banner;
  var espnData = null;
  var officialData = null;
  var officialTime = null;
  var ESPN_MAX_AGE = 4 * 60 * 60 * 1000;
  // Mevcut app.js'deki injBase fonksiyonu bu degiskeni okuyor.
  window.CMREMOTE = null;
  var TEAM_ABBR = {
    AtlantaHawks:'ATL',BostonCeltics:'BOS',BrooklynNets:'BKN',CharlotteHornets:'CHA',
    ChicagoBulls:'CHI',ClevelandCavaliers:'CLE',DallasMavericks:'DAL',DenverNuggets:'DEN',
    DetroitPistons:'DET',GoldenStateWarriors:'GSW',HoustonRockets:'HOU',IndianaPacers:'IND',
    LAClippers:'LAC',LosAngelesLakers:'LAL',MemphisGrizzlies:'MEM',MiamiHeat:'MIA',
    MilwaukeeBucks:'MIL',MinnesotaTimberwolves:'MIN',NewOrleansPelicans:'NOP',NewYorkKnicks:'NYK',
    OklahomaCityThunder:'OKC',OrlandoMagic:'ORL',Philadelphia76ers:'PHI',PhoenixSuns:'PHX',
    PortlandTrailBlazers:'POR',SacramentoKings:'SAC',SanAntonioSpurs:'SAS',TorontoRaptors:'TOR',
    UtahJazz:'UTA',WashingtonWizards:'WAS'
  };
  var STATES = {OUT:'OUT',QUESTIONABLE:'Q',DOUBTFUL:'D',PROBABLE:'P',AVAILABLE:'AVAILABLE',Q:'Q',D:'D',P:'P',DTD:'DTD',GTD:'GTD'};
  function el(id){return document.getElementById(id)}
  function setText(message, mode){
    if (!banner) return;
    banner.textContent = message;
    banner.dataset.state = mode || 'info';
  }
  function initBanner(){
    if(banner) return;
    var bar = document.querySelector('.injbar');
    if(!bar) return;
    banner = document.createElement('div');
    banner.id = 'cm-live-source';
    banner.setAttribute('role','status');
    bar.insertAdjacentElement('afterend',banner);
    setText('NBA resmî raporu kontrol ediliyor…');
    // ESPN: gercek kaynak cekimi. NBA: kayitli resmî raporu yeniden oku.
    var btn = el('inj-up');
    if(btn){
      btn.textContent = 'ESPN’i kontrol et';
      btn.onclick = function(){refresh(true, 'espn')};
    }
    var nb = el('nba-inj-check');
    if(nb){
      nb.textContent = 'NBA resmî raporu kontrol et';
      nb.onclick = function(){refresh(true, 'nba')};
    }
  }
  function parseUtc(s){
    if(typeof s!=='string'||!s) return NaN;
    return Date.parse(s.replace(' ','T')+'Z');
  }
  function normName(s){
    return String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase()
      .replace(/[.'’\-]/g,'').replace(/\b(jr|sr|ii|iii|iv)\b/g,'').replace(/\s+/g,' ').trim();
  }
  function safeStatus(s){return STATES[String(s||'').toUpperCase()]||null}
  // ESPN DTD (day-to-day) bir maç katılım tahmini değildir.
  // Bu nedenle DTD ile NBA Q/D/P/O aynı düzeyde karşılaştırılamaz.
  // Yalnızca açıkça birbirine ters katılım kararlarını 'gerçek çelişki' say.
  function compareSources(nba,espn){
    if(nba===espn)return 'uyumlu';
    if(espn==='DTD'||espn==='GTD'||nba==='DTD'||nba==='GTD')return 'farklilik';
    if((nba==='OUT'&&(espn==='AVAILABLE'||espn==='P'))||
       (espn==='OUT'&&(nba==='AVAILABLE'||nba==='P')))
      return 'celiski';
    return 'farklilik';
  }
  function safeTeamForPlayer(name){
    // Oyuncu adını sitemizdeki mevcut kadro verisiyle kontrol et.
    // Kadroda olmayan ESPN kayıtları uyarı için tutulur ama analize uygulanmaz.
    if(typeof P!=='object'||!P)return null;
    var key=normName(name), matches=[];
    for(var id in P){
      var p=P[id];
      if(p&&normName(p.name)===key&&typeof p.team==='string')matches.push(p.team);
    }
    return matches.length===1?matches[0]:null;
  }
  function checkValid(data){
    if(!data||data.success!==true||!data.report||!Array.isArray(data.players))
      throw Error('NBA API rapor döndürmedi');
    if(data.report.player_count!==data.players.length||!data.players.length)
      throw Error('NBA raporu eksik / oyuncu sayısı uyuşmuyor');
    var time=parseUtc(data.report.updated_at);
    if(!Number.isFinite(time)||time>Date.now()+5*60*1000)
      throw Error('NBA rapor tarihi geçersiz');
    if(Date.now()-time>MAX_AGE_MS)
      throw Error('NBA raporu 24 saatten eski');
    return time;
  }

  var ESPN_TEAMS={
    'Atlanta Hawks':'ATL','Boston Celtics':'BOS','Brooklyn Nets':'BKN',
    'Charlotte Hornets':'CHA','Chicago Bulls':'CHI','Cleveland Cavaliers':'CLE',
    'Dallas Mavericks':'DAL','Denver Nuggets':'DEN','Detroit Pistons':'DET',
    'Golden State Warriors':'GSW','Houston Rockets':'HOU','Indiana Pacers':'IND',
    'LA Clippers':'LAC','Los Angeles Clippers':'LAC','Los Angeles Lakers':'LAL',
    'Memphis Grizzlies':'MEM','Miami Heat':'MIA','Milwaukee Bucks':'MIL',
    'Minnesota Timberwolves':'MIN','New Orleans Pelicans':'NOP','New York Knicks':'NYK',
    'Oklahoma City Thunder':'OKC','Orlando Magic':'ORL','Philadelphia 76ers':'PHI',
    'Phoenix Suns':'PHX','Portland Trail Blazers':'POR','Sacramento Kings':'SAC',
    'San Antonio Spurs':'SAS','Toronto Raptors':'TOR','Utah Jazz':'UTA',
    'Washington Wizards':'WAS'
  };
  function normalizedTeam(value){
    var raw=String(value||'').trim();
    if(TEAM_ABBR[raw])return TEAM_ABBR[raw];
    if(ESPN_TEAMS[raw])return ESPN_TEAMS[raw];
    return ESPN_TEAMS[raw.replace(/([a-z])([A-Z])/g,'$1 $2')]||null;
  }
  function parseEspn(data){
    if(!data||data.success!==true||!Array.isArray(data.players))throw Error('ESPN API biçimi geçersiz');
    if(data.count!==data.players.length)throw Error('ESPN oyuncu sayısı uyuşmuyor');
    var collected=parseUtc(data.last_check);
    if(!Number.isFinite(collected)||collected>Date.now()+5*60000||Date.now()-collected>ESPN_MAX_AGE)
      throw Error('ESPN kontrolü güncel değil');
    var list=Object.create(null), teams=Object.create(null);
    for(var p of data.players){
      if(!p||typeof p.player_name!=='string'||!p.player_name.trim())continue;
      var t=normalizedTeam(p.team), state=safeStatus(p.status);
      if(!state||!t)continue;
      var key=normName(p.player_name);
      // ESPN'de aynı isimle birden çok takım kaydı varsa otomatik eşleştirme yapma.
      if(teams[key]&&teams[key]!==t){delete list[key];teams[key]='AMBIGUOUS';continue}
      if(teams[key]==='AMBIGUOUS')continue;
      teams[key]=t;
      list[key]=[state,'ESPN · geçici bilgi (kontrol: '+new Date(collected).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul',hour:'2-digit',minute:'2-digit'})+' TSİ)','ESPN'];
    }
    return {list:list,teams:teams,checkedAt:collected,count:data.players.length};
  }
  function statusSummary(){
    var rm=window.CMREMOTE;
    var count=rm?Object.keys(rm.conflicts||{}).length:0;
    var differences=rm?Object.keys(rm.differences||{}).length:0;
    var withheld=rm?Object.keys(rm.unverified||{}).length:0;
    var only=rm?Object.keys(rm.espnOnly||{}).length:0;
    var extra=(count?' · ⚠ '+count+' gerçek çelişki (NBA esas)':'')+(differences?' · '+differences+' durum farklılığı (NBA esas)':'')+(only?' · '+only+' ESPN-only bildirimi (NBA listesinde yok; analize uygulanmaz)':'')+(withheld?' · '+withheld+' takım eşleşmesi doğrulanamayan ESPN kaydı (analize uygulanmaz)':'');
    var esp=espnData?' · ESPN '+espnData.count+' kayıt (kontrol saati; haber saati değil)':' · ESPN canlı yedeği kullanılamıyor';
    if(rm){var time=new Date(rm.updatedAt).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
      setText('NBA Official · '+Object.keys(rm.list).length+' oyuncu · Son aktarım '+time+' (TSİ)'+esp+extra+' · NBA verisi analizlerde önceliklidir.','ok');
    }else if(espnData){setText('Resmî NBA raporu güncel değil · ESPN geçici: '+espnData.count+' kayıt. Verinin yayımlanma zamanı bilinmiyor.','warn')}
    else setText('Canlı sakatlık kaynakları kullanılamıyor; eski veriler güncel olmayabilir.','warn');
  }
  function apply(data,time){
    var list=Object.create(null), submitted=new Set(), missing=new Set();
    var missingNames=[];
    try{missingNames=JSON.parse(data.report.not_submitted_json||'[]')}catch(e){throw Error('Takım rapor bilgisi bozuk')}
    if(!Array.isArray(missingNames)) throw Error('Takım rapor bilgisi bozuk');
    missingNames.forEach(function(t){if(TEAM_ABBR[t]) missing.add(TEAM_ABBR[t])});
    for(var p of data.players){
      if(!p||typeof p.player_name!=='string'||typeof p.reason!=='string'||!TEAM_ABBR[p.team])
        throw Error('NBA oyuncu / takım bilgisi eksik');
      var s=safeStatus(p.status);
      if(!s) throw Error('NBA sakatlık durumu tanınmadı');
      submitted.add(TEAM_ABBR[p.team]);
      var k=normName(p.player_name);
      if(list[k]) throw Error('Çakışan oyuncu kaydı: '+p.player_name);
      list[k]=[s,p.reason+' (NBA Official)',p.report_key||data.report.report_key];
    }
    // D1 kaydi ancak butun oyuncular dogrulandiktan sonra uygulanir.
    var key=data.report.report_key+'|'+data.report.updated_at+'|'+data.players.length+'|ESPN:'+
      (espnData?espnData.checkedAt:'none');
    var conflicts=Object.create(null), differences=Object.create(null), extra=Object.create(null), unverified=Object.create(null), officialTeams=Object.create(null);
    data.players.forEach(function(p){officialTeams[normName(p.player_name)]=TEAM_ABBR[p.team]});
    if(espnData){
      for(var ek of Object.keys(espnData.list)){
        var et=espnData.teams[ek];
        // Takım doğruluğu bilinen oyuncularda ESPN'nin farklı takım kaydı risklidir.
        var localTeam=safeTeamForPlayer(ek);
        if(localTeam&&localTeam!==et){unverified[ek]={espnTeam:et,siteTeam:localTeam};continue}
        if(Object.prototype.hasOwnProperty.call(list,ek)){
          if(officialTeams[ek]!==et) {unverified[ek]={espnTeam:et,officialTeam:officialTeams[ek]};continue}
          var verdict=compareSources(list[ek][0],espnData.list[ek][0]);
          if(verdict==='celiski')conflicts[ek]={nba:list[ek][0],espn:espnData.list[ek][0]};
          if(verdict==='farklilik')differences[ek]={nba:list[ek][0],espn:espnData.list[ek][0]};
        }else if(et&&submitted.has(et)){
          extra[ek]=espnData.list[ek][0]; // uyarı; analize uygulanmaz
        }
      }
      Object.keys(conflicts).forEach(function(ck){
        list[ck][1]+=' · ⚠ ESPN: '+conflicts[ck].espn+' (gerçek çelişki; NBA esas)';
      });
      Object.keys(differences).forEach(function(ck){
        list[ck][1]+=' · ℹ ESPN: '+differences[ck].espn+' (durum farklılığı; NBA esas)';
      });
    }
    window.CMREMOTE={list:list,submitted:submitted,missing:missing,espn:espnData?espnData.list:null,
      conflicts:conflicts,differences:differences,unverified:unverified,espnOnly:extra,
      espnTeams:espnData?espnData.teams:null,updatedAt:time,reportKey:data.report.report_key};
    statusSummary();
    if(key!==lastKey){
      lastKey=key;
      // Var olan oyuncu modelini, sakatlik panelini ve onbellegi yenile.
      if(typeof window.injChanged==='function') window.injChanged();
      else if(typeof injChanged==='function') injChanged();
    }
  }
  async function fetchEspn(throwOnError){
    var ctrl=new AbortController(), timer=setTimeout(function(){ctrl.abort()},12000);
    try{
      var res=await fetch(ESPN_API,{cache:'no-store',signal:ctrl.signal});
      if(!res.ok)throw Error('ESPN API HTTP '+res.status);
      espnData=parseEspn(await res.json());
    }catch(e){espnData=null;console.warn('ESPN read only snapshot:',e.message||e);if(throwOnError)throw e}
    finally{clearTimeout(timer)}
  }
  function applyEspnOnly(){
    // NBA resmi bilgi yoksa ESPN'yi geçici kaynak olarak kullan.
    var old=window.CMREMOTE;
    if(old&&Date.now()-old.updatedAt<=MAX_AGE_MS){
      // Re-build the official list and conflicts from pristine API data.
      if(officialData)apply(officialData,officialTime);
      return;
    }
    var changed=!!old||!!espnData;
    window.CMREMOTE=espnData?{list:Object.create(null),submitted:new Set(),missing:new Set(),
      espn:espnData.list,espnTeams:espnData.teams,conflicts:Object.create(null),
      differences:Object.create(null),unverified:Object.create(null),espnOnly:Object.create(null),
      updatedAt:espnData.checkedAt,reportKey:null}:null;
    statusSummary();
    if(changed&&typeof injChanged==='function')injChanged();
  }
  async function refresh(manual, mode){
    if(fetching)return;
    fetching=true;
    var btn=el('inj-up'), nb=el('nba-inj-check');
    if(manual){
      if(btn)btn.disabled=true;
      if(nb)nb.disabled=true;
      if(mode==='espn'&&btn)btn.textContent='ESPN kontrol ediliyor…';
      if(mode==='nba'&&nb)nb.textContent='NBA raporu okunuyor…';
    }
    var refreshResult=null;
    try{
      if(manual&&mode==='espn'){
        var postCtrl=new AbortController();
        var postTimer=setTimeout(function(){postCtrl.abort()},18000);
        try{
          var postRes=await fetch(ESPN_REFRESH_API,{method:'POST',cache:'no-store',signal:postCtrl.signal});
          refreshResult=await postRes.json();
          if(!postRes.ok||!refreshResult.success)throw Error(refreshResult.error||'ESPN sorgulama hatası');
        } finally {clearTimeout(postTimer)}
      }
      await fetchEspn(!!(manual&&mode==='espn'));
      var controller=new AbortController();
      var timer=setTimeout(function(){controller.abort()},12000);
      var response;
      try {response=await fetch(API,{cache:'no-store',signal:controller.signal});}
      finally{clearTimeout(timer)}
      if(!response.ok)throw Error('NBA API HTTP '+response.status);
      var data=await response.json();
      var time=checkValid(data);
      officialData=data; officialTime=time;
      apply(data,time);
      if(manual&&mode==='espn'){
        setText(refreshResult&&refreshResult.skipped
          ? 'ESPN zaten son 5 dakika içinde kontrol edilmişti; kayıtlı liste yeniden okundu. NBA resmî raporu öncelikli.'
          : 'ESPN kaynağı şimdi yeniden sorgulandı; kayıtlı liste yenilendi. NBA resmî raporu öncelikli.', 'info');
      }
      if(manual&&mode==='nba'){
        setText('NBA resmî raporu yeniden okundu. Son kaydedilen rapor: '+
          new Date(time).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul'})+
          '. Yeni NBA PDF çekimi 15 dakikalık GitHub iş akışında yapılır.', 'info');
      }
    }catch(e){
      if(officialData&&Number.isFinite(officialTime)&&Date.now()-officialTime<=MAX_AGE_MS){
        apply(officialData,officialTime);
      } else {officialData=null;officialTime=null;applyEspnOnly()}
      setText('⚠ Kontrol tamamlanamadı; son geçerli sakatlık listesi korunuyor. '+(e.message||e),'warn');
      console.warn('Cizgi Masasi NBA sync:',e);
    }finally{
      fetching=false;
      if(btn){btn.disabled=false;btn.textContent='ESPN’i kontrol et'}
      if(nb){nb.disabled=false;nb.textContent='NBA resmî raporu kontrol et'}
    }
  }
  function start(){
    if(ready)return;
    if(typeof injChanged!=='function'||!el('inj-st'))return;
    ready=true;initBanner();refresh(false);
    setInterval(function(){if(!document.hidden)refresh(false)},PERIOD_MS);
    document.addEventListener('visibilitychange',function(){if(!document.hidden)refresh(false)});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);
  else start();
})();
