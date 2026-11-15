#!/usr/bin/env python3
"""Guvenli idempotent Pages workflow degisikligi: diger workflow'lara dokunmaz."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
w=root/'.github/workflows/cizgi-masasi-otomatik-pages.yml'
if not w.is_file():sys.exit('HATA: Pages workflow bulunamadi; dokunulmadi')
s=w.read_text(encoding='utf-8')
name="      - 'Cizgi Masasi - Karne Otomasyonu'"
if name not in s:
    anchor="      - 'Cizgi Masasi - Iddaa NBA Barem Senkronizasyonu'"
    if anchor not in s:sys.exit('HATA: iddaa tetikleyici bulunamadi; dokunulmadi')
    s=s.replace(anchor,anchor+'\n'+name,1)
# Existing workflow builds public/ directory and copies seed/data.json into it.
anchor="          shutil.copyfile(data_file, folder / 'data.json')"
if s.count(anchor)!=1:sys.exit('HATA: Pages data kopyalama satiri bulunamadi; dokunulmadi')
addon="""          # Karne V1: yalnızca yeni dönemin doğrulanmış kayıtlarını yayımla.
          karne_seed = pathlib.Path('seed/karne.json')
          if karne_seed.is_file():
              import json as cm_json
              card = cm_json.loads(karne_seed.read_text(encoding='utf-8'))
              if card.get('startDate') != '2026-11-15' or not isinstance(card.get('docs'), list):
                  raise RuntimeError('KARNE seed format hatasi')
              (folder / 'karne.json').write_text(cm_json.dumps(card,ensure_ascii=False,indent=2)+'\\n', encoding='utf-8')
          # Çalışan sitenin JS'sine dokunma: ek yama dosyalarını yayınla.
          for patch in ('karne-v1.js', 'karne-v1.css'):
              src = pathlib.Path('site-patches') / patch
              shutil.copyfile(src, folder / patch)
          page_file=folder / 'index.html'
          html=page_file.read_text(encoding='utf-8')
          if 'id="cm-v1-vitrin"' not in html:
              hook='<div class="hgames" id="h-games"'
              if hook not in html:raise RuntimeError('Vitrin ekleme noktasi yok')
              html=html.replace(hook,'<section id="cm-v1-vitrin" aria-label="Kasa ve Karne Vitrini"></section>\\n    '+hook,1)
          if 'karne-v1.css' not in html:
              html=html.replace('</head>', '<link rel="stylesheet" href="karne-v1.css?v=1">\\n</head>',1)
          if 'karne-v1.js' not in html:
              html=html.replace('<script src="baslat.js', '<script src="karne-v1.js?v=1"></script>\\n<script src="baslat.js',1)
          page_file.write_text(html,encoding='utf-8')
          print('KARNE V1 site yamasina eklendi')
""".rstrip('\n')
if 'KARNE V1 site yamasina eklendi' not in s:
    s=s.replace(anchor,anchor+'\n'+addon,1)
w.write_text(s,encoding='utf-8')
print('OK: karne workflow tetikleyicisi, seed ve vitrin yama yayini kuruldu')
