#!/usr/bin/env python3
"""Takim sekmesi 'Kim yokken kim artiyor': devam eden yokluklari da say.

Sorun: withoutTable() bir oyuncunun kacirdigi maclari yalnizca KENDI ILK ve SON oynadigi maclar
arasinda sayiyor. Su an sakat olan oyuncunun son oynadigindan sonraki maclari araliga girmiyor;
ornegin Markkanen (UTA) 13 maçın 8'ini oynadi, son 4 maci disarida, arada tek mac kacirdi ->
sayi 1 < 2 esigi -> tabloda gorunmuyordu. Duzeltme: aralik, takimin en son macina kadar uzar.
Yalnizca YAYINLANAN gorunum-diger.js degistirilir; idempotenttir.
"""
from pathlib import Path
import argparse

MARKER = '/*CM_TAKIM_SON_YOKLUK_V1*/'
OLD = 'lo=span[0],hi=span.at(-1);'
NEW = ('lo=span[0],hi=(()=>{const last=span.at(-1),tl=[...teamDS(t)].sort().at(-1);'
       'return tl&&tl>last?tl:last})();' + MARKER)


def patch(src: str) -> str:
    if MARKER in src:
        return src
    start = src.find('function withoutTable')
    end = src.find('function renderTeam', start)
    if start < 0 or end < 0:
        raise RuntimeError('withoutTable bulunamadi; site kodu degismis, yayin durduruldu')
    body = src[start:end]
    if body.count(OLD) != 1:
        raise RuntimeError('withoutTable araligi beklenen bicimde degil; yayin durduruldu')
    return src[:start] + body.replace(OLD, NEW) + src[end:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default='public')
    a = ap.parse_args()
    path = Path(a.site) / 'gorunum-diger.js'
    src = path.read_text(encoding='utf-8')
    out = patch(src)
    if out != src:
        path.write_text(out, encoding='utf-8')
        print('UYGULANDI: Takim yokken aralik takimin son macina kadar uzatildi')
    else:
        print('ZATEN UYGULANMIS: Takim yokken yamasi')


if __name__ == '__main__':
    main()
