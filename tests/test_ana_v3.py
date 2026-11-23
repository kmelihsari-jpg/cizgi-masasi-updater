"""ana-v3 (21 Kasım 2026) testleri. Ağ yok. node/jsdom yoksa DOM testi atlanır.
Çalıştır: python tests/test_ana_v3.py"""
import json, pathlib, shutil, subprocess, sys, tempfile, unittest, datetime as dt
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ana_v3_kur as K  # noqa: E402

JS = (ROOT / 'site-patches/ana-v3.js').read_text(encoding='utf-8')
CSS = (ROOT / 'site-patches/ana-v3.css').read_text(encoding='utf-8')
HTML = '<html><body><!--CM_YAKIN_V1_BASLA-->x<!--CM_YAKIN_V1_BITIR-->\n</body></html>'


class Blok(unittest.TestCase):
    def test_once_idempotent_after_yakin(self):
        out = K.install(HTML, JS, CSS)
        self.assertEqual(out.count(K.START), 1)
        self.assertLess(out.index('CM_YAKIN_V1_BITIR'), out.index(K.START))
        self.assertEqual(K.install(out, JS, CSS), out)

    def test_fails_closed(self):
        with self.assertRaises(RuntimeError):
            K.install('<html></html>', JS, CSS)
        with self.assertRaises(RuntimeError):
            K.install(HTML, 'x</script>', CSS)

    def test_index_synced(self):
        html = (ROOT / 'site-patches/index.html').read_text(encoding='utf-8')
        self.assertIn(K.START, html, 'python scripts/ana_v3_kur.py calistir')
        self.assertEqual(K.install(html, JS, CSS), html, 'index.html icindeki ana-v3 kopyasi eski')
        self.assertIn('<!--CM_YAKIN_V1_BITIR-->', html, 'yakin bloğu silinmemeli')

    def test_mobil_mac_listesi_yatay_kaymaz(self):
        rule = next(l for l in CSS.splitlines() if l.startswith('#view-home #h-games.hgames.cm4-list{'))
        for k in ('grid-auto-flow:row!important', 'grid-auto-columns:auto!important', 'min-width:0!important'):
            self.assertIn(k, rule)
        self.assertIn('#view-home #h-games.hgames.cm4-list>.gcard.cm4g{min-width:0!important', CSS)

    def test_no_writes_and_vitrin_rules_untouched(self):
        for bad in ('store.set', 'localStorage', 'fetch(', 'XMLHttpRequest', 'sendBeacon', 'saveTonight', 'kasaCand=', 'kasaAll=', 'heroCard=', 'noBet='):
            self.assertNotIn(bad, JS, bad)

    def test_start_dates(self):
        self.assertIn("START = '2026-11-21'", (ROOT / 'scripts/karne_automation.py').read_text(encoding='utf-8'))
        self.assertIn("if(day < '2026-11-21')continue;", (ROOT / 'scripts/karne_automation.py').read_text(encoding='utf-8'))
        self.assertIn("const START='2026-11-21';", (ROOT / 'site-patches/karne-v1.js').read_text(encoding='utf-8'))
        self.assertIn("card.get('startDate') != '2026-11-21'", (ROOT / '.github/workflows/cizgi-masasi-otomatik-pages.yml').read_text(encoding='utf-8'))
        card = json.loads((ROOT / 'seed/karne.json').read_text(encoding='utf-8'))
        self.assertEqual(card['startDate'], '2026-11-21')
        self.assertTrue(all(d['date'] >= '2026-11-21' for d in card['docs']))

    def test_archive_keeps_everything(self):
        old = json.loads((ROOT / K.OLD_ARC).read_text(encoding='utf-8'))
        new = json.loads((ROOT / K.NEW_ARC).read_text(encoding='utf-8'))
        dates = {d['date'] for d in new['docs']}
        self.assertTrue({d['date'] for d in old['docs']} <= dates)
        self.assertIn('2026-11-15', dates)
        self.assertEqual(sorted(pathlib.Path(ROOT / 'arsiv/karne').glob('karne-eski-*.json'))[-1].name, pathlib.Path(K.NEW_ARC).name,
                         'Barem Gecmisi en son arsivi okur; yeni arsiv en sonda olmali')


