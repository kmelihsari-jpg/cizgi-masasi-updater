import datetime as dt, json, pathlib, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from cf_deploy_sayac import say, uyari_ac

NOW = dt.datetime(2026, 11, 20, 14, 0, tzinfo=dt.timezone.utc)


def sahte_api(deploylar, sayfa_boyu=25):
    """deploylar: {proje: [iso zaman, ...]} yeniden eskiye."""
    cagri = []
    def get(path):
        cagri.append(path)
        q = dict(x.split('=') for x in path.split('?')[1].split('&')) if '?' in path else {}
        sayfa = int(q.get('page', 1))
        if path.split('?')[0].endswith('/pages/projects'):
            return {'success': True, 'result': [{'name': n} for n in deploylar] if sayfa == 1 else [],
                    'result_info': {'total_pages': 1}}
        ad = path.split('/pages/projects/')[1].split('/')[0]
        lst = deploylar[ad]
        parca = lst[(sayfa - 1) * sayfa_boyu: sayfa * sayfa_boyu]
        return {'success': True, 'result': [{'created_on': t} for t in parca],
                'result_info': {'total_pages': max(1, -(-len(lst) // sayfa_boyu))}}
    return get, cagri


def gun(d, h=12):
    return dt.datetime(2026, 11 if d > 0 else 10, d if d > 0 else 31 + d, h, tzinfo=dt.timezone.utc).isoformat().replace('+00:00', 'Z')


class Sayac(unittest.TestCase):
    def test_iki_proje_bu_ay_toplanir(self):
        cizgi = [gun(20)] * 30 + [gun(1, 0)] * 5 + [gun(-1)] * 40   # 35 bu ay, 40 ekim
        valensia = [gun(18)] * 3 + [gun(16)] * 60
        get, cagri = sahte_api({'cizgi-masasi': cizgi, 'valensia-reputation': valensia})
        s = say(get, 'hesap', NOW)
        self.assertEqual(s['projeler'], {'cizgi-masasi': 35, 'valensia-reputation': 63})
        self.assertEqual(s['toplam'], 98)
        self.assertEqual(s['ay'], '2026-11')
        # Ekim sayfalarinin hepsi okunmaz (erken durur)
        self.assertLess(len([c for c in cagri if 'cizgi-masasi/deployments' in c]), 4)

    def test_bos_proje(self):
        get, _ = sahte_api({'cizgi-masasi': []})
        self.assertEqual(say(get, 'h', NOW)['toplam'], 0)


class Uyari(unittest.TestCase):
    def sahte(self, mevcut):
        acilan = []
        def istek(yol, veri=None):
            if veri is None:
                return [{'title': b} for b in mevcut]
            acilan.append(veri['title']); return {}
        return istek, acilan

    def sonuc(self, n):
        return {'ay': '2026-11', 'toplam': n, 'projeler': {'cizgi-masasi': n - 10, 'valensia-reputation': 10}}

    def test_esik_alti_issue_yok(self):
        istek, acilan = self.sahte([])
        self.assertIsNone(uyari_ac(self.sonuc(399), istek)); self.assertEqual(acilan, [])

    def test_400_bir_kez(self):
        istek, acilan = self.sahte([])
        b = uyari_ac(self.sonuc(400), istek)
        self.assertEqual(acilan, [b]); self.assertIn('uyari', b)
        istek2, acilan2 = self.sahte([b])
        self.assertIsNone(uyari_ac(self.sonuc(430), istek2)); self.assertEqual(acilan2, [])

    def test_470_ayri_kritik(self):
        istek, acilan = self.sahte(['Cloudflare Pages kotasi 2026-11: uyari (400+/500)'])
        b = uyari_ac(self.sonuc(471), istek)
        self.assertIn('KRITIK', b); self.assertEqual(acilan, [b])

    def test_yeni_ay_yeni_issue(self):
        istek, acilan = self.sahte(['Cloudflare Pages kotasi 2026-11: uyari (400+/500)'])
        s = self.sonuc(400); s['ay'] = '2026-12'
        self.assertIsNotNone(uyari_ac(s, istek))


if __name__ == '__main__':
    unittest.main()
