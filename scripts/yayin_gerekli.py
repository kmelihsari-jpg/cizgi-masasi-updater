"""Pages yayini gerekli mi? (Cloudflare Pages ucretsiz planinda ayda 500 deploy siniri)

Yalniz workflow_run olaylarinda ve yalniz iki kaynakta yayini atlayabilir:
  - Karne Otomasyonu: seed/karne.json kayitlari canli sitedekiyle ayniysa (yeni oneri eklenmediyse) atla.
  - Iddaa Barem Senkronu: baslamamis maclarin barem/oran satirlari canli sitedekiyle ayniysa ve canli
    barem okumasi TAZELE_SAAT'ten yeniyse atla. (Site 6 saatten eski baremi "eskidi" sayar; 4 saatte bir
    degisiklik olmasa da yayinlanir.)
Diger her durumda (push, elle, diger workflow'lar, herhangi bir hata/eksik veri) YAYINLA.
Siki mod: hesaptaki Pages deploy sayisi (CF_TOPLAM, cf_deploy_sayac.py) SIKI_ESIK'e ulasinca iddaa'nin 4 saatlik
tazeleme yayini kalkar; iddaa yalniz barem/oran degisince yayinlar (kalan pay Valensia'ya ve onemli guncellemelere).

Cikti: GITHUB_OUTPUT dosyasina `yayinla=true|false`; ekrana neden.
"""
import json
import os
import pathlib
import sys
import time
import urllib.request

SITE = 'https://cizgi-masasi.pages.dev/'
TAZELE_SAAT = 4
SIKI_ESIK = 470
KARNE = 'Cizgi Masasi - Karne Otomasyonu'
IDDAA = 'Cizgi Masasi - Iddaa NBA Barem Senkronizasyonu'


def baslamamis(doc, now_unix):
    rows = doc.get('rows') if isinstance(doc, dict) else None
    if not isinstance(rows, list):
        raise ValueError('rows yok')
    out = set()
    for r in rows:
        p = str(r).split('|')
        if len(p) != 5:
            raise ValueError('gecersiz satir')
        if int(p[4]) > now_unix:
            out.add(str(r))
    return out


def karar(olay, kaynak, seed_iddaa=None, canli_iddaa=None, seed_karne=None, canli_karne=None, now=None, cf_toplam=None):
    """(yayinla: bool, neden: str). Emin olunamayan her durumda yayinla."""
    now = time.time() if now is None else now
    if olay != 'workflow_run':
        return True, f'olay={olay}: her zaman yayinla'
    try:
        if kaynak == KARNE:
            if not isinstance(seed_karne, dict) or not isinstance(canli_karne, dict):
                return True, 'karne verisi okunamadi'
            a = json.dumps(seed_karne.get('docs'), sort_keys=True, ensure_ascii=False)
            b = json.dumps(canli_karne.get('docs'), sort_keys=True, ensure_ascii=False)
            if a != b:
                return True, 'karnede yeni kayit var'
            return False, 'karne degismedi (yeni oneri yok)'
        if kaynak == IDDAA:
            if not isinstance(seed_iddaa, dict) or not isinstance(canli_iddaa, dict):
                return True, 'iddaa verisi okunamadi'
            if canli_iddaa.get('stale'):
                return True, 'canli barem eskimis (stale)'
            yas = (now * 1000 - int(canli_iddaa.get('ts', 0))) / 3600000
            siki = cf_toplam is not None and cf_toplam >= SIKI_ESIK
            if not siki and (yas < 0 or yas >= TAZELE_SAAT):
                return True, f'canli barem okumasi {yas:.1f} saatlik (esik {TAZELE_SAAT})'
            s = baslamamis(seed_iddaa, int(now))
            c = baslamamis(canli_iddaa, int(now))
            if s != c:
                return True, f'barem/oran degisti (+{len(s - c)} / -{len(c - s)} satir)'
            if siki:
                return False, f'baremler ayni; siki mod (Pages {cf_toplam}/500), tazeleme yayini yok'
            return False, f'baremler ayni, canli okuma {yas:.1f} saatlik'
        return True, f'kaynak={kaynak}: her zaman yayinla'
    except Exception as e:  # noqa: BLE001 - emin degilsen yayinla
        return True, f'hata: {e}'


def canli_json(name):
    req = urllib.request.Request(SITE + name + '?_=' + str(int(time.time())),
                                 headers={'Cache-Control': 'no-cache', 'User-Agent': 'cizgi-yayin-karari'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def seed_json(name):
    p = pathlib.Path('seed') / name
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else None


def main():
    olay = os.environ.get('OLAY', '')
    kaynak = os.environ.get('KAYNAK', '')
    veri = {}
    if olay == 'workflow_run' and kaynak in (KARNE, IDDAA):
        dosya = 'karne.json' if kaynak == KARNE else 'iddaa-lines.json'
        anahtar = 'karne' if kaynak == KARNE else 'iddaa'
        try:
            veri['seed_' + anahtar] = seed_json(dosya)
            veri['canli_' + anahtar] = canli_json(dosya)
        except Exception as e:  # noqa: BLE001
            print('UYARI: veri okunamadi, yayinlanacak:', e)
    try:
        veri['cf_toplam'] = int(os.environ['CF_TOPLAM']) if os.environ.get('CF_TOPLAM') else None
    except ValueError:
        veri['cf_toplam'] = None
    yayinla, neden = karar(olay, kaynak, **veri)
    print(('YAYINLA: ' if yayinla else 'ATLA: ') + neden)
    out = os.environ.get('GITHUB_OUTPUT')
    if out:
        with open(out, 'a', encoding='utf-8') as f:
            f.write('yayinla=' + ('true' if yayinla else 'false') + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
