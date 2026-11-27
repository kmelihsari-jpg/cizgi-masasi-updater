#!/usr/bin/env python3
"""Vitrin V2 (27 Kasim 2026): rol degisimi kapisi + Merdiven Alti'ndan 'secim' yolu + market cesitliligi.
model.js'e idempotent yama (karne_returning.patch_site zincirinde, oran_kademe'den SONRA calisir;
site yayini ve headless Karne ayni modeli kullanir).

1) Rol degisimi kapisi (cmRol): son 2 macin dakika ortalamasi 22'nin altindaysa ya da son 3 mac
   ortalamasi sezon ortalamasinin %85'inin altindaysa oyuncu Vitrin'e (Kasa) girmez. Merdiven Alti'nda gorunmeye devam eder.
   (Brook Lopez: Ingram gelince 21.5 ve 18.3 dk, 3 ve 6 sayi; sezon ortalamasi 22+ oldugu icin eski kapi gormuyordu.)
2) 'secim' etiketi: Saglam/Deger kapisini gecemeyen ama oran <= 2.50, ham model olasiligi >= %60,
   %25 iddaa karisimli olasilik >= 1/oran ve en az 1 destek sinyali olan bahis Vitrin'e girebilir
   (Merdiven Alti'nin karnede en iyi calisan kesiti).
3) AST/STL: tum yollarda ham model olasiligi >= %65 gerekir (tamamen yasak degil, daha yuksek esik).
4) Market cesitliligi: Vitrin'de ayni gecede ayni marketten en fazla 2 bahis; fazlasi Merdiven Alti'na
   ('limit' sebebiyle, capMk=true) duser.
5) Donus kapisi (cmDonus, ayri isaret CM-VITRIN-V2-DONUS): ayni takimda sezon ortalamasi >= 25 dk olan bir oyuncu son 2+ takim macini
   kacirmis (missedStreak >= 2) ve durumu OUT/D degilse (AVAILABLE/Q/kayitsiz: bu gece donebilir) takim arkadaslari Vitrin'e girmez:
   son maclardaki dakika/sayi onsuz oynanan maclardan sisiyor, model bunu sadece su an OUT olanlar icin duzeltiyor
   (Grimes: Reaves 5 mac yoktu, bu gece donuyor). Merdiven Alti'nda gorunmeye devam eder.
6) Yildiz OUT on kabulu (CM-VITRIN-V2-PRIOR): 'o yokken' ornegi yoksa (adj.n=0) cikanin o marketteki payi / takimin ilk 8 oyuncusunun payi
   kadar (x0.4, en cok +%12) artis; sakatlik firsati bu durumda n<3 kapisini gecer (EV >= .08 sarti ayni). cmDonusAd: Merdiven Alti uyarisi.
Karne kayit sekli degismez (tag alani 'secim' de alabilir; etiketsiz eski kayitlar 'deger' sayilir).
"""
import argparse
from pathlib import Path

MARK = '/* CM-VITRIN-V2 */'

PREFIX = MARK + '''
const V2={rolMin:22,rolOran:.85,mrdModel:.60,astStl:.65,mkMax:2};
function cmRol(all){const n=all.length;if(n<3)return false;const m=x=>x.min||0,l2=(m(all[n-1])+m(all[n-2]))/2,l3=(m(all[n-1])+m(all[n-2])+m(all[n-3]))/3,s=sum(all,m)/n;return l2<V2.rolMin||l3<s*V2.rolOran}
function cmMrd(raw,p25,odd,sup){return odd<=2.5&&raw>=V2.mrdModel&&p25>=1/odd&&sup.length>=1}
function cmAstStl(mk,raw){return (mk==='AST'||mk==='STL')&&raw<V2.astStl}
function cmCapMk(cc,max){const cnt={},keep=[];for(const c of cc.keep){cnt[c.mk]=(cnt[c.mk]||0)+1;if(cnt[c.mk]<=max)keep.push(c);else{c.capMk=true;cc.cap.push(c)}}return {keep,cap:cc.cap}}
'''

EDITS = [
    ("mpg(p.id)<22)return null;",
     "mpg(p.id)<22||cmRol(all))return null;"),
    ("deg=r.a.tag==='go';let sur=false;",
     "deg=r.a.tag==='go',mrd=cmMrd(raw,p25,odd,sup);if(cmAstStl(mk,raw))return null;let sur=false;"),
    ("}else if(!sag&&!deg)return null;",
     "}else if(!sag&&!deg&&!mrd)return null;"),
    ("const tag=sur?'surpriz':sag?'saglam':'deger',ev=sag?p25*(odd-1)-(1-p25):r.a.ev,",
     "const tag=sur?'surpriz':sag?'saglam':deg?'deger':'secim',ev=sag||!deg?p25*(odd-1)-(1-p25):r.a.ev,"),
    ("const cc=cmCapGame([...best.values()].sort(cmp),CM_MAC_MAX);",
     "let cc=cmCapMk(cmCapGame([...best.values()].sort(cmp),CM_MAC_MAX),V2.mkMax);"),
    ("bu maçta 3 bahis dolu, kâğıt üstüne düştü",
     "${c.capMk?'bu gecenin '+c.mk+' bahis sınırı doldu, Merdiven Altı listesine düştü':'bu maçta 3 bahis dolu, kâğıt üstüne düştü'}"),
]


