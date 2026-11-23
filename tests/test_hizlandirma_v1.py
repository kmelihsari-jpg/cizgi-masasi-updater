import pathlib, re, shutil, subprocess
try:
    import yaml
except ImportError:
    yaml = None
ROOT = pathlib.Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
js = (ROOT / 'site-patches' / 'hizlandirma-v1.js').read_text(encoding='utf-8')

# 1) is hatti: adim var, hata olursa yayin durmaz, baslat.js'ten once eklenir
wf = (ROOT / '.github/workflows/cizgi-masasi-otomatik-pages.yml').read_text(encoding='utf-8')
if yaml:
    y = yaml.safe_load(wf)
    steps = y['jobs'][list(y['jobs'])[0]]['steps']
    st = [s for s in steps if 'Hizlandirma V1' in s.get('name', '')]
    assert len(st) == 1 and st[0].get('continue-on-error') is True
    run = st[0]['run']
    names = [s.get('name', '') for s in steps]
    assert names.index(st[0]['name']) > names.index('Barem Gecmisi V2 (arsivden son 8 barem) yamasini ekle')
else:
    i = wf.index('- name: Hizlandirma V1')
    j = wf.index('- name:', i + 10)
    run = wf[i:j]
    assert 'continue-on-error: true' in run
    assert i > wf.index('- name: Barem Gecmisi V2')
assert "hizlandirma-v1.js?v=" in run and "marker = '<script src=\"baslat.js'" in run

# 2) davranis (node): sonuclar ayni, onbellek sakatlik degisince bosalir
if NODE:
    code = r'''
const calls={dk:0,io:0};
global.window=global;
global.INJV=1;global.INJ={a:1};global.LIVE=null;global.IOV={};global.SHR={};
global.dayKey=function(ts){calls.dk++;return 'D'+ts};
global.injOf=function(n){calls.io++;return (window.CMREMOTE&&window.CMREMOTE.list[n])||(IOV[n]==='OUT'?['OUT','x','']:null)};
window.CMREMOTE={list:{A:['OUT','n','']},espn:{},submitted:new Set()};
const raw={dk:global.dayKey,io:global.injOf};
eval(process.argv[1]);
const a=[];
for(let i=0;i<5;i++){a.push(dayKey(5),dayKey('s'),injOf('A'),injOf('B'))}
if(calls.dk!==2||calls.io!==2)throw new Error('onbellek calismiyor '+JSON.stringify(calls));
if(dayKey(5)!==raw.dk(5)||JSON.stringify(injOf('A'))!==JSON.stringify(raw.io('A')))throw new Error('sonuc farkli');
// elle isaretleme + INJV artisi
IOV.B='OUT';INJV++;
if(!injOf('B')||injOf('B')[0]!=='OUT')throw new Error('INJV sonrasi bayat');
// CMREMOTE yeniden atanirsa
window.CMREMOTE={list:{B:['OUT','n','']},espn:{},submitted:new Set()};
if(injOf('A')!==null)throw new Error('CMREMOTE degisince bayat');
// null donusler de onbellekte kalir, undefined kalmaz
if(injOf('Z')!==null)throw new Error('null');
const c=calls.io;injOf('Z');if(calls.io!==c)throw new Error('null onbelleklenmedi');
// ikinci yukleme idempotans
const f1=window.injOf;eval(process.argv[1]);if(window.injOf!==f1)throw new Error('cift sarma');
console.log('ok');
'''
    r = subprocess.run([NODE, '-e', code, js], capture_output=True, text=True)
    assert r.returncode == 0 and 'ok' in r.stdout, r.stderr[:600]
print('test_hizlandirma_v1 OK')
