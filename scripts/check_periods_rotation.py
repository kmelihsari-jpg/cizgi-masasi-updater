#!/usr/bin/env python3
"""Validate optional periods and rotation exports without changing data."""
import json
from pathlib import Path

seen = 0
p = Path('seed/periods.json')
if p.exists():
    x = json.loads(p.read_text(encoding='utf-8-sig'))
    assert all(isinstance(x.get(k), list) for k in ('dates', 'cols', 'rows'))
    assert {'pid', 'd', 'q', 'min', 'pts', 'reb', 'ast'} <= set(x['cols'])
    assert len(x['rows']) >= 100 and x['dates']
    assert all(len(row) == len(x['cols']) for row in x['rows'])
    assert x['dates'] == sorted(x['dates'])
    assert all(isinstance(d, str) and len(d) == 10 for d in x['dates'])
    c = {name: i for i, name in enumerate(x['cols'])}
    assert all(isinstance(r[c['d']], int) and 0 <= r[c['d']] < len(x['dates']) for r in x['rows'])
    assert all(r[c['q']] in (1,2,3,4,5,6,7,8) for r in x['rows'])
    print(f"PERIODS OK: son tarih={x['dates'][-1]} satir={len(x['rows'])}")
    seen += 1
r = Path('seed/rotation.json')
if r.exists():
    x = json.loads(r.read_text(encoding='utf-8-sig'))
    assert isinstance(x.get('t'), dict) and len(x['t']) >= 20
    assert isinstance(x.get('updated'), str) and len(x['updated']) == 10
    count = 0
    for team in x['t'].values():
        assert isinstance(team.get('p'), list)
        for player in team['p']:
            assert isinstance(player.get('b'), list) and len(player['b']) == 48
            assert all(isinstance(v, (int, float)) and 0 <= v <= 100 for v in player['b'])
            count += 1
    print(f"ROTATION OK: guncelleme={x['updated']} oyuncu={count}")
    seen += 1
assert seen, 'seed/periods.json veya seed/rotation.json bulunamadi'
