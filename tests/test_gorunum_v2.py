#!/usr/bin/env python3
"""gorunum-v2 (19 Kasım) testleri: index.html bloğu, yayın workflow'unun aradığı işaretler, JS sözdizimi, küçük mantık."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import gorunum_v2_kur as kur  # noqa: E402

SP = ROOT / 'site-patches'
NODE = shutil.which('node')


def node(code):
    return subprocess.run([NODE, '-e', code], capture_output=True, text=True, check=True).stdout


def syntax(path):
    if NODE:
        node("new Function(require('fs').readFileSync(%s,'utf8'))" % json.dumps(str(path)))


# 1) index.html: blok eslesme-yokken bloğundan sonra, </body>'den önce, tek kez; tekrar kurulum değiştirmez
html = (SP / 'index.html').read_text(encoding='utf-8')
assert html.count(kur.START) == 1 and html.count(kur.END) == 1
assert html.index('<!--CM_ESLESME_YOKKEN_V1_BITIR-->') < html.index(kur.START) < html.rindex('</body>')
js = (SP / 'gorunum-v2.js').read_text(encoding='utf-8')
css = (SP / 'gorunum-v2.css').read_text(encoding='utf-8')
assert kur.install(html, js, css) == html, 'index.html bloğu güncel değil: python scripts/gorunum_v2_kur.py'
# yayın workflow'unun index.html / canli-sakatlik / gorunum-ana için aradığı işaretler
for need in ('id="nba-inj-check"', 'id="inj-up"', 'baslat.js', 'canli-sakatlik.js', 'gorunum-ana.js?v=20261119b', 'canli-sakatlik.js?v=20261120a'):
    assert need in html, need
panel = (SP / 'canli-sakatlik.js').read_text(encoding='utf-8')
assert 'ESPN_REFRESH_API' in panel and "refresh(true, 'espn')" in panel
home = (SP / 'gorunum-ana.js').read_text(encoding='utf-8')
assert 'Underdog baglantisi kapali' in home
for f in ('function cmGameCard(', 'function cmKuHtml(', 'function cmObBest(', "class=\"ob-card\""):
    assert f in home, f
assert 'model ${MK[r.bm].label}' not in home, 'eski "model PTS x1.30" satırı kalmamalı'
# 13 Kasım hatası: NBA resmi kaynak varken eski INJ.date gösterilmez
assert "st.textContent=window.CMREMOTE?" in home
assert "createElement('details')" in panel and 'cmls-short' in panel

# 2) Sözdizimi
for f in ('gorunum-v2.js', 'gorunum-ana.js', 'canli-sakatlik.js'):
    syntax(SP / f)

# 3) Kayıtlara yazma yok: v2 yalnızca görünüm
for bad in ('saveTonight(', 'store.set(\'cm-slip', 'IDB.', 'karne.json', 'fetch('):
    assert bad not in js, 'gorunum-v2 kayıt/ağ işlemi içermemeli: ' + bad

# 4) Küçük mantık: OUT kartında en çok artan istatistik seçimi
if NODE:
    fn = home[home.index('function cmObBest('):]
    fn = fn[:fn.index('\n')]
    out = json.loads(node(fn + ";console.log(JSON.stringify([cmObBest({dp:10.5,dr:1.4,da:2}),cmObBest({dp:1,dr:1.8,da:0.2}),cmObBest({dp:-1,dr:0,da:0})]))"))
    assert out[0] == {'mk': 'PTS', 'v': 10.5}, out
    assert out[1] == {'mk': 'REB', 'v': 1.8}, out
    assert out[2] is None, out

print('PASS: gorunum-v2 (blok, workflow isaretleri, sozdizimi, yazma yok, OUT karti)')
