#!/usr/bin/env python3
"""Safe, incremental NBA CDN -> Cizgi Masasi seed/data.json sync.

Default is read-only. --apply is an explicit opt-in. Never replaces existing
player-game statistics or tracking columns. Requires nba_cdn_source.py beside it.
"""
from __future__ import annotations
import argparse
import copy
import datetime as dt
import json
import os
from pathlib import Path
import re
import tempfile
from collections import Counter
from nba_cdn_source import read_recent

BASIC = ('min', 'pts', 'reb', 'ast', 'stl', 'blk', 'fg3m', 'fg3a', 'tov', 'start', 'fga', 'fta', 'oreb')
REQUIRED = ('pid', 'd', 't', 'o', 'home', 'win', 'min', 'pts', 'reb', 'ast', 'stl', 'blk', 'fg3m', 'fg3a', 'tov', 'start', 'margin', 'fga', 'fta', 'oreb')
STATS = {'pts':'pts', 'reb':'reb', 'ast':'ast', 'stl':'stl', 'blk':'blk',
         'fg3m':'fg3m', 'fg3a':'fg3a', 'tov':'tov', 'fga':'fga', 'fta':'fta', 'oreb':'oreb'}


def parse_minutes(value):
    """NBA liveData generally uses ISO 8601 duration e.g. PT27M12.00S."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        result = float(value)
    elif isinstance(value, str):
        s = value.strip()
        iso = re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?', s)
        mmss = re.fullmatch(r'(\d+):(\d{1,2})(?::(\d{1,2}))?', s)
        if iso and any(x is not None for x in iso.groups()):
            h, m, sec = iso.groups()
            result = float(h or 0)*60 + float(m or 0) + float(sec or 0)/60
        elif mmss:
            x, y, z = mmss.groups()
            result = int(x)*60 + int(y) + int(z)/60 if z is not None else int(x) + int(y)/60
        else:
            try: result = float(s)
            except ValueError: raise ValueError('Unknown minutes format: ' + repr(value))
    else:
        raise ValueError('Unknown minutes type: ' + repr(value))
    if not 0 <= result <= 70:
        raise ValueError('Implausible minutes: ' + repr(value))
    return round(result, 2)


def positive_int(v, name):
    if isinstance(v, bool) or isinstance(v, float) and not v.is_integer():
        raise ValueError(f'{name} is not an integer: {v!r}')
    try:
        n = int(v)
    except (ValueError, TypeError):
        raise ValueError(f'{name} invalid: {v!r}')
    if n < 0:
        raise ValueError(f'{name} negative: {v!r}')
    return n


def merge(seed, games):
    """Pure function: return (new dataset, report), never mutate seed."""
    data = copy.deepcopy(seed)
    for key in ('cols','rows','players','teams','dates','season'):
        if key not in data:
            raise ValueError('Missing seed field: ' + key)
    cols = data['cols']
    if len(cols) != len(set(cols)) or any(k not in cols for k in REQUIRED):
        raise ValueError('Unexpected seed columns')
    ci = {name: i for i, name in enumerate(cols)}
    teams = data['teams']
    if len(teams) != len(set(teams)):
        raise ValueError('Duplicate team codes')
    ti = {t: i for i, t in enumerate(teams)}
    players = data['players']
    pi = {str(p[0]): p for p in players}
    if len(pi) != len(players):
        raise ValueError('Duplicate NBA player ID in seed players')
    old_dates = list(data['dates'])
    if len(old_dates) != len(set(old_dates)):
        raise ValueError('Duplicate dates in seed')
    for day in old_dates:
        dt.date.fromisoformat(day)
    known = set()
    for row in data['rows']:
        if len(row) != len(cols):
            raise ValueError('Malformed existing row')
        key = (str(row[ci['pid']]), old_dates[row[ci['d']]], teams[row[ci['t']]])
        if key in known:
            raise ValueError('Duplicate existing key: ' + repr(key))
        known.add(key)
    initial_count = len(known)
    seen_games = set()
    pending = []
    added_players = {}
    dates = set(old_dates)
    checked = Counter()
    window = Counter()
    existing_discrepancies = 0
    skipped_inactive = 0
    for game in games:
        gid = str(game['game_id'])
        if gid in seen_games:
            raise ValueError('Duplicate game ID: ' + gid)
        seen_games.add(gid)
        date = game['game_date']
        dt.date.fromisoformat(date)
        if not date.startswith(data['season'][:4] + '-') and not date.startswith('20' + data['season'][5:] + '-'):
            raise ValueError('Game outside dataset season: ' + date)
        team_scores = {x['team']: positive_int(x['score'], 'team score') for x in game['teams']}
        if len(team_scores) != 2 or len(set(team_scores) - set(ti)):
            raise ValueError('Unknown/invalid team score for ' + gid)
        sides = Counter()
        for item in game['players']:
            pid = str(item['nba_player_id'])
            if not pid.isdigit() or not str(item.get('name') or '').strip():
                raise ValueError('Invalid player identity for ' + gid)
            if parse_minutes(item['minutes']) == 0 and item['starter']:
                # Imkansiz kayit: 0 dakikayla ilk 5 baslayan oyuncu = oynamadi. Satir yazma,
                # oyuncu sayimina da katma (yoksa "cok az oyuncu" kontrolu maskelenir).
                skipped_inactive += 1
                continue
            team, opponent = item['team'], item['opponent']
            if team not in team_scores or opponent not in team_scores or team == opponent:
                raise ValueError('Team mismatch for ' + gid)
            sides[team] += 1
            key = (pid, date, team)
            if key in checked:
                raise ValueError('Duplicate player in CDN payload: ' + repr(key))
            checked[key] += 1
            window[date] += 1
            vals = {k: positive_int(item[k], k) for k in STATS}
            vals.update(min=parse_minutes(item['minutes']), start=int(bool(item['starter'])),
                        home=int(bool(item['home'])), win=int(team_scores[team] > team_scores[opponent]),
                        margin=team_scores[team] - team_scores[opponent])
            if vals['fg3m'] > vals['fg3a'] or vals['fg3a'] > vals['fga'] or vals['oreb'] > vals['reb']:
                raise ValueError('Invalid stat consistency for ' + repr(key))
            if key in known:
                # Never overwrite earlier values; the user may have historical tracking fields.
                continue
            known.add(key)
            dates.add(date)
            if pid not in pi and pid not in added_players:
                # Position is unknown in boxscore; leave it blank rather than inventing one.
                added_players[pid] = [int(pid), item['name'].strip(), team, '']
            values = dict(vals, pid=int(pid), d=date, t=team, o=opponent)
            pending.append(values)
        if any(sides[t] < 5 for t in team_scores):
            raise ValueError(f'Too few played athletes: {gid} {dict(sides)}')
    sorted_dates = sorted(dates)
    date_index = {d: i for i, d in enumerate(sorted_dates)}
    # Preserve logical meaning of every old row, including historic tracking columns.
    for row in data['rows']:
        row[ci['d']] = date_index[old_dates[row[ci['d']]]]
    data['dates'] = sorted_dates
    for pid, player in sorted(added_players.items()):
        data['players'].append(player)
    for values in pending:
        row = [None] * len(cols)
        values['d'] = date_index[values['d']]
        values['t'] = ti[values['t']]
        values['o'] = ti[values['o']]
        for col, val in values.items():
            if col in ci:
                row[ci[col]] = val
        data['rows'].append(row)
    # Cross-check that no original record/field has changed, accounting for date indices.
    after = {}
    for row in data['rows']:
        key = (str(row[ci['pid']]), sorted_dates[row[ci['d']]], teams[row[ci['t']]])
        if key in after:
            raise ValueError('Duplicate after merge: ' + repr(key))
        after[key] = row
    for old in seed['rows']:
        key = (str(old[ci['pid']]), old_dates[old[ci['d']]], teams[old[ci['t']]])
        newer = after[key]
        if any(old[i] != newer[i] for i, col in enumerate(cols) if col != 'd'):
            raise ValueError('Historical stats changed: ' + repr(key))
    if len(data['rows']) != initial_count + len(pending):
        raise ValueError('Row count mismatch')
    if pending:
        data['updated'] = dt.datetime.now(dt.timezone.utc).isoformat()
    report = {'status':'verified', 'games_checked':len(seen_games), 'cdn_rows':sum(window.values()),
              'already_present':sum(window.values()) - len(pending), 'new_rows':len(pending),
              'skipped_inactive':skipped_inactive, 'new_players':list(added_players.values()), 'rows_before':initial_count,
              'rows_after':len(data['rows']), 'latest_date':sorted_dates[-1] if sorted_dates else None,
              'dates_checked':dict(sorted(window.items())), 'tracking_preserved':True,
              'existing_rows_preserved':True, 'season':data['season']}
    return data, report


def write_atomic(path, data):
    path = Path(path)
    fd, filename = tempfile.mkstemp(prefix='.nba-cdn-', suffix='.json', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(data, out, ensure_ascii=False, separators=(',', ':'))
            out.write('\n')
        os.replace(filename, path)
    finally:
        if os.path.exists(filename): os.unlink(filename)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--site', default='seed')
    p.add_argument('--days', type=int, default=7)
    p.add_argument('--apply', action='store_true', help='Explicitly persist verified additions')
    p.add_argument('--report', default='out/nba-cdn-sync-report.json')
    args = p.parse_args()
    if not 1 <= args.days <= 14:
        p.error('--days must be 1..14')
    path = Path(args.site) / 'data.json'
    seed = json.loads(path.read_text(encoding='utf-8'))
    games = read_recent(days=args.days)
    result, report = merge(seed, games)
    report['mode'] = 'APPLY' if args.apply else 'DRY_RUN'
    dest = Path(args.report)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if args.apply and report['new_rows']:
        write_atomic(path, result)
        print('APPLIED: data.json updated (no tracking/rotation files changed)')
    else:
        print('READ ONLY: no seed file changed')


if __name__ == '__main__':
    main()
