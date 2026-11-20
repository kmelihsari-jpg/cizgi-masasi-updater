"""Cloudflare Pages aylik deploy sayaci (ucretsiz planda ayda 500; hesaptaki TUM Pages projeleri birlikte sayilir).

Hesaptaki her Pages projesinin (cizgi-masasi, valensia-reputation, ileride eklenecekler) bu takvim ayindaki
(UTC) deploy'larini Cloudflare API'den sayar. Yalniz okur; hicbir seyi degistirmez.

Cikti: --out JSON dosyasi ({ay, toplam, sinir, projeler, okundu} ya da {hata}), GITHUB_OUTPUT'a cf_toplam=N,
Actions ozetine (GITHUB_STEP_SUMMARY) bir satir. Sitede GOSTERILMEZ.
Uyari: 400 ve 470 esiklerinde, o ay icin acik yoksa repoda birer issue acar (GitHub sahibine e-posta gonderir;
ayda en fazla 2). Hata olursa yayini durdurmaz (exit 0).
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

API = 'https://api.cloudflare.com/client/v4'
SINIR = 500
EN_FAZLA_SAYFA = 40


def api_get(token):
    def get(path):
        req = urllib.request.Request(API + path, headers={'Authorization': 'Bearer ' + token,
                                                         'User-Agent': 'cizgi-deploy-sayac'})
        with urllib.request.urlopen(req, timeout=30) as r:
            doc = json.loads(r.read().decode('utf-8'))
        if not doc.get('success'):
            raise RuntimeError('Cloudflare API: ' + json.dumps(doc.get('errors'))[:200])
        return doc
    return get


def zaman(s):
    return dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))


def ay_basi(now):
    return now.astimezone(dt.timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def say(get, hesap, now):
    bas = ay_basi(now)
    projeler = []
    for sayfa in range(1, 11):
        doc = get(f'/accounts/{hesap}/pages/projects' + ('' if sayfa == 1 else f'?page={sayfa}'))
        sonuc = doc.get('result') or []
        projeler += [p['name'] for p in sonuc]
        toplam_sayfa = (doc.get('result_info') or {}).get('total_pages')
        if not sonuc or not toplam_sayfa or sayfa >= toplam_sayfa:
            break
    sayim = {}
    for ad in projeler:
        n = 0
        for sayfa in range(1, EN_FAZLA_SAYFA + 1):
            doc = get(f'/accounts/{hesap}/pages/projects/{urllib.parse.quote(ad)}/deployments?page={sayfa}')
            sonuc = doc.get('result') or []
            zamanlar = [zaman(d['created_on']) for d in sonuc if d.get('created_on')]
            n += sum(1 for t in zamanlar if t >= bas)
            toplam_sayfa = (doc.get('result_info') or {}).get('total_pages')
            # Liste yeniden eskiye sirali: sayfanin tamami bu aydan onceyse dur.
            if not zamanlar or all(t < bas for t in zamanlar) or (toplam_sayfa and sayfa >= toplam_sayfa):
                break
        sayim[ad] = n
    return {'ay': bas.strftime('%Y-%m'), 'toplam': sum(sayim.values()), 'sinir': SINIR, 'projeler': sayim,
            'okundu': now.astimezone(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')}


UYARI_ESIKLERI = ((470, 'KRITIK'), (400, 'uyari'))


def gh_istek(token, repo, yol, veri=None):
    req = urllib.request.Request(f'https://api.github.com/repos/{repo}{yol}',
                                 data=json.dumps(veri).encode('utf-8') if veri is not None else None,
                                 method='POST' if veri is not None else 'GET',
                                 headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                                          'User-Agent': 'cizgi-deploy-sayac'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def uyari_basligi(sonuc):
    for esik, seviye in UYARI_ESIKLERI:
        if sonuc['toplam'] >= esik:
            return f"Cloudflare Pages kotasi {sonuc['ay']}: {seviye} ({esik}+/{SINIR})"
    return None


def uyari_ac(sonuc, istek):
    """Esik asildiysa ve bu ay bu esik icin issue yoksa ac. Donus: acilan baslik ya da None."""
    baslik = uyari_basligi(sonuc)
    if not baslik:
        return None
    acik = istek('/issues?state=all&per_page=100')
    if any(i.get('title') == baslik for i in acik):
        return None
    govde = (f"Bu ay (UTC {sonuc['ay']}) hesaptaki Cloudflare Pages deploy sayisi **{sonuc['toplam']}/{SINIR}**.\n\n"
             + '\n'.join(f'- {ad}: {n}' for ad, n in sonuc['projeler'].items())
             + '\n\n470 ve ustunde Cizgi Masasi siki moda gecer (iddaa yalniz barem/oran degisince yayinlar). '
               'Sinir dolarsa ay sonuna kadar yeni deploy yapilamaz; ucret cikmaz. Otomatik acildi (cf_deploy_sayac.py).')
    istek('/issues', {'title': baslik, 'body': govde})
    return baslik


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='cf-kota.json')
    a = ap.parse_args()
    token, hesap = os.environ.get('CF_API_TOKEN'), os.environ.get('CF_ACCOUNT_ID')
    try:
        if not token or not hesap:
            raise RuntimeError('CF_API_TOKEN / CF_ACCOUNT_ID yok')
        sonuc = say(api_get(token), hesap, dt.datetime.now(dt.timezone.utc))
        print(f"CLOUDFLARE PAGES {sonuc['ay']}: {sonuc['toplam']}/{SINIR}", sonuc['projeler'])
        if sonuc['toplam'] >= 400:
            print(f"::warning::Cloudflare Pages bu ay {sonuc['toplam']}/{SINIR} deploy")
        gh_token, repo = os.environ.get('GITHUB_TOKEN'), os.environ.get('GITHUB_REPOSITORY')
        if gh_token and repo:
            try:
                acilan = uyari_ac(sonuc, lambda yol, veri=None: gh_istek(gh_token, repo, yol, veri))
                if acilan:
                    print('UYARI ISSUE ACILDI:', acilan)
            except Exception as e:  # noqa: BLE001
                print('UYARI: kota issue acilamadi:', str(e)[:200])
    except Exception as e:  # noqa: BLE001 - sayac yayini asla durdurmaz
        sonuc = {'hata': str(e)[:200]}
        print('UYARI: deploy sayaci okunamadi:', sonuc['hata'])
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(sonuc, f, ensure_ascii=False)
    ozet = os.environ.get('GITHUB_STEP_SUMMARY')
    if ozet:
        with open(ozet, 'a', encoding='utf-8') as f:
            if 'toplam' in sonuc:
                f.write(f"**Cloudflare Pages bu ay:** {sonuc['toplam']}/{SINIR} deploy ("
                        + ' · '.join(f'{k} {v}' for k, v in sonuc['projeler'].items()) + ')\n')
            else:
                f.write(f"**Cloudflare Pages sayaci okunamadi:** {sonuc['hata']}\n")
    out = os.environ.get('GITHUB_OUTPUT')
    if out and 'toplam' in sonuc:
        with open(out, 'a', encoding='utf-8') as f:
            f.write(f"cf_toplam={sonuc['toplam']}\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
