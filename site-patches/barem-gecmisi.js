/* Cizgi Masasi: Barem Gecmisi V2.
   Oyuncu kartinda secili market icin iddaa'nin verdigi son 8 baremi gosterir:
   mac gunu, barem, oran (acilis -> kapanis), gerceklesen ve tuttu/tutmadi.
   Kaynaklar: barem-arsiv.ndjson (sadece-ekleme arsiv), karne-eski.json (5-14 Kasim karnesi),
   sayfadaki REAL (yeni donem karnesi). Sonuc, oyuncunun mac verisinden (byP) hesaplanir.
   Hicbir veriyi yazmaz/silmez; hata olursa kutu gizli kalir. */
(function(){'use strict';
  const LIMIT=8;
  let ARC=null,OLD=null,LOADING=false;

  function parseArc(txt){
    const m=new Map();
    for(const line of String(txt||'').split('\n')){
      if(!line.trim())continue;
      let a;try{a=JSON.parse(line)}catch(_){continue}
      if(!Array.isArray(a)||a.length<6)continue;
      const t=a[0],pid=a[1],mk=a[2],n=a[3],odd=a[4],gt=a[5];
      const k=pid+'|'+mk;let e=m.get(k);if(!e){e=new Map();m.set(k,e)}
      const kk=n+'|'+gt;let r=e.get(kk);
      if(!r){e.set(kk,{n,gt,open:odd,tOpen:t,close:odd,tClose:t})}
      else{if(t<r.tOpen){r.tOpen=t;r.open=odd}if(t>=r.tClose){r.tClose=t;r.close=odd}}
    }
    return m;
  }

  function load(){
    if(LOADING||ARC)return;LOADING=true;
    Promise.all([
      fetch('barem-arsiv.ndjson',{cache:'no-cache'}).then(r=>r.ok?r.text():'').catch(()=>''),
      fetch('karne-eski.json',{cache:'no-cache'}).then(r=>r.ok?r.json():null).catch(()=>null)
    ]).then(([a,o])=>{
      ARC=parseArc(a);OLD=(o&&Array.isArray(o.docs))?o.docs:[];LOADING=false;
      try{bhistRefresh()}catch(_){}
    }).catch(()=>{LOADING=false});
  }

  const RANK={kasa:3,inj:2,tribun:1};
  const LABEL={kasa:'Kasa',inj:'Sakatlık',tribun:'Kâğıt üstü'};

  // Karne belgelerinden (eski + yeni dönem) bu oyuncu+market icin kayitlar.
  function fromKarne(docs,pid,mk,out){
    for(const doc of docs||[]){
      if(!doc||!doc.date)continue;
      const parts=[['kasa',doc.picks,doc.early],['inj',doc.injPicks,doc.iearly],['tribun',doc.shadow,doc.searly]];
      for(const [kind,arr,early] of parts){
        (arr||[]).forEach((c,i)=>{
          if(String(c.id)!==String(pid)||c.mk!==mk||c.n==null)return;
          const key=doc.date+'|'+c.n;const cur=out.get(key);
          const ev=Array.isArray(early)?early[i]:undefined;
          if(!cur){out.set(key,{date:doc.date,n:c.n,gt:c.gt?Math.round(c.gt/ (c.gt>1e11?1000:1)):null,open:c.odd||null,close:c.odd||null,tag:kind,ev});}
          else{
            if(cur.open==null&&c.odd){cur.open=c.odd;cur.close=c.odd}
            if(!cur.tag||RANK[kind]>RANK[cur.tag]){cur.tag=kind;if(ev!==undefined)cur.ev=ev}
          }
        });
      }
    }
  }

  function outcome(pid,mk,n,date,gt,ev){
    const g=(byP[pid]||[]).find(x=>x.ds===date);
    if(g){const real=val(g,mk);return{res:real>=n?'hit':'miss',real}}
    if(typeof ev==='number')return{res:ev>=n?'hit':'miss',real:ev};
    if(ev==='dnp')return{res:'void',real:null};
    if(gt&&gt*1000>Date.now())return{res:'pending',real:null};
    if(D&&Array.isArray(D.dates)&&D.dates.includes(date))return{res:'void',real:null};
    return{res:'pending',real:null};
  }

  function collect(pid,mk){
    const rows=new Map();
    const arc=ARC&&ARC.get(pid+'|'+mk);
    if(arc)for(const r of arc.values()){
      const date=dayKey(r.gt*1000),key=date+'|'+r.n,cur=rows.get(key);
      if(!cur||r.gt>cur.gt)rows.set(key,{date,n:r.n,gt:r.gt,open:r.open,close:r.close,tag:null,ev:undefined});
    }
    const kar=new Map();
    fromKarne(OLD,pid,mk,kar);
    try{fromKarne(typeof REAL!=='undefined'?REAL:[],pid,mk,kar)}catch(_){}
    for(const [key,k] of kar){
      const cur=rows.get(key);
      if(cur){cur.tag=k.tag;cur.ev=k.ev}
      else if(k.open)rows.set(key,k);
    }
    const out=[...rows.values()].map(r=>({...r,...outcome(pid,mk,r.n,r.date,r.gt,r.ev)}));
    out.sort((a,b)=>a.date<b.date?1:a.date>b.date?-1:(b.gt||0)-(a.gt||0));
    return out.slice(0,LIMIT);
  }

  function oddText(r){
    const o=Number(r.open),c=Number(r.close);
    if(Number.isFinite(o)&&Number.isFinite(c)&&Math.abs(o-c)>=0.005)return o.toFixed(2)+' → '+c.toFixed(2);
    return Number.isFinite(c)?c.toFixed(2):'–';
  }

  renderBHist=function(mk){
    const el=$('bhist');if(!el)return;el.hidden=true;el.innerHTML='';
    try{
      if(!S.pid||!mk||!D||!D.dates)return;
      load();
      const rows=collect(String(S.pid),mk);
      if(!rows.length)return;
      const dec=rows.filter(r=>r.res==='hit'||r.res==='miss'),hit=dec.filter(r=>r.res==='hit').length;
      const sum=dec.length>=3?`<p class="note" style="margin:0 0 6px">Son ${dec.length} sonuçlanan barem: <b>${hit} tuttu</b>, ${dec.length-hit} tutmadı</p>`:'';
      const tag={hit:'<span class="pos">✓ tuttu</span>',miss:'<span class="neg">✗ tutmadı</span>',void:'<span class="note">oynamadı</span>',pending:'<span class="note">bekliyor</span>'};
      el.innerHTML=`<h3>İddaa barem geçmişi</h3>${sum}<div class="tablewrap"><table><thead><tr><th class="l">Maç</th><th>Barem</th><th>Oran</th><th>Sonuç</th><th></th></tr></thead><tbody>${rows.map(r=>`<tr><td class="l">${esc(fmtD(r.date))}${r.tag?` <span class="note">· ${esc(LABEL[r.tag])}</span>`:''}</td><td><b>${r.n}+</b></td><td>${esc(oddText(r))}</td><td>${r.real==null?'–':esc(r.real)}</td><td>${tag[r.res]||''}</td></tr>`).join('')}</tbody></table></div>`;
      el.hidden=false;
    }catch(e){console.error(e)}
  };

  load();
})();
