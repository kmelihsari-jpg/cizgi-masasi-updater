#!/usr/bin/env python3
"""Keep Kasa/history intact; clear future/current ungraded Tribun candidates created by V1."""
import argparse, datetime as dt, json, pathlib, shutil
from zoneinfo import ZoneInfo

def cleanup(path, today=None):
    path=pathlib.Path(path)
    if not path.exists():
        print('SKIP: karne.json dosyasi henuz yok');return False
    today=today or dt.datetime.now(ZoneInfo('Europe/Istanbul')).date().isoformat()
    obj=json.loads(path.read_text(encoding='utf-8-sig'))
    if isinstance(obj,list):
        print('SKIP: beklenmeyen eski format, dokunulmadi');return False
    docs=obj.get('docs')
    if not isinstance(docs,list):
        print('SKIP: docs dizisi yok');return False
    changed=0
    for doc in docs:
        if not isinstance(doc,dict) or doc.get('date','') < today:continue
        shadow=doc.get('shadow') or []
        if not shadow:continue
        # Never change graded shadows or days with graded Kasa entries.
        if any(x is not None for x in (doc.get('searly') or [])) or any(x is not None for x in (doc.get('early') or [])):
            print('KORUNDU: sonuc islenmis gun',doc.get('date'));continue
        old_keys={(str(x.get('id')),x.get('mk')) for x in shadow if isinstance(x,dict)}
        doc['shadow']=[]
        # first is a combined baseline list: remove only matching Tribun entries
        doc['first']=[x for x in (doc.get('first') or []) if not(isinstance(x,dict) and (str(x.get('id')),x.get('mk')) in old_keys
                       and not any(str(y.get('id'))==str(x.get('id')) and y.get('mk')==x.get('mk') for y in (doc.get('picks') or [])))]
        changed+=len(shadow)
        print('TEMIZLENDI:',doc.get('date'),'bekleyen Tribun=',len(shadow),'Kasa korundu=',len(doc.get('picks') or []))
    if not changed:
        print('NO CHANGE: temizlenecek sonuc bekleyen Tribun yok');return False
    backup=path.with_name(path.stem+'-tribun-yedek'+path.suffix)
    if not backup.exists():shutil.copy2(path,backup)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('KAYDEDILDI',path,'temizlenen',changed,'yerel yedek:',backup)
    return True

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--file',default='seed/karne.json');a.add_argument('--date',help='test icin YYYY-MM-DD');args=a.parse_args();cleanup(args.file,args.date)
