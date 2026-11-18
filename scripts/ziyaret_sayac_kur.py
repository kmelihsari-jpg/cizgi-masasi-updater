"""Ziyaret sayacini site-patches/index.html icine ekler ya da guncel surumle degistirir.

Kullanim: python scripts/ziyaret_sayac_kur.py [--index site-patches/index.html]
- Blok yoksa: canli-sakatlik.js satirindan hemen sonra ekler.
- Blok varsa (eski surum): sadece o blogu yenisiyle degistirir; baska hicbir satira dokunmaz.
- Ayni surum zaten varsa dokunmaz. Baglanti noktasi yoksa/birden fazlaysa hata verir, dosyaya yazmaz.
"""
import argparse, pathlib, re, sys

SNIPPET = r'''<script id="cm-ziyaret-sayac">
/* Ziyaret sayaci: cihaz bilgisi + ekranda gecirilen sure + ilk giriste tek seferlik isim sorusu.
   IP gonderilmez; sonuclar sadece sahibinin /panel sayfasinda. */
(function(){
  try{
    if(navigator.doNotTrack==='1'||location.protocol!=='https:')return;
    var API='https://cizgi-masasi-api.k-melihsari.workers.dev/api/visit';
    var mem={};
    function get(st,k){try{return window[st].getItem(k)}catch(e){return mem[st+k]||null}}
    function set(st,k,v){try{window[st].setItem(k,v)}catch(e){mem[st+k]=v}}
    function rid(){var s='',c='abcdefghijklmnopqrstuvwxyz0123456789',a;
      try{a=new Uint8Array(16);crypto.getRandomValues(a)}catch(e){a=[];for(var i=0;i<16;i++)a.push(Math.random()*256)}
      for(var j=0;j<16;j++)s+=c.charAt(a[j]%36);return s}
    var vid=get('localStorage','cm_vid');if(!vid||!/^[a-z0-9]{8,40}$/.test(vid)){vid=rid();set('localStorage','cm_vid',vid)}
    var sid=get('sessionStorage','cm_sid');if(!sid||!/^[a-z0-9]{8,40}$/.test(sid)){sid=rid();set('sessionStorage','cm_sid',sid)}
    var m=location.search.match(/[?&]ad=([^&]+)/);
    if(m){try{set('localStorage','cm_ad',decodeURIComponent(m[1].replace(/\+/g,' ')).replace(/[<>"'`]/g,'').trim().slice(0,30))}catch(e){}}
    var nick=get('localStorage','cm_ad')||'';
    function pg(){var b=document.querySelector('.tab[aria-pressed="true"]')||document.querySelector('[data-bv][aria-pressed="true"]');return b&&(b.id||b.getAttribute('data-bv'))||'tab-home'}
    var ref='';try{ref=document.referrer?new URL(document.referrer).hostname:''}catch(e){}
    var cur=pg(),acc=0,lastT=Date.now(),lastSend=0;
    function send(p,ms,nv){
      var body=JSON.stringify({sid:sid,vid:vid,page:p,dt:Math.round(ms/1000),nv:nv?1:0,nick:nick,
        screen:(screen.width||0)+'x'+(screen.height||0),lang:navigator.language||'',ref:ref});
      lastSend=Date.now();
      try{fetch(API,{method:'POST',body:body,keepalive:true,headers:{'Content-Type':'text/plain'}}).catch(function(){})}catch(e){}
    }
    function step(){
      var now=Date.now();
      if(document.visibilityState==='visible')acc+=Math.min(now-lastT,10000);
      lastT=now;
      var p=pg();
      if(p!==cur){send(cur,acc,false);acc=0;cur=p;send(cur,0,true)}
      else if(acc>0&&now-lastSend>=30000){send(cur,acc,false);acc=0}
    }
    document.addEventListener('visibilitychange',function(){
      if(document.visibilityState==='hidden'){acc+=Math.min(Date.now()-lastT,10000);lastT=Date.now();if(acc>0){send(cur,acc,false);acc=0}}
      else lastT=Date.now();
    });
    window.addEventListener('pagehide',function(){if(acc>0){send(cur,acc,false);acc=0}});
    send(cur,0,true);
    setInterval(step,5000);
    /* Ilk giriste bir kez isim sor. Kaydet ya da Gec denince bir daha sorulmaz. */
    function ask(){
      if(nick||get('localStorage','cm_ad_asked'))return;
      try{if(window.top!==window.self)return}catch(e){return}
      function build(){
        if(document.getElementById('cm-ad-ov'))return;
        /* Tek sefer garantisi: baska sekme zaten sorduysa sorma; kalici yazamiyorsak hic sorma;
           soruyu gosterdigimiz anda isaretle (kapatilsa ya da yok sayilsa bile bir daha cikmaz). */
        try{
          var L=window.localStorage;
          if(L.getItem('cm_ad_asked')||L.getItem('cm_ad'))return;
          L.setItem('cm_ad_asked','1');
          if(L.getItem('cm_ad_asked')!=='1')return;
        }catch(e){return}
        var ov=document.createElement('div');ov.id='cm-ad-ov';
        ov.setAttribute('style','position:fixed;top:0;left:0;right:0;bottom:0;z-index:2147483000;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;padding:16px;font-family:system-ui,Segoe UI,Roboto,sans-serif');
        var box=document.createElement('form');
        box.setAttribute('style','background:#171e26;color:#e6edf3;border:1px solid #2b3a48;border-radius:14px;padding:18px;max-width:340px;width:100%;box-shadow:0 10px 40px rgba(0,0,0,.5);box-sizing:border-box');
        var h=document.createElement('div');h.textContent='Hoş geldin! Adın ne?';
        h.setAttribute('style','font-size:18px;font-weight:700;margin-bottom:6px');
        var t=document.createElement('div');t.textContent='Sadece ilk girişte soruyorum. Site sahibi hangi cihazdan kimin girdiğini bu isimle görür.';
        t.setAttribute('style','font-size:13px;line-height:1.4;color:#9fb3c8;margin-bottom:12px');
        var inp=document.createElement('input');inp.type='text';inp.maxLength=30;inp.placeholder='Adın veya takma adın';
        inp.setAttribute('autocomplete','off');inp.setAttribute('autocapitalize','words');
        inp.setAttribute('style','width:100%;box-sizing:border-box;font-size:16px;padding:10px 12px;border-radius:10px;border:1px solid #2b3a48;background:#0f1419;color:#e6edf3;margin-bottom:12px');
        var row=document.createElement('div');row.setAttribute('style','display:flex;gap:8px');
        var ok=document.createElement('button');ok.type='submit';ok.textContent='Kaydet';
        ok.setAttribute('style','flex:1;font-size:15px;padding:10px;border-radius:10px;border:0;background:#1f6feb;color:#fff;font-weight:600');
        var no=document.createElement('button');no.type='button';no.textContent='Geç';
        no.setAttribute('style','font-size:15px;padding:10px 16px;border-radius:10px;border:1px solid #2b3a48;background:transparent;color:#9fb3c8');
        row.appendChild(ok);row.appendChild(no);
        box.appendChild(h);box.appendChild(t);box.appendChild(inp);box.appendChild(row);ov.appendChild(box);
        function close(){if(ov.parentNode)ov.parentNode.removeChild(ov)}
        function skip(){set('localStorage','cm_ad_asked','1');close()}
        box.addEventListener('submit',function(e){
          e.preventDefault();
          var v=inp.value.replace(/[<>"'`]/g,'').trim().slice(0,30);
          if(!v){inp.focus();return}
          set('localStorage','cm_ad',v);set('localStorage','cm_ad_asked','1');
          nick=v;close();send(cur,0,false);
        });
        no.addEventListener('click',skip);
        ov.addEventListener('keydown',function(e){if(e.key==='Escape')skip()});
        document.body.appendChild(ov);
        try{inp.focus()}catch(e){}
      }
      setTimeout(build,1500);
    }
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ask);else ask();
  }catch(e){}
})();
</script>'''
ANCHOR = re.compile(r'<script src="canli-sakatlik\.js[^"]*"></script>')
BLOCK = re.compile(r'<script id="cm-ziyaret-sayac">.*?</script>', re.S)


def patch(html: str) -> str:
    nl = '\r\n' if '\r\n' in html else '\n'
    block = SNIPPET.replace('\r\n', '\n').replace('\n', nl)
    existing = BLOCK.findall(html)
    if len(existing) > 1:
        raise RuntimeError('Birden fazla cm-ziyaret-sayac blogu var: %d' % len(existing))
    if len(existing) == 1:
        return BLOCK.sub(lambda m: block, html, count=1)
    found = ANCHOR.findall(html)
    if len(found) != 1:
        raise RuntimeError('canli-sakatlik.js baglanti noktasi bulunamadi/tek degil: %d' % len(found))
    return ANCHOR.sub(lambda m: m.group(0) + nl + block, html, count=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--index', default='site-patches/index.html')
    path = pathlib.Path(ap.parse_args().index)
    old = path.read_bytes().decode('utf-8')
    new = patch(old)
    if new == old:
        print('ZIYARET SAYACI zaten guncel; dokunulmadi')
        return 0
    if new.count('<script') != new.count('</script>') or len(new) < len(old) - 500:
        raise RuntimeError('Beklenmeyen sonuc; dosya yazilmadi')
    path.write_bytes(new.encode('utf-8'))
    print('ZIYARET SAYACI guncellendi:', path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