MARK_D = '/* CM-VITRIN-V2-DONUS */'
DONUS_FN = MARK_D + '''
function cmDonus(p){for(const m of Object.values(P)){if(m.id===p.id||m.team!==p.team)continue;const mg=byP[m.id];if(!mg||mg.length<8||mpg(m.id)<25)continue;const i=injOf(m.name);if(i&&(i[0]==='OUT'||i[0]==='D'))continue;if(missedStreak(m)>=2)return true}return false}
'''
DONUS_OLD = "mpg(p.id)<22||cmRol(all))return null;"
DONUS_NEW = "mpg(p.id)<22||cmRol(all)||cmDonus(p))return null;"


def _patch_donus(source):
    if MARK_D in source:
        return source
    if MARK not in source or source.count(DONUS_OLD) != 1:
        raise RuntimeError('Vitrin V2 donus kapisi: beklenen kod tam 1 kez bulunamadi')
    source = source.replace(DONUS_OLD, DONUS_NEW, 1)
    return source.replace('function kasaCand(r,day,now)', DONUS_FN + 'function kasaCand(r,day,now)', 1)


MARK_A = '/* CM-VITRIN-V2-DONUSAD */'
DONUSAD_FN = MARK_A + '''
function cmDonusAd(p){for(const m of Object.values(P)){if(m.id===p.id||m.team!==p.team)continue;const mg=byP[m.id];if(!mg||mg.length<8||mpg(m.id)<25)continue;const i=injOf(m.name);if(i&&(i[0]==='OUT'||i[0]==='D'))continue;if(missedStreak(m)>=2)return m.name}return null}
'''


def _patch_donusad(source):
    """Merdiven Alti kartinda 'X donuyor' uyarisi icin donen oyuncunun adini veren yardimci (cmDonus ile ayni kural)."""
    if MARK_A in source:
        return source
    if source.count('function cmDonus(p){') != 1:
        raise RuntimeError('Vitrin V2 donus adi: cmDonus bulunamadi')
    return source.replace('function cmDonus(p){', DONUSAD_FN + 'function cmDonus(p){', 1)


MARK_P = '/* CM-VITRIN-V2-PRIOR */'
PRIOR_FN = MARK_P + '''
function cmPrior(m,mk){const tm=Object.values(P).filter(q=>q.team===m.team&&q.id!==m.id&&byP[q.id]&&byP[q.id].length>=5).sort((a,b)=>mpg(b.id)-mpg(a.id)).slice(0,8);const av=q=>{const g=byP[q.id]||[];return g.length?sum(g,x=>val(x,mk))/g.length:0};const O=av(m),R=sum(tm,av);return O>0&&R>0?Math.min(1.12,1+.4*O/R):1}
function cmAdjE(e,p,mk){e=adjE(e,p,mk);const a=e.adj;if(a&&a.n===0&&a.outs&&a.outs.length){let f=1;for(const m of a.outs)f*=Math.max(1+.07*Math.min(mpg(m.id),36)/30,cmPrior(m,mk));f=Math.max(.85,Math.min(1.3,f));if(f>a.f+.005){e.mu*=f/a.f;e.adj=Object.assign({},a,{f,pr:true})}}return e}
'''
PRIOR_EDITS = [
    ("adjE(e,P[S.pid],mk)", "cmAdjE(e,P[S.pid],mk)"),
    ("const e=adjE(expect(all,sample,mk,{opp,pos,dvp:DVP,avgs:AVG,lgConv}),p,mk);const pr=lineProbs(",
     "const e=cmAdjE(expect(all,sample,mk,{opp,pos,dvp:DVP,avgs:AVG,lgConv}),p,mk);const pr=lineProbs("),
    ("r.adj.f<1.05||r.adj.n<3)continue;", "r.adj.f<1.05||(r.adj.n<3&&!r.adj.pr))continue;"),
]


def _patch_prior(source):
    """Yildiz OUT ve 'o yokken' ornegi yok (n=0): eski sabit ~%7 yerine, cikanin o marketteki payina gore
    sinirli (en cok %12) on kabul. Ornek varsa (n>0) eski hesap aynen kalir. Sakatlik firsati n<3 kapisini
    sadece bu on kabul icin (pr) gevsetir; EV kapisi (>= .08) ayni."""
    if MARK_P in source:
        return source
    for old, _new in PRIOR_EDITS:
        if source.count(old) != 1:
            raise RuntimeError('Vitrin V2 on kabul: beklenen kod tam 1 kez bulunamadi: ' + old[:70])
    for old, new in PRIOR_EDITS:
        source = source.replace(old, new, 1)
    return source.replace('function scanRows(){', PRIOR_FN + 'function scanRows(){', 1)


def patch_model(source):
    return _patch_prior(_patch_donusad(_patch_donus(_patch_v2(source))))


def _patch_v2(source):
    if MARK in source:
        return source
    if 'function kasaCand(r,day,now)' not in source or 'CM-ORAN-KADEME-V1' not in source or 'CM-SAGLAM-MERDIVEN-V1' not in source:
        raise RuntimeError('Vitrin V2: model.js oran kademesi/merdiven yamalarindan once uygulanamaz')
    for old, _new in EDITS:
        if source.count(old) != 1:
            raise RuntimeError('Vitrin V2: beklenen kod tam 1 kez bulunamadi: ' + old[:70])
    for old, new in EDITS:
        source = source.replace(old, new, 1)
    return source.replace('function kasaCand(r,day,now)', PREFIX + 'function kasaCand(r,day,now)', 1)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='public/model.js')
    a = ap.parse_args()
    p = Path(a.model)
    old = p.read_text(encoding='utf-8')
    new = patch_model(old)
    if new != old:
        p.write_text(new, encoding='utf-8')
    print('VITRIN V2: uygulandi' if new != old else 'VITRIN V2: zaten uygulanmis')
