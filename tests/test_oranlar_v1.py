"""oranlar-v1 testleri (ag yok). jsdom yoksa DOM testi atlanir."""
import json, os, pathlib, shutil, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from oranlar_v1_kur import install, START, END  # noqa: E402

JS = (ROOT / 'site-patches/oranlar-v1.js').read_text(encoding='utf-8')
CSS = (ROOT / 'site-patches/oranlar-v1.css').read_text(encoding='utf-8')
HTML = '<html><body><script src="canli-sakatlik.js?v=1"></script>\n<script id="x"></script>\n</body></html>'


class OranlarTest(unittest.TestCase):
    def test_once_and_idempotent(self):
        out = install(HTML, JS, CSS)
        self.assertEqual(out.count(START), 1)
        self.assertLess(out.index('canli-sakatlik.js'), out.index(START))
        self.assertEqual(install(out, JS, CSS), out)

    def test_replaces_old_version(self):
        new = install(install(HTML, '/*eski*/', '.a{}'), JS, CSS)
        self.assertNotIn('/*eski*/', new)
        self.assertEqual((new.count(START), new.count(END)), (1, 1))

    def test_fails_closed(self):
        with self.assertRaises(RuntimeError):
            install('<html></html>', JS, CSS)
        with self.assertRaises(RuntimeError):
            install(HTML, 'x</script>', CSS)

    def test_index_in_repo_is_synced(self):
        html = (ROOT / 'site-patches/index.html').read_text(encoding='utf-8')
        self.assertIn(START, html, 'index.html icinde blok yok: python scripts/oranlar_v1_kur.py calistir')
        self.assertEqual(install(html, JS, CSS), html, 'index.html icindeki kopya eski')

    def test_read_only_no_writes(self):
        for bad in ('store.set', 'localStorage', 'IDB', 'saveTonight', 'karne', 'fetch(', 'XMLHttpRequest', 'sendBeacon'):
            self.assertNotIn(bad, JS, bad)

    def test_syntax_and_dom(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node yok')
        subprocess.run([node, '--check', str(ROOT / 'site-patches/oranlar-v1.js')], check=True)
        probe = subprocess.run([node, '-e', "require('jsdom')"], capture_output=True)
        if probe.returncode:
            self.skipTest('jsdom yok, DOM testi atlandi')
        r = subprocess.run([node, str(ROOT / 'tests/oranlar_dom_harness.js'), str(ROOT / 'site-patches/oranlar-v1.js')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o['chips'], 4); self.assertEqual(o['rowsClosed'], 1); self.assertEqual(o['rowsOpen'], 4)
        self.assertTrue(o['noteKept']); self.assertEqual(o['dkMatchRows'], 2); self.assertEqual(o['dkExtra'], 1)
        self.assertEqual(o['picked'], [2.5, '4.8', 'over']); self.assertTrue(o['renderCalled'])
        self.assertEqual(o['inputs'], ['2.5', '4.8']); self.assertEqual(o['chipPick'], [0.5, '1.17'])
        self.assertEqual(o['manual'], 1); self.assertTrue(o['noLadder']); self.assertEqual(o['noChips'], 0)
        self.assertTrue(o['origUntouched']); self.assertTrue(o['segEmpty']); self.assertEqual(o['dimmed'], ['2'])
        self.assertIn('1.40–1.75', o['karne']); self.assertIn('1.40–1.75', o['karneDyn'])


if __name__ == '__main__':
    unittest.main()
