#!/usr/bin/env python3
"""Publish read-only, source-derived update metadata; no claims about workflow success."""
import argparse
import datetime as dt
import json
import pathlib
import re
import shutil

STYLES = 'cm-update-status.css'
SCRIPT = 'cm-update-status.js'

# Fix the source asset that actually renders the legacy notice. A DOM-only
# MutationObserver can miss late renderers, shadow roots and cached updates.
LEGACY_BAREM = re.compile(r"Baremler\s+20[:.]15\s*(?:['’]|\\['’])te\s+okunuyor\.?", re.I)
BAREM_REPLACEMENT = ('Barem kontrol saatleri: 18.30, 19.30 ve 20.30 (TSİ). '
                     'Güncel İddaa baremi bulunmuyorsa öneriler doğrulanmış sayılmaz.')

def rewrite_legacy_barem_assets(site):
    """Replace only the exact obsolete sentence, never unrelated time strings.

    This runs on copied publish assets, not live site or source repo JS files.
    """
    touched=[]
    for file in sorted(site.rglob('*')):
        if not file.is_file() or file.suffix not in ('.html', '.js'):
            continue
        if file.name == SCRIPT:
            continue
        before=file.read_text(encoding='utf-8')
        after, count=LEGACY_BAREM.subn(BAREM_REPLACEMENT, before)
        if count:
            file.write_text(after, encoding='utf-8')
            touched.append((str(file.relative_to(site)),count))
    return touched

def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else None
    except (ValueError, UnicodeError):
        return None

def iso_from(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdecimal()):
            n = float(value)
            if n > 1e12: n /= 1000
            if n < 1577836800 or n > 4102444800: return None
            d = dt.datetime.fromtimestamp(n, tz=dt.timezone.utc)
        else:
            d = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            if d.tzinfo is None: return None
        return d.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
    except (ValueError, TypeError, OverflowError, OSError):
        return None

def extract_stamp(doc, keys):
    if not isinstance(doc, dict): return None
    for key in keys:
        result=iso_from(doc.get(key))
        if result: return result
    return None

def build(seed):
    data = read_json(seed/'data.json')
    odds = read_json(seed/'iddaa-lines.json')
    tracking = read_json(seed/'tracking-local.json')
    karne = read_json(seed/'karne.json')
    periods = read_json(seed/'periods.json')
    rotation = read_json(seed/'rotation.json')
    entries = [
        ('nba', 'NBA oyuncu istatistikleri', data, ('updated', 'generatedAt'), 'Kaydedilen veri zamanı'),
        ('tracking', 'Tracking aktarımı', tracking, ('exported_at', 'exportedAt', 'updated'), 'Önbellek aktarım zamanı; birleştirme garantisi değildir'),
        ('odds', 'İddaa baremleri', odds, ('ts', 'updated', 'generatedAt'), 'Son kaydedilen barem zamanı'),
        ('karne', 'Günün Bahisleri / Vitrin', karne, ('generatedAt', 'updated'), 'Son Karne dosyası zamanı'),
        ('periods', 'Periyot verileri', periods, ('updated', 'generatedAt'), 'Kaydedilen dosya zamanı'),
        ('rotation', 'Rotasyon verileri', rotation, ('updated', 'generatedAt'), 'Kaydedilen dosya zamanı'),
    ]
    output = []
    for ident, label, obj, keys, note in entries:
        output.append({'id':ident,'label':label,'updated_at':extract_stamp(obj,keys),'description':note})
    return {'schema_version':1,'entries':output, 'notes':[
        'NBA CDN: günlük temel oyuncu istatistiklerini otomatik tamamlama',
        'İddaa barem kontrolü: planlanan saatler 18.30, 19.30 ve 20.30 (TSİ); gerçekleşen kayıt zamanı yukarıdadır',
        'Tracking: Windows önbelleği ile GitHub birleştirmesinde veri koruma kontrolleri',
        'Vitrin: yeni öneriler için güncel barem ve sakatlık doğrulama kontrolü',
        'Eksik tracking değerlerini sıfırla değiştirmeme ve eski maçları koruma'
    ]}

def deploy(site,seed,src):
    html_path=site/'index.html'
    if not html_path.is_file():raise RuntimeError('public/index.html yok, yayina dokunulmadi')
    html=html_path.read_text(encoding='utf-8')
    if '</body>' not in html or '</head>' not in html:
        raise RuntimeError('Sitede head/body kapanisi yok, yayina dokunulmadi')
    if not (src/STYLES).is_file() or not (src/SCRIPT).is_file():
        raise RuntimeError('Site yama dosyasi eksik')
    if 'cm-update-status.js' not in html:
        html=html.replace('</body>', '<script src="cm-update-status.js?v=20261115b" defer></script>\n</body>', 1)
    html=html.replace('cm-update-status.js?v=20261115a','cm-update-status.js?v=20261115b')
    if 'cm-update-status.css' not in html:
        html=html.replace('</head>', '<link rel="stylesheet" href="cm-update-status.css?v=20261115a">\n</head>', 1)
    data=build(seed)
    site.mkdir(exist_ok=True,parents=True)
    (site/'cm-updates.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name in (STYLES,SCRIPT):shutil.copyfile(src/name,site/name)
    html_path.write_text(html,encoding='utf-8')
    fixes=rewrite_legacy_barem_assets(site)
    if fixes:
        print('ESKI 20:15 METNI KAYNAKTAN DUZELTILDI:', fixes)
    else:
        print('UYARI: kaynak HTML/JS icinde eski metin bulunamadi; tarayici ekrani ayrica kontrol edilmeli')
    print('UPDATE STATUS: JSON + gorunur site paneli hazir, 6 kaynagin zamanlari varsa yazildi')
    return data

def main():
    p=argparse.ArgumentParser();p.add_argument('--site',default='public');p.add_argument('--seed',default='seed');p.add_argument('--patches',default='site-patches');a=p.parse_args()
    deploy(pathlib.Path(a.site),pathlib.Path(a.seed),pathlib.Path(a.patches))
if __name__=='__main__':main()
