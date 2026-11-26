import pathlib, sys, unittest
from unittest import mock
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
try:
    import nba_official as n
except ImportError:  # pdfplumber/bs4 yoksa atla
    n = None


@unittest.skipIf(n is None, 'nba_official bagimliliklari yok')
class BosRapor(unittest.TestCase):
    def test_bos_rapor_hata_vermez_ve_yazmaz(self):
        from datetime import datetime
        with mock.patch.object(n, 'find_latest', return_value=(datetime(2026, 11, 26, 9, 0), 'https://x/y.pdf')), \
             mock.patch.object(n, 'parse_pdf', return_value=([], [])), \
             mock.patch.object(n.S, 'get') as g, mock.patch.object(n.S, 'post') as post, \
             mock.patch('sys.argv', ['x']):
            g.return_value.status_code = 200
            g.return_value.content = b'%PDF-1.4'
            n.main()
            post.assert_not_called()

    def test_az_oyuncu_hala_hata(self):
        from datetime import datetime
        pl = [{'player_name': 'A B', 'team': 'UtahJazz', 'status': 'OUT', 'reason': 'x'}]
        with mock.patch.object(n, 'find_latest', return_value=(datetime(2026, 11, 26, 9, 0), 'https://x/y.pdf')), \
             mock.patch.object(n, 'parse_pdf', return_value=(pl, [])), \
             mock.patch.object(n.S, 'get') as g, mock.patch('sys.argv', ['x']):
            g.return_value.status_code = 200
            g.return_value.content = b'%PDF-1.4'
            # parse_pdf mock'landigi icin esik kontrolu burada calismaz; yalniz bos-rapor yolunun disina ciktigini dogrula
            with mock.patch.object(n, 'check_examples'):
                with self.assertRaises(RuntimeError):
                    n.main()  # NBA_IMPORT_TOKEN yok -> hata


if __name__ == '__main__':
    unittest.main()