class Reset(unittest.TestCase):
    def test_reset_once_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            r = pathlib.Path(t); (r / 'seed').mkdir(); (r / 'arsiv/karne').mkdir(parents=True)
            (r / K.OLD_ARC).write_text(json.dumps({'docs': [{'date': '2026-11-05', 'picks': [1]}]}), encoding='utf-8')
            (r / 'seed/karne.json').write_text(json.dumps({'startDate': '2026-11-15', 'startBalance': 100, 'docs': [{'date': '2026-11-15', 'picks': [2]}, {'date': '2026-11-21', 'picks': [3]}]}), encoding='utf-8')
            now = dt.datetime(2026, 11, 21, 13, tzinfo=dt.timezone.utc)
            self.assertTrue(K.karne_reset(r, now))
            a = json.loads((r / K.NEW_ARC).read_text(encoding='utf-8'))
            self.assertEqual([d['date'] for d in a['docs']], ['2026-11-05', '2026-11-15', '2026-11-21'])
            c = json.loads((r / 'seed/karne.json').read_text(encoding='utf-8'))
            self.assertEqual((c['startDate'], c['startBalance'], c['docs']), ('2026-11-21', 100, []))
            before = (r / K.NEW_ARC).read_text(encoding='utf-8')
            self.assertFalse(K.karne_reset(r, now))
            self.assertEqual((r / K.NEW_ARC).read_text(encoding='utf-8'), before)
            self.assertEqual(json.loads((r / K.OLD_ARC).read_text(encoding='utf-8'))['docs'][0]['date'], '2026-11-05')

    def test_reset_refuses_unknown_period(self):
        with tempfile.TemporaryDirectory() as t:
            r = pathlib.Path(t); (r / 'seed').mkdir()
            (r / 'seed/karne.json').write_text(json.dumps({'startDate': '2026-10-01', 'docs': []}), encoding='utf-8')
            with self.assertRaises(RuntimeError):
                K.karne_reset(r)


class Dom(unittest.TestCase):
    def test_syntax_and_dom(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node yok (Claude kendi ortamında çalıştırdı)')
        subprocess.run([node, '--check', str(ROOT / 'site-patches/ana-v3.js')], check=True)
        if subprocess.run([node, '-e', "require('jsdom')"], capture_output=True).returncode:
            self.skipTest('jsdom yok')
        out = subprocess.run([node, str(ROOT / 'tests/ana_v3_harness.js'), str(ROOT / 'site-patches/ana-v3.js')], capture_output=True, text=True, check=True).stdout
        d = json.loads(out)
        self.assertEqual(d['rh'], 1)
        self.assertEqual(d['games'], 2); self.assertTrue(d['list'])
        self.assertEqual([x.split('|')[0] for x in d['tags']], ['MIL', 'PHI', 'NOP', 'SAS'])
        self.assertEqual(d['rec'], ['10-5'] * 4); self.assertEqual(d['b2b'], ['B2B']); self.assertEqual(d['home'], ['PHI', 'SAS'])
        self.assertTrue(d['noChips'])
        self.assertEqual(d['vitCards'], 0); self.assertTrue(d['tableKept'], 'Vitrin altindaki fotografli satirlar aynen kalmali')
        self.assertIn('Kasa defteri', d['side'])
        self.assertTrue(d['nearHidden']); self.assertTrue(d['paperHidden']); self.assertTrue(d['vitrinNotInMerdiven'])
        self.assertEqual(d['merdiven'], ['Aday Bir']); self.assertEqual(d['waiting'], ['Bekleyen Dort'])
        self.assertEqual(d['merdivenBet'], ['REB 7+']); self.assertEqual(d['gauge'], 1); self.assertIn('Eşleşme güçlü', d['why'][0])
        self.assertEqual(d['gates'], 3); self.assertEqual(d['addBtn'], 1)
        self.assertEqual(d['weak'], ['Eşleşme zayıf']); self.assertIn('#27', d['weakTxt']); self.assertIn('Eşleşme orta', d['mid'])
        self.assertEqual(d['m4Names'], ['öne çıkan bahis yok', 'Uc AST 6+']); self.assertEqual(d['m4Bars'], ['10/10']); self.assertIn('model %75', d['m4Haps'][0])
        self.assertEqual(d['revir'], ['Out Bes']); self.assertEqual(d['revirBen'], ['Fayda Alti', 'Fayda Yedi']); self.assertEqual(d['revirTitle'], 'Revir raporu')
        self.assertEqual(d['revirCols'], 5); self.assertGreaterEqual(d['revirDk'], 1)
        self.assertEqual(d['revirBar'], ['Fayda Alti|2/3 · %67'], 'yokken baremler: n>=3 olanlar, ilk 3')
        self.assertEqual(d['revirGo'], ['PHI', 5, 5, 'team'])
        self.assertEqual(d['drawers'], ['Yükselenler|true', 'Günün alt önerileri|true']); self.assertTrue(d['openAfterClick'])
        self.assertEqual(d['risers'], 1); self.assertEqual(d['unders'], ['−1.6'])
        self.assertEqual(d['karne'], 'Merdiven Altı'); self.assertIn('Merdiven Altı', d['kstrip'])
        self.assertEqual(d['shadow'], ['Aday Bir|REB|7|2|merdiven'])
        self.assertTrue(d['shadowNoVitrin']); self.assertEqual(d['picksKept'], 2)
        self.assertEqual(d['goto'], [1, 'REB']); self.assertTrue(d['emptyHidden'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
