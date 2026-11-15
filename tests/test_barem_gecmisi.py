"""Barem Gecmisi V2 yamasi: arsivden son 8 barem + sonuc. Yerel, agsiz (route ile)."""
import json, pathlib, unittest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
JS = (ROOT / 'site-patches' / 'barem-gecmisi.js').read_text(encoding='utf-8')
ARC = ''.join(p.read_text(encoding='utf-8') for p in sorted((ROOT / 'arsiv' / 'iddaa').glob('lines-*.ndjson')))
OLD = (ROOT / 'arsiv' / 'karne' / 'karne-eski-2026-11-05_14.json').read_text(encoding='utf-8')

TOWNS = 1626157
# Sentetik oyuncu: 12 gun, her gun tek barem (10+), son 8 gosterilmeli.
SYN = ''.join(json.dumps([1790000000 + i * 86400, 999, 'PTS', 10, 1.7 + (i % 3) / 100, 1790040000 + i * 86400, 'test']) + '\n' for i in range(12))

HTML = """<!doctype html><html><head><meta charset="utf-8"></head><body>
<div id="view-player"><div id="bhist" hidden></div></div>
<script>
const S={pid:null,mk:'3PM'};
let D={dates:[]};
const byP={};
const MK={PTS:{c:['pts']},'3PM':{c:['fg3m']}};
function val(g,mk){return MK[mk].c.reduce((s,c)=>s+g[c],0)}
const ETZ='America/New_York';
function dayKey(ts){return new Date(ts).toLocaleDateString('en-CA',{timeZone:ETZ})}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function fmtD(iso){const[y,m,d]=iso.split('-').map(Number);return new Date(Date.UTC(y,m-1,d,12)).toLocaleDateString('tr-TR',{day:'numeric',month:'short',timeZone:'UTC'})}
const $=id=>document.getElementById(id);
let REAL=[];
function renderBHist(){}
function bhistRefresh(){try{const v=$('view-player');if(v&&!v.hidden&&S.pid)renderBHist(S.mk)}catch(e){}}
</script>
<script src="barem-gecmisi.js"></script>
</body></html>"""


class BaremGecmisiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def page(self, arc=ARC + SYN, old=OLD, status=200):
        pg = self.browser.new_page()
        pg.clock.install(time=__import__('datetime').datetime(2026, 11, 15, 18, 30))
        def route(r):
            u = r.request.url
            if u.endswith('barem-gecmisi.js'):
                r.fulfill(status=200, content_type='text/javascript; charset=utf-8', body=JS)
            elif u.endswith('barem-arsiv.ndjson'):
                r.fulfill(status=status, content_type='text/plain; charset=utf-8', body=arc)
            elif u.endswith('karne-eski.json'):
                r.fulfill(status=status, content_type='application/json; charset=utf-8', body=old)
            else:
                r.fulfill(status=200, content_type='text/html; charset=utf-8', body=HTML)
        pg.route('**/*', route)
        pg.goto('http://t.test/')
        pg.wait_for_function('typeof ARC!=="undefined"||true')
        pg.wait_for_timeout(400)
        return pg

    def render(self, pg, pid, mk, byp, dates):
        return pg.evaluate("""([pid,mk,byp,dates])=>{S.pid=pid;S.mk=mk;D.dates=dates;for(const k in byp)byP[k]=byp[k];renderBHist(mk);const el=$('bhist');return {hidden:el.hidden,html:el.innerHTML}}""", [pid, mk, byp, dates])

    def test_towns_old_and_new_lines(self):
        pg = self.page()
        byp = {str(TOWNS): [{'ds': '2026-11-11', 'fg3m': 2}, {'ds': '2026-11-13', 'fg3m': 3}]}
        r = self.render(pg, TOWNS, '3PM', byp, ['2026-11-11', '2026-11-13'])
        self.assertFalse(r['hidden'])
        h = r['html']
        self.assertIn('1.89', h)               # 11 Kasim: karne kaydi (arsiv oncesi)
        self.assertIn('2.45', h)               # 13 Kasim: arsiv + karne
        self.assertIn('1.68', h)               # 15 Kasim: guncel barem, mac daha oynanmadi
        self.assertEqual(h.count('✓ tuttu'), 2)
        self.assertIn('bekliyor', h)
        self.assertIn('Kasa', h)
        self.assertLess(h.index('1.68'), h.index('2.45'))   # yeniden eskiye
        self.assertLess(h.index('2.45'), h.index('1.89'))
        pg.close()

    def test_limit_8_newest_first(self):
        pg = self.page()
        r = self.render(pg, 999, 'PTS', {}, [])
        self.assertFalse(r['hidden'])
        self.assertEqual(r['html'].count('<tr><td'), 8)
        pg.close()

    def test_miss_when_below_line_and_dnp(self):
        pg = self.page(arc='', old=json.dumps({'docs': [{'date': '2026-11-13', 'picks': [{'id': 5, 'mk': 'PTS', 'n': 20, 'odd': 1.6}], 'early': [12]}, {'date': '2026-11-12', 'picks': [{'id': 5, 'mk': 'PTS', 'n': 20, 'odd': 1.7}], 'early': ['dnp']}]}))
        r = self.render(pg, 5, 'PTS', {'5': []}, [])
        self.assertIn('✗ tutmadı', r['html'])
        self.assertIn('oynamadı', r['html'])
        pg.close()

    def test_hidden_without_records_and_when_files_missing(self):
        pg = self.page(arc='', old='', status=404)
        r = self.render(pg, 424242, 'PTS', {}, [])
        self.assertTrue(r['hidden'])
        self.assertEqual(r['html'], '')
        pg.close()

    def test_archive_not_modified_inputs(self):
        # Betik sadece okur: fetch disinda yazma/silme cagrisi yok.
        for bad in ('localStorage.setItem', 'indexedDB', 'method:\'POST\'', 'method: "POST"', '.delete('):
            self.assertNotIn(bad, JS)


if __name__ == '__main__':
    unittest.main()
