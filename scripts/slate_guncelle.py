"""Maç takvimini (data.json 'slate') NBA CDN fikstüründen yeniler.

slate satırı: [UTC ISO zaman, deplasman, ev sahibi]  (sitede away=s[1], home=s[2]).
- Önümüzdeki GUN_ILERI gün (ET) için normal sezon / NBA Cup maçlarını ekler.
- Eski satırlar son GUN_GERI gün için korunur (daha eskisi atılır), aynı maç iki kez yazılmaz.
- Fikstür alınamaz ya da boş/bozuk gelirse data.json'a DOKUNMAZ (çıkış kodu 0, uyarı basar).
Kullanım: python scripts/slate_guncelle.py --data seed/data.json [--fikstur dosya.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

ET = ZoneInfo('America/New_York')
GUN_ILERI = 7
GUN_GERI = 10
MAC_ID = re.compile(r'00[26]\d{7}')  # 002 normal sezon (Cup grup/çeyrek/yarı dahil), 006 Cup finali


def _utc(s):
    s = str(s or '').strip()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?Z', s):
        return None
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc)
    except ValueError:
        return None


def _iso(t):
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')


def fikstur_maclari(schedule, simdi):
    bugun = simdi.astimezone(ET).date()
    son = bugun + timedelta(days=GUN_ILERI)
    out = []
    for blok in (schedule.get('leagueSchedule') or {}).get('gameDates') or []:
        for g in blok.get('games') or []:
            if not MAC_ID.fullmatch(str(g.get('gameId', ''))):
                continue
            t = _utc(g.get('gameDateTimeUTC'))
            away = (g.get('awayTeam') or {}).get('teamTricode')
            home = (g.get('homeTeam') or {}).get('teamTricode')
            if not t or not away or not home:
                continue
            if bugun - timedelta(days=1) <= t.astimezone(ET).date() <= son:
                out.append([_iso(t), away, home])
    return out


def birlestir(eski, yeni, simdi):
    """Eski satırlardan yalnız son GUN_GERI gün; yeni fikstür aynı (gün, deplasman, ev) maçı ezer."""
    sinir = simdi - timedelta(days=GUN_GERI)
    def anahtar(s):
        t = _utc(s[0])
        return (t.astimezone(ET).date().isoformat() if t else s[0], s[1], s[2])
    tablo = {}
    for s in eski or []:
        t = _utc(s[0]) if isinstance(s, list) and len(s) >= 3 else None
        if t and t >= sinir:
            tablo[anahtar(s)] = [s[0], s[1], s[2]]
    for s in yeni:
        tablo[anahtar(s)] = s
    return sorted(tablo.values(), key=lambda s: (s[0], s[1], s[2]))


def yaz(path, data):
    from update_nba_cdn import write_atomic
    write_atomic(path, data)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='seed/data.json')
    ap.add_argument('--fikstur', help='Test için yerel fikstür JSON dosyası')
    ap.add_argument('--simdi', help='Test için UTC zaman (ISO, Z ile)')
    a = ap.parse_args(argv)
    simdi = _utc(a.simdi) if a.simdi else datetime.now(timezone.utc)
    try:
        if a.fikstur:
            schedule = json.loads(Path(a.fikstur).read_text(encoding='utf-8'))
        else:
            from nba_cdn_source import fetch_json
            schedule = fetch_json('staticData/scheduleLeagueV2_1.json')
    except Exception as e:  # ağ hatası: mevcut takvim korunur
        print('UYARI: fikstur alinamadi, slate degismedi:', e)
        return 0
    yeni = fikstur_maclari(schedule, simdi)
    if not yeni:
        print('UYARI: fikstürde önümüzdeki günler için maç yok/okunamadı, slate degismedi')
        return 0
    path = Path(a.data)
    data = json.loads(path.read_text(encoding='utf-8'))
    eski = data.get('slate') or []
    son = birlestir(eski, yeni, simdi)
    if son == eski:
        print('SLATE: degisiklik yok,', len(son), 'mac')
        return 0
    data['slate'] = son
    yaz(path, data)
    gunler = sorted({_utc(s[0]).astimezone(ET).date().isoformat() for s in son if _utc(s[0]) >= simdi})
    print(f'SLATE GUNCELLENDI: {len(eski)} -> {len(son)} mac; gelecek gunler (ET): {", ".join(gunler)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
