#!/usr/bin/env python3
"""Pure fixture checks; does not read or change real seed/data.json."""
import importlib.util
from pathlib import Path
import copy
spec = importlib.util.spec_from_file_location('merge_tracking', Path(__file__).with_name('merge_tracking.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
base = {
 'dates':['2026-11-12','2026-11-13'],
 'cols':['pid','d','t','pot','rc','rcon','runc','rdef'],
 'rows':[[123,0,0,7,None,2,None,None],[123,1,0,None,None,None,None,None]],
}
report = {'source':'local-nba-tracking-cache-v1','records':[
 {'pid':'123','date':'2026-11-12','pot':None,'rc':11,'rcon':None,'runc':5,'rdef':6},
 {'pid':'123','date':'2026-11-13','pot':9,'rc':10,'rcon':2,'runc':3,'rdef':5},
]}
data = copy.deepcopy(base)
r = mod.merge(data,report)
assert r['matched_records'] == 2
assert data['rows'][0][3] == 7, 'null overwrote existing Potential Assists'
assert data['rows'][0][4] == 11
assert data['rows'][1][3] == 9
before=copy.deepcopy(data)
r2=mod.merge(data,report)
assert data == before and r2['changed_player_games'] == 0, 'not idempotent'
try:
 mod.merge(copy.deepcopy(base), {'source':'local-nba-tracking-cache-v1','records':[{'pid':'123','date':'2026-11-12','pot':-1}]})
 raise AssertionError('negative metric accepted')
except ValueError:pass
print('PASS: null preservation, dated updates, idempotency, invalid values')
