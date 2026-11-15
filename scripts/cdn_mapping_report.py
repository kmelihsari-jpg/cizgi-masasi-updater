"""Read-only integration preflight, never modifies seed/data.json."""
import json
from pathlib import Path
from nba_cdn_source import read_recent

source = Path('seed/data.json')
if not source.exists():
    raise SystemExit('Missing seed/data.json')
existing = json.loads(source.read_text(encoding='utf-8'))
for key in ('cols', 'rows', 'players', 'teams', 'dates'):
    if key not in existing:
        raise SystemExit('Missing key in existing dataset: ' + key)
games = read_recent(days=7)
players = [p for game in games for p in game['players']]
report = {
    'source': 'NBA CDN', 'mode': 'READ_ONLY',
    'games_checked': len(games), 'players_checked': len(players),
    'game_ids': [g['game_id'] for g in games],
    'seed_shape': {'columns': existing['cols'], 'player_container_type': type(existing['players']).__name__,
                   'team_container_type': type(existing['teams']).__name__,
                   'existing_rows': len(existing['rows']), 'existing_dates': len(existing['dates'])},
    'nba_player_sample': players[:3],
    'warning': 'NBA IDs have not yet been mapped to seed player indexes. No data was written.'
}
Path('out').mkdir(exist_ok=True)
Path('out/nba-cdn-entegrasyon-raporu.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('NBA CDN: checked', len(games), 'games and', len(players), 'played-player records')
print('SEED columns:', existing['cols'])
print('SEED types:', report['seed_shape'])
print('READ ONLY: no site or seed data modified')
