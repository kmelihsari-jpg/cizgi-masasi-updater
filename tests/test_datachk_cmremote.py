import pathlib, sys, subprocess, shutil
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from karne_returning import patch_text, patch_datachk, DC_MARK
root=pathlib.Path(__file__).resolve().parents[1]
# 1) Eski fixture dataChk icermiyor: sessizce atlanmali, mevcut V3 testleri bozulmamali.
fx=(root/'tests'/'fixture-model.js').read_text(encoding='utf-8')
assert patch_text(fx,[]).count('CM_CONFIRMED_RETURNS = [];')==1
# 2) dataChk iceren model: uyari yalnizca CMREMOTE yokken uretilmeli, idempotent olmali.
DC="function dataChk(r,p,all){const w=[];try{if(typeof LIVE!=='undefined'&&(!LIVE||!LIVE.ts||Date.now()-LIVE.ts>6*3600e3))w.push('sakatl\u0131k listesi 6 saatten eski');}catch(e){}return w}"
src=fx+"\n"+DC
out=patch_datachk(src)
DC_PATCHED=patch_datachk(DC)
assert DC_MARK in out and 'window.CMREMOTE' in out and patch_datachk(out)==out
assert patch_text(patch_text(src,[]),[]).count(DC_MARK)==1
# 3) Beklenmeyen dataChk gorunumu: degistirmeden hata ver.
try:
    patch_datachk("function dataChk(){ /* farkli */ }"); raise SystemExit('FAIL: hata beklenirdi')
except RuntimeError: pass
# 4) Davranis (node varsa): CMREMOTE varken uyari yok, yokken var.
if shutil.which('node'):
    js=DC_PATCHED
    t=js+"\nvar LIVE=null,window={};var r1=dataChk({},{},[]).length;window.CMREMOTE={espn:{a:1}};var r2=dataChk({},{},[]).length;console.log(r1,r2)"
    res=subprocess.run(['node','-e',t],capture_output=True,text=True)
    assert res.stdout.split()==['1','0'],res.stdout+res.stderr
print('PASS: dataChk CMREMOTE yamasi (uyari yalniz Worker verisi yokken), idempotent, V3 yamasi korunuyor')
