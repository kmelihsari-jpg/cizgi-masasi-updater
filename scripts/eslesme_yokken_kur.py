#!/usr/bin/env python3
"""Eşleşme özeti + Takım 'yokken baremler' (eslesme-yokken-v1) bloğunu site-patches/index.html'e gömer.

Kaynak: site-patches/eslesme-yokken-v1.js ve .css. index.html yayın workflow'unda olduğu gibi kopyalandığı
için workflow değişmez. Blok işaretler arasında durur; tekrar çalıştırınca güncel sürümle değiştirilir (idempotent).
Kullanım: python scripts/eslesme_yokken_kur.py [--index site-patches/index.html]
"""
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
START = '<!--CM_ESLESME_YOKKEN_V1_BASLA-->'
END = '<!--CM_ESLESME_YOKKEN_V1_BITIR-->'
ANCHOR = '<script src="canli-sakatlik.js'


def block(js: str, css: str) -> str:
    if '</script' in js.lower() or '</style' in css.lower():
        raise RuntimeError('Gömülecek kodda kapanış etiketi var')
    return f'{START}\n<style id="cm-eslesme-yokken-css">\n{css.strip()}\n</style>\n<script id="cm-eslesme-yokken">\n{js.strip()}\n</script>\n{END}'


def install(html: str, js: str, css: str) -> str:
    b = block(js, css)
    if START in html:
        s = html.index(START)
        e = html.index(END, s) + len(END)
        return html[:s] + b + html[e:]
    i = html.find(ANCHOR)
    j = html.rfind('</body>')
    if i < 0 or j < i:
        raise RuntimeError('canli-sakatlik.js etiketi ya da </body> bulunamadı; index.html beklenen biçimde değil')
    return html[:j] + b + '\n' + html[j:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--index', default=str(ROOT / 'site-patches/index.html'))
    a = ap.parse_args()
    p = Path(a.index)
    html = p.read_text(encoding='utf-8')
    js = (ROOT / 'site-patches/eslesme-yokken-v1.js').read_text(encoding='utf-8')
    css = (ROOT / 'site-patches/eslesme-yokken-v1.css').read_text(encoding='utf-8')
    out = install(html, js, css)
    if out != html:
        p.write_text(out, encoding='utf-8', newline='\n')
        print('UYGULANDI: eslesme-yokken-v1 index.html icine gomuldu')
    else:
        print('ZATEN GUNCEL: eslesme-yokken-v1')


if __name__ == '__main__':
    main()
