import json, pathlib, sys, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from yayin_gerekli import karar, KARNE, IDDAA

NOW = 1795200000.0
GELECEK = int(NOW) + 7200
GECMIS = int(NOW) - 600


def idd(rows, ts_saat_once=1.0, **ek):
    d = {'ts': int((NOW - ts_saat_once * 3600) * 1000), 'rows': rows, 'count': len(rows)}
    d.update(ek)
    return d


class YayinKarari(unittest.TestCase):
    def test_push_ve_elle_her_zaman(self):
        self.assertTrue(karar('push', '')[0])
        self.assertTrue(karar('workflow_dispatch', '')[0])

    def test_diger_kaynaklar_her_zaman(self):
        self.assertTrue(karar('workflow_run', 'Cizgi Masasi - NBA CDN Guvenli Uygula')[0])

    def test_karne_ayni_atla(self):
        k = {'docs': [{'date': '2026-11-20', 'picks': [{'id': 1}]}], 'generatedAt': 'a'}
        k2 = dict(k, generatedAt='b')
        self.assertFalse(karar('workflow_run', KARNE, seed_karne=k, canli_karne=k2, now=NOW)[0])

    def test_karne_yeni_kayit_yayinla(self):
        a = {'docs': [{'date': '2026-11-20', 'picks': [{'id': 1}]}]}
        b = {'docs': [{'date': '2026-11-20', 'picks': []}]}
        self.assertTrue(karar('workflow_run', KARNE, seed_karne=a, canli_karne=b, now=NOW)[0])

    def test_karne_veri_yok_yayinla(self):
        self.assertTrue(karar('workflow_run', KARNE, now=NOW)[0])

    def test_iddaa_ayni_taze_atla(self):
        r = [f'1|PTS|20|1.8|{GELECEK}']
        y, neden = karar('workflow_run', IDDAA, seed_iddaa=idd(r, 0.1), canli_iddaa=idd(r, 1.0), now=NOW)
        self.assertFalse(y, neden)

    def test_iddaa_baslamis_mac_farki_sayilmaz(self):
        r = [f'1|PTS|20|1.8|{GELECEK}']
        canli = r + [f'2|REB|8|1.9|{GECMIS}']
        self.assertFalse(karar('workflow_run', IDDAA, seed_iddaa=idd(r, 0.1), canli_iddaa=idd(canli), now=NOW)[0])

    def test_iddaa_oran_degisti_yayinla(self):
        a = [f'1|PTS|20|1.8|{GELECEK}']
        b = [f'1|PTS|20|1.9|{GELECEK}']
        self.assertTrue(karar('workflow_run', IDDAA, seed_iddaa=idd(a, 0.1), canli_iddaa=idd(b), now=NOW)[0])

    def test_iddaa_canli_4_saat_eski_yayinla(self):
        r = [f'1|PTS|20|1.8|{GELECEK}']
        self.assertTrue(karar('workflow_run', IDDAA, seed_iddaa=idd(r, 0.1), canli_iddaa=idd(r, 4.0), now=NOW)[0])

    def test_iddaa_stale_yayinla(self):
        self.assertTrue(karar('workflow_run', IDDAA, seed_iddaa=idd([], 0.1), canli_iddaa=idd([], 1, stale=True), now=NOW)[0])

    def test_bozuk_veri_yayinla(self):
        self.assertTrue(karar('workflow_run', IDDAA, seed_iddaa={'ts': 1, 'rows': ['bozuk']}, canli_iddaa=idd([], 1), now=NOW)[0])

    def test_workflow_adlari_gercek(self):
        wf = pathlib.Path(__file__).resolve().parents[1] / '.github' / 'workflows'
        adlar = [l.split(':', 1)[1].strip() for f in wf.glob('*.yml') for l in f.read_text(encoding='utf-8').splitlines() if l.startswith('name:')]
        self.assertIn(KARNE, adlar)
        self.assertIn(IDDAA, adlar)
        pages = (wf / 'cizgi-masasi-otomatik-pages.yml').read_text(encoding='utf-8')
        self.assertIn('scripts/yayin_gerekli.py', pages)
        self.assertIn("steps.gerek.outputs.yayinla != 'false'", pages)


if __name__ == '__main__':
    unittest.main()
