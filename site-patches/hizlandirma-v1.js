/* Hizlandirma V1 (23 Kasim 2026)
   Ana sayfa cizimi ~8 sn suruyordu (PC'de fan sesi / yavaslik). Iki saf/sabit hesap onbellege alinir:
   1) dayKey(ts): ayni zaman damgasi icin toLocaleDateString sonucu (saf fonksiyon).
   2) injOf(ad): sakatlik durumu; onbellek INJV (clearModelCache/injChanged'de artar) ve sakatlik
      kaynaklarinin (INJ, LIVE, CMREMOTE ve alanlari, SHR/IOV anahtar sayisi) degismesiyle bosalir.
   Hicbir veri, oneri kurali, karne ya da arsiv dosyasina dokunmaz. Hata olursa yama sessizce devre disi kalir. */
(function(){
  'use strict';
  if(window.__cmHizlandirma)return;
  window.__cmHizlandirma=1;
  try{
    if(typeof dayKey==='function'){
      var dkOrig=dayKey,dkMap=new Map();
      window.dayKey=function(ts){
        if(typeof ts!=='number'&&typeof ts!=='string')return dkOrig(ts);
        var v=dkMap.get(ts);
        if(v===undefined){
          v=dkOrig(ts);
          if(dkMap.size>5000)dkMap.clear();
          dkMap.set(ts,v);
        }
        return v;
      };
    }
  }catch(e){console.warn('hizlandirma dayKey',e)}
  try{
    if(typeof injOf==='function'){
      var ioOrig=injOf,ioMap=new Map(),ioSig=null;
      var cnt=function(o){try{return o?Object.keys(o).length:-1}catch(e){return -2}};
      var sigNow=function(){
        var r=window.CMREMOTE||null;
        return [
          typeof INJV!=='undefined'?INJV:0,
          typeof INJ!=='undefined'?INJ:null,
          typeof LIVE!=='undefined'?LIVE:null,
          typeof IOV!=='undefined'?IOV:null,
          typeof SHR!=='undefined'?SHR:null,
          r,r&&r.list,r&&r.espn,r&&r.espnTeams,r&&r.submitted,
          cnt(typeof SHR!=='undefined'?SHR:null),
          cnt(typeof IOV!=='undefined'?IOV:null),
          r&&r.submitted&&typeof r.submitted.size==='number'?r.submitted.size:-1
        ];
      };
      var same=function(a,b){
        if(!a||!b||a.length!==b.length)return false;
        for(var i=0;i<a.length;i++)if(a[i]!==b[i])return false;
        return true;
      };
      window.injOf=function(name){
        var s=sigNow();
        if(!same(s,ioSig)){ioMap=new Map();ioSig=s}
        if(typeof name!=='string')return ioOrig(name);
        var v=ioMap.get(name);
        if(v===undefined){
          v=ioOrig(name);
          if(v===undefined)return v;
          ioMap.set(name,v);
        }
        return v;
      };
    }
  }catch(e){console.warn('hizlandirma injOf',e)}
})();
