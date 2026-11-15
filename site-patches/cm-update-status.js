(()=>{
  'use strict';
  const panelId='cm-update-status';
  function node(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
  function human(iso){if(!iso)return 'Henüz doğrulanmış zaman yok';let t=new Date(iso);if(Number.isNaN(t.getTime()))return 'Henüz doğrulanmış zaman yok';return new Intl.DateTimeFormat('tr-TR',{timeZone:'Europe/Istanbul',dateStyle:'short',timeStyle:'short'}).format(t)+' (TSİ)';}
  async function render(){
    if(document.getElementById(panelId))return;
    const section=node('section',undefined,'cm-updates');section.id=panelId;section.setAttribute('aria-label','Son Güncellemeler ve Veri Durumu');
    const details=node('details');const summary=node('summary','Son Güncellemeler ve Veri Durumu');details.append(summary);
    const body=node('div',undefined,'cm-updates-body');body.append(node('p','Kaydedilen dosyaların en son veri zamanları gösterilir. Planlanan çalışma saatleri, güncellemenin başarıyla yapıldığını kanıtlamaz.','cm-updates-hint'));
    const list=node('div','Yükleniyor…','cm-updates-list');body.append(list);
    const heading=node('h3','Son sistem iyileştirmeleri');const notes=node('ul');body.append(heading,notes);details.append(body);section.append(details);
    const vitrin=document.getElementById('cm-v1-vitrin');
    if(vitrin&&vitrin.parentNode)vitrin.insertAdjacentElement('afterend',section);
    else {const target=document.querySelector('main')||document.body;target.appendChild(section);}
    try{
      const res=await fetch('cm-updates.json',{cache:'no-store'});
      if(!res.ok)throw Error('HTTP '+res.status);
      const result=await res.json();if(result.schema_version!==1||!Array.isArray(result.entries))throw Error('gecersiz format');
      list.textContent='';
      for(const r of result.entries){const item=node('div',undefined,'cm-updates-item');item.append(node('span',r.label,'cm-updates-label'),node('strong',human(r.updated_at),'cm-updates-time'));if(r.description)item.title=r.description;list.append(item);}
      for(const n of (result.notes||[])){const li=node('li',String(n));notes.append(li);}
    }catch(e){list.textContent='Güncelleme zamanlarına şu anda ulaşılamıyor.';}
  }
  // Eski arayuzde sabit yazilmis olan 20:15 barem duyurusunu duzelt.
  // Verinin basariyla cekildigini iddia etmez; gercek zaman panelde ayrica gosterilir.
  const oldBarem=/Baremler\s+20[:.]15['’]?te\s+okunuyor\.?/gi;
  const newBarem='Barem kontrolleri 18.30, 19.30 ve 20.30 için planlıdır. Gerçek son kayıt zamanını Son Güncellemeler bölümünden kontrol et.';
  function fixLegacyText(){
    const host=document.querySelector('main')||document.body;
    if(!host)return;
    const walker=document.createTreeWalker(host,NodeFilter.SHOW_TEXT);
    let item,changed=0;
    while((item=walker.nextNode())){
      const parent=item.parentElement;
      if(!parent||parent.closest('script,style,textarea,pre,code,#cm-update-status'))continue;
      const before=item.nodeValue||'';
      if(!before.includes('20:15')&&!before.includes('20.15'))continue;
      const after=before.replace(oldBarem,newBarem);
      if(after!==before){item.nodeValue=after;changed++;}
    }
    return changed;
  }
  let pending=false;
  function scheduleFix(){if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;fixLegacyText();});}
  function start(){render();fixLegacyText();const target=document.querySelector('main')||document.body;
    const watcher=new MutationObserver(scheduleFix);watcher.observe(target,{subtree:true,childList:true,characterData:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
