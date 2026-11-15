#!/usr/bin/env python3
"""Insert exactly one returning-player patch step into existing Pages workflow."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'.github/workflows/cizgi-masasi-otomatik-pages.yml'
text=p.read_text(encoding='utf-8')
name='      - name: Confirmed return model yamasini uygula'
anchor='      - name: Hazirlanan siteyi indirilebilir test paketi olarak sakla'
if name not in text and text.count(anchor)!=1:raise SystemExit('HATA: Pages artifact adimi beklenenden farkli; degisiklik yapilmadi')
step='''      - name: Confirmed return model yamasini uygula
        shell: bash
        run: python3 scripts/karne_returning.py --model public/model.js --confirmed seed/confirmed-active.json

'''
if name not in text:
    p.write_text(text.replace(anchor,step+anchor,1),encoding='utf-8')
    print('OK: Canli sitedeki model.js ve otomatik Karne ayni kurali kullaniyor')
else:
    print('ALREADY INSTALLED: Pages workflow korundu')
# An empty allow-list is safest. Never overwrite user-maintained official confirmations.
conf=root/'seed/confirmed-active.json'
if not conf.exists():
    conf.parent.mkdir(parents=True,exist_ok=True)
    conf.write_text('{"players": []}\n',encoding='utf-8')
    print('OLUSTURULDU:',conf)
else:
    print('KORUNDU:',conf)
