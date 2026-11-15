#!/usr/bin/env python3
"""Mevcut GitHub Pages yayin workflow'unu BOZMADAN iddaa entegrasyonu ekler."""
from pathlib import Path
import argparse,sys

ap=argparse.ArgumentParser()
ap.add_argument('--repo',default='.')
args=ap.parse_args()
root=Path(args.repo).resolve()
workflow=root/'.github/workflows/cizgi-masasi-otomatik-pages.yml'
if not workflow.is_file():
    sys.exit('DURDURULDU: '+str(workflow)+' bulunamadi. Dosya adi farkliysa elle inceleme gerekli.')
s=workflow.read_text(encoding='utf-8')
name="      - 'Cizgi Masasi - Iddaa NBA Barem Senkronizasyonu'"
if name not in s:
    marker="      - 'Cizgi Masasi - Yerel Tracking Verisini Birlestir'"
    if marker not in s:sys.exit('DURDURULDU: Beklenen workflow_run listesi yok, otomatik degisiklik yapilmadi')
    s=s.replace(marker, marker+'\n'+name,1)
# Site builder Python code block: replace only a precisely located line
needle="          shutil.copyfile(data_file, folder / 'data.json')"
inject="""          shutil.copyfile(data_file, folder / 'data.json')
          # Github senkronizasyonundan gelen oyuncu baremleri. Eski web kopyasini ez.
          iddaa_seed = pathlib.Path('seed/iddaa-lines.json')
          if iddaa_seed.is_file():
              iddaa = json.loads(iddaa_seed.read_text(encoding='utf-8'))
              rows = iddaa.get('rows')
              if not isinstance(rows, list) or int(iddaa.get('count', -1)) != len(rows):
                  raise RuntimeError('Iddaa seed JSON gecersiz; yayin durduruldu')
              now_unix = int(time.time())
              # Sadece henuz baslamamis mac satirlari; baslamis maclari asla yayinlama.
              live_rows = []
              for r in rows:
                  parts = str(r).split('|')
                  if len(parts) != 5:
                      raise RuntimeError('Gecersiz iddaa satiri; yayin durduruldu')
                  if int(parts[4]) > now_unix:
                      live_rows.append(r)
              iddaa['rows'] = live_rows
              iddaa['count'] = len(live_rows)
              # 6 saatten eski cekim kullanilmaz. Hata durumunda eski oranlari kaldir.
              if now_unix * 1000 - int(iddaa.get('ts', 0)) > 6 * 3600 * 1000:
                  iddaa['rows'] = []
                  iddaa['count'] = 0
                  iddaa['stale'] = True
              (folder / 'iddaa-lines.json').write_text(
                  json.dumps(iddaa, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')
              print('IDDAA siteye eklendi:', iddaa['count'], 'satir; stale=', bool(iddaa.get('stale', False)))
""".rstrip('\n')
if 'IDDAA siteye eklendi:' not in s:
    if s.count(needle)!=1:sys.exit('DURDURULDU: Beklenen data copy noktasi yok, otomatik degisiklik yapilmadi')
    s=s.replace(needle,inject,1)
workflow.write_text(s,encoding='utf-8')
print('TAMAM: Mevcut Pages yayini korundu, iddaa workflow_run ve seed override eklendi')
