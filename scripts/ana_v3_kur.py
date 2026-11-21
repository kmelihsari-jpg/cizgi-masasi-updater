#!/usr/bin/env python3
"""Ana sayfa v3 (21 Kasım 2026) kurulumu. Tekrar çalıştırılabilir (idempotent).

1) site-patches/ana-v3.js/.css bloğunu site-patches/index.html'e gömer (yakın adaylar bloğundan sonra).
2) Karne yeni dönemi (2026-11-21, 100 birim), sadece bir kez:
   - Eski karne SİLİNMEZ: arsiv/karne/karne-eski-2026-11-05_21.json = önceki arşiv (5-14 Kasım) + seed/karne.json
     belgeleri. Barem Geçmişi en son arşiv dosyasını okuduğu için iki dönem de orada kalır. Dosya varsa üzerine yazılmaz.
   - seed/karne.json yeni dönemle boş açılır.
3) START tarihini karne_automation.py, karne-v1.js ve yayın workflow'undaki karne kontrolünde 2026-11-21 yapar.
Kullanım: python scripts/ana_v3_kur.py
"""
from pathlib import Path
import datetime as dt, json, argparse

ROOT = Path(__file__).resolve().parents[1]
START = '<!--CM_ANA_V3_BASLA-->'
END = '<!--CM_ANA_V3_BITIR-->'
AFTER = '<!--CM_YAKIN_V1_BITIR-->'
OLD_D, NEW_D = '2026-11-15', '2026-11-21'
OLD_ARC = 'arsiv/karne/karne-eski-2026-11-05_14.json'
NEW_ARC = 'arsiv/karne/karne-eski-2026-11-05_21.json'


def block(js, css):
    if '</script' in js.lower() or '</style' in css.lower():
        raise RuntimeError('Gömülecek kodda kapanış etiketi var')
    return f'{START}\n<style id="cm-ana-v3-css">\n{css.strip()}\n</style>\n<script id="cm-ana-v3">\n{js.strip()}\n</script>\n{END}'


def install(html, js, css):
    b = block(js, css)
    if START in html:
        s = html.index(START); e = html.index(END, s) + len(END)
        return html[:s] + b + html[e:]
    i = html.find(AFTER)
    j = html.rfind('</body>')
    if i < 0 or j < i:
        raise RuntimeError('Yakın adaylar bloğu ya da </body> bulunamadı; index.html beklenen biçimde değil')
    k = i + len(AFTER)
    return html[:k] + '\n' + b + html[k:]


def swap(path, pairs, name):
    p = ROOT / path; t = p.read_text(encoding='utf-8'); o = t
    for old, new, need in pairs:
        if new in t and old not in t:
            continue
        if old not in t:
            raise RuntimeError(f'{name}: beklenen metin yok: {old!r}')
        if need is not None and t.count(old) != need:
            raise RuntimeError(f'{name}: {old!r} {t.count(old)} kez geçiyor, {need} bekleniyordu')
        t = t.replace(old, new)
    if t != o:
        p.write_text(t, encoding='utf-8', newline='\n'); print('GUNCELLENDI:', path)
    else:
        print('ZATEN GUNCEL:', path)


def karne_reset(root=ROOT, today=None):
    seed = root / 'seed/karne.json'
    cur = json.loads(seed.read_text(encoding='utf-8-sig'))
    if cur.get('startDate') == NEW_D:
        print('KARNE ZATEN YENI DONEMDE'); return False
    if cur.get('startDate') != OLD_D or not isinstance(cur.get('docs'), list):
        raise RuntimeError('seed/karne.json beklenen dönemde değil; dokunulmadı')
    arc = root / NEW_ARC
    if not arc.exists():
        old = json.loads((root / OLD_ARC).read_text(encoding='utf-8'))
        if not isinstance(old.get('docs'), list) or not old['docs']:
            raise RuntimeError('Eski karne arşivi geçersiz')
        docs = sorted(old['docs'] + cur['docs'], key=lambda d: d.get('date', ''))
        out = {'kaynak': f"{OLD_ARC} + seed/karne.json ({OLD_D} dönemi)",
               'donem': f"2026-11-05 – {NEW_D} öncesi; {NEW_D} gecesi kaydı varsa o da burada",
               'arsivlendi': (today or dt.datetime.now(dt.timezone.utc)).isoformat(),
               'docs': docs}
        arc.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        print('ARSIV YAZILDI:', NEW_ARC, len(docs), 'gun')
    else:
        a = json.loads(arc.read_text(encoding='utf-8'))
        have = {d.get('date') for d in a.get('docs', [])}
        miss = [d.get('date') for d in cur['docs'] if d.get('date') not in have]
        if miss:
            raise RuntimeError(f'Arşiv var ama şu günler eksik: {miss}; dokunulmadı')
        print('ARSIV ZATEN VAR:', NEW_ARC)
    new = {'startDate': NEW_D, 'startBalance': 100,
           'generatedAt': (today or dt.datetime.now(dt.timezone.utc)).isoformat(), 'docs': []}
    seed.write_text(json.dumps(new, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('KARNE YENI DONEM:', NEW_D, '100 birim')
    return True


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--sadece-blok', action='store_true'); a = ap.parse_args()
    idx = ROOT / 'site-patches/index.html'
    html = idx.read_text(encoding='utf-8')
    js = (ROOT / 'site-patches/ana-v3.js').read_text(encoding='utf-8')
    css = (ROOT / 'site-patches/ana-v3.css').read_text(encoding='utf-8')
    out = install(html, js, css)
    if out != html:
        idx.write_text(out, encoding='utf-8', newline='\n'); print('UYGULANDI: ana-v3 index.html icine gomuldu')
    else:
        print('ZATEN GUNCEL: ana-v3')
    if a.sadece_blok:
        return
    swap('scripts/karne_automation.py', [(f"START = '{OLD_D}'", f"START = '{NEW_D}'", 1),
                                         (f"if(day < '{OLD_D}')continue;", "if(day < '" + NEW_D + "')continue;", 1)], 'karne_automation')
    swap('site-patches/karne-v1.js', [(f"const START='{OLD_D}';", f"const START='{NEW_D}';", 1),
                                      ('Yeni Karne dönemi · 15 Kasım 2026', 'Yeni Karne dönemi · 21 Kasım 2026', 1)], 'karne-v1')
    swap('.github/workflows/cizgi-masasi-otomatik-pages.yml',
         [(f"card.get('startDate') != '{OLD_D}'", f"card.get('startDate') != '{NEW_D}'", 1)], 'workflow')
    karne_reset()


if __name__ == '__main__':
    main()
