#!/usr/bin/env python3
"""Sunucu tarafi sakatlik firsati: goruntu karsilastirmasi (INJ_JS, node), injPicks ekleme kurallari, goruntu dosyasi."""
import json, pathlib, shutil, subprocess, sys, tempfile, time
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import karne_automation as ka

NOW = time.time()
def item(pid, mk, line, odd, team='LAC', opp='HOU', ev=.1, gt=None, name=None):
    return {'id': pid, 'name': name or 'P%d' % pid, 'team': team, 'opp': opp, 'pos': 'SF', 'mk': mk, 'line': line, 'n': int(line + .5), 'odd': odd,
            'ev': ev, 'tag': 'inj', 'gt': (gt or (NOW + 3 * 3600)) * 1000, '_day': '2026-11-28', 'news': {'id': 9, 'name': 'X', 'to': 'OUT'}}

def py_tests():
    stamp = '2026-11-28T10:00:00+00:00'
    # gunun belgesi yok -> olusur
    docs = []; by = {}
    n = ka.add_inj_picks({'inj': [item(1, 'PTS', 12.5, 1.8), item(2, 'REB', 5.5, 1.7, ev=.2), item(1, 'AST', 3.5, 1.9), item(1, '3PM', 1.5, 1.8)]}, by, docs, stamp, 'o', 'd', NOW)
    d = by['2026-11-28']
    assert n == 3 and len(d['injPicks']) == 3 and docs == [d], d      # oyuncu basina en fazla 2 (id=1: PTS, AST); 3PM atilir
    assert [c['id'] for c in d['injPicks']][0] == 2                   # ev'e gore sirali (REB .2 once)
    assert all('_day' not in c and c['capturedAt'] == stamp for c in d['injPicks'])
    # ayni id|mk tekrar eklenmez, Kasa'da olan eklenmez, mac siniri (3) injPicks+picks birlikte
    n2 = ka.add_inj_picks({'inj': [item(2, 'REB', 5.5, 1.7), item(3, 'PTS', 10.5, 1.7)]}, by, docs, stamp, 'o', 'd', NOW)
    assert n2 == 0, d['injPicks']                                      # 3 oyuncu zaten dolu: LAC@HOU 3 bahis -> 4. yok
    docs2 = [{'date': '2026-11-28', 'picks': [{'id': 7, 'mk': 'PTS', 'team': 'LAC', 'opp': 'HOU'}], 'injPicks': []}]; by2 = {'2026-11-28': docs2[0]}
    assert ka.add_inj_picks({'inj': [item(7, 'PTS', 12.5, 1.8)]}, by2, docs2, stamp, 'o', 'd', NOW) == 0    # Kasa'da ayni id|mk
    # gecersiz kayitlar: baslamis mac, line!=n-.5, bilinmeyen market, 16 saatten uzak
    bad = [item(11, 'PTS', 12.5, 1.8, gt=NOW - 60), item(12, 'PTS', 12.5, 1.8), item(13, 'XYZ', 5.5, 1.8), item(14, 'PTS', 12.5, 1.8, gt=NOW + 20 * 3600)]
    bad[1]['n'] = 20
    assert ka.add_inj_picks({'inj': bad}, {}, [], stamp, 'o', 'd', NOW) == 0
    # sonuclanmis gunun kaydina dokunmaz
    docs3 = [{'date': '2026-11-28', 'early': [1], 'picks': [], 'injPicks': []}]
    assert ka.add_inj_picks({'inj': [item(21, 'PTS', 12.5, 1.8)]}, {'2026-11-28': docs3[0]}, docs3, stamp, 'o', 'd', NOW) == 0
    # goruntu dosyasi
    with tempfile.TemporaryDirectory() as t:
        p = pathlib.Path(t) / 'snap.json'
        snap = {str(i): '' for i in range(90)}; snap['5'] = 'OUT'
        assert ka.save_snap(p, None, {'snap': snap, 'evCount': 0}, NOW, stamp) is True
        raw, prev = ka.load_prev_snap(p, NOW + 3600)
        assert prev == snap
        assert ka.load_prev_snap(p, NOW + 25 * 3600)[1] is None        # 20 saatten eski: olay uretme
        assert ka.save_snap(p, raw, {'snap': snap}, NOW + 3600, stamp) is False   # degismedi, taze: yazmaz
        assert ka.save_snap(p, raw, {'snap': snap}, NOW + 4 * 3600, stamp) is True  # 3 saatten eski: tazele
        assert ka.save_snap(p, raw, {'snap': {'1': 'OUT'}}, NOW, stamp) is False    # cok az oyuncu: kaydetme

