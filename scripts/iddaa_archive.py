#!/usr/bin/env python3
"""Cizgi Masasi - iddaa baremleri icin SADECE-EKLEME arsivi.

Her calismada iddaa-lines.json'daki satirlari arsivle karsilastirir:
  * (oyuncu, market, barem, mac-saati) arsivde yoksa           -> yeni kayit eklenir
  * ayni anahtarin son orani degistiyse                        -> yeni kayit eklenir
  * degismediyse                                               -> hicbir sey yazilmaz
Mevcut kayitlar ASLA degistirilmez, silinmez ya da yeniden yazilmaz.

Kayit bicimi (her satir bir JSON dizisi, ay basina bir dosya):
  arsiv/iddaa/lines-YYYY-MM.ndjson : [cekim_unix_sn, oyuncu_id, "MARKET", barem, oran, mac_baslama_unix_sn, "kaynak"]
  arsiv/iddaa/log.ndjson           : her ise yarayan calismanin ozeti

Eski bir goruntuyu sonradan eklemek icin --backfill kullan; goruntuleri kronolojik sirayla ver.
"""
import argparse, datetime as dt, hashlib, json, os, sys
from pathlib import Path

MARKETS = {'PTS', 'REB', 'AST', 'STL', 'BLK', '3PM', 'SRA', 'RA'}


def fetch_time(doc):
    ts = doc.get('ts')
    if isinstance(ts, (int, float)) and ts > 1e11:
        return int(ts // 1000)
    if isinstance(ts, (int, float)) and ts > 1e9:
        return int(ts)
    u = str(doc.get('updated', ''))
    if u:
        return int(dt.datetime.fromisoformat(u.replace('Z', '+00:00')).timestamp())
    raise ValueError('Cekim zamani (ts/updated) yok')


def parse_row(s):
    v = str(s).split('|')
    if len(v) != 5 or v[1] not in MARKETS:
        return None
    try:
        return (int(v[0]), v[1], int(v[2]), float(v[3]), int(v[4]))
    except ValueError:
        return None


def load_state(folder):
    """Anahtar -> (son_t, son_oran); ayrica arsivdeki en yeni cekim zamani."""
    state, newest = {}, 0
    for f in sorted(folder.glob('lines-*.ndjson')):
        for n, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            if not line.strip():
                continue
            try:
                t, pid, mk, bar, odd, gt, _src = json.loads(line)
            except Exception as e:
                raise RuntimeError(f'{f.name}:{n} okunamadi ({e}); arsive dokunulmadi')
            k = (pid, mk, bar, gt)
            if k not in state or t >= state[k][0]:
                state[k] = (t, odd)
            newest = max(newest, t)
    return state, newest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lines', required=True, help='iddaa-lines.json')
    ap.add_argument('--archive', required=True, help='arsiv klasoru, orn. arsiv/iddaa')
    ap.add_argument('--source', default='github-sync')
    ap.add_argument('--backfill', action='store_true', help='arsivdeki en yeni kayittan eski bir goruntuyu eklemeye izin ver')
    a = ap.parse_args()

    doc = json.loads(Path(a.lines).read_text(encoding='utf-8'))
    rows = doc.get('rows')
    if not isinstance(rows, list):
        sys.exit('HATA: rows listesi yok; arsive dokunulmadi')
    t = fetch_time(doc)
    folder = Path(a.archive)
    folder.mkdir(parents=True, exist_ok=True)
    state, newest = load_state(folder)
    if t < newest and not a.backfill:
        print(f'ATLANDI: goruntu ({t}) arsivdeki en yeni kayittan ({newest}) eski; --backfill gerekir')
        return 0

    new, bad, seen = [], 0, set()
    for s in rows:
        r = parse_row(s)
        if r is None:
            bad += 1
            continue
        pid, mk, bar, odd, gt = r
        k = (pid, mk, bar, gt)
        if k in seen:
            continue
        seen.add(k)
        if k not in state or state[k][1] != odd:
            new.append([t, pid, mk, bar, odd, gt, a.source])
    if not new:
        print(f'ARSIV: degisiklik yok ({len(rows)} satir, {bad} gecersiz)')
        return 0

    month = dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime('%Y-%m')
    target = folder / f'lines-{month}.ndjson'
    payload = ''.join(json.dumps(x, ensure_ascii=False, separators=(',', ':')) + '\n' for x in new)
    with open(target, 'a', encoding='utf-8') as f:   # yalnizca sona ekle
        f.write(payload)
    digest = hashlib.sha256('\n'.join(sorted(map(str, rows))).encode()).hexdigest()[:16]
    entry = {'t': t, 'iso': dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
             'src': a.source, 'rows': len(rows), 'added': len(new), 'invalid': bad, 'sha': digest, 'file': target.name}
    with open(folder / 'log.ndjson', 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f'ARSIV: {len(new)} yeni kayit -> {target} (satir={len(rows)}, gecersiz={bad})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
