#!/usr/bin/env python3
"""seed/data.json icindeki 'hayalet' oyuncu-mac satirlarini temizler.

Hayalet satir: dakikasi 0 olup ilk 5 (start=1) isaretli satir. Fiilen oynayan
bir oyuncu 0 dakikayla ilk 5 baslayamaz; bu satirlar NBA CDN box score'unda
"played":"0" (INACTIVE) gelen oyuncularin, bayragin metin olmasi yuzunden
yanlislikla yazilmasindan olusur (bkz. nba_cdn_source.flag).

Oynamayan oyuncunun satiri OLMAMALIDIR: sayfa "X yokken" filtresini, mpg'yi,
missedStreak'i ve Kasa adaylarini "o gun satiri var mi" kuralina gore hesaplar.

Kapsam disi (dokunulmaz):
  * min=0 ama start=0 olan eski kayitlar (ESPN: sahaya <1 dk cikanlar, tracking
    verisi olanlar). Bunlar fiilen oynamistir.
  * history.json (gecen sezon) bu script'in konusu degildir.

Varsayilan salt okunurdur; --apply acikca yazar. Idempotenttir.
"""
from __future__ import annotations
import argparse
import json
import os
import tempfile
from collections import Counter
from pathlib import Path


def is_phantom(row, ci):
    m = row[ci['min']]
    return m is not None and m == 0 and bool(row[ci['start']])


def clean(data):
    """Saf fonksiyon: (yeni veri, rapor). Girdiyi degistirmez."""
    cols = data['cols']
    ci = {n: i for i, n in enumerate(cols)}
    for k in ('pid', 'd', 't', 'min', 'start'):
        if k not in ci:
            raise ValueError('Eksik sutun: ' + k)
    dates, teams = data['dates'], data['teams']
    names = {p[0]: p[1] for p in data['players']}
    kept, removed = [], []
    for r in data['rows']:
        (removed if is_phantom(r, ci) else kept).append(r)
    by_date = Counter(dates[r[ci['d']]] for r in removed)
    by_team_game = Counter((dates[r[ci['d']]], teams[r[ci['t']]]) for r in removed)
    remaining_pids = {r[ci['pid']] for r in kept}
    only_phantom = sorted({r[ci['pid']] for r in removed} - remaining_pids)
    out = dict(data)
    out['rows'] = kept
    report = {
        'rows_before': len(data['rows']), 'rows_after': len(kept), 'removed': len(removed),
        'removed_by_date': dict(sorted(by_date.items())),
        'team_games_affected': len(by_team_game),
        'players_with_no_rows_left': [{'id': i, 'name': names.get(i)} for i in only_phantom],
        'zero_min_rows_kept': sum(1 for r in kept if r[ci['min']] == 0),
    }
    return out, report


def write_atomic(path, data):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix='.clean-', suffix='.json', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
            f.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default='seed')
    ap.add_argument('--apply', action='store_true', help='Temizlenmis veriyi yaz')
    ap.add_argument('--report', default='out/phantom-clean-report.json')
    a = ap.parse_args()
    path = Path(a.site) / 'data.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    new, report = clean(data)
    report['mode'] = 'APPLY' if a.apply else 'DRY_RUN'
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if a.apply and report['removed']:
        write_atomic(path, new)
        print('APPLIED: hayalet satirlar silindi')
    else:
        print('READ ONLY' if not a.apply else 'Temizlenecek satir yok')


if __name__ == '__main__':
    main()