JS_STUB = r"""
const vm=require('vm'),fs=require('fs');
const code=fs.readFileSync(process.argv[2],'utf8');
const ctx=vm.createContext({console,Date,Math,JSON,Object,Array,Number,String,Set,Map});
vm.runInContext(`
var P={},byP={},status={},calls=[];
for(let i=1;i<=6;i++){P[i]={id:i,name:'P'+i,team:'AAA'};byP[i]=Array.from({length:10},()=>({min:i===6?10:30}))}
P[7]={id:7,name:'P7',team:'AAA'};byP[7]=Array.from({length:3},()=>({min:30}));
function mpg(id){const g=byP[id];return g.reduce((s,x)=>s+x.min,0)/g.length}
function injOf(n){return status[n]?[status[n]]:null}
function dayKey(ts){return '2026-11-28'}
function injOppItems(ev,now,news){calls.push(ev.id);return [{id:100+ev.id,mk:'PTS',line:9.5,n:10,odd:1.8,ev:.1,gt:now+3600e3,tag:'inj',team:'AAA',opp:'BBB',name:'B',news}]}
`,ctx);
const fn=vm.runInContext('('+code+')',ctx);
const out={};
vm.runInContext("status={P2:'OUT',P3:'Q'}",ctx);
out.noPrev=fn({prev:null});
out.firstRun=fn(undefined);
// onceki: P2 saglikli (yok), P3 saglikli; simdi P2 OUT (yeni), P4 OUT ve onceden de OUT
vm.runInContext("status={P2:'OUT',P4:'OUT',P6:'OUT',P7:'OUT'}",ctx);
out.withPrev=fn({prev:{1:'',2:'',3:'',4:'OUT',5:''}});
// 13 yeni OUT => olay uretme
vm.runInContext("for(let i=1;i<=6;i++)status['P'+i]='OUT'",ctx);
out.many=fn({prev:{}});
console.log(JSON.stringify(out));
"""

def js_tests():
    if not shutil.which('node'):
        print('SKIP: node yok, INJ_JS testi atlandi'); return
    with tempfile.TemporaryDirectory() as t:
        t = pathlib.Path(t); (t / 'fn.js').write_text(ka.INJ_JS, encoding='utf-8'); (t / 'run.js').write_text(JS_STUB, encoding='utf-8')
        r = subprocess.run(['node', str(t / 'run.js'), str(t / 'fn.js')], capture_output=True, text=True); assert r.returncode == 0, r.stderr
        o = json.loads(r.stdout.strip().splitlines()[-1])
    assert set(o['noPrev']['snap']) == {'1', '2', '3', '4', '5'}, o['noPrev']   # P6 (10 dk) ve P7 (3 mac) goruntude yok
    assert o['noPrev']['inj'] == [] and o['noPrev']['hadPrev'] is False
    assert o['firstRun']['inj'] == []
    w = o['withPrev']; assert w['evCount'] == 1 and [c['id'] for c in w['inj']] == [102] and w['inj'][0]['_day'] == '2026-11-28', w
    assert w['snap']['2'] == 'OUT' and w['snap']['4'] == 'OUT'
    assert o['many']['evCount'] == 5 and len(o['many']['inj']) == 5, o['many']   # 12 veya az yeni OUT: uretir


def main():
    py_tests(); js_tests()
    print('PASS: sunucu tarafi sakatlik firsati (injPicks kurallari, goruntu dosyasi, INJ_JS)')

if __name__ == '__main__':
    main()
