#!/usr/bin/env python3
"""Produce validated local JSON artifacts for private review. No public deployment."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import html as html_lib
import json
import re
from pathlib import Path
import time
import urllib.request

CATS = ('PTS', 'FG', 'FT', '3PM', 'REB', 'AST', 'STL', 'BLK', 'TO')
POSITIONS = ('PG', 'SG', 'SF', 'PF', 'C')
TEAM_MAP = {'NY':'NYK', 'NO':'NOP', 'GS':'GSW', 'SA':'SAS', 'PHO':'PHX'}
TEAMRANK_MAP = {
 'Atlanta':'ATL','Boston':'BOS','Brooklyn':'BKN','Charlotte':'CHA','Chicago':'CHI',
 'Cleveland':'CLE','Dallas':'DAL','Denver':'DEN','Detroit':'DET','Golden State':'GSW',
 'Houston':'HOU','Indiana':'IND','LA Clippers':'LAC','LA Lakers':'LAL','Memphis':'MEM',
 'Miami':'MIA','Milwaukee':'MIL','Minnesota':'MIN','New Orleans':'NOP','New York':'NYK',
 'Okla City':'OKC','Orlando':'ORL','Philadelphia':'PHI','Phoenix':'PHX','Portland':'POR',
 'Sacramento':'SAC','San Antonio':'SAS','Toronto':'TOR','Utah':'UTA','Washington':'WAS'}
TR_KEYS = '''points-per-game average-scoring-margin offensive-efficiency floor-percentage 1st-quarter-points-per-game 2nd-quarter-points-per-game 3rd-quarter-points-per-game 4th-quarter-points-per-game 1st-half-points-per-game 2nd-half-points-per-game overtime-points-per-game points-in-paint-per-game fastbreak-points-per-game fastbreak-efficiency average-biggest-lead average-1st-quarter-margin average-2nd-quarter-margin average-3rd-quarter-margin average-4th-quarter-margin average-1st-half-margin average-2nd-half-margin average-overtime-margin average-margin-thru-3-quarters points-from-2-pointers points-from-3-pointers percent-of-points-from-2-pointers percent-of-points-from-3-pointers percent-of-points-from-free-throws shooting-pct effective-field-goal-pct three-point-pct two-point-pct free-throw-pct true-shooting-percentage field-goals-made-per-game field-goals-attempted-per-game three-pointers-made-per-game three-pointers-attempted-per-game free-throws-made-per-game free-throws-attempted-per-game three-point-rate two-point-rate fta-per-fga ftm-per-100-possessions free-throw-rate non-blocked-2-pt-pct offensive-rebounds-per-game defensive-rebounds-per-game team-rebounds-per-game total-rebounds-per-game offensive-rebounding-pct defensive-rebounding-pct total-rebounding-percentage blocks-per-game steals-per-game block-pct steal-pct assists-per-game turnovers-per-game turnovers-per-possession assist--per--turnover-ratio assists-per-fgm assists-per-possession turnover-pct personal-fouls-per-game technical-fouls-per-game personal-fouls-per-possession personal-foul-pct opponent-points-per-game opponent-average-scoring-margin defensive-efficiency opponent-floor-percentage opponent-1st-quarter-points-per-game opponent-2nd-quarter-points-per-game opponent-3rd-quarter-points-per-game opponent-4th-quarter-points-per-game opponent-overtime-points-per-game opponent-points-in-paint-per-game opponent-fastbreak-points-per-game opponent-fastbreak-efficiency opponent-average-biggest-lead opponent-1st-half-points-per-game opponent-2nd-half-points-per-game opponent-points-from-2-pointers opponent-points-from-3-pointers opponent-percent-of-points-from-2-pointers opponent-percent-of-points-from-3-pointers opponent-percent-of-points-from-free-throws opponent-shooting-pct opponent-effective-field-goal-pct opponent-three-point-pct opponent-two-point-pct opponent-free-throw-pct opponent-true-shooting-percentage opponent-field-goals-made-per-game opponent-field-goals-attempted-per-game opponent-three-pointers-made-per-game opponent-three-pointers-attempted-per-game opponent-free-throws-made-per-game opponent-free-throws-attempted-per-game opponent-three-point-rate opponent-two-point-rate opponent-fta-per-fga opponent-ftm-per-100-possessions opponent-free-throw-rate opponent-non-blocked-2-pt-pct opponent-offensive-rebounds-per-game opponent-defensive-rebounds-per-game opponent-team-rebounds-per-game opponent-total-rebounds-per-game opponent-offensive-rebounding-pct opponent-defensive-rebounding-pct opponent-blocks-per-game opponent-steals-per-game opponent-block-pct opponent-steals-perpossession opponent-steal-pct opponent-assists-per-game opponent-turnovers-per-game opponent-assist--per--turnover-ratio opponent-assists-per-fgm opponent-assists-per-possession opponent-turnovers-per-possession opponent-turnover-pct opponent-personal-fouls-per-game opponent-technical-fouls-per-game opponent-personal-fouls-per-possession opponent-personal-foul-pct games-played possessions-per-game extra-chances-per-game effective-possession-ratio opponent-effective-possession-ratio points-plus-rebounds-plus-assists-per-game points-plus-rebounds-per-game points-plus-assists-per-game rebounds-plus-assists-per-game steals-plus-blocks-per-game opponent-points-plus-rebounds-plus-assists-per-gam opponent-points-plus-rebounds-per-game opponent-points-plus-assists-per-game opponent-rebounds-plus-assists-per-game opponent-steals-plus-blocks-per-game win-pct-all-games win-pct-close-games opponent-win-pct-all-games opponent-win-pct-close-games'''.split()
HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36', 'Accept':'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8'}

def get(url, referer):
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={**HEADERS,'Referer':referer})
            with urllib.request.urlopen(req,timeout=30) as r:
                if r.status!=200: raise RuntimeError(f'HTTP {r.status}')
                return r.read(3_000_000).decode('utf-8','replace')
        except Exception:
            if attempt==2: raise
            time.sleep(1.5*(attempt+1))

def parse_dvp(page):
    rows=re.findall(r'<tr>\s*<td>(PG|SG|SF|PF|C)</td>(.*?)</tr>',page,re.S)
    cellpattern=r'ContentPlaceHolder1_GridView1_Label\d+_\d+">([^<]*)</span>[^<]*<span[^>]*>(\d+)</span>'
    out={}
    seen=set()
    for pos,raw in rows:
        cells=re.findall(cellpattern,raw)
        if len(cells)!=10: continue
        team=html_lib.unescape(cells[0][0]).strip()
        team=TEAM_MAP.get(team,team)
        if (team,pos) in seen: raise ValueError(f'Duplicate: {team}/{pos}')
        seen.add((team,pos))
        ov=int(cells[0][1]); assert 1<=ov<=150
        vals={};ranks={}
        for i,cat in enumerate(CATS,1):
            value=float(cells[i][0].strip().replace(',',''))
            rank=int(cells[i][1])
            if not 1<=rank<=150: raise ValueError(f'Invalid rank {team}/{pos}/{cat}')
            vals[cat]=value;ranks[cat]=rank
        out.setdefault(team,{})[pos]={'ov':ov,'v':vals,'r':ranks}
    if len(out)!=30 or len(seen)!=150 or any(set(v)!=set(POSITIONS) for v in out.values()):
        raise ValueError(f'DVP count mismatch: teams={len(out)}, rows={len(seen)}')
    if not all(k in TEAMRANK_MAP.values() for k in out): raise ValueError('Unknown team code')
    upd=re.search(r'Updated:</strong>\s*([^<]*?)\s+by',page)
    return {'t':out,'source':'Hashtag Basketball','updated':upd.group(1).strip() if upd else datetime.now(timezone.utc).strftime('%Y-%m-%d (checked UTC)')}

def strip_tags(value):
    return html_lib.unescape(re.sub(r'<[^>]+>','',value)).strip()

def parse_tr(page):
    m=re.search(r'<tbody[^>]*>(.*?)</tbody>',page,re.S|re.I)
    if not m: raise ValueError('tbody missing')
    rows=re.findall(r'<tr[^>]*>(.*?)</tr>',m.group(1),re.S|re.I)
    table={}
    for raw in rows:
        cells=[strip_tags(s) for s in re.findall(r'<td[^>]*>(.*?)</td>',raw,re.S|re.I)]
        if len(cells)<8:continue
        code=TEAMRANK_MAP.get(cells[1]);
        if not code:continue
        if code in table: raise ValueError(f'duplicate team {code}')
        values=[]
        for i in (0,2,3,4,5,6,7):
            token=cells[i].replace(',','').replace('%','').strip()
            try: val=float(token) if token else None
            except ValueError: val=None
            values.append(val)
        if values[0] is None: raise ValueError(f'Invalid rank for {code}')
        table[code]=values
    if len(table)!=30:raise ValueError(f'expected 30 teams, got {len(table)}')
    name_match=re.search(r'<h1[^>]*>(.*?)</h1>',page,re.S|re.I)
    return {'n':strip_tags(name_match.group(1)) if name_match else '', 't':table}

def build_tr(limit=0):
    stats={};failed=[]
    keys=TR_KEYS[:limit] if limit else TR_KEYS
    for i,key in enumerate(keys,1):
        try:
            page=get(f'https://www.teamrankings.com/nba/stat/{key}','https://www.teamrankings.com/nba/team-stats/')
            stats[key]=parse_tr(page)
            print(f'[{i}/{len(keys)}] OK {key}',flush=True)
        except Exception as e:
            failed.append((key,str(e)))
            print(f'[{i}/{len(keys)}] FAILED {key}: {e}',flush=True)
        time.sleep(.2)
    threshold=min(140,len(keys))
    if len(stats)<threshold:
        raise ValueError(f'TeamRankings validation failed: {len(stats)} < {threshold}; no JSON output')
    return {'src':'teamrankings.com/nba','updated':datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'cols':['rank','sezon','son3','son1','ev','dep','gecen'],'s':stats},failed

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='output')
    parser.add_argument('--source',choices=['dvp','teamrankings','both'],default='both')
    parser.add_argument('--tr-limit',type=int,default=0,help='Only for verification; output then is incomplete')
    a=parser.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    if a.source in ('dvp','both'):
        dvp=parse_dvp(get('https://hashtagbasketball.com/nba-defense-vs-position','https://hashtagbasketball.com/'))
        (out/'dvp.json').write_text(json.dumps(dvp,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        print('DVP OK: 150 rows, 30 teams',flush=True)
    if a.source in ('teamrankings','both'):
        tr,failed=build_tr(a.tr_limit)
        (out/'teamrankings.json').write_text(json.dumps(tr,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        print(f'TeamRankings OK: {len(tr["s"])} categories; skipped {len(failed)}',flush=True)
    print('Validated files are review-only; no auto publication or git push.',flush=True)
if __name__=='__main__':main()
