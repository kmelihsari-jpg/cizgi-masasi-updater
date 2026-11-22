#!/usr/bin/env python3
"""Oran kademesi (19 Kasim 2026): iddaa merdiveninin uc (15-20 oranli) basamaklari Kasa'yi domine etmesin.
model.js'e idempotent yama (karne_returning.patch_text icinden cagrilir; site ve headless Karne ayni modeli kullanir).
  oran <= 2.50 : mevcut kurallar (saglam / deger) aynen
  2.50 - 5.00  : 'surpriz' etiketi; assess 'go' + getiri >= %12 + DK/FD piyasa teyidi (model, piyasanin ana baremindeki olasiligina +-0.08 yakin) gerekir; gecede en fazla 1
  > 5.00       : Kasa'ya girmez
Saglam bandi 1.40-1.75 (eski 1.50-1.75): ayri isaret CM-SAGLAM-BAND-V1, kademe yamasi uygulanmis modele de eklenir.
Saglam merdiven (22 Kasim 2026, CM-SAGLAM-MERDIVEN-V1): ayni oyuncu+bahiste Saglam basamak varsa en dusuk (en garanti)
Saglam basamak secilir; onun ustundeki Saglam/Deger basamaklar Kasa'ya ayri aday olarak girmez, secilen bahse c.lad
("merdiven dizebilirsin") listesi olarak eklenir. Karne kayit sekli degismez (pickDoc lad'i yazmaz).
"""
import argparse
from pathlib import Path

MARK = '/* CM-ORAN-KADEME-V1 */'
MARK2 = '/* CM-SAGLAM-BAND-V1 */'
SAG_OLD = 'const SAG={lo:1.5,hi:1.75,'
SAG_NEW = 'const SAG={lo:1.4,hi:1.75,'

CONST = MARK + '''
const ORAN={hi1:2.5,hi2:5,ev:.12,agree:.08,maxSur:1};
function cmMktAgree(p,mk,r){const ml=mktLine(p.id,mk);if(!ml||!ml.o)return false;const a=1/ml.o,b=ml.u?1/ml.u:null,pi=b?a/(a+b):a/1.05;const m=lineProbs(r.mu,Math.max(1.02,MK[mk].phi),ml.line).over;return Math.abs(m-pi)<=ORAN.agree}
'''

OLD1 = "deg=r.a.tag==='go';if(!sag&&!deg)return null;"
NEW1 = ("deg=r.a.tag==='go';let sur=false;if(odd>ORAN.hi2)return null;"
        "if(odd>ORAN.hi1){if(!deg||!(r.a.ev>=ORAN.ev)||!cmMktAgree(p,mk,r))return null;sur=true}else if(!sag&&!deg)return null;")
OLD2 = "const tag=sag?'saglam':'deger',"
NEW2 = "const tag=sur?'surpriz':sag?'saglam':'deger',"
OLD3 = "const m=c.chk.length?flag:best,o=m.get(c.p.id);if(!o||cmp(c,o)<0)m.set(c.p.id,c)}"
NEW3 = ("if(c.tag==='surpriz'){if(!c.chk.length){const so=sur.get(c.p.id);if(!so||cmp(c,so)<0)sur.set(c.p.id,c)}continue}"
        "const m=c.chk.length?flag:best,o=m.get(c.p.id);if(!o||cmp(c,o)<0)m.set(c.p.id,c)}")
OLD4 = "const cmp=(x,y)=>y.ev-x.ev||y.sup.length-x.sup.length||x.p.id-y.p.id||(x.mk<y.mk?-1:x.mk>y.mk?1:0)||x.line-y.line,best=new Map(),flag=new Map();"
NEW4 = OLD4[:-1] + ",sur=new Map();"
OLD5 = "const cc=cmCapGame([...best.values()].sort(cmp),CM_MAC_MAX);return {pass:cc.keep,"
NEW5 = ("const cc=cmCapGame([...best.values()].sort(cmp),CM_MAC_MAX);"
        "for(const sc of [...sur.values()].filter(c=>!best.has(c.p.id)&&!flag.has(c.p.id)).sort(cmp).slice(0,ORAN.maxSur)){const g=sc.g||{},k=(g.home||'')+'@'+(g.away||'')+'@'+(g.ts||'');"
        "if(cc.keep.filter(c=>{const h=c.g||{};return (h.home||'')+'@'+(h.away||'')+'@'+(h.ts||'')===k}).length<CM_MAC_MAX)cc.keep.push(sc);else cc.cap.push(sc)}"
        "return {pass:cc.keep,")


