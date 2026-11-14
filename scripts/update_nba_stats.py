#!/usr/bin/env python3
"""Incremental NBA box-score sync for Cizgi Masasi. No pip dependencies.

This sync uses ESPN's publicly accessible scoreboard/summary endpoints; their format
may change and availability is not guaranteed. When format is unrecognized it skips
rather than fabricating statistics or silently deleting existing data.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request
import unicodedata
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
TEAMS = {'NY':'NYK','NYK':'NYK','GS':'GSW','GSW':'GSW','SA':'SAS','SAS':'SAS',
         'NO':'NOP','NOP':'NOP','UTAH':'UTA','WSH':'WAS','WAS':'WAS','BKN':'BKN',
         'PHO':'PHX','PHX':'PHX'}


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('ascii')
    s = s.lower().replace('’', "'")
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return re.sub(r'[^a-z0-9]', '', s)


def team_abbr(s):
    t = str(s or '').strip().upper()
    return TEAMS.get(t, t)


def get_json(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'CizgiMasasi/1.0 (personal NBA stats viewer)',
        'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=22) as response:
        if response.status != 200: raise RuntimeError(f'HTTP {response.status}')
        return json.load(response)


def season_start(season):
    m = re.fullmatch(r'(20\d\d)-(\d\d)', season)
    if not m: raise ValueError('Unrecognized season: '+str(season))
    return dt.date(int(m.group(1)), 10, 1)


def parse_float(x):
    try: return float(str(x).replace(',', '').replace('+', '').strip())
    except (ValueError, TypeError): return None


def num(x):
    v=parse_float(x)
    return None if v is None else int(v) if v.is_integer() else v


def minutes(x):
    if x is None: return None
    s=str(x).strip()
    if ':' in s:
        try:
            a,b=s.split(':',1);return round(int(a)+int(b)/60,2)
        except ValueError: return None
    return num(s)


def made_att(x):
    m=re.fullmatch(r'\s*(\d+)\s*[-/]\s*(\d+)\s*',str(x))
    return (int(m.group(1)),int(m.group(2))) if m else (None,None)


def parse_athlete(st, labels):
    # ESPN sometimes emits named stat objects and sometimes parallel label/value lists.
    if isinstance(st, dict):
        st=st.get('statistics') or st.get('stats') or []
    if isinstance(st, list) and st and isinstance(st[0], dict):
        d={str(z.get('name') or z.get('abbreviation') or z.get('label') or '').upper():z.get('value', z.get('displayValue')) for z in st}
    elif isinstance(st, list):
        if len(st)!=len(labels): return None
        d=dict(zip((x.upper() for x in labels),st))
    else: return None
    # The usual boxscore schema has FG, 3PT, FT, etc.
    pts=num(d.get('PTS')); reb=num(d.get('REB')); ast=num(d.get('AST'))
    mins=minutes(d.get('MIN'))
    if any(x is None for x in (pts,reb,ast,mins)): return None
    fg3m,fg3a=made_att(d.get('3PT',d.get('3P')))
    fgm,fga=made_att(d.get('FG'))
    ftm,fta=made_att(d.get('FT'))
    return {'min':mins,'pts':pts,'reb':reb,'ast':ast,
            'stl':num(d.get('STL')),'blk':num(d.get('BLK')),
            'fg3m':fg3m,'fg3a':fg3a,'fga':fga,'fta':fta,
            'oreb':num(d.get('OREB',d.get('OR'))),
            'tov':num(d.get('TO',d.get('TOV')))}


def get_team_scores(summary):
    ev=summary.get('header',{}).get('competitions',[])
    competition=ev[0] if ev else summary.get('boxscore',{}).get('competition',{})
    out={}
    for c in competition.get('competitors',[]):
        a=team_abbr(c.get('team',{}).get('abbreviation'))
        score=parse_float(c.get('score'))
        if a and score is not None: out[a]=(score,c.get('homeAway')=='home')
    return out


def players_from_summary(summary, roster_by_name_team):
    box=summary.get('boxscore',{})
    scores=get_team_scores(summary)
    if len(scores)!=2: return [],'Missing two verified team scores'
    output=[]; examined=0; missing=0
    for team in box.get('players',[]):
        abb=team_abbr(team.get('team',{}).get('abbreviation'))
        if abb not in scores: continue
        score,home=scores[abb]
        opp=next(a for a in scores if a!=abb)
        other_score=scores[opp][0]
        for block in team.get('statistics',[]):
            labels=block.get('labels') or block.get('names') or []
            for row in block.get('athletes',[]):
                if row.get('didNotPlay') or row.get('didNotDress'): continue
                athlete=row.get('athlete') or {}
                name=athlete.get('displayName') or athlete.get('fullName') or ''
                vals=parse_athlete(row.get('stats',row.get('statistics')),labels)
                if not name or vals is None: continue
                examined+=1
                # No arbitrary ESPN athlete IDs: only trusted exact full-name + team mapping.
                pid=roster_by_name_team.get((norm(name),abb))
                if not pid:
                    missing+=1;continue
                vals.update(pid=pid,t=abb,o=opp,home=int(home),win=int(score>other_score),
                            margin=int(score-other_score),start=int(bool(row.get('starter'))))
                output.append(vals)
    # Fail closed: less than 8 correctly matched players means roster/source may be incompatible.
    by_team={t:sum(1 for p in output if p['t']==t) for t in scores}
    if len(output)<8 or examined<12 or len(output)/examined<0.55 or any(n<4 for n in by_team.values()):
        return [],f'Insufficient roster match: {len(output)}/{examined} athletes; team matches {by_team}'
    return output,f'matched {len(output)}/{examined}; unmatched {missing}'


def rotation_trends(data):
    c={k:i for i,k in enumerate(data['cols'])}
    date=data['dates']; teams=data['teams']; players={p[0]:p for p in data['players']}
    by_team=defaultdict(lambda:defaultdict(list))
    for r in data['rows']:
        pid=r[c['pid']];
        if pid not in players: continue
        game_date=date[r[c['d']]];t=teams[r[c['t']]];mi=r[c['min']]
        if mi is not None:by_team[t][pid].append((game_date,float(mi),int(r[c['start']]) if r[c['start']] is not None else None))
    result={}
    for t,px in by_team.items():
        p=[]
        for pid,games in px.items():
            games.sort(key=lambda x:x[0]);recent=games[-5:]
            p.append({'id':pid,'name':players[pid][1],'games':len(games),
                      'last_game':games[-1][0],'minutes_last5':round(sum(g[1] for g in recent)/len(recent),1),
                      'minutes_season':round(sum(g[1] for g in games)/len(games),1),
                      'starts_last5':sum(g[2] == 1 for g in recent),
                      'sample_last5':len(recent)})
        result[t]=sorted(p,key=lambda x:x['minutes_last5'],reverse=True)
    return {'source':'Completed-game box scores (ESPN API)','type':'per-game minutes, not on-court rotation intervals',
            'updated':dt.datetime.now(dt.timezone.utc).isoformat(),
            'latest_game':data['dates'][-1],'teams':result}


def update_data(data, dates_to_get, getter, limit=8):
    cols=data['cols']; ci={k:i for i,k in enumerate(cols)}
    teams=data['teams'];ti={t:i for i,t in enumerate(teams)}
    idx={(r[ci['pid']],data['dates'][r[ci['d']]],teams[r[ci['t']]]) for r in data['rows']}
    roster={(norm(n),t):pid for pid,n,t,*other in data['players']}
    events=[]
    for day in dates_to_get:
        board=getter(BASE+'/scoreboard?dates='+day.strftime('%Y%m%d')+'&limit=50')
        for ev in board.get('events',[]):
            st=ev.get('status',{}).get('type',{})
            if not st.get('completed') and st.get('name')!='STATUS_FINAL':continue
            if ev.get('id'):events.append((str(ev['id']),ev.get('date') or ''))
    # Avoid duplicates from overlapping scoreboards.
    events=list(dict(events).items())
    added=0;matched_games=0;notes=[]
    for eid,stamp in events[:max(limit,1)]:
        try:
            gameday=dt.datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date().isoformat()
            if gameday not in data['dates']:
                data['dates'].append(gameday)
            didx=data['dates'].index(gameday)
            summary=getter(BASE+'/summary?event='+eid)
            got,msg=players_from_summary(summary,roster)
            if not got:
                notes.append(eid+': '+msg);continue
            batch=[]
            for p in got:
                key=(p['pid'],gameday,p['t'])
                if key in idx:continue
                if p['t'] not in ti or p['o'] not in ti:continue
                row=[None]*len(cols)
                values={**p,'d':didx,'t':ti[p['t']],'o':ti[p['o']]}
                for col,val in values.items():
                    if col in ci:row[ci[col]]=val
                batch.append((key,row))
            for key,row in batch:
                idx.add(key);data['rows'].append(row)
            added+=len(batch);matched_games+=1
            notes.append(f'{eid} {gameday}: {msg}; new rows {len(batch)}')
        except Exception as exc:
            notes.append(eid+': ERROR '+str(exc)[:180])
    # Do not promote dates for unsuccessful summaries.
    used={r[ci['d']] for r in data['rows']}
    old_dates=data['dates']; new_dates=sorted({old_dates[i] for i in used}); remap={i:new_dates.index(s) for i,s in enumerate(old_dates) if s in new_dates}
    for row in data['rows']:row[ci['d']]=remap[row[ci['d']]]
    data['dates']=new_dates
    if added:
        data['updated']=dt.datetime.now(dt.timezone.utc).isoformat()
    return added,matched_games,notes


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--site',default='site');ap.add_argument('--days',type=int,default=3)
    ap.add_argument('--limit',type=int,default=30);ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
    path=Path(a.site)/'data.json';data=json.loads(path.read_text(encoding='utf-8'))
    season=season_start(data['season']);today=dt.datetime.now(ZoneInfo('America/New_York')).date()
    days=[today-dt.timedelta(days=n) for n in range(min(max(a.days,1),7))]
    days=[d for d in days if d>=season]
    if not days: print('Outside site season, no update');return
    try:added,games,notes=update_data(data,days,get_json,a.limit)
    except Exception as e:print('Scoreboard fetch failed (original files intact):',e);sys.exit(1)
    for line in notes:print(line)
    print(f'Validated boxscores: {games}; new player-game rows: {added}; latest stored date: {data["dates"][-1]}')
    print('NOT: potential assists / rebound chances, shot zones and quarter splits ESPN boxscore kaynakli DEGIL; eski kayitlar korunur, yeni satirlarda bu alanlar null kalir.')
    if a.dry_run:return
    if added:
        path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
        (Path(a.site)/'rotation-live.json').write_text(json.dumps(rotation_trends(data),ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    else:print('Nothing new - original site data unchanged')

if __name__=='__main__':main()
