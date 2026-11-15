from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
wf=root/'.github/workflows/cizgi-masasi-otomatik-pages.yml'
css=root/'site-patches/mobile-wide-v1.css'
if not wf.is_file() or not css.is_file():
    raise SystemExit('HATA: Workflow veya CSS bulunamadi.')
s=wf.read_text(encoding='utf-8')
marker='      - name: Mobil genis gorunumu siteye ekle'
if marker in s:
    print('OK: Mobil yama zaten workflow icinde; ikinci kez eklenmedi.')
else:
    anchor='      - name: Hazirlanan siteyi indirilebilir test paketi olarak sakla'
    if s.count(anchor)!=1:
        raise SystemExit('HATA: Site paketleme asamasi beklenen yapida degil; otomatik degisiklik yapilmadi.')
    patch='''      - name: Mobil genis gorunumu siteye ekle
        shell: bash
        run: |
          set -euo pipefail
          python3 - <<'PY_MOBILE_WIDE'
          from pathlib import Path
          import shutil
          src=Path('site-patches/mobile-wide-v1.css')
          dst=Path('public/mobile-wide-v1.css')
          html_file=Path('public/index.html')
          if not src.is_file() or not html_file.is_file():
              raise RuntimeError('Mobil CSS veya site index.html yok')
          html=html_file.read_text(encoding='utf-8')
          tag='<link rel="stylesheet" href="mobile-wide-v1.css?v=20261115a">'
          if tag not in html:
              if '</head>' not in html:
                  raise RuntimeError('index.html head etiketi bulunamadi')
              html=html.replace('</head>',tag+'\\n</head>',1)
          shutil.copyfile(src,dst)
          html_file.write_text(html,encoding='utf-8')
          print('MOBIL WIDE CSS EKLENDI; analiz veri dosyalari degismedi')
          PY_MOBILE_WIDE

'''
    s=s.replace(anchor,patch+anchor,1)
    wf.write_text(s,encoding='utf-8')
    print('OK: Mobil CSS site yayin paketine eklendi.')
print('CSS boyutu:',css.stat().st_size)
