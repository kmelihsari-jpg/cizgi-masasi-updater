"""Box score butunlugu: "eksik veri" ile "gercekten oynamadi" ayrimi.

Sayfa bir oyuncunun yokluguna "o gun satiri yok" diye karar verir (X yokken filtresi,
missedStreak, mpg, Kasa). Bu yuzden bir maçin box score'u EKSIKSE (ornegin ismi
eslesmeyen oyuncu sessizce atlandiysa) o oyuncular yanlislikla "yoktu" sayilir.

Olcut: DAKIKA KAPANISI. Bir takimin oyuncu dakikalari toplami 240 + 25 x uzatma olur.
Toplam bunun cok altindaysa satirlar eksiktir (kayip dakika = eksik oyuncu).
Toplam kapaniyorsa maç TAMDIR ve satiri olmayan oyuncu gercekten oynamamistir
(ornek: IND 2 Kasim 2026'da 6 oyuncu 241 dk oynadi; box score eksik degil).

Mevcut 376 takim-macta en buyuk sapma 3 dk (ESPN dakikalari tam sayiya yuvarlar).
"""
from __future__ import annotations
from collections import defaultdict

REGULATION = 240.0
OVERTIME = 25.0
TOL_ROUNDED = 4.0   # dakikalar tam sayi (ESPN): oyuncu basi +-0.5 yuvarlama
TOL_EXACT = 2.0     # saniyeli dakika (NBA CDN)


def closure(minutes):
    """minutes: bir takimin oyuncu dakikalari. Saf fonksiyon."""
    ms = [float(m) for m in minutes]
    total = sum(ms)
    rounded = all(m.is_integer() for m in ms)
    tol = TOL_ROUNDED if rounded else TOL_EXACT
    ot = max(0, round((total - REGULATION) / OVERTIME))
    expected = REGULATION + OVERTIME * ot
    resid = total - expected
    return {'sum': round(total, 2), 'expected': expected, 'overtimes': ot,
            'residual': round(resid, 2), 'tol': tol, 'rows': len(ms),
            'ok': bool(ms) and abs(resid) <= tol,
            'missing_minutes': round(max(0.0, -resid), 2)}


def team_games(data):
    """{(tarih, takim): closure(...)} seed/data.json bicimindeki veri icin."""
    ci = {n: i for i, n in enumerate(data['cols'])}
    groups = defaultdict(list)
    for r in data['rows']:
        groups[(data['dates'][r[ci['d']]], data['teams'][r[ci['t']]])].append(r[ci['min']])
    return {k: closure(v) for k, v in groups.items()}


def partial_games(data):
    """Dakika kapanisina uymayan (eksik/supheli) takim-maclar."""
    return {k: v for k, v in team_games(data).items() if not v['ok']}


def absence_status(data, pid, date, team=None):
    """'played' | 'absent_verified' | 'unknown_partial' | 'no_game'.

    absent_verified: takimin maci TAM (dakika kapaniyor) ve oyuncunun satiri yok.
    unknown_partial: takimin box score'u eksik; oyuncunun oynayip oynamadigi bilinmez.
    """
    ci = {n: i for i, n in enumerate(data['cols'])}
    if date not in data['dates']:
        return 'no_game'
    di = data['dates'].index(date)
    teams = data['teams']
    if team is None:
        mine = [teams[r[ci['t']]] for r in data['rows'] if r[ci['pid']] == pid]
        team = max(set(mine), key=mine.count) if mine else None
    if team is None or team not in teams:
        return 'no_game'
    ti = teams.index(team)
    day_rows = [r for r in data['rows'] if r[ci['d']] == di and r[ci['t']] == ti]
    if not day_rows:
        return 'no_game'
    if any(r[ci['pid']] == pid and r[ci['min']] is not None and r[ci['min']] > 0 for r in day_rows):
        return 'played'
    cl = closure([r[ci['min']] for r in day_rows])
    return 'absent_verified' if cl['ok'] else 'unknown_partial'
