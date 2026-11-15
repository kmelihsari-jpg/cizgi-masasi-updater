#!/usr/bin/env python3
"""Safely install the small PWA coupon safe-area patch into Pages packaging."""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
w = root / '.github/workflows/cizgi-masasi-otomatik-pages.yml'
css = root / 'site-patches/pwa-slip-safe-v1.css'
js = root / 'site-patches/pwa-slip-safe-v1.js'
if not all(p.is_file() for p in (w, css, js)):
    sys.exit('HATA: Workflow / CSS / JS dosyasi yok. Islem durduruldu.')
s = w.read_text(encoding='utf-8')
marker = '      - name: iPhone PWA Kupon ust guvenli alan V1'
anchor = '      - name: Hazirlanan siteyi indirilebilir test paketi olarak sakla'
if marker in s:
    print('OK: Kupon PWA V1 yayina baglanmis, tekrar eklenmedi.')
    sys.exit(0)
if s.count(anchor) != 1:
    sys.exit('HATA: Pages workflow beklenen artifact adimini icermiyor. Dosya degistirilmedi.')
step = '''      - name: iPhone PWA Kupon ust guvenli alan V1
        shell: bash
        run: |
          set -euo pipefail
          python3 - <<'PY_CM_PWA_SLIP'
          from pathlib import Path
          import shutil
          public = Path('public')
          html_path = public / 'index.html'
          if not html_path.is_file():
              raise RuntimeError('public/index.html yok')
          html = html_path.read_text(encoding='utf-8')
          if 'id="slip"' not in html or 'id="slip-close"' not in html:
              raise RuntimeError('Kupon paneli / kapatma dugmesi bulunamadi; yayin durduruldu')
          if '</head>' not in html or '</body>' not in html:
              raise RuntimeError('HTML kapanis etiketleri bulunamadi')
          for name in ('pwa-slip-safe-v1.css', 'pwa-slip-safe-v1.js'):
              source = Path('site-patches') / name
              if not source.is_file():
                  raise RuntimeError('Eksik kaynak: ' + str(source))
              shutil.copyfile(source, public / name)
          if 'pwa-slip-safe-v1.css' not in html:
              html = html.replace('</head>', '<link rel="stylesheet" href="pwa-slip-safe-v1.css?v=20261115d">\\n</head>', 1)
          if 'pwa-slip-safe-v1.js' not in html:
              html = html.replace('</body>', '<script src="pwa-slip-safe-v1.js?v=20261115d"></script>\\n</body>', 1)
          html_path.write_text(html, encoding='utf-8')
          print('PWA KUPON DUZELTMESI: guvenli ust alan, sabit kapatma dugmesi; baska veriye dokunulmadi')
          PY_CM_PWA_SLIP

'''
w.write_text(s.replace(anchor, step + anchor, 1), encoding='utf-8')
print('OK: PWA Kupon V1 Pages workflow yayin adimi eklendi.')
