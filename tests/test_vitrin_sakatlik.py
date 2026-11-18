import ast, json, pathlib, re, shutil, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import vitrin_sakatlik_kur as V

NODE = shutil.which('node')
def node_check(text, name):
    if not NODE:
        return
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / name
        f.write_text(text, encoding='utf-8')
        r = subprocess.run([NODE, '--check', str(f)], capture_output=True, text=True)
        assert r.returncode == 0, name + ' sozdizimi bozuk: ' + r.stderr[:400]

def node_run(code):
    r = subprocess.run([NODE, '-e', code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:600]
    return r.stdout.strip()

# 1) model.js: yama, idempotans, sozdizimi
model = (ROOT / 'tests' / 'fixture-model.js').read_text(encoding='utf-8')
m1 = V.patch_model(model)
assert V.MODEL_MARK in m1 and 'cmCapGame(' in m1 and 'cap:cc.cap' in m1
assert "capK.has(k))c.why='limit'" in m1 and "why==='limit')return" in m1
assert V.patch_model(m1) == m1, 'ikinci calistirma degistirmemeli'
node_check(m1, 'model.js')

# 2) cmCapGame davranisi
if NODE:
    fn = re.search(r'function cmCapGame.*\n', V.MODEL_PREFIX).group(0)
    out = node_run(fn + r'''
const L=[];for(let i=0;i<5;i++)L.push({id:i,g:{home:'A',away:'B',ts:1}});L.push({id:9,g:{home:'C',away:'D',ts:2}});
const r=cmCapGame(L,3);
console.log(JSON.stringify({keep:r.keep.map(x=>x.id),cap:r.cap.map(x=>x.id)}))''')
    d = json.loads(out)
    assert d['keep'] == [0, 1, 2, 9] and d['cap'] == [3, 4], d

# 3) app.js: ambulans + kalici sakatlik firsatlari
app = (ROOT / 'tests' / 'fixture-app-injury.js').read_text(encoding='utf-8')
a1 = V.patch_app(app)
assert V.APP_MARK in a1 and "sawtooth" in a1 and "cm-injopp" in a1 and "i===2?1175:880" not in a1
assert V.patch_app(a1) == a1
node_check(a1, 'app.js')

# 4) beklenen kod yoksa HATA (site bozulmaz)
for bad in (model.replace("function pickSplit(day,now){", "function pickSplitX(day,now){"), ):
    try:
        V.patch_model(bad); raise SystemExit('FAIL: eksik kod hata vermedi')
    except RuntimeError:
        pass
try:
    V.patch_app(app.replace('INJOPP=[],INJSEEN=', 'INJOPP=[], INJSEEN=')); raise SystemExit('FAIL: eksik kod hata vermedi')
except RuntimeError:
    pass

# 5) index.html
h = V.patch_html('<html><head></head><body></body></html>')
assert 'vitrin-dantel-v1.css' in h and V.patch_html(h) == h

# 6) tam kurulum (gecici public klasoru)
with tempfile.TemporaryDirectory() as d:
    pub = pathlib.Path(d) / 'public'; pub.mkdir()
    (pub / 'model.js').write_text(model, encoding='utf-8')
    (pub / 'app.js').write_text(app, encoding='utf-8')
    (pub / 'index.html').write_text('<html><head></head><body></body></html>', encoding='utf-8')
    V.main(['--site', str(pub), '--patches', str(ROOT / 'site-patches')])
    assert (pub / 'vitrin-dantel-v1.css').is_file()
    before = {n: (pub / n).read_text(encoding='utf-8') for n in ('model.js', 'app.js', 'index.html')}
    V.main(['--site', str(pub), '--patches', str(ROOT / 'site-patches')])
    assert before == {n: (pub / n).read_text(encoding='utf-8') for n in before}
    # bozuk model: hicbir dosya yazilmamali
    (pub / 'model.js').write_text('function bos(){}', encoding='utf-8')
    (pub / 'app.js').write_text(app, encoding='utf-8')
    try:
        V.main(['--site', str(pub), '--patches', str(ROOT / 'site-patches')]); raise SystemExit('FAIL')
    except RuntimeError:
        pass
    assert V.APP_MARK not in (pub / 'app.js').read_text(encoding='utf-8')

# 7) gorunum-ana.js: vitrine sakatlik firsati katilimi
home = (ROOT / 'site-patches' / 'gorunum-ana.js').read_text(encoding='utf-8')
assert 'function homeItems0(day,bets)' in home and home.count('function homeItems(day,bets)') == 1
assert "rtag inj" in home and 'cmHeroOrtu()' in home
node_check(home, 'gorunum-ana.js')
if NODE:
    part = home[home.index('/* CM-VITRIN-SAKATLIK-V1 */'):]
    code = r'''
const now=Date.now(),T=now+3600e3,day='D';
let INJOPP=[],REAL=[],S={hDay:day},slate=[],IDDRAW={ts:now};
const dayKey=()=>day,tm=()=>'20:05';
let CANDS={},ROWS=[];
const scanRows=()=>ROWS,kasaCand=(r)=>CANDS[r.p.id+'|'+r.mk]||null;
let BASE=[];function homeItems0(){return BASE.slice()}
''' + part + r'''
const g=(h,a)=>({home:h,away:a,ts:T});
const mk=(id,ev,gm)=>({p:{id,team:gm.home},mk:'PTS',ev,g:gm});
const opp=(id,extra)=>Object.assign({id,mk:'PTS',gt:T},extra||{});
function setup(base,inj,cands){BASE=base;INJOPP=inj;CANDS={};ROWS=[];for(const c of cands){CANDS[c.p.id+'|'+c.mk]=c;ROWS.push({p:c.p,mk:c.mk})}}
const A=g('AAA','BBB'),B=g('CCC','DDD'),out={};
// hero'dan degerli firsat basa gelir
setup([{c:mk(1,.10,A)},{c:mk(2,.05,B)}],[opp(7)],[mk(7,.30,B)]);
out.top=homeItems('D',[]).map(o=>o.c.p.id);
// daha dusuk deger araya girer
setup([{c:mk(1,.10,A)},{c:mk(2,.05,B)}],[opp(7)],[mk(7,.07,B)]);
out.mid=homeItems('D',[]).map(o=>o.c.p.id);
// maçta zaten 3 bahis varsa girmez
setup([{c:mk(1,.1,A)},{c:mk(2,.09,A)},{c:mk(3,.08,A)}],[opp(7)],[mk(7,.5,A)]);
out.full=homeItems('D',[]).map(o=>o.c.p.id);
// Kasa kapisindan gecmeyen (kasaCand null) girmez; test, baslamis ve ayni oyuncu atlanir
setup([{c:mk(1,.1,A)}],[opp(8),opp(9,{test:true}),opp(10,{gt:now-1000}),opp(1)],[mk(9,.9,B),mk(10,.9,B),mk(1,.9,A)]);
out.skip=homeItems('D',[]).map(o=>o.c.p.id);
// firsat yoksa liste ayni
setup([{c:mk(1,.1,A)}],[],[]);out.none=homeItems('D',[]).map(o=>o.c.p.id);
// kilitli (x) kayit ile karsilastirma
setup([{x:{d:{id:5,mk:'PTS',team:'AAA',ev:.2}}}],[opp(7)],[mk(7,.4,B)]);
out.locked=homeItems('D',[]).map(o=>o.c?o.c.p.id:o.x.d.id);
console.log(JSON.stringify(out));'''
    r = json.loads(node_run(code))
    assert r['top'] == [7, 1, 2], r
    assert r['mid'] == [1, 7, 2], r
    assert r['full'] == [1, 2, 3], r
    assert r['skip'] == [1], r
    assert r['none'] == [1], r
    assert r['locked'] == [7, 5], r

    # vitrin bos: baremler eskiyse "henuz gelmedi", tazeyse "sakatlik haberi" metni
    code2 = r"""
const day='D';let S={hDay:day},slate=[{ts:1}],IDDRAW={ts:null};const dayKey=()=>day;
""" + home[home.index('function cmHeroOrtu()'):home.index('function cmOrtuKalk()')] + r"""
const o={};
IDDRAW={ts:Date.now()-20*3600e3};o.eski=cmHeroOrtu();
IDDRAW={ts:Date.now()-1*3600e3};o.taze=cmHeroOrtu();
IDDRAW=null;o.yok=cmHeroOrtu();
slate=[];o.macyok=cmHeroOrtu();
console.log(JSON.stringify(o));"""
    r2 = json.loads(node_run(code2))
    assert 'Vitrin misafir gelince açılır' in r2['eski'] and 'Baremler gelince örtü kalkar' in r2['eski'], r2
    assert 'vitrinlik bir şey çıkmadı' in r2['taze'] and 'sakatlık haberi gelirse açılır' in r2['taze'], r2
    assert 'misafir gelince' in r2['yok'] and r2['macyok'] == '', r2

# 8) Karne otomasyonu: ayni mactan en fazla 3 kayit
import karne_automation as K
assert K.MAC_MAX == 3
assert K.game_key({'team': 'LAL', 'opp': 'BOS'}) == K.game_key({'team': 'BOS', 'opp': 'LAL'})
assert K.game_counts([{'team': 'A', 'opp': 'B'}, {'team': 'B', 'opp': 'A'}, {'team': 'C', 'opp': 'D'}]) == {('A', 'B'): 2, ('C', 'D'): 1}
src = (ROOT / 'scripts' / 'karne_automation.py').read_text(encoding='utf-8')
ast.parse(src)
assert 'mac_say.get(gk,0)>=MAC_MAX' in src and "previous.get('injPicks',[])" in src

# 9) workflow adimi
y = (ROOT / '.github' / 'workflows' / 'cizgi-masasi-otomatik-pages.yml').read_text(encoding='utf-8')
assert 'scripts/vitrin_sakatlik_kur.py --site public --patches site-patches' in y
assert y.index('karne_returning.py --model public/model.js') < y.index('vitrin_sakatlik_kur.py --site public')
if not NODE:
    print('UYARI: node yok; JS davranis testleri atlandi')
print('PASS: vitrin/sakatlik/3 sinir yamasi (model, app, vitrin, Karne ekleme siniri, workflow)')
