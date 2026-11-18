"""Vitrin 'Oran dusuk ama yine de degerli' kutusu: kural testi (node ile)."""
import json, subprocess, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
js = (root/'site-patches'/'gorunum-ana.js').read_text(encoding='utf-8')
html = (root/'site-patches'/'index.html').read_text(encoding='utf-8')
assert '<div id="h-near" hidden></div>' in html
assert 'const NEAR=cmNear(IT,others)' in js and 'cmRenderNear(NEAR)' in js
i = js.index('const CM_NEAR='); j = js.index('function cmRenderNear')
snippet = js[i:j]
test = r'''
const S={hDay:'d'};const noBet=i=>i&&['Q','GTD','DTD','D'].includes(i[0]);const cmPid=o=>o.c?o.c.p.id:null;
''' + snippet + r'''
const now=Date.now(),g=ts=>({home:'A',away:'B',ts});
const mk=(id,odd,need,model,extra={})=>Object.assign({p:{id,name:'P'+id,team:'A'},g:g(now+3e6),mk:'PTS',il:{odd,n:10},why:'value',need,model},extra);
const others=[mk(1,1.39,1.91,.70),mk(2,1.57,2.00,.72),mk(3,1.57,2.15,.68),mk(4,1.20,2.00,.80),mk(5,1.50,1.60,.50),mk(6,1.57,2.0,.70,{inj:['Q']}),mk(7,1.57,2.0,.70,{g:g(now-1)}),mk(8,1.57,2.0,.70,{why:'nobarem'}),mk(9,1.9,1.7,.8),mk(10,1.57,2.0,.56),mk(11,1.57,2.0,.54)];
const it4=[{c:{p:{id:100}}},{c:{p:{id:101}}},{c:{p:{id:102}}},{c:{p:{id:103}}}];
const r=cmNear(it4,others).map(c=>c.p.id);
const r5=cmNear(it4.concat([{c:{p:{id:104}}}]),others).length;
const rd=cmNear([{c:{p:{id:1}}}],others).map(c=>c.p.id);
console.log(JSON.stringify({r,r5,rd}));
'''
out = subprocess.run(['node','-e',test],capture_output=True,text=True)
assert out.returncode==0, out.stderr
d = json.loads(out.stdout.strip().splitlines()[-1])
assert d['r'] == [2,10,3,1], d   # oran/gereken orana gore sirali; model >= %55; 11 (%54) disarida
assert d['r5'] == 0, d        # vitrin 5 ve ustu -> kutu yok
assert 1 not in d['rd'], d    # vitrinde olan oyuncu kutuya girmez
print('PASS: yakin kutu (5 alti, %30 sinir, model %55, noBet/baslamis/vitrindeki elenir)', d)

# Görsel kart yapısı: oran çubuğu, model ve eksik oran rozetleri, oyuncuya tıklama
k = js.index('function cmRenderNear'); e = js.index('\n', js.index('goPlayer(Number(b.dataset.p),b.dataset.m)}}', k))
render = r'''
const el={hidden:true,innerHTML:'',onclick:null};const $=id=>id==='h-near'?el:null;
const document={getElementById:()=>null,createElement:()=>({}),head:{appendChild:()=>{}}};
const MK={PTS:{label:'PTS'}};const esc=s=>String(s);const fmt=(x,d)=>Number(x).toFixed(d??1);const tm=()=>'03:00';const P={7:{}};let gitti=null;const goPlayer=(a,b)=>{gitti=[a,b]};
''' + js[k:e] + r'''
cmRenderNear([{p:{id:7,name:'Bam Adebayo',team:'MIA'},g:{home:'MIA',ts:0},opp:'MIL',mk:'PTS',il:{n:20,odd:1.57},need:2.0,model:.72}]);
el.onclick({target:{closest:()=>({dataset:{p:'7',m:'PTS'}})}});
cmRenderNear([]);const bos=[el.hidden,el.innerHTML];
console.log(JSON.stringify({gitti,bos}));
'''
html_out = subprocess.run(['node','-e',render.replace("cmRenderNear([]);const bos", "const h=el.innerHTML;console.log(h);cmRenderNear([]);const bos")],capture_output=True,text=True)
assert html_out.returncode==0, html_out.stderr
h, last = html_out.stdout.strip().splitlines()[0], json.loads(html_out.stdout.strip().splitlines()[-1])
for parca in ['class="nb-grid"','class="nr-bet">PTS 20+','width:79%','iddaa <b>1.57</b>','gereken <b>2.00</b>','model %72','0.43 oran eksik','önerilmiş bahis değil','data-p="7"']:
    assert parca in h, parca
assert last['gitti'] == [7,'PTS'] and last['bos'] == [True,''], last
print('PASS: yakin kutu kart gorunumu')
