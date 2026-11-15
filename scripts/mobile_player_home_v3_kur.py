#!/usr/bin/env python3
"""Idempotently inject mobile V3 CSS after earlier responsive patches into the Pages workflow."""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
wf = root / '.github/workflows/cizgi-masasi-otomatik-pages.yml'
css = root / 'site-patches/mobile-player-home-v3.css'
if not wf.is_file() or not css.is_file():
    sys.exit('HATA: Yayın iş akışı ya da V3 CSS yok; işlem yapılmadı.')
s = wf.read_text(encoding='utf-8')
step = '      - name: Mobil oyuncu ve ana sayfa V3 yamasini ekle'
anchor = '      - name: Hazirlanan siteyi indirilebilir test paketi olarak sakla'
if step in s:
    print('OK: V3 zaten kurulu; tekrarlanmadi.')
else:
    if s.count(anchor) != 1:
        sys.exit('HATA: Beklenen yayin paketi adimi bulunamadi, workflow degistirilmedi.')
    injection = '''      - name: Mobil oyuncu ve ana sayfa V3 yamasini ekle
        shell: bash
        run: |
          set -euo pipefail
          python3 - <<'PY_CM_MOBILE_V3'
          from pathlib import Path
          import shutil
          source = Path('site-patches/mobile-player-home-v3.css')
          destination = Path('public/mobile-player-home-v3.css')
          html_file = Path('public/index.html')
          assert source.is_file() and html_file.is_file(), 'V3 kaynak/site dosyasi bulunamadi'
          shutil.copyfile(source, destination)
          html = html_file.read_text(encoding='utf-8')
          tag = '<link rel="stylesheet" href="mobile-player-home-v3.css?v=20261115c">'
          if 'mobile-player-home-v3.css' not in html:
              assert '</head>' in html, 'HTML head kapanisi bulunamadi'
              html = html.replace('</head>', tag + '\\n</head>', 1)
              html_file.write_text(html, encoding='utf-8')
          print('MOBIL V3 HAZIR: sol baslik + oyuncu grafik okunabilirligi')
          PY_CM_MOBILE_V3

'''
    wf.write_text(s.replace(anchor, injection+anchor, 1), encoding='utf-8')
    print('OK: Mobil V3 yayın adımı eklendi.')
print('CSS', css.stat().st_size, 'byte')
