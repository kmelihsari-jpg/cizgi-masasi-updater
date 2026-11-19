#!/usr/bin/env python3
"""Merge verified local NBA tracking cache export into seed/data.json.
Never turns missing metrics into zero; refuses malformed or unrelated data.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

FIELDS = ('pot', 'rc', 'rcon', 'runc', 'rdef')
MKT_KEYS = ('PTS', 'REB', 'AST', '3PM')

def merge_mkt(data, report):
    """Piyasa (DK/FD) baremlerini data['mkt'] olarak yazar. Yalniz daha yeni mktAt kabul edilir.
    Gecersiz yapi hata verir; mkt yoksa hicbir sey degismez. True = degisti."""
    mkt = report.get('mkt'); at = report.get('mktAt')
    if mkt is None and at is None: return False
    if not isinstance(mkt, dict) or not isinstance(at, str): raise ValueError('Bad mkt payload')
    dt.datetime.strptime(at, '%Y-%m-%dT%H:%M:%SZ')
    clean = {}
    for pid, mks in mkt.items():
        if not str(pid).isdigit() or not isinstance(mks, dict): raise ValueError('Bad mkt player: ' + str(pid))
        row = {}
        for mk, v in mks.items():
            if mk not in MKT_KEYS: continue
            ok = (isinstance(v, list) and len(v) == 4 and v[3] in ('draftkings', 'fanduel')
                  and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v[:2])
                  and 0 <= v[0] <= 200 and 1.0 < v[1] < 50
                  and (v[2] is None or (isinstance(v[2], (int, float)) and 1.0 < v[2] < 50)))
            if not ok: raise ValueError('Bad mkt entry: %s %s %r' % (pid, mk, v))
            row[mk] = v
        if row: clean[str(pid)] = row
    if not clean: return False
    old = data.get('mktAt')
    if isinstance(old, str) and old >= at and data.get('mkt') == clean: return False
    if isinstance(old, str) and old > at: return False
    data['mkt'] = clean; data['mktAt'] = at
    return True

def merge(data, report):
    assert isinstance(data, dict) and isinstance(data.get('rows'), list)
    assert report.get('source') == 'local-nba-tracking-cache-v1'
    ci = {k:i for i,k in enumerate(data['cols'])}
    for col in ('pid','d','t',*FIELDS):
        if col not in ci: raise ValueError('Missing site column: ' + col)
    dates=data['dates']; idx={}
    for row in data['rows']:
        k=(str(row[ci['pid']]), dates[row[ci['d']]])
        # An NBA player cannot play two different teams on the same day in this dataset.
        if k in idx: raise ValueError('Duplicate player-date row: '+str(k))
        idx[k]=row
    changed=0; matched=0; unseen=[]; imported=0
    for item in report.get('records',[]):
        if not isinstance(item,dict): raise ValueError('Bad record type')
        date=item.get('date'); pid=str(item.get('pid',''))
        dt.date.fromisoformat(date)
        k=(pid,date)
        valid={}
        for field in FIELDS:
            value=item.get(field)
            if value is None: continue
            if isinstance(value,bool) or not isinstance(value,(int,float)) or value<0 or value>150:
                raise ValueError(f'Invalid {field} for {k}: {value!r}')
            valid[field]=value
        if not valid:continue
        imported+=1
        row=idx.get(k)
        if row is None:
            unseen.append(k);continue
        matched+=1
        touched=False
        for field,value in valid.items():
            old=row[ci[field]]
            # New confirmed result supersedes earlier result; null never overwrites.
            if old != value:
                row[ci[field]]=value;touched=True
        if touched:changed+=1
    mkt_changed = merge_mkt(data, report)
    return {'mkt_changed':mkt_changed,'source_records_with_metrics':imported,'matched_records':matched,
            'changed_player_games':changed,'not_found_in_boxscore':len(unseen),
            'unmatched_examples':unseen[:10]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',default='seed/data.json')
    p.add_argument('--tracking',default='seed/tracking-local.json')
    p.add_argument('--dry-run',action='store_true')
    args=p.parse_args()
    path=Path(args.data);inputpath=Path(args.tracking)
    data=json.loads(path.read_text(encoding='utf-8'))
    report=json.loads(inputpath.read_text(encoding='utf-8'))
    result=merge(data,report)
    print(json.dumps(result,ensure_ascii=False))
    if result['source_records_with_metrics'] and not result['matched_records']:
        raise SystemExit('No player/date match: refusing to publish')
    if (result['changed_player_games'] or result['mkt_changed']) and not args.dry_run:
        data['updated']=dt.datetime.now(dt.timezone.utc).isoformat()
        path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
        print('SAVED',path)
if __name__=='__main__':main()
