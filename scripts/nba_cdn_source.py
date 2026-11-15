"""Read-only NBA CDN normalizer for Cizgi Masasi.

The caller owns mapping NBA player IDs to seed/data.json and persistence.
Never writes to the existing dataset. stdlib only.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import re
import time
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BASE = 'https://cdn.nba.com/static/json/'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://www.nba.com/',
    'Accept-Language': 'en-US,en;q=0.5',
}


def fetch_json(path, attempts=3, timeout=18):
    if not re.fullmatch(r'[A-Za-z0-9_./-]+', path) or '..' in path:
        raise ValueError('Invalid CDN path')
    for i in range(attempts):
        try:
            req = Request(BASE + path, headers=HEADERS)
            with urlopen(req, timeout=timeout) as r:
                result = json.load(r)
            if not isinstance(result, dict):
                raise ValueError('JSON object expected')
            return result
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(1 + i * 2)


def recent_final_games(schedule, days=7, today=None):
    """Return recent completed regular-season games, sorted by date and NBA game ID."""
    today = today or datetime.now(ZoneInfo('America/New_York')).date()
    found = {}
    for block in schedule.get('leagueSchedule', {}).get('gameDates', []):
        for game in block.get('games', []):
            gid = str(game.get('gameId', ''))
            if not re.fullmatch(r'002\d{7}', gid):
                continue
            if int(game.get('gameStatus', 0) or 0) != 3:
                continue
            d = str(game.get('gameDateEst') or game.get('gameDateTimeEst') or block.get('gameDate') or '')[:10]
            try:
                day = date.fromisoformat(d)
            except ValueError:
                continue
            if today - timedelta(days=days) <= day <= today:
                found[gid] = {'game_id': gid, 'game_date': d,
                              'home': (game.get('homeTeam') or {}).get('teamTricode'),
                              'away': (game.get('awayTeam') or {}).get('teamTricode')}
    return sorted(found.values(), key=lambda v: (v['game_date'], v['game_id']))


_FALSE_FLAGS = {'', '0', 'false', 'no', 'n', 'none', 'null', 'inactive'}


def flag(value):
    """NBA CDN bayraklari (played, starter) bazen "0"/"1" METNI gelir.

    Python'da bool("0") True'dur; bu yuzden duz truthiness kullanilmaz.
    Oynamayan (INACTIVE) oyuncular "played":"0" ile gelir ve satir olarak
    veriye girmemelidir: oynamayan oyuncunun satiri olmamasi "yoktu" demektir.
    """
    if isinstance(value, str):
        return value.strip().lower() not in _FALSE_FLAGS
    return bool(value)


def played_in_game(p):
    """Resmi box score'a gore oyuncu fiilen oynadi mi?"""
    if not flag(p.get('played')):
        return False
    if str(p.get('status') or '').strip().upper() == 'INACTIVE':
        return False
    if str(p.get('notPlayingReason') or '').strip():
        return False
    return True


def normalize_boxscore(raw, expected_id=None):
    game = raw.get('game') or {}
    gid = str(game.get('gameId', ''))
    if not re.fullmatch(r'\d{10}', gid) or (expected_id and gid != expected_id):
        raise ValueError('Game ID mismatch')
    if int(game.get('gameStatus', 0) or 0) != 3:
        raise ValueError('Not a completed game')
    output = []
    teams = [game.get('homeTeam') or {}, game.get('awayTeam') or {}]
    if any(not str(t.get('teamTricode') or '') for t in teams):
        raise ValueError('Team missing')
    if any(not isinstance(t.get('score'), (int, float)) for t in teams):
        raise ValueError('Team final score missing')
    for team, opp in ((teams[0], teams[1]), (teams[1], teams[0])):
        played_count = 0
        for p in team.get('players', []):
            if not played_in_game(p):
                continue
            stats = p.get('statistics') or {}
            keys = ('points', 'assists', 'reboundsTotal', 'threePointersMade', 'threePointersAttempted',
                    'fieldGoalsMade', 'fieldGoalsAttempted', 'freeThrowsMade', 'freeThrowsAttempted',
                    'reboundsOffensive', 'reboundsDefensive', 'steals', 'blocks', 'turnovers', 'minutes')
            if not all(k in stats for k in keys):
                raise ValueError('Missing required boxscore stats')
            if not str(p.get('personId') or '').isdigit():
                raise ValueError('Missing NBA person ID')
            played_count += 1
            output.append({
                'game_id': gid, 'nba_player_id': str(p['personId']),
                'name': p.get('name') or (str(p.get('firstName') or '')+' '+str(p.get('familyName') or '')).strip(),
                'team': team['teamTricode'], 'opponent': opp['teamTricode'],
                'home': team is teams[0], 'starter': flag(p.get('starter')),
                'minutes': stats['minutes'], 'pts': stats['points'],
                'ast': stats['assists'], 'reb': stats['reboundsTotal'],
                'oreb': stats['reboundsOffensive'], 'dreb': stats['reboundsDefensive'],
                'fgm': stats['fieldGoalsMade'], 'fga': stats['fieldGoalsAttempted'],
                'ftm': stats['freeThrowsMade'], 'fta': stats['freeThrowsAttempted'],
                'fg3m': stats['threePointersMade'], 'fg3a': stats['threePointersAttempted'],
                'stl': stats['steals'], 'blk': stats['blocks'], 'tov': stats['turnovers'],
            })
        if played_count < 5:
            raise ValueError('Insufficient players in boxscore')
    ids = [(p['nba_player_id'], p['team']) for p in output]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate players in boxscore')
    return {'game_id': gid, 'players': output,
            'teams': [{ 'team': t['teamTricode'], 'score': t['score']} for t in teams]}


def read_recent(days=7, max_games=160):
    schedule = fetch_json('staticData/scheduleLeagueV2_1.json')
    games = recent_final_games(schedule, days=days)
    if len(games) > max_games:
        raise ValueError('Game count exceeds safety limit')
    if not games:
        raise ValueError('No finished regular-season games found for requested window')
    results = []
    for meta in games:
        raw = fetch_json(f'liveData/boxscore/boxscore_{meta["game_id"]}.json')
        box = normalize_boxscore(raw, meta['game_id'])
        box['game_date'] = meta['game_date']
        results.append(box)
    return results
