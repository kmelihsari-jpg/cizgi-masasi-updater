#!/usr/bin/env python3
"""Cizgi Masasi: mac oncesi immutable Kasa kaydi + istatistikten sonuc.
Snapshot: mevcut yayinlanan JS modelini headless Chromium icinde calistirir.
Settle: yalnizca oynandigi dogrulanmis NBA maclarinin sonucunu hesaplar.
"""
import argparse, datetime as dt, json, os, pathlib, sys, time
from zoneinfo import ZoneInfo

START = '2026-11-15'
VALID = {'PTS','REB','AST','STL','BLK','3PM','SRA','RA'}
TZ=ZoneInfo('Europe/Istanbul')

def load(p, default=None):
    p=pathlib.Path(p)
    return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else default

def dump(p, obj):
    p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(p)

def as_docs(raw):
    if isinstance(raw,dict): return list(raw.get('docs') or [])
    if isinstance(raw,list): return raw
    return []

def valid_pick(p, starts, now):
    try:
        odd=float(p['odd']); n=int(p['n']); line=float(p['line']); pid=int(p['id'])
        game=starts[(p['date'],p['team'],p['opp'])]
        if not(1<odd<100 and n>0 and pid>0 and p['mk'] in VALID and abs(line-(n-.5))<.0001):return False
        return game>now+60
    except (ValueError,TypeError,KeyError): return False

def snapshot(args):
    from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout
    raw=load(args.output, {'docs':[]}); docs=as_docs(raw)
    odds=load(args.odds)
    data=load(args.data)
    if not isinstance(odds,dict) or not isinstance(data,dict):raise RuntimeError('Seed data/odds yok')
    now=time.time();stamp=dt.datetime.now(dt.timezone.utc).isoformat()
    age=(now*1000-int(odds.get('ts',0)))/3600000
    data_age=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(data['updated'].replace('Z','+00:00'))).total_seconds()/3600
    if age<0 or age>6 or data_age<0 or data_age>16:
        print(f'SKIP: veri bayat (iddaa={age:.1f}h, istatistik={data_age:.1f}h)');return False
    if not odds.get('rows'):print('SKIP: iddaa baremi yok');return False
    # Onceki geceyi silemez; ayni gece icin picks ilk kayitla kilitlenir.
    old_by_day={d.get('date'):d for d in docs}
    out=[]
    today_tr=dt.datetime.now(TZ).date().isoformat()
    # Site and headless model must use the exact same confirmed-return safeguards.
    from karne_returning import patch_text, records
    confirmed=records(args.confirmed)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'],**({'executable_path':os.environ['CM_CHROMIUM']} if os.environ.get('CM_CHROMIUM') else {}))
        page=browser.new_page(locale='tr-TR',timezone_id='Europe/Istanbul',service_workers='block')
        page.on('console', lambda m: print('BROWSER',m.type,m.text[:180]) if m.type=='error' else None)
        # Site JS modelini aynen kullan, fakat verileri guncel GitHub seed dosyalarindan ver.
        def intercept(route):
            u=route.request.url.split('?')[0]
            if u.endswith('/model.js'):
                response=route.fetch()
                content=patch_text(response.text(),confirmed)
                return route.fulfill(response=response,body=content)
            if u.endswith('/data.json'):
                return route.fulfill(status=200,body=json.dumps(data),content_type='application/json')
            if u.endswith('/iddaa-lines.json'):
                return route.fulfill(status=200,body=json.dumps(odds),content_type='application/json')
            return route.continue_()
        page.route('**/*',intercept)
        try:
            page.goto(args.site,wait_until='domcontentloaded',timeout=45000)
            page.wait_for_function("typeof D!=='undefined' && D && D.players && typeof pickSplit==='function' && typeof IDDRAW!=='undefined' && IDDRAW && IDDRAW.rows && IDDRAW.rows.length > 0", timeout=45000)
            result=page.evaluate('''() => {
              const now=Date.now(), out=[];
              // Gecenin bitimine kadar: 3 gunluk takvim degil, yalnizca yakin 16 saat.
              const MAX_AHEAD=16*3600*1000;
              function eligible(c,day){
                if(!c || !c.id || !c.team || !c.opp || !c.mk)return false;
                const p=P && P[c.id];
                if(!p || p.team!==c.team || !byP || !byP[p.id])return false;
                if(byP[p.id].length<5 || mpg(p.id)<22 || !cmReturnAllowed(p,day))return false;
                if(noBet(injOf(p.name)))return false;
                const game=slate.find(g=>dayKey(g.ts)===day &&
                  ((g.home===c.team && g.away===c.opp)||(g.away===c.team && g.home===c.opp)));
                return !!game && game.ts>now+60000 && game.ts<=now+MAX_AHEAD;
              }
              for(const day of dayList()) {
                if(day < '2026-11-15')continue;
                const games=slate.filter(g=>dayKey(g.ts)===day && g.ts>now+60000 && g.ts<=now+MAX_AHEAD);
                if(!games.length)continue;
                const doc=tonightDoc(day,null,now);
                if(!doc)continue;
                doc.picks=(doc.picks||[]).filter(c=>eligible(c,day));
                doc.shadow=(doc.shadow||[]).filter(c=>eligible(c,day)).slice(0,15);
                out.push({day,games:games.map(g=>({ts:g.ts,home:g.home,away:g.away})),doc});
              }
              return {out,updated:D.updated,oddsAt:IDDRAW.ts};
            }''')
        except BrowserTimeout as exc:
            raise RuntimeError('Sayfa / model zaman asimi; dokuman yazilmadi') from exc
        finally:browser.close()
    for entry in result['out']:
        day=entry['day'];
        games=entry['games']; starts={}
        for g in games:
            starts[(day,g['home'],g['away'])]=g['ts']/1000
            starts[(day,g['away'],g['home'])]=g['ts']/1000
        doc=entry['doc'];picks=[]
        for p in doc.get('picks',[]):
            p['date']=day
            if valid_pick(p,starts,now):picks.append({k:v for k,v in p.items() if k!='date'})
        # Barem yok / dogrulanamayan secim Kasa'ya giremez.
        # JS tarafindaki oyuncu/sakatlik ve mac filtresinden gecen Tribun adaylari.
        shadow=doc.get('shadow',[])[:15]
        if not picks and not shadow:continue
        previous=old_by_day.get(day)
        if previous:
            # Onceki secimleri/sonuclari degistirme. Sonraki barem okumalarinda
            # sadece yeni acilan oyuncu secimlerini (mac baslamadan) ekle.
            if any(k in previous for k in ('early','earlyAt','searly')):
                print('SETTLED LOCK',day);continue
            keys={int(p['id']) for p in previous.get('picks',[])+previous.get('injPicks',[])}
            added=[dict(p,capturedAt=stamp) for p in picks if int(p['id']) not in keys]
            if added:
                previous.setdefault('picks',[]).extend(added)
                previous.setdefault('first',[]).extend(added)
            sh_keys={(p['id'],p['mk']) for p in previous.get('shadow',[])}
            new_shadow=[p for p in shadow if (p['id'],p['mk']) not in sh_keys]
            room=max(0,15-len(previous.get('shadow',[])))
            if room:previous.setdefault('shadow',[]).extend(new_shadow[:room])
            if added or (room and new_shadow):
                print('APPENDED',day,'newKasa=',len(added),'newTribun=',min(room,len(new_shadow)))
                out.append(day)
            else:print('LOCKED',day,'degisecek yeni aday yok')
            continue
        picks=[dict(p,capturedAt=stamp) for p in picks]
        saved=dict(date=day,saved=stamp,first=picks+shadow,picks=picks,shadow=shadow,injPicks=[],
                   dataUpdated=result['updated'],oddsUpdated=odds.get('updated'),source='github-actions-headless',locked=True)
        docs.append(saved);old_by_day[day]=saved
        print('FROZEN',day,'kasa=',len(picks),'tribun=',len(shadow))
        out.append(day)
    if not out:print('NO CHANGE: yeni gece/kayit yok');return False
    docs=sorted((d for d in docs if d.get('date','')>=START),key=lambda x:x['date'])
    dump(args.output,{'startDate':START,'startBalance':100,'generatedAt':stamp,'docs':docs})
    return True

