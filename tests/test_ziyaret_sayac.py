"""Ziyaret sayaci + panel testleri (ag yok). Node 22+ gerekir (node:sqlite)."""
import pathlib, re, shutil, subprocess, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ZiyaretSayacTest(unittest.TestCase):
    def test_index_has_single_counter_and_keeps_other_scripts(self):
        html = (ROOT / 'site-patches' / 'index.html').read_text(encoding='utf-8')
        self.assertEqual(html.count('id="cm-ziyaret-sayac"'), 1)
        for needed in ('baslat.js', 'canli-sakatlik.js', 'id="nba-inj-check"', 'id="inj-up"', 'serviceWorker'):
            self.assertIn(needed, html)
        self.assertEqual(html.count('<script'), html.count('</script>'))

    def test_installer_is_idempotent_replaces_old_version_and_fails_closed(self):
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from ziyaret_sayac_kur import patch
        html = (ROOT / 'site-patches' / 'index.html').read_text(encoding='utf-8')
        block = re.compile(r'<script id="cm-ziyaret-sayac">.*?</script>', re.S)
        self.assertEqual(len(block.findall(html)), 1)
        self.assertEqual(patch(html), html)                                   # guncel -> degismez
        bare = html.replace('\n' + block.search(html).group(0), '', 1)
        self.assertNotIn('cm-ziyaret-sayac', bare)
        self.assertEqual(patch(bare), html)                                   # yoksa -> ayni sonucu uretir
        old = block.sub(lambda m: '<script id="cm-ziyaret-sayac">/* eski surum */</script>', html)
        self.assertEqual(patch(old), html)                                    # eski surum -> yenisiyle degisir
        crlf = html.replace('\n', '\r\n')
        out = patch(block.sub(lambda m: '<script id="cm-ziyaret-sayac">/* eski */</script>', crlf))
        self.assertEqual(out.count('\r\n'), out.count('\n'))                    # CRLF dosyada satir sonu bozulmaz
        with self.assertRaises(RuntimeError):
            patch(html + html[html.index('<script id="cm-ziyaret-sayac">'):html.index('</script>', html.index('<script id="cm-ziyaret-sayac">')) + 9])
        with self.assertRaises(RuntimeError):
            patch(bare.replace('canli-sakatlik.js', 'baska.js'))             # baglanti noktasi yoksa dokunmaz

    def test_worker_keeps_old_routes(self):
        src = (ROOT / 'worker' / 'cizgi-masasi-api.js').read_text(encoding='utf-8')
        for route in ('/api/import-nba', '/api/refresh-espn', '/api/nba-injuries', '/api/espn-injuries',
                      '/api/health', '/api/sync-status', '/api/test-espn', '/api/test-nba'):
            self.assertIn(route, src)
        self.assertIn('async scheduled(', src)

    def test_worker_and_client_with_node(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node yok')
        ver = subprocess.run([node, '--version'], capture_output=True, text=True).stdout.strip().lstrip('v').split('.')
        if (int(ver[0]), int(ver[1] if len(ver) > 1 else 0)) < (22, 5):
            self.skipTest('node:sqlite icin Node 22.5+ gerekir')
        out = subprocess.run([node, '--no-warnings', str(ROOT / 'tests' / 'ziyaret_sayac.test.mjs'), str(ROOT)],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn('TUM TESTLER GECTI', out.stdout)


if __name__ == '__main__':
    unittest.main()
