#!/usr/bin/env python3
"""Missed-last-game exception: only explicit, fresh, dated, source-backed confirmations."""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

MARK = '/* CM-RETURNING-PLAYER-V3 */'


def records(path):
    path=Path(path)
    if not path.exists():
        return []
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict) or not isinstance(data.get('players'),list):
        raise ValueError('confirmed-active.json players listesi gerektirir')
    out=[]
    now=dt.datetime.now(dt.timezone.utc)
    for r in data['players']:
        if not isinstance(r,dict):
            continue
        try:
            d=dt.date.fromisoformat(r['date']); chk=dt.datetime.fromisoformat(r['checkedAt'].replace('Z','+00:00'))
            if chk.tzinfo is None:continue
            age=(now-chk.astimezone(dt.timezone.utc)).total_seconds()
            # No stale/future records. Explicit primary-source evidence, not 'not listed injured'.
            if not 0<=age<=6*3600:continue
            if not isinstance(r['id'],int) or isinstance(r['id'],bool) or r['id']<=0:continue
            if not isinstance(r['team'],str) or not r['team'] or len(r['team'])>5:continue
            if r.get('status')!='confirmed_active':continue
            if r.get('sourceType') not in ('nba_official','team_official'):continue
            if not isinstance(r.get('sourceUrl'),str) or not r['sourceUrl'].startswith('https://'):continue
            if not isinstance(r.get('evidence'),str) or len(r['evidence'].strip())<10:continue
            out.append({'id':r['id'],'team':r['team'],'date':d.isoformat(),
                        'checkedAt':chk.isoformat(), 'sourceType':r['sourceType']})
        except (KeyError,ValueError,TypeError,OverflowError):continue
    return out


def _patch_returns(source,rows):
    if MARK in source:
        # Rebuild the embedded allow-list at every publish/snapshot; never retain a stale confirmation.
        pattern=r'const CM_CONFIRMED_RETURNS = [^;]*;'
        replacement='const CM_CONFIRMED_RETURNS = '+json.dumps(rows,ensure_ascii=True,separators=(',',':'))+';'
        newer,n=re.subn(pattern,lambda _:replacement,source,count=1)
        if n!=1:raise RuntimeError('V3 listesi mevcut ama okunamadi')
        return newer
    if 'function kasaCand(r,day,now)' not in source or 'function pickScan(day)' not in source:
        raise RuntimeError('model.js beklenen fonksiyonlari bulunamadi, degisiklik yapilmadi')
    first='if(noBet(inj)||missedStreak(p)>=1)continue;'
    second='if(noBet(inj)||missedStreak(p)>=1)return null;'
    start=source.index('function pickScan(day)')
    end=source.index('function pickList(day)',start)
    block=source[start:end]
    if block.count(first)!=1:raise RuntimeError('pickScan uygunluk satiri farkli')
    block=block.replace(first,'if(noBet(inj)||!cmReturnAllowed(p,day))continue;',1)
    source=source[:start]+block+source[end:]
    start=source.index('function kasaCand(r,day,now)')
    end=source.index('function kasaAll(day,now)',start)
    block=source[start:end]
    if block.count(second)!=1:raise RuntimeError('kasaCand uygunluk satiri farkli')
    block=block.replace(second,'if(noBet(inj)||!cmReturnAllowed(p,day))return null;',1)
    source=source[:start]+block+source[end:]
    prefix='''/* CM-RETURNING-PLAYER-V3 */
const CM_CONFIRMED_RETURNS = __RECORDS__;
function cmReturnAllowed(p,day){
  if(missedStreak(p)<1)return true;
  // Takim/oyuncu/gun eslesmesi ve en fazla 6 saatlik resmi dogrulama gerekir.
  // Durumu OUT/Q/D/GTD/DTD ise noBet kontrolu ayrica engeller.
  const now=Date.now();
  return CM_CONFIRMED_RETURNS.some(c=>c.id===p.id && c.team===p.team && c.date===day &&
    now-Date.parse(c.checkedAt)>=0 && now-Date.parse(c.checkedAt)<=6*3600*1000);
}
'''.replace('__RECORDS__',json.dumps(rows,ensure_ascii=True,separators=(',',':')))
    return prefix+'\n'+source

DC_MARK='/* CM-DATACHK-CMREMOTE */'
DC_OLD="if(typeof LIVE!=='undefined'&&(!LIVE||!LIVE.ts||Date.now()-LIVE.ts>6*3600e3))w.push('sakatl\u0131k listesi 6 saatten eski');"
DC_NEW=("if(typeof LIVE!=='undefined'&&!(typeof window!=='undefined'&&window.CMREMOTE&&(window.CMREMOTE.espn||(window.CMREMOTE.list&&Object.keys(window.CMREMOTE.list).length)))"
        "&&(!LIVE||!LIVE.ts||Date.now()-LIVE.ts>6*3600e3))w.push('sakatl\u0131k listesi 6 saatten eski');")

def patch_datachk(source):
    """dataChk sakatlik tazeligini eski LIVE yerine Worker verisine (CMREMOTE) gore olcer.
    CMREMOTE yuklendiyse sahte '6 saatten eski' uyarisi uretmez; yoksa eski kural aynen calisir."""
    if DC_MARK in source:return source
    if 'function dataChk(' not in source:return source
    if DC_OLD not in source:raise RuntimeError('dataChk LIVE satiri farkli, degisiklik yapilmadi')
    return source.replace(DC_OLD,DC_NEW,1).replace('function dataChk(',DC_MARK+'\nfunction dataChk(',1)

def patch_text(source,rows):
    return patch_datachk(_patch_returns(source,rows))

def patch_site(source,rows):
    """patch_text + oran kademesi (oran_kademe.py) + Vitrin V2 (vitrin_v2.py). Site yayini ve headless Karne bunu kullanir."""
    from oran_kademe import patch_model
    from vitrin_v2 import patch_model as vitrin_v2
    return vitrin_v2(patch_model(patch_text(source,rows)))


def patch_file(model,confirmation):
    model=Path(model)
    old=model.read_text(encoding='utf-8')
    updated=patch_site(old,records(confirmation))
    if updated!=old:model.write_text(updated,encoding='utf-8')
    print('RETURN V3:',len(records(confirmation)),'guvenilir aktif kadro dogrulamasi, model yama uygulandi')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--model',default='public/model.js')
    ap.add_argument('--confirmed',default='seed/confirmed-active.json')
    a=ap.parse_args();patch_file(a.model,a.confirmed)