def settle(args):
    docs=as_docs(load(args.output,{'docs':[]})); data=load(args.data)
    if not data:raise RuntimeError('data bulunamadi')
    col={k:i for i,k in enumerate(data['cols'])};team=data['teams'];dates=data['dates'];bygame={};played={};latest=dates[-1]
    for row in data['rows']:
        date=dates[row[col['d']]];team_name=team[row[col['t']]];opp=team[row[col['o']]]
        played[(date,team_name,opp)]=True
        pid=int(row[col['pid']]);vals={k:row[col[k]] for k in ('pts','reb','ast','stl','blk','fg3m')}
        bygame[(date,pid)]=vals
    def v(vals,mk):
        if mk=='3PM':return vals['fg3m']
        if mk=='SRA':return vals['pts']+vals['reb']+vals['ast']
        if mk=='RA':return vals['reb']+vals['ast']
        return vals[mk.lower()]
    changed=False;resolved=0
    for doc in docs:
        day=doc['date'];
        if day<START:continue
        for key,early in (('picks','early'),('shadow','searly'),('injPicks','iearly')):
            items=doc.get(key,[]);old=doc.get(early,[]);new=[]
            for i,p in enumerate(items):
                val0=old[i] if i<len(old) else None
                if val0 is not None: new.append(val0);continue
                vals=bygame.get((day,int(p['id'])))
                if vals:
                    r=v(vals,p['mk']);new.append(r);resolved+=1
                elif played.get((day,p.get('team'),p.get('opp'))):
                    new.append('dnp');resolved+=1
                else:new.append(None)
            if new!=old:doc[early]=new;changed=True
    if changed:
        dump(args.output,{'startDate':START,'startBalance':100,'generatedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'docs':docs})
    print('SETTLE', 'changed='+str(changed),'resolved='+str(resolved),'statsLatest='+latest)
    return changed

def main():
    a=argparse.ArgumentParser();a.add_argument('mode',choices=['snapshot','settle']);a.add_argument('--data',default='seed/data.json');a.add_argument('--odds',default='seed/iddaa-lines.json');a.add_argument('--output',default='seed/karne.json');a.add_argument('--site',default='https://cizgi-masasi.pages.dev/');a.add_argument('--confirmed',default='seed/confirmed-active.json');args=a.parse_args()
    return snapshot(args) if args.mode=='snapshot' else settle(args)
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERROR',repr(e),file=sys.stderr);sys.exit(1)
