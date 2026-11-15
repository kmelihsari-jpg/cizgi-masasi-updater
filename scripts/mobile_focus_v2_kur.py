#!/usr/bin/env python3
"""Install an isolated mobile UI patch to the existing Cloudflare Pages packaging workflow."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
wf = root / '.github/workflows/cizgi-masasi-otomatik-pages.yml'
css = root / 'site-patches/mobile-focus-v2.css'
js = root / 'site-patches/mobile-focus-v2.js'
if not all(p.is_file() for p in (wf,css,js)):
    raise SystemExit('HATA: Workflow veya mobil V2 dosyalari eksik; hicbir sey degistirilmedi.')
s = wf.read_text(encoding='utf-8')
marker = '      - name: Mobil odakli kompakt gorunumu siteye ekle'
anchor = '      - name: Hazirlanan siteyi indirilebilir test paketi olarak sakla'
if marker in s:
    print('OK: Mobil V2 yayini zaten ayarlanmis.')
else:
    if s.count(anchor) != 1:
        raise SystemExit('HATA: Beklenen Pages artifact adimi yok; workflow degistirilmedi.')
    patch = '''      - name: Mobil odakli kompakt gorunumu siteye ekle
        shell: bash
        run: |
          set -euo pipefail
          python3 - <<'PY_CM_MOBILE_V2'
          from pathlib import Path
          import shutil
          public = Path('public')
          htmlpath = public / 'index.html'
          if not htmlpath.is_file():
              raise RuntimeError('public/index.html bulunamadi')
          html = htmlpath.read_text(encoding='utf-8')
          assert '</head>' in html and '</body>' in html, 'HTML head/body eksik'
          for f in ('mobile-focus-v2.css', 'mobile-focus-v2.js'):
              src = Path('site-patches') / f
              if not src.is_file(): raise RuntimeError('Eksik mobil yama: ' + f)
              shutil.copyfile(src, public / f)
          css_tag = '<link rel="stylesheet" href="mobile-focus-v2.css?v=20261115b">'
          js_tag = '<script defer src="mobile-focus-v2.js?v=20261115b"></script>'
          if 'mobile-focus-v2.css' not in html:
              html = html.replace('</head>', css_tag+'\\n</head>', 1)
          if 'mobile-focus-v2.js' not in html:
              html = html.replace('</body>', js_tag+'\\n</body>', 1)
          htmlpath.write_text(html, encoding='utf-8')
          print('MOBIL FOCUS V2 HAZIR: JS ve CSS yayinda; veri ve bahis kodlari korundu')
          PY_CM_MOBILE_V2

'''
    s = s.replace(anchor, patch + anchor, 1)
    wf.write_text(s, encoding='utf-8')
    print('OK: Mobil V2 yayin adimi eklendi.')
print('Mobil CSS:', css.stat().st_size, 'byte; JS:', js.stat().st_size, 'byte')
