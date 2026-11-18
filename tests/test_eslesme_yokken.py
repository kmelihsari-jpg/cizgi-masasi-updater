"""eslesme-yokken-v1 testleri (ag yok; yalnizca gecici bir test dosyasi yazar ve siler)."""
import pathlib, sys, unittest, shutil, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from eslesme_yokken_kur import install, START, END  # noqa: E402

JS = (ROOT / 'site-patches/eslesme-yokken-v1.js').read_text(encoding='utf-8')
CSS = (ROOT / 'site-patches/eslesme-yokken-v1.css').read_text(encoding='utf-8')
HTML = '<html><body><script src="canli-sakatlik.js?v=1"></script>\n<script id="x"></script>\n</body></html>'


class KurTest(unittest.TestCase):
    def test_once_and_idempotent(self):
        out = install(HTML, JS, CSS)
        self.assertEqual(out.count(START), 1)
        self.assertLess(out.index('canli-sakatlik.js'), out.index(START))
        self.assertEqual(install(out, JS, CSS), out)

    def test_replaces_old_version(self):
        old = install(HTML, '/*eski*/', '.a{}')
        new = install(old, JS, CSS)
        self.assertNotIn('/*eski*/', new)
        self.assertEqual(new.count(START), 1)
        self.assertEqual(new.count(END), 1)

    def test_fails_closed(self):
        with self.assertRaises(RuntimeError):
            install('<html></html>', JS, CSS)
        with self.assertRaises(RuntimeError):
            install(HTML, 'x</script>', CSS)

    def test_index_in_repo_is_synced(self):
        html = (ROOT / 'site-patches/index.html').read_text(encoding='utf-8')
        self.assertIn(START, html, 'index.html icinde blok yok: kur betigini calistir')
        self.assertEqual(install(html, JS, CSS), html, 'index.html icindeki kopya eski')

    def test_read_only_no_writes(self):
        """Sadece goruntu: kayit/karne/paylasilan veriye yazan cagri yok."""
        for bad in ('store.set', 'localStorage', 'IDB', 'saveTonight', 'karne', 'fetch(', '.set('):
            self.assertNotIn(bad, JS, bad)

    @unittest.skipUnless(shutil.which('node'), 'node yok')
    def test_js_syntax(self):
        r = subprocess.run(['node', '--check', str(ROOT / 'site-patches/eslesme-yokken-v1.js')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    @unittest.skipUnless(shutil.which('node'), 'node yok')
    def test_yokken_hesabi(self):
        """Sahte veri: A yokken B'nin 3 maci; barem 9.5 (iddaa) -> 2/3; DOM yerine sahte kutu."""
        harness = r'''
const boxes={};function el(id){return boxes[id]||(boxes[id]={id,innerHTML:'',insertAdjacentHTML(p,h){this.innerHTML+=h},addEventListener(){},parentNode:{insertBefore(){}}})}
global.window=global;global.document={getElementById:el,createElement:()=>el('cm-eo')};
const g=(ds,pts)=>({ds,t:'TOR',pts,reb:1,ast:1,fg3m:0,stl:0,blk:0,min:30});
global.S={team:'TOR',woBoth:false,mk:'PTS',pid:2,line:null,side:'over',seg:'G',opp:'MIA',pos:'SG'};
global.P={1:{id:1,name:'Ana Oyuncu',team:'TOR'},2:{id:2,name:'Bek Oyuncu',team:'TOR'}};
global.byP={1:[g('d1',20),g('d2',20)],2:[g('d1',5),g('d2',5),g('d3',12),g('d4',8),g('d5',15)]};global.HIST={};
global.MK={PTS:{label:'PTS',c:['pts']},REB:{label:'REB',c:['reb']},AST:{label:'AST',c:['ast']},'3PM':{label:'3PM',c:['fg3m']},STL:{label:'STL',c:['stl']},BLK:{label:'BLK',c:['blk']},RA:{label:'RA',c:['reb','ast']},SRA:{label:'SRA',c:['pts','reb','ast']}};
global.val=(x,mk)=>MK[mk].c.reduce((s,c)=>s+x[c],0);
global.lineFor=(id,mk)=>id===2&&mk==='PTS'?{line:9.5,n:10,odd:1.7}:null;global.mktLine=()=>null;
global.mpg=id=>30;global.teamDS=()=>new Set(['d1','d2','d3','d4','d5']);global.injOf=()=>null;
global.esc=s=>String(s);global.fmt=(n,d=1)=>Number(n).toFixed(d);global.pct=p=>'%'+Math.round(p*100);global.rkCol=()=>'#0f0';
global.withoutTable=()=>[{m:P[1],missed:3,rows:[],inj:['OUT']}];
global.renderTeam=function(){el('t-wo').innerHTML='<table></table>'};
global.renderResults=function(){};global.curSample=()=>byP[2];global.defaultLine=()=>4.5;global.hitOf=(s,mk,l)=>({p:.5});global.rankFor=()=>3;global.renderAll=()=>{};global.goPlayer=()=>{};
require(process.argv[2]);
renderTeam();const h=el('t-wo').innerHTML;
if(!h.includes('Ana Oyuncu yokken'))throw new Error('baslik yok '+h);
if(!/PTS 10\+ · <b>1.70<\/b><\/span><span class="cm-wob-hr g">2\/3 · %67/.test(h))throw new Error('hesap yanlis '+h);
renderResults();if(!el('cm-eo').innerHTML.includes('data-eo="PTS"'))throw new Error('ozet yok');
console.log('OK');
'''
        f = ROOT / 'tests' / '_eslesme_harness.js'
        try:
            f.write_text(harness, encoding='utf-8')
            r = subprocess.run(['node', str(f), str(ROOT / 'site-patches/eslesme-yokken-v1.js')], capture_output=True, text=True)
        finally:
            f.unlink(missing_ok=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipUnless(shutil.which('node'), 'node yok')
    def test_grafik_cercevesi(self):
        """Canli renderChart (18 Kasim kopyasi): REB'de rc, AST'de pot cercevesi; 3PM ayni; bozuk metinde dokunmaz."""
        harness = r'''
const fs=require('fs');global.window=global;const box={};
global.document={getElementById:id=>box[id]||(box[id]={innerHTML:'',style:{},insertAdjacentHTML(){},addEventListener(){},parentNode:{insertBefore(){}}}),createElement:()=>({})};
global.$=id=>document.getElementById(id);
eval(fs.readFileSync(process.argv[3],'utf8').replace('function renderChart','global.renderChart=function renderChart'));
global.S={side:'over',pos:'C'};global.val=(x,mk)=>({PTS:x.pts,REB:x.reb,AST:x.ast,'3PM':x.fg3m})[mk];global.rankFor=()=>5;global.fmtG=g=>g.ds;
global.esc=s=>String(s).replace(/"/g,'&quot;');global.fmt=n=>Number(n).toFixed(1);
const orig=renderChart;require(process.argv[2]);
if(renderChart===orig)throw new Error('yama uygulanmadi');
const s=[{ds:'a',o:'MIL',min:30,pts:10,reb:8,ast:4,fg3m:1,fg3a:3,rc:15,pot:10},{ds:'b',o:'MIL',min:30,pts:9,reb:14,ast:3,fg3m:0,fg3a:2,rc:14,pot:2}];
const run=mk=>{renderChart(s,mk,5.5,null);return $('chart').innerHTML};
let h=run('REB');if(!h.includes('<i>8/15</i>')||!h.includes('ribaund şansı'))throw new Error('REB '+h);
h=run('AST');if(!h.includes('<i>4/10</i>')||!h.includes('potansiyel asist')||!h.includes('Asist/potansiyel: 3/2'))throw new Error('AST '+h);
h=run('3PM');if(!h.includes('<i>1/3</i>')||!h.includes('üçlük denemesi'))throw new Error('3PM '+h);
h=run('PTS');if(h.includes('pcb-att')||h.includes('pcb-leg'))throw new Error('PTS cerceve olmamali');
if(CM_chartPatch('function x(){}')!==null)throw new Error('bozuk metinde null donmeli');
console.log('OK');
'''
        f = ROOT / 'tests' / '_grafik_harness.js'
        try:
            f.write_text(harness, encoding='utf-8')
            r = subprocess.run(['node', str(f), str(ROOT / 'site-patches/eslesme-yokken-v1.js'), str(ROOT / 'tests/fixture-renderchart-20261118.js')], capture_output=True, text=True)
        finally:
            f.unlink(missing_ok=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
