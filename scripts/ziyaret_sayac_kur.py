"""Ziyaret sayacini site-patches/index.html icine ekler (tekrar calistirilabilir, mevcut kodu degistirmez).

Kullanim: python scripts/ziyaret_sayac_kur.py [--index site-patches/index.html]
Sadece canli-sakatlik.js satirindan hemen sonra tek bir <script id="cm-ziyaret-sayac"> blogu ekler.
Baglanti noktasi yoksa ya da birden fazlaysa hata verip dosyaya dokunmaz.
"""
import argparse, pathlib, re, sys

SNIPPET = r'''<script id="cm-ziyaret-sayac">
/* Ziyaret sayaci: cihaz bilgisi + ekranda gecirilen sure. IP gonderilmez; sonuclar sadece sahibinin /panel sayfasinda. */
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
    if(m){try{set('localStorage','cm_ad',decodeURIComponent(m[1].replace(/\+/g,' ')).slice(0,30))}catch(e){}}
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
  }catch(e){}
})();
</script>'''
ANCHOR = re.compile(r'<script src="canli-sakatlik\.js[^"]*"></script>')


def patch(html: str) -> str:
    if 'id="cm-ziyaret-sayac"' in html:
        return html
    found = ANCHOR.findall(html)
    if len(found) != 1:
        raise RuntimeError('canli-sakatlik.js baglanti noktasi bulunamadi/tek degil: %d' % len(found))
    nl = '\r\n' if '\r\n' in html else '\n'
    block = SNIPPET.replace('\r\n', '\n').replace('\n', nl)
    return ANCHOR.sub(lambda m: m.group(0) + nl + block, html, count=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--index', default='site-patches/index.html')
    path = pathlib.Path(ap.parse_args().index)
    old = path.read_bytes().decode('utf-8')
    new = patch(old)
    if new == old:
        print('ZIYARET SAYACI zaten ekli; dokunulmadi')
        return 0
    if new.count('<script') != new.count('</script>') or len(new) < len(old) + 500:
        raise RuntimeError('Beklenmeyen sonuc; dosya yazilmadi')
    path.write_bytes(new.encode('utf-8'))
    print('ZIYARET SAYACI eklendi:', path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
