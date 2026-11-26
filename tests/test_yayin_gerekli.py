import json, pathlib, sys, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from yayin_gerekli import karar, KARNE, IDDAA, FARK_DOSYALARI

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

    def test_siki_mod_tazeleme_yok(self):
        r = [f'1|PTS|20|1.8|{GELECEK}']
        self.assertTrue(karar('workflow_run', IDDAA, seed_iddaa=idd(r, 0.1), canli_iddaa=idd(r, 5.0), now=NOW, cf_toplam=469)[0])
        self.assertFalse(karar('workflow_run', IDDAA, seed_iddaa=idd(r, 0.1), canli_iddaa=idd(r, 5.0), now=NOW, cf_toplam=470)[0])

    def test_siki_modda_degisiklik_yine_yayinlanir(self):
        a = [f'1|PTS|20|1.8|{GELECEK}']
        b = [f'1|PTS|20|1.9|{GELECEK}']
        self.assertTrue(karar('workflow_run', IDDAA, seed_iddaa=idd(a, 0.1), canli_iddaa=idd(b, 5.0), now=NOW, cf_toplam=495)[0])
        k = {'docs': [{'picks': [1]}]}
        self.assertTrue(karar('workflow_run', KARNE, seed_karne=k, canli_karne={'docs': []}, now=NOW, cf_toplam=495)[0])

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
        self.assertIn("needs.karar.outputs.yayinla != 'false'", pages)
        self.assertIn('yayinla: ${{ steps.gerek.outputs.yayinla }}', pages)
        self.assertIn('FARK_VARSA: ${{ inputs.fark_varsa }}', pages)
        # Agir build job'u karardan sonra gelir; karar job'unda build/indirme adimi olmamali.
        self.assertLess(pages.index('  karar:'), pages.index('  siteyi-hazirla:'))
        self.assertNotIn('wrangler', pages[pages.index('  karar:'):pages.index('  siteyi-hazirla:')])
        # Hicbir workflow kendi basina yayin tetiklemez; yayin yalniz Worker'in sabit noktalarindan (dispatch) ve push ile.
        self.assertNotIn('workflow_run', pages)
        self.assertIn('scripts/cf_deploy_sayac.py', pages)
        self.assertIn('CF_TOPLAM: ${{ steps.kota.outputs.cf_toplam }}', pages)
        self.assertIn('issues: write', pages)
        self.assertNotIn('--kota', pages)


FN = 1795200000
IDD = {'ts': FN * 1000 - 3600000, 'rows': ['a|b|c|2.0|%d' % (FN + 5000)]}


def _dosyalar(**degisen):
    d = {ad: {'ad': ad, 'v': 1} for ad in FARK_DOSYALARI}
    d['iddaa-lines.json'] = IDD
    d['karne.json'] = {'docs': [{'date': '2026-11-24', 'picks': [1]}], 'generatedAt': 'x'}
    d.update(degisen)
    return d


