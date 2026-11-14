#!/usr/bin/env python3
"""Cizgi Masasi: read-only NBA tracking + rotation source diagnostic.

Does not modify seed/data.json or attempt to estimate NBA tracking metrics.
Only uses Python standard library. Outputs a source report as a GitHub artifact.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ESPN = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
REPORT = Path('tracking-kaynak-raporu.json')


def fetch(url, timeout=13, headers=None):
    h = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/132.0 Safari/537.36',
         'Accept': 'application/json, text/plain, */*',
         'Accept-Language': 'en-US,en;q=0.9'}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(4_000_000)
            content_type = r.headers.get('Content-Type', '')
            try:
                doc = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                return {'ok': False, 'http': r.status, 'error': 'Yanıt JSON değil', 'content_type': content_type}, None
            return {'ok': True, 'http': r.status}, doc
    except urllib.error.HTTPError as e:
        return {'ok': False, 'http': e.code, 'error': 'HTTP '+str(e.code)}, None
    except Exception as e:
        return {'ok': False, 'error': type(e).__name__+': '+str(e)[:130]}, None


def count_plays(plays):
    if isinstance(plays, dict):
        plays = plays.get('all') or plays.get('items') or []
    if not isinstance(plays, list):
        return {'events': 0, 'substitutions': 0, 'examples': []}
    subs=[]
    for p in plays:
        if not isinstance(p, dict):
            continue
        typ = p.get('type') or {}
        t = str(typ.get('text', '') if isinstance(typ, dict) else typ)
        desc = str(p.get('text') or p.get('description') or '')
        if ('substitut' in (t+' '+desc).lower() or
            'enters the game' in desc.lower() or
            'leaves the game' in desc.lower()):
            if len(subs) < 3:
                subs.append({'type': t[:80], 'text': desc[:110], 'clock': p.get('clock', {}).get('displayValue') if isinstance(p.get('clock'), dict) else str(p.get('clock'))})
    # Counting by first three examples is not sufficient: scan full list.
    num = sum(1 for p in plays if isinstance(p, dict) and (
        'substitut' in (str(p.get('type', {}).get('text', '')) if isinstance(p.get('type'), dict) else str(p.get('type', ''))).lower() or
        any(x in str(p.get('text') or p.get('description') or '').lower() for x in ('substitut', 'enters the game', 'leaves the game'))))
    return {'events': len(plays), 'substitutions': num, 'examples': subs}


def test_espn():
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=-4))).date()
    checked=[]
    for n in range(1, 6):
        day = today-dt.timedelta(days=n)
        status, board = fetch(ESPN+'/scoreboard?'+urllib.parse.urlencode({'dates': day.strftime('%Y%m%d'), 'limit': 50}))
        checked.append({'date': day.isoformat(), 'scoreboard': status})
        if not board:
            continue
        events=[e for e in board.get('events', []) if (e.get('status', {}).get('type', {}).get('completed') or e.get('status', {}).get('type', {}).get('name')=='STATUS_FINAL')]
        for e in events[:3]:
            eid=str(e.get('id', ''))
            if not eid:
                continue
            result, summary=fetch(ESPN+'/summary?event='+urllib.parse.quote(eid))
            checked[-1]['sample_game_id']=eid
            checked[-1]['summary']=result
            if summary:
                plays=summary.get('plays')
                checked[-1]['play_by_play']=count_plays(plays)
                checked[-1]['keys']=list(summary.keys())[:18]
                checked[-1]['boxscore_team_count']=len(summary.get('boxscore', {}).get('players') or [])
                # Also try dedicated PBP endpoint if summary lacks plays.
                if checked[-1]['play_by_play']['events']==0:
                    st, pbp = fetch(ESPN+'/playbyplay?event='+urllib.parse.quote(eid))
                    checked[-1]['dedicated_playbyplay_endpoint']=st
                    if pbp:
                        checked[-1]['dedicated_play_by_play']=count_plays(pbp.get('plays'))
                if checked[-1]['play_by_play']['events']:
                    return checked
    return checked


def test_nba_live():
    # Known format-example game ID used only to establish CDN access, not current-season coverage.
    game_id='0022500001'
    url='https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_'+game_id+'.json'
    status, doc=fetch(url, timeout=12, headers={'Referer':'https://www.nba.com/'})
    result={'game_id':game_id, 'connection':status}
    if doc:
        actions=doc.get('game', {}).get('actions') or []
        substitutions=[x for x in actions if x.get('actionType')=='substitution']
        result.update({'events':len(actions),'substitutions':len(substitutions),
                       'has_person_id':any(bool(x.get('personId')) for x in substitutions)})
    return result


def test_tracking():
    # This is a reachability test, not a successful-data guarantee.
    params={'College':'','Conference':'','Country':'','DateFrom':'','DateTo':'',
            'Division':'','DraftPick':'','DraftYear':'','GameScope':'',
            'GameSegment':'','Height':'','LastNGames':'0','LeagueID':'00',
            'Location':'','MeasureType':'Passing','Month':'0','OpponentTeamID':'0',
            'Outcome':'','PORound':'0','PaceAdjust':'N','PerMode':'Totals',
            'Period':'0','PlayerExperience':'','PlayerOrTeam':'Player',
            'PlayerPosition':'','PlusMinus':'N','Rank':'N','Season':'2025-26',
            'SeasonSegment':'','SeasonType':'Regular Season','ShotClockRange':'',
            'StarterBench':'','TeamID':'0','VsConference':'','VsDivision':'',
            'Weight':''}
    query='https://stats.nba.com/stats/leaguedashptstats?'+urllib.parse.urlencode(params)
    status, doc=fetch(query,timeout=9,headers={'Referer':'https://www.nba.com/',
                                                'Origin':'https://www.nba.com',
                                                'x-nba-stats-origin':'stats','x-nba-stats-token':'true'})
    result={'connection':status,'metric':'Potential Assists (passing)'}
    if doc:
        sets=doc.get('resultSets') or ([doc['resultSet']] if isinstance(doc.get('resultSet'),dict) else [])
        if isinstance(sets,dict): sets=[sets]
        result['tables']=[{'name':s.get('name'), 'rows':len(s.get('rowSet') or []),
                           'has_potential_ast':any(str(c).upper()=='POTENTIAL_AST' for c in s.get('headers',[]))}
                          for s in sets if isinstance(s,dict)]
    return result


def main():
    report={'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'purpose':'Kaynak erisimi testi; veri dosyalari degistirilmez',
            'espn':test_espn(),
            'nba_live_cdn':test_nba_live(),
            'nba_tracking':test_tracking()}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('\n===== CIZGI MASASI - TRACKING / ROTASYON KAYNAK TESTI =====')
    for s in report['espn']:
        print('ESPN',s['date'],'scoreboard:',s['scoreboard'],
              'game:',s.get('sample_game_id'), 'plays:',s.get('play_by_play'),
              'pbp_endpoint:',s.get('dedicated_playbyplay_endpoint'))
    print('NBA CDN:',report['nba_live_cdn'])
    print('NBA TRACKING:',report['nba_tracking'])
    print('Rapor:',REPORT)
    print('Veriler korunuyor: seed/data.json ve canli siteye yazilmadi.')


if __name__=='__main__':
    main()
