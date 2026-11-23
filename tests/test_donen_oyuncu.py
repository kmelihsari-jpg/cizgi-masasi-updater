"""donen-oyuncu-v1 testleri (ag yok)."""
import json, pathlib, shutil, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from donen_oyuncu_kur import install, START, END  # noqa: E402

JS = (ROOT / 'site-patches/donen-oyuncu-v1.js').read_text(encoding='utf-8')
CSS = (ROOT / 'site-patches/donen-oyuncu-v1.css').read_text(encoding='utf-8')
HTML = '<html><body><script src="canli-sakatlik.js?v=1"></script>\n<script id="x"></script>\n</body></html>'


class KurTest(unittest.TestCase):
    def test_once_and_idempotent(self):
        out = install(HTML, JS, CSS)
        self.assertEqual(out.count(START), 1)
        self.assertLess(out.index('canli-sakatlik.js'), out.index(START))
        self.assertEqual(install(out, JS, CSS), out)

    def test_fails_closed(self):
        with self.assertRaises(RuntimeError):
            install('<html></html>', JS, CSS)
        with self.assertRaises(RuntimeError):
            install(HTML, 'x</script>', CSS)

    def test_index_in_repo_is_synced(self):
        html = (ROOT / 'site-patches/index.html').read_text(encoding='utf-8')
        self.assertIn(START, html, 'index.html icinde blok yok: python scripts/donen_oyuncu_kur.py calistir')
        self.assertEqual(install(html, JS, CSS), html, 'index.html icindeki kopya eski')

    def test_read_only_no_writes(self):
        for bad in ('store.set', 'localStorage', 'IDB', 'saveTonight', 'karne', 'fetch(', 'XMLHttpRequest', 'sendBeacon', '.set('):
            self.assertNotIn(bad, JS, bad)

    def test_syntax_and_dom(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node yok')
        subprocess.run([node, '--check', str(ROOT / 'site-patches/donen-oyuncu-v1.js')], check=True)
        if subprocess.run([node, '-e', "require('jsdom')"], capture_output=True).returncode:
            self.skipTest('jsdom yok, DOM testi atlandi')
        r = subprocess.run([node, str(ROOT / 'tests/donen_oyuncu_dom_harness.js'), str(ROOT / 'site-patches/donen-oyuncu-v1.js')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o['badges'], 2)
        self.assertEqual(sorted(o['rowsWithBadge']), ['2', '3'])
        self.assertIn('Ingram dönüyor', o['text'])
        self.assertTrue(o['btnClean'])
        self.assertEqual(o['badgesAfter'], 3)
        self.assertTrue(o['noLineNoBadge'])


if __name__ == '__main__':
    unittest.main()
