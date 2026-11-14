import copy
import importlib.util
import json
from pathlib import Path
spec=importlib.util.spec_from_file_location('stats',Path(__file__).with_name('update_nba_stats.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.minutes('31:30')==31.5
assert m.made_att('7-15')==(7,15)
assert m.norm('Jalen Duren')==m.norm('JALEN DUREN')
data=json.load(open(Path(__file__).parent.parent/'seed'/'data.json'))
assert len(data['cols'])==25
print('PASS: stats and roster schema; players=',len(data['players']))
# Build synthetic valid boxscore using 8+ known players from two teams.
picks={}
for p in data['players']:
 if p[2] in ('CLE','DAL'):
  picks.setdefault(p[2],[]).append(p)
for team in picks:picks[team]=picks[team][:8]
assert all(len(g)==8 for g in picks.values())
comp={'competitors':[{'team':{'abbreviation':'CLE'},'score':'110','homeAway':'home'},
                      {'team':{'abbreviation':'DAL'},'score':'100','homeAway':'away'}]}
labels=['MIN','FG','3PT','FT','OREB','DREB','REB','AST','STL','BLK','TO','PF','+/-','PTS']
block=[]
for team,pp in picks.items():
 block.append({'team':{'abbreviation':team},'statistics':[{'labels':labels,'athletes':[
 {'athlete':{'displayName':p[1]},'stats':['30:12','8-16','3-7','2-3','1','4','5','6','1','0','2','2','+10','21'],'starter':True}
 for p in pp]}]})
summary={'header':{'competitions':[comp]},'boxscore':{'players':block}}
roster={(m.norm(n),t):pid for pid,n,t,*_ in data['players']}
rows,msg=m.players_from_summary(summary,roster)
assert len(rows)==16,(len(rows),msg)
assert rows[0]['fg3m']==3 and rows[0]['fga']==16 and rows[0]['min']==30.2
assert {r['t'] for r in rows}=={'CLE','DAL'}
print('PASS: synthetic 16-player boxscore parsed and matched')
# verify no duplicate insertion after two runs; use a date not in active data
mock={m.BASE+'/scoreboard?dates=20261117&limit=50':{'events':[{'id':'x1','date':'2026-11-18T00:00:00Z','status':{'type':{'completed':True}}}]},
      m.BASE+'/summary?event=x1':summary}
def getter(url):return mock[url]
new=copy.deepcopy(data)
a,g,_=m.update_data(new,[__import__('datetime').date(2026,11,17)],getter)
assert a==16 and g==1,(a,g)
a2,g2,_=m.update_data(new,[__import__('datetime').date(2026,11,17)],getter)
assert a2==0,(a2,g2)
print('PASS: 16 new player-games inserted, second run inserts zero')
assert m.rotation_trends(new)['type'].startswith('per-game')
print('PASS: rotation trend generation')
