#!/usr/bin/env python3
"""Read-only, bounded NBA tracking access audit. No credentials, no data writes."""
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0'
MAX_BODY = 2_000_000
TIMEOUT = 9


def get_json(url, referer):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Accept': 'application/json, text/plain, */*',
        'Referer': referer, 'Origin': referer.rstrip('/'),
        'x-nba-stats-origin': 'stats' if 'stats.nba.com' in url else 'nba',
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        status = response.status
        raw = response.read(MAX_BODY + 1)
    if len(raw) > MAX_BODY:
        raise ValueError('response too large')
    return status, json.loads(raw)


def find_game_id():
    schedule = 'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json'
    _, data = get_json(schedule, 'https://www.nba.com/')
    today = datetime.now(ZoneInfo('America/New_York')).date()
    candidates = []
    for block in (data.get('leagueSchedule') or {}).get('gameDates', []):
        for game in block.get('games', []):
            gid = str(game.get('gameId') or '')
            d = str(game.get('gameDateEst') or game.get('gameDateTimeEst') or block.get('gameDate') or '')[:10]
            try:
                day = datetime.strptime(d, '%Y-%m-%d').date()
            except ValueError:
                continue
            if re.fullmatch(r'002\d{7}', gid) and game.get('gameStatus') == 3 and today - timedelta(days=10) <= day <= today:
                candidates.append((d, gid))
    if not candidates:
        raise RuntimeError('no recent completed regular season game available')
    return sorted(candidates)[-1]


def describe(payload):
    # Explicitly distinguish visible key names from verified player-level values.
    keys = list(payload)[:15] if isinstance(payload, dict) else []
    track = payload.get('boxScorePlayerTrack') if isinstance(payload, dict) else None
    players = []
    if isinstance(track, dict):
        for side in ('homeTeam', 'awayTeam'):
            players += (track.get(side) or {}).get('players') or []
    valid = [p for p in players if isinstance(p, dict) and p.get('personId')]
    fields = set()
    populated = set()
    for p in valid:
        stats = p.get('statistics') or {}
        fields.update(stats)
        populated.update(k for k, v in stats.items() if v is not None)
    return {'root_keys': keys, 'player_rows_with_id': len(valid),
            'rebound_chances_total_present': 'reboundChancesTotal' in populated,
            'rebound_chances_offensive_present': 'reboundChancesOffensive' in populated,
            'rebound_chances_defensive_present': 'reboundChancesDefensive' in populated,
            'potential_assists_present': any('potential' in k.lower() and 'assist' in k.lower() for k in populated),
            'sample_player_stat_keys': sorted(fields)[:40]}


def main():
    report = {'mode': 'READ_ONLY', 'tested_at_utc': datetime.now(ZoneInfo('UTC')).isoformat(), 'tests': []}
    try:
        date, gid = find_game_id()
        report.update({'game_date': date, 'game_id': gid})
        print('Recent final NBA game:', date, gid, flush=True)
    except Exception as ex:
        report['schedule_error'] = f'{type(ex).__name__}: {str(ex)[:180]}'
        print('Schedule unavailable:', report['schedule_error'], flush=True)
        # A known, previously played NBA game ID used only for endpoint availability testing.
        gid = '0021700807'
        report['fallback_historical_game_id'] = gid
    base = 'https://cdn.nba.com/static/json/liveData/'
    tests = [
        ('stats_boxscore_playertrack_v3', f'https://stats.nba.com/stats/boxscoreplayertrackv3?GameID={gid}', 'https://stats.nba.com/'),
        ('cdn_playertrack_candidate', base+f'boxscoreplayertrack/boxscoreplayertrack_{gid}.json', 'https://www.nba.com/'),
        ('cdn_playertrack_candidate_alt', base+f'boxscoreplayertrack_{gid}.json', 'https://www.nba.com/'),
    ]
    for name, url, referer in tests:
        result = {'name': name, 'url': url}
        try:
            code, data = get_json(url, referer)
            result.update({'http_status': code, 'valid_json': True, 'evidence': describe(data)})
        except urllib.error.HTTPError as ex:
            result.update({'http_status': ex.code, 'error': f'HTTP {ex.code}'})
        except Exception as ex:
            result['error'] = f'{type(ex).__name__}: {str(ex)[:180]}'
        report['tests'].append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    usable = [t['name'] for t in report['tests'] if t.get('evidence',{}).get('player_rows_with_id',0) >= 10 and t['evidence'].get('rebound_chances_total_present')]
    report['verified_rebound_chances_sources'] = usable
    report['verified_potential_assists_sources'] = [t['name'] for t in report['tests'] if t.get('evidence',{}).get('player_rows_with_id',0)>=10 and t['evidence'].get('potential_assists_present')]
    Path('out').mkdir(exist_ok=True)
    Path('out/tracking-cloud-probe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('VERDICT', json.dumps({'rebound_chances': usable, 'potential_assists': report['verified_potential_assists_sources']}), flush=True)
    print('READ ONLY: no seed, tracking, Git or Cloudflare data changed', flush=True)


if __name__ == '__main__':
    main()
