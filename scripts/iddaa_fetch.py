#!/usr/bin/env python3
"""Cizgi Masasi - Iddaa NBA player props to iddaa-lines.json.
Uses the public event JSON endpoints; no Claude-browser dependency.
Requires no external Python packages. Fail-closed on invalid/missing data.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
import unicodedata
import urllib.request
from pathlib import Path

BASE = 'https://sportsbookv2.iddaa.com/sportsbook/'
MARKETS = {831:'PTS',832:'REB',833:'AST',834:'STL',835:'BLK',836:'3PM',840:'SRA',860:'RA'}
TEAM_NAMES = {
 'atlanta':'ATL','boston':'BOS','brooklyn':'BKN','charlotte':'CHA','chicago':'CHI',
 'cleveland':'CLE','dallas':'DAL','denver':'DEN','detroit':'DET','golden state':'GSW',
 'houston':'HOU','indiana':'IND','la clippers':'LAC','los angeles clippers':'LAC',
 'la lakers':'LAL','los angeles lakers':'LAL','memphis':'MEM','miami':'MIA',
 'milwaukee':'MIL','minnesota':'MIN','new orleans':'NOP','new york':'NYK',
 'oklahoma city':'OKC','oklahoma':'OKC','oklahoma thunder':'OKC','orlando':'ORL','philadelphia':'PHI','phoenix':'PHX',
 'portland':'POR','sacramento':'SAC','san antonio':'SAS','toronto':'TOR',
 'utah':'UTA','washington':'WAS',
}
# Explicit, manually reviewed aliases only; never fuzzy-match different players.
ALIASES = {
 'nikola jokic':'nikola jokic','luka doncic':'luka doncic',
 'karl anthony towns':'karl anthony towns',
 'pj washington':'p j washington',
 'cj mccollum':'c j mccollum',
 'og anunoby':'o g anunoby',
 'jaren jackson':'jaren jackson jr',
}
PLAYER_RE = re.compile(r'^(.+?)\s+(\d{1,3})\+$')

def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).casefold()
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('’',"'")
    return re.sub(r'[^a-z0-9]+',' ',s).strip()

def strip_suffix(k):
    return re.sub(r'\s+(jr|sr|ii|iii|iv)$','',k)

def load_json(path):
    with open(path,'r',encoding='utf-8-sig') as f:
        return json.load(f)

def download(url, timeout=22):
    req = urllib.request.Request(url, headers={'Accept':'application/json', 'User-Agent':'Mozilla/5.0 (compatible; CizgiMasasiData/1.0)'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw = r.read(12_000_000)
    doc = json.loads(raw.decode('utf-8-sig'))
    if doc.get('isSuccess') is not True or not isinstance(doc.get('data'),dict):
        raise ValueError('Iddaa JSON isSuccess/data gecersiz')
    return doc['data']

def roster_index(data):
    players=data.get('players')
    if not isinstance(players,list) or len(players)<200:
        raise ValueError('data.json oyuncu kadrosu eksik (<200)')
    by_name={}
    for p in players:
        if not isinstance(p,list) or len(p)<3:continue
        pid,name,team=p[:3]
        try:pid=int(pid)
        except (TypeError,ValueError):continue
        k=norm(name)
        by_name.setdefault(k,[]).append((pid,str(team)))
        # Ek (Jr./Sr./II...) olmadan yazilan isimler icin yedek anahtar; yalnizca tam eslesme yoksa kullanilir.
        k2=strip_suffix(k)
        if k2!=k:by_name.setdefault('~'+k2,[]).append((pid,str(team)))
    return by_name

def parse_event(event,by_name):
    home=TEAM_NAMES.get(norm(event.get('hn','')))
    away=TEAM_NAMES.get(norm(event.get('an','')))
    if not home or not away or home==away:
        return [], [], 0, 'Takim adi taninmadi'
    matched={}; missing=set(); seen=0
    for m in event.get('m',[]):
        mk=MARKETS.get(m.get('st'))
        if not mk or m.get('s',1)!=1:continue
        for o in m.get('o',[]):
            parsed=PLAYER_RE.fullmatch(str(o.get('n','')).strip())
            try:odd=float(o.get('odd',0))
            except (TypeError,ValueError):continue
            if not parsed or not 1<odd<1000:continue
            seen+=1
            name,n=parsed.group(1),int(parsed.group(2))
            if n<1:continue
            key=norm(name)
            key=ALIASES.get(key,key)
            possibles=[(pid,team) for pid,team in by_name.get(key,[]) if team in (home,away)]
            if not possibles:
                possibles=[(pid,team) for pid,team in by_name.get('~'+strip_suffix(key),[]) if team in (home,away)]
            if len(possibles)!=1:
                missing.add(name)
                continue
            pid=possibles[0][0]
            ident=(pid,mk,n)
            # Highest advertised odd if an identical selection occurs twice.
            if ident not in matched or odd>matched[ident][3]:
                matched[ident]=(pid,mk,n,odd,int(event['d']))
    return list(matched.values()), sorted(missing), seen, ''

def encode(row):
    pid,mk,n,odd,start=row
    return f'{pid}|{mk}|{n}|{odd:g}|{start}'

def parse_old(row,now):
    try:
        a=row.split('|')
        if len(a)!=5 or a[1] not in MARKETS.values():return None
        v=(int(a[0]),a[1],int(a[2]),float(a[3]),int(a[4]))
        if v[0]>0 and v[2]>0 and 1<v[3]<1000 and v[4]>now:return v
    except (ValueError,TypeError,AttributeError):pass
    return None

def write_atomic(path,doc):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.iddaa-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(doc,f,ensure_ascii=False,indent=2)
            f.write('\n')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.remove(tmp)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data',required=True,help='Site data.json, contains players [id,name,team]')
    ap.add_argument('--output',required=True,help='Site iddaa-lines.json')
    ap.add_argument('--fixture',help='Use a saved single event-detail JSON for OFFLINE test; NEVER writes output')
    ap.add_argument('--max-hours',type=int,default=28)
    args=ap.parse_args()
    data=load_json(args.data)
    by_name=roster_index(data)
    now=int(dt.datetime.now(dt.timezone.utc).timestamp())
    if args.fixture:
        raw=load_json(args.fixture)
        event=raw.get('data',raw)
        rows,unmatched,seen,reason=parse_event(event,by_name)
        print(f'FIXTURE TEST (YAZMA YOK) | {event.get("hn")} - {event.get("an")} | aday={seen} eslesen={len(rows)} eslesmeyen={len(unmatched)}')
        if reason:print('UYARI:',reason)
        for r in rows[:12]:print(' ',encode(r))
        if unmatched:print('ESLESMEYENLER:', ', '.join(unmatched[:30]))
        return 0 if rows else 2
    updated=data.get('updated','')
    try:
        age=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(updated.replace('Z','+00:00'))).total_seconds()
    except (ValueError,TypeError):
        age=1e12
    if age>7*86400:
        print('STOP: data.json kadrosu 7 gunden eski veya tarihsiz; yanlis oyuncu-takim eslesmesini onlemek icin yazilmadi')
        return 3
    events=download(BASE+'events?st=2&type=0&version=0').get('events',[])
    selected=sorted((ev for ev in events if ev.get('ci')==138 and ev.get('s',0)==0 and now<int(ev.get('d',0))<=now+args.max_hours*3600),key=lambda e:e['d'])
    print('BASLAMAMIS NBA MACLARI:',len(selected))
    if not selected:
        print('NO CHANGE: Baslamamis NBA maci yok')
        return 0
    good=[]; bad=[]; unmatched=[]; replaced=set()
    for ev in selected:
        label=f'{ev.get("hn")} - {ev.get("an")}'
        try:
            detail=download(BASE+'event/'+str(ev['i']))
            if detail.get('i')!=ev.get('i') or detail.get('ci')!=138 or int(detail.get('d',-1))!=int(ev['d']):
                raise ValueError('Mac ID/lig/baslama eslesmiyor')
            rows,miss,seen,reason=parse_event(detail,by_name)
            if reason or not rows:raise ValueError(reason or f'Barem eslesmedi (aday={seen})')
            good.extend(rows);replaced.add(int(ev['d']))
            unmatched.extend(f'{label}: {n}' for n in miss)
            print('OK',label,'aday=',seen,'eslesen=',len(rows),'eslesmeyen=',len(miss))
        except Exception as e:
            bad.append(f'{label}: {e}')
            print('SKIP',bad[-1])
    if not good:
        print('NO CHANGE: Dogrulanmis barem yok; eski dosya korundu')
        return 2
    if bad:
        print('UYARI: Bazı maclar okunamadi; sadece dogrulanan maclar yenilenecek, digerlerinin mevcut gelecek satirlari korunacak')
    output=Path(args.output)
    # Same-file update: remove old rows for reread games, never retain started games.
    old=[]
    if output.exists():
        old_doc=load_json(output)
        old=[v for s in old_doc.get('rows',[]) if (v:=parse_old(s,now)) and v[4] not in replaced]
    all_rows={}
    for r in old+good:
        k=(r[0],r[1],r[2],r[4]);
        if k not in all_rows or r[3]>all_rows[k][3]:all_rows[k]=r
    rows=sorted(all_rows.values(),key=lambda r:(r[4],r[0],r[1],r[2]))
    stamp=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    doc={'ts':int(dt.datetime.now(dt.timezone.utc).timestamp()*1000),'updated':stamp,'src':'iddaa-direct-json','games':len(selected),'count':len(rows),'unmatched':len(unmatched),'rows':[encode(r) for r in rows]}
    write_atomic(output,doc)
    print('PUBLISHED',str(output),'rows=',len(rows),'games=',len(selected),'unmatched=',len(unmatched))
    if unmatched:
        report=output.with_name('iddaa-unmatched.txt')
        report.write_text('\n'.join(unmatched)+'\n',encoding='utf-8')
        print('REVIEW',str(report))
        for u in unmatched:print('ESLESMEYEN',u)
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:
        print('ERROR:',str(e),file=sys.stderr);sys.exit(1)