class SabitYayinNoktasi(unittest.TestCase):
    def test_fark_yok_atla(self):
        y, neden = karar('workflow_dispatch', '', now=FN, fark_modu=True, seed_dosyalar=_dosyalar(), canli_dosyalar=_dosyalar())
        self.assertFalse(y, neden)

    def test_karne_generatedat_farki_sayilmaz(self):
        s = _dosyalar(**{'karne.json': {'docs': [{'date': '2026-11-24', 'picks': [1]}], 'generatedAt': 'baska'}})
        self.assertFalse(karar('workflow_dispatch', '', now=FN, fark_modu=True, seed_dosyalar=s, canli_dosyalar=_dosyalar())[0])

    def test_data_farkli_yayinla(self):
        s = _dosyalar(**{'data.json': {'ad': 'data.json', 'v': 2}})
        y, neden = karar('workflow_dispatch', '', now=FN, fark_modu=True, seed_dosyalar=s, canli_dosyalar=_dosyalar())
        self.assertTrue(y)
        self.assertIn('data.json', neden)

    def test_karne_docs_farkli_yayinla(self):
        s = _dosyalar(**{'karne.json': {'docs': [{'date': '2026-11-24', 'picks': [1, 2]}]}})
        self.assertTrue(karar('workflow_dispatch', '', now=FN, fark_modu=True, seed_dosyalar=s, canli_dosyalar=_dosyalar())[0])

    def test_okunamayan_dosya_yayinla(self):
        c = _dosyalar(); c['periods.json'] = None
        self.assertTrue(karar('workflow_dispatch', '', now=FN, fark_modu=True, seed_dosyalar=_dosyalar(), canli_dosyalar=c)[0])
        self.assertTrue(karar('workflow_dispatch', '', fark_modu=True)[0])

    def test_fark_modu_kapaliysa_elle_her_zaman(self):
        self.assertTrue(karar('workflow_dispatch', '', seed_dosyalar=_dosyalar(), canli_dosyalar=_dosyalar())[0])

    def test_fark_modu_yalniz_dispatch(self):
        self.assertTrue(karar('push', '', fark_modu=True, seed_dosyalar=_dosyalar(), canli_dosyalar=_dosyalar())[0])

    def test_iddaa_oran_degisti_yayinla(self):
        s = _dosyalar(**{'iddaa-lines.json': {'ts': IDD['ts'], 'rows': ['a|b|c|2.1|%d' % (FN + 5000)]}})
        y, neden = karar('workflow_dispatch', '', now=FN, fark_modu=True, seed_dosyalar=s, canli_dosyalar=_dosyalar())
        self.assertTrue(y); self.assertIn('iddaa', neden)

    def test_iddaa_baslamis_mac_farki_sayilmaz(self):
        eski = 'x|y|z|1.5|%d' % (FN - 100)
        s = _dosyalar(**{'iddaa-lines.json': {'ts': IDD['ts'], 'rows': IDD['rows'] + [eski]}})
        self.assertFalse(karar('workflow_dispatch', '', now=FN, fark_modu=True, seed_dosyalar=s, canli_dosyalar=_dosyalar())[0])

    def test_iddaa_4_saat_eskidi_yayinla_siki_modda_degil(self):
        eski = {'ts': FN * 1000 - 5 * 3600000, 'rows': IDD['rows']}
        c = _dosyalar(**{'iddaa-lines.json': eski})
        self.assertTrue(karar('workflow_dispatch', '', now=FN, fark_modu=True, seed_dosyalar=c, canli_dosyalar=c)[0])
        self.assertFalse(karar('workflow_dispatch', '', now=FN, cf_toplam=480, fark_modu=True, seed_dosyalar=c, canli_dosyalar=c)[0])


class MacsizGun(unittest.TestCase):
    def test_macsiz_gunde_4_saat_tazeleme_yok(self):
        bos = {'ts': FN * 1000 - 5 * 3600000, 'rows': ['a|b|c|2.0|%d' % (FN - 600)]}  # tek satir, mac baslamis
        c = _dosyalar(**{'iddaa-lines.json': bos})
        y, neden = karar('workflow_dispatch', '', now=FN, fark_modu=True, seed_dosyalar=c, canli_dosyalar=c)
        self.assertFalse(y, neden)
        y, neden = karar('workflow_run', IDDAA, seed_iddaa=bos, canli_iddaa=bos, now=FN)
        self.assertFalse(y, neden)

    def test_macsiz_gunde_bile_stale_yayinla(self):
        bos = {'ts': FN * 1000 - 5 * 3600000, 'rows': [], 'stale': True}
        c = _dosyalar(**{'iddaa-lines.json': bos})
        self.assertTrue(karar('workflow_dispatch', '', now=FN, fark_modu=True, seed_dosyalar=c, canli_dosyalar=c)[0])

    def test_yeni_mac_satiri_gelince_yayinla(self):
        canli = {'ts': FN * 1000 - 5 * 3600000, 'rows': []}
        seed = {'ts': FN * 1000 - 600000, 'rows': ['a|b|c|2.0|%d' % (FN + 5000)]}
        self.assertTrue(karar('workflow_run', IDDAA, seed_iddaa=seed, canli_iddaa=canli, now=FN)[0])


if __name__ == '__main__':
    unittest.main()
