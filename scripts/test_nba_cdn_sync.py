"""Offline, deterministic tests; no network, no seed writes."""
import copy
from update_nba_cdn import merge, parse_minutes

assert parse_minutes('PT28M30.00S') == 28.5
assert parse_minutes('31:30') == 31.5
assert parse_minutes('PT1H2M15S') == 62.25
cols = ['pid','d','t','o','home','win','min','pts','reb','ast','stl','blk','fg3m','fg3a','tov','start','pot','rc','margin','rcon','runc','rdef','fga','fta','oreb']
seed = {'season':'2026-27', 'cols':cols, 'dates':['2026-11-11','2026-11-13'],
        'teams':['CHI','MIN'], 'players':[[10,'Old Player','CHI','G']],
        'rows':[[10,1,0,1,1,1,31,15,3,4,1,0,1,3,2,1,9,12,5,7,8,3,9,4,2]]}

def p(pid, team, opp, name=None):
    return {'nba_player_id':str(pid),'name':name or f'Player {pid}', 'team':team,'opponent':opp,
            'home':team=='CHI','starter':True,'minutes':'PT20M30.00S','pts':10,'reb':4,'ast':2,
            'stl':1,'blk':0,'fg3m':1,'fg3a':2,'tov':1,'fga':7,'fta':3,'oreb':1}
games = [{'game_id':'0022600123','game_date':'2026-11-12',
          'teams':[{'team':'CHI','score':100},{'team':'MIN','score':90}],
          'players':[p(x,'CHI','MIN') for x in range(10,15)] + [p(x,'MIN','CHI') for x in range(20,25)]}]
original=copy.deepcopy(seed)
new,report=merge(seed,games)
assert seed==original
assert report['new_rows']==10 and report['rows_after']==11
assert new['dates']==['2026-11-11','2026-11-12','2026-11-13']
assert new['rows'][0][1]==2 and new['rows'][0][16:18]==[9,12]
assert new['rows'][1][16] is None and new['rows'][1][17] is None
assert all(len(r)==25 for r in new['rows'])
new2,r2=merge(new,games)
assert r2['new_rows']==0 and new2==new
for bad in ('PT200M0S','bogus'):
    try:parse_minutes(bad)
    except ValueError:pass
    else:raise AssertionError('Invalid duration allowed')
games[0]['players'][0]['team']='XYZ'
try:merge(seed,games)
except ValueError:pass
else:raise AssertionError('Invalid team accepted')
print('PASS: minutes, identity, new players, date indices, tracking preservation, idempotency, fail closed')
