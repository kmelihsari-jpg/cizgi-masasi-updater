#!/usr/bin/env python3
"""Vitrin + sakatlik + 3 sinir yamasi (yayin sirasinda public/ klasorune uygulanir).

1) model.js : Kasa'da ayni mactan en fazla 3 bahis (fazlasi Kagit ustune 'limit' sebebiyle duser).
2) app.js   : sakatlik bildirim bipi yerine ambulans sireni; sakatlik firsatlari sayfa yenilenince kaybolmasin
               (localStorage 'cm-injopp', 6 saat).
3) index.html: dantel vitrin gorunumu (vitrin-dantel-v1.css) baglantisi.

Her yama isaretli ve tekrar calistirilabilir (idempotent). Beklenen kod bulunamazsa HATA verir, hicbir dosya yazilmaz;
yayin durur ve site bozulmaz.
"""
import argparse
import shutil
import sys
from pathlib import Path

MODEL_MARK = '/* CM-KASA-MAC-3 */'
APP_MARK = '/* CM-VITRIN-SAKATLIK-APP */'
CSS_NAME = 'vitrin-dantel-v1.css'
CSS_TAG = '<link rel="stylesheet" href="vitrin-dantel-v1.css?v=20261118a">'

MODEL_PREFIX = MODEL_MARK + r'''
const CM_MAC_MAX=3;
function cmCapGame(list,max){const cnt={},keep=[],cap=[];for(const c of list){const g=c.g||{},k=(g.home||'')+'@'+(g.away||'')+'@'+(g.ts||'');if((cnt[k]||0)<max){cnt[k]=(cnt[k]||0)+1;keep.push(c)}else cap.push(c)}return {keep,cap}}
'''

MODEL_EDITS = [
    ("return {pass:[...best.values()].sort(cmp),flag:[...flag.values()].sort(cmp)}}",
     "const cc=cmCapGame([...best.values()].sort(cmp),CM_MAC_MAX);return {pass:cc.keep,flag:[...flag.values()].sort(cmp),cap:cc.cap}}"),
    ("function pickSplit(day,now){const ka=kasaAll(day,now),bets=ka.pass,inK=",
     "function pickSplit(day,now){const ka=kasaAll(day,now),bets=ka.pass,capK=new Set((ka.cap||[]).map(c=>c.p.id+'|'+c.mk)),inK="),
    ("if(!c.il)c.why='nobarem';else if(c.a?.tag!=='go'){c.why='value';c.need=needOdds(c)}",
     "if(capK.has(k))c.why='limit';else if(!c.il)c.why='nobarem';else if(c.a?.tag!=='go'){c.why='value';c.need=needOdds(c)}"),
    ("return {bets,others}}",
     "for(const c of (ka.cap||[])){if(!others.some(o=>o.p.id===c.p.id&&o.mk===c.mk))others.push(Object.assign(c,{why:'limit'}))}return {bets,others}}"),
    ("if(c.il&&c.why==='player')return",
     "if(c.il&&c.why==='limit')return `iddaa ${fmt(c.il.odd,2)} · bu maçta 3 bahis dolu, kâğıt üstüne düştü`;if(c.il&&c.why==='player')return"),
]

APP_BEEP_OLD = ("[0,.22,.44].forEach((d,i)=>{const o=ACTX.createOscillator(),g=ACTX.createGain();o.type='sine';"
                "o.frequency.value=i===2?1175:880;g.gain.setValueAtTime(.0001,t+d);g.gain.exponentialRampToValueAtTime(.35,t+d+.02);"
                "g.gain.exponentialRampToValueAtTime(.0001,t+d+.18);o.connect(g);g.connect(ACTX.destination);o.start(t+d);o.stop(t+d+.2)})")
APP_BEEP_NEW = ("[0,.25,.5,.75,1,1.25].forEach((d,i)=>{const o=ACTX.createOscillator(),g=ACTX.createGain();o.type='sawtooth';"
                "o.frequency.value=i%2?880:660;g.gain.setValueAtTime(.0001,t+d);g.gain.exponentialRampToValueAtTime(.1,t+d+.02);"
                "g.gain.exponentialRampToValueAtTime(.0001,t+d+.23);o.connect(g);g.connect(ACTX.destination);o.start(t+d);o.stop(t+d+.25)})")

APP_EDITS = [
    (APP_BEEP_OLD, APP_BEEP_NEW),
    ("INJOPP=[],INJSEEN=",
     "INJOPP=(()=>{try{return(store.get('cm-injopp')||[]).filter(c=>c&&c.gt>Date.now()-6*3600e3)}catch(e){return []}})(),INJSEEN="),
    ("INJOPP=INJOPP.concat(items);if(!IOWN&&!TEST){",
     "INJOPP=INJOPP.concat(items);if(!TEST){try{store.set('cm-injopp',INJOPP.filter(c=>c.gt>Date.now()-6*3600e3).slice(-40))}catch(e){}}if(!IOWN&&!TEST){"),
]


def apply_edits(source, edits, mark, prefix=None):
    """Isaret varsa degistirmez; yoksa her eski metin TAM BIR KEZ bulunmali, aksi halde hata."""
    if mark in source:
        return source
    for old, _new in edits:
        n = source.count(old)
        if n != 1:
            raise RuntimeError(f'Beklenen kod {n} kez bulundu (1 olmali): {old[:70]!r}')
    for old, new in edits:
        source = source.replace(old, new, 1)
    if prefix is not None:
        return prefix + '\n' + source
    return mark + '\n' + source


def patch_model(source):
    return apply_edits(source, MODEL_EDITS, MODEL_MARK, prefix=MODEL_PREFIX)


def patch_app(source):
    return apply_edits(source, APP_EDITS, APP_MARK)


def patch_html(html):
    if CSS_NAME in html:
        return html
    if '</head>' not in html:
        raise RuntimeError('index.html head kapanisi bulunamadi')
    return html.replace('</head>', CSS_TAG + '\n</head>', 1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default='public')
    ap.add_argument('--patches', default='site-patches')
    a = ap.parse_args(argv)
    site, patches = Path(a.site), Path(a.patches)
    files = {n: site / n for n in ('model.js', 'app.js', 'index.html')}
    for n, p in files.items():
        if not p.is_file():
            raise RuntimeError('Site dosyasi yok: ' + n)
    css = patches / CSS_NAME
    if not css.is_file():
        raise RuntimeError('Yama dosyasi yok: ' + CSS_NAME)
    new = {
        'model.js': patch_model(files['model.js'].read_text(encoding='utf-8')),
        'app.js': patch_app(files['app.js'].read_text(encoding='utf-8')),
        'index.html': patch_html(files['index.html'].read_text(encoding='utf-8')),
    }
    for n, text in new.items():  # hepsi dogrulandi; simdi yaz
        files[n].write_text(text, encoding='utf-8')
    shutil.copyfile(css, site / CSS_NAME)
    print('VITRIN/SAKATLIK/3 SINIR YAMASI HAZIR: model.js, app.js, index.html,', CSS_NAME)


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        print('HATA:', exc, file=sys.stderr)
        sys.exit(1)