def _patch_kademe(source):
    if MARK in source:
        return source
    if 'function kasaCand(r,day,now)' not in source or 'function kasaAll(day,now)' not in source:
        raise RuntimeError('model.js beklenen fonksiyonlari bulunamadi, oran kademesi uygulanmadi')
    for old in (OLD1, OLD2, OLD3, OLD4, OLD5):
        if source.count(old) != 1:
            raise RuntimeError('oran kademesi: beklenen kod tam 1 kez bulunamadi: ' + old[:60])
    source = (source.replace(OLD1, NEW1, 1).replace(OLD2, NEW2, 1).replace(OLD3, NEW3, 1)
              .replace(OLD4, NEW4, 1).replace(OLD5, NEW5, 1))
    return source.replace('function kasaCand(r,day,now)', CONST + 'function kasaCand(r,day,now)', 1)


def _patch_saglam(source):
    if MARK2 in source:
        return source
    if source.count(SAG_OLD) != 1:
        raise RuntimeError('saglam bandi: const SAG satiri tam 1 kez bulunamadi, degisiklik yapilmadi')
    return source.replace(SAG_OLD, MARK2 + '\n' + SAG_NEW, 1)


MARK3 = '/* CM-SAGLAM-MERDIVEN-V1 */'
MER_FN = MARK3 + '''
function cmSagMerdiven(cs){const grp=new Map(),out=[];for(const c of cs){const k=c.p.id+'|'+c.mk;if(!grp.has(k))grp.set(k,[]);grp.get(k).push(c)}
  for(const g of grp.values()){const sg=g.filter(c=>c.tag==='saglam'&&!c.chk.length).sort((x,y)=>x.line-y.line||y.il.odd-x.il.odd);if(!sg.length){out.push(...g);continue}
    const safe=sg[0],lad=[];for(const c of g){if(c===safe)continue;if(c.line>safe.line&&!c.chk.length){lad.push(c);continue}out.push(c)}
    safe.lad=lad.sort((x,y)=>x.line-y.line).map(c=>({n:c.il.n,line:c.line,odd:c.il.odd,tag:c.tag,model:c.pr.over}));out.push(safe)}
  return out}
'''
OLD_M1 = "for(const r of scanRows()){const c=kasaCand(r,day,now);if(!c)continue;if(c.tag==='surpriz')"
NEW_M1 = "const cs=[];for(const r of scanRows()){const c=kasaCand(r,day,now);if(!c)continue;if(c.tag==='surpriz')"
OLD_M2 = "continue}const m=c.chk.length?flag:best,o=m.get(c.p.id);if(!o||cmp(c,o)<0)m.set(c.p.id,c)}"
NEW_M2 = "continue}cs.push(c)}for(const c of cmSagMerdiven(cs)){const m=c.chk.length?flag:best,o=m.get(c.p.id);if(!o||cmp(c,o)<0)m.set(c.p.id,c)}"


def _patch_merdiven(source):
    if MARK3 in source:
        return source
    for old in (OLD_M1, OLD_M2, 'function kasaAll(day,now)'):
        if source.count(old) != 1:
            raise RuntimeError('saglam merdiven: beklenen kod tam 1 kez bulunamadi: ' + old[:60])
    source = source.replace(OLD_M1, NEW_M1, 1).replace(OLD_M2, NEW_M2, 1)
    return source.replace('function kasaAll(day,now)', MER_FN + 'function kasaAll(day,now)', 1)


def patch_model(source):
    return _patch_merdiven(_patch_saglam(_patch_kademe(source)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='public/model.js')
    a = ap.parse_args()
    p = Path(a.model)
    old = p.read_text(encoding='utf-8')
    new = patch_model(old)
    if new != old:
        p.write_text(new, encoding='utf-8')
    print('ORAN KADEME V1 + SAGLAM 1.40-1.75 + MERDIVEN: uygulandi' if new != old else 'ORAN KADEME V1 + SAGLAM 1.40-1.75 + MERDIVEN: zaten uygulanmis')
