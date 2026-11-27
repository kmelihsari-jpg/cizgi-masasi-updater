#!/usr/bin/env python3
"""Tek seferlik, idempotent Karne duzeltmesi (27 Kasim 2026, Melih'in acik onayiyla).
27 Kasim Vitrin kaydindan Brook Lopez PTS 10.5 cikarilir: Ingram gelince rolu dustu (son 2 mac 21.5 ve 18.3 dk,
3 ve 6 sayi), eski dakika kapisi bunu gormedi. Orijinal kayit arsiv/karne/duzeltmeler.ndjson dosyasina
SADECE EKLENIR (silinmez); 'first' listesi (ilk gorulen oneriler) degismez.
"""
import argparse, datetime as dt, json, pathlib

DAY = '2026-11-27'; PID = 201572; MK = 'PTS'; LINE = 10.5

def run(karne, arsiv):
    karne = pathlib.Path(karne); arsiv = pathlib.Path(arsiv)
    raw = json.loads(karne.read_text(encoding='utf-8-sig'))
    docs = raw['docs'] if isinstance(raw, dict) else raw
    doc = next((d for d in docs if d.get('date') == DAY), None)
    if not doc:
        print('DUZELTME: 27 Kasim kaydi yok, degisiklik yok'); return False
    hit = [p for p in doc.get('picks', []) if int(p['id']) == PID and p['mk'] == MK and float(p['line']) == LINE]
    if not hit:
        print('DUZELTME: Lopez kaydi zaten yok, degisiklik yok'); return False
    if doc.get('early') or doc.get('searly'):
        raise RuntimeError('27 Kasim kaydi sonuclanmis, otomatik duzeltme yapilmadi')
    removed = hit[0]
    doc['picks'] = [p for p in doc['picks'] if p is not removed]
    # picks ile birebir sirali 'early' yok (sonuclanmamis); yine de tutarlilik icin kontrol
    arsiv.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({'at': dt.datetime.now(dt.timezone.utc).isoformat(), 'date': DAY, 'action': 'removed_from_picks',
                       'reason': 'Rol degisimi (Ingram): son 2 macta 21.5 ve 18.3 dk, 3 ve 6 sayi; eski dakika kapisi gormedi. Melih onayiyla cikarildi.',
                       'record': removed}, ensure_ascii=False)
    with arsiv.open('a', encoding='utf-8') as f:
        f.write(line + '\n')
    tmp = karne.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'); tmp.replace(karne)
    print('DUZELTME: Lopez PTS 10.5 Vitrin kaydindan cikarildi, orijinal arsive eklendi'); return True

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--karne', default='seed/karne.json')
    ap.add_argument('--arsiv', default='arsiv/karne/duzeltmeler.ndjson')
    a = ap.parse_args(); run(a.karne, a.arsiv)
