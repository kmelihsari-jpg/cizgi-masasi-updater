#!/usr/bin/env python3
"""Install GitHub Pages job patch idempotently; fail safely if flow changed."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
workflow=root/'.github/workflows/cizgi-masasi-otomatik-pages.yml'
patch=root/'scripts/dvp_position_patch.py'
if not workflow.is_file() or not patch.is_file():
    raise SystemExit('HATA: Workflow veya DVP patch script eksik')
s=workflow.read_text(encoding='utf-8')
marker='      - name: Oyuncu DVP manuel pozisyon secici V1'
anchor='      - name: Hazirlanan siteyi indirilebilir test paketi olarak sakla'
if marker in s:
    print('OK: DVP adimi daha once eklenmis')
elif s.count(anchor)!=1:
    raise SystemExit('HATA: Beklenen Pages yayin adimi yok; workflow degistirilmedi')
else:
    step='''      - name: Oyuncu DVP manuel pozisyon secici V1
        shell: bash
        run: |
          set -euo pipefail
          python3 scripts/dvp_position_patch.py --site public

'''
    workflow.write_text(s.replace(anchor,step+anchor,1),encoding='utf-8')
    print('OK: DVP yayin adimi eklendi')
