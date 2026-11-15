"""Read-only NBA CDN vs Cizgi Masasi identity and game coverage report.

Never writes to seed/data.json. Use in existing GitHub Actions preflight.
"""
import json
from collections import Counter
from pathlib import Path
from nba_cdn_source import read_recent

seed = json.loads(Path('seed/data.json').read_text(encoding='utf-8'))
for field in ('cols', 'rows', 'players', 'teams', 'dates'):
    if field not in seed:
        raise SystemExit(f'Missing seed field: {field}')
cols = {name: i for i, name in enumerate(seed['cols'])}
for field in ('pid', 'd', 't'):
    if field not in cols:
        raise SystemExit(f'Missing column: {field}')
players = seed['players']
player_ids = {str(player[0]) for player in players if isinstance(player, list) and player}
team_codes = set(seed['teams'])
existing = set()
for row in seed['rows']:
    pid = str(row[cols['pid']])
    day = seed['dates'][row[cols['d']]]
    team = seed['teams'][row[cols['t']]]
    key = (pid, day, team)
    if key in existing:
        raise SystemExit(f'Duplicate existing row: {key}')
    existing.add(key)

games = read_recent(days=7)
missing = []
unknown = {}
unknown_teams = set()
covered = 0
per_date = Counter()
for game in games:
    for item in game['players']:
        key = (str(item['nba_player_id']), game['game_date'], item['team'])
        per_date[game['game_date']] += 1
        if key in existing:
            covered += 1
        else:
            missing.append({'game_id': game['game_id'], 'date': game['game_date'],
                            'player_id': key[0], 'name': item['name'], 'team': item['team'],
                            'player_known': key[0] in player_ids})
        if key[0] not in player_ids:
            unknown[key[0]] = {'id': key[0], 'name': item['name'], 'team': item['team']}
        if item['team'] not in team_codes or item['opponent'] not in team_codes:
            unknown_teams.update(t for t in (item['team'], item['opponent']) if t not in team_codes)

summary = {'mode': 'READ_ONLY', 'games_checked': len(games),
           'cdn_player_game_rows': sum(per_date.values()), 'already_in_seed': covered,
           'missing_player_game_rows': len(missing), 'missing_player_ids': len(unknown),
           'unknown_teams': sorted(unknown_teams), 'existing_seed_rows': len(seed['rows']),
           'existing_seed_dates': len(seed['dates']), 'cdn_rows_by_date': dict(sorted(per_date.items())),
           'unknown_players_sample': list(unknown.values())[:25], 'missing_rows_sample': missing[:25]}
Path('out').mkdir(exist_ok=True)
Path('out/nba-cdn-eslesme-v2.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('=== NBA CDN ESLESME OZETI ===')
for label in ('games_checked', 'cdn_player_game_rows', 'already_in_seed',
              'missing_player_game_rows', 'missing_player_ids', 'unknown_teams',
              'existing_seed_rows', 'cdn_rows_by_date'):
    print(f'{label}: {summary[label]}')
print('unknown_players_sample:', json.dumps(summary['unknown_players_sample'][:8], ensure_ascii=False))
print('READ ONLY: seed/data.json unchanged')
