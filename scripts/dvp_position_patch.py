#!/usr/bin/env python3
"""Add per-browser per-player DVP position overrides to the PUBLISHED player-view JS only."""
from pathlib import Path
import argparse

MARKER = '/* CM_DVP_MANUAL_POSITION_V1 */'
HOOK = r'''
/* CM_DVP_MANUAL_POSITION_V1 */
function cmDvpReadPosition(id){
  const allowed=['PG','SG','SF','PF','C'];
  const fallback=posOf(id);
  try {
    const saved=localStorage.getItem('cm-dvp-user-pos-v1:'+String(id));
    return allowed.includes(saved)?saved:fallback;
  } catch (_e) { return fallback; }
}
function cmDvpWritePosition(id,pos){
  try {
    const key='cm-dvp-user-pos-v1:'+String(id);
    if(pos===null)localStorage.removeItem(key);
    else localStorage.setItem(key,pos);
  } catch (_e) { /* private mode: update this session only */ }
}
const cmDvpOriginalRenderMatchup=renderMatchup;
renderMatchup=function(mk){
  cmDvpOriginalRenderMatchup(mk);
  const host=document.getElementById('matchup');
  if(!host || !S || S.pid==null)return;
  const initial=posOf(S.pid), current=S.pos;
  const items=['PG','SG','SF','PF','C'].map(pos=>
    '<button type="button" class="cm-dvp-choice" data-cm-dvp-pos="'+pos+'" aria-pressed="'+(pos===current)+'">'+pos+'</button>'
  ).join('');
  const isCustom=current!==initial;
  host.insertAdjacentHTML('afterbegin',
    '<section class="cm-dvp-manual" aria-label="DVP pozisyonunu değiştir">'+
      '<div class="cm-dvp-header"><strong>DVP pozisyonu</strong><small>Veride: '+initial+' · Analizde: <b>'+current+'</b></small></div>'+
      '<div class="cm-dvp-controls">'+items+
      '<button type="button" class="cm-dvp-reset" data-cm-dvp-reset="1" '+(!isCustom?'disabled':'')+'>Varsayılana dön</button></div>'+
      '<p class="cm-dvp-tip">Sadece bu tarayıcıdaki oyuncu analizini ve tahminini değiştirir. Ortak Kasa / Karne etkilenmez.</p>'+
    '</section>'
  );
};
document.addEventListener('click',function(evt){
  const target=evt.target;
  if(!(target instanceof Element))return;
  const btn=target.closest('[data-cm-dvp-pos], [data-cm-dvp-reset]');
  if(!btn || !btn.closest('#matchup') || !S || S.pid==null)return;
  const reset=btn.hasAttribute('data-cm-dvp-reset');
  const pos=reset?posOf(S.pid):btn.getAttribute('data-cm-dvp-pos');
  if(!['PG','SG','SF','PF','C'].includes(pos))return;
  cmDvpWritePosition(S.pid,reset?null:pos);
  S.pos=pos;
  renderResults();
});
'''
CSS = r'''
/* CM DVP manual position: visible on phone and desktop */
.cm-dvp-manual{padding:12px;margin:0 0 12px;border:1px solid rgba(245,145,48,.4);border-radius:12px;background:rgba(245,145,48,.06)}
.cm-dvp-header{display:flex;align-items:baseline;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.cm-dvp-header strong{font-size:13px;color:var(--text,#f6f6f6)}
.cm-dvp-header small,.cm-dvp-tip{font-size:11px;color:var(--muted,#aaa)}
.cm-dvp-controls{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.cm-dvp-choice,.cm-dvp-reset{appearance:none;border:1px solid rgba(255,255,255,.24);background:rgba(255,255,255,.05);color:inherit;border-radius:7px;cursor:pointer;min-height:35px;padding:7px 10px;font-size:12px;font-weight:700}
.cm-dvp-choice[aria-pressed="true"]{background:#e78028;border-color:#e78028;color:#141414}
.cm-dvp-reset{margin-left:auto;font-size:11px;font-weight:500}
.cm-dvp-reset:disabled{opacity:.35;cursor:default}
.cm-dvp-tip{margin:9px 0 0;line-height:1.45}
@media(max-width:480px){.cm-dvp-manual{padding:9px;margin-bottom:10px}.cm-dvp-choice{flex:1;min-width:37px;padding:7px 5px}.cm-dvp-reset{margin-left:0;width:100%}}
'''

def patch(site):
    site=Path(site)
    js=site/'gorunum-oyuncu.js'
    html=site/'index.html'
    if not js.is_file() or not html.is_file():
        raise RuntimeError('Yayin dosyalari eksik; degisiklik yapilmadi')
    src=js.read_text(encoding='utf-8')
    page=html.read_text(encoding='utf-8')
    if MARKER not in src:
        needle='S.pos=posOf(id);'
        if src.count(needle)!=1 or 'function renderMatchup(mk)' not in src or 'function renderResults()' not in src:
            raise RuntimeError('Oyuncu JS beklenen yapiyla uyusmuyor; guvenlik nedeniyle yayin durduruldu')
        # Anchor replacement only once, only within player display. Global Kasa model.js untouched.
        src=src.replace(needle,'S.pos=cmDvpReadPosition(id);',1)
        src+='\n'+HOOK
    css_path=site/'cm-dvp-position-v1.css'
    css_path.write_text(CSS,encoding='utf-8')
    if 'cm-dvp-position-v1.css' not in page:
        if '</head>' not in page:
            raise RuntimeError('HTML head kapanisi yok')
        page=page.replace('</head>','<link rel="stylesheet" href="cm-dvp-position-v1.css?v=20261115a">\n</head>',1)
    # Both files are only committed after validation of required anchors.
    js.write_text(src,encoding='utf-8')
    html.write_text(page,encoding='utf-8')
    print('OK: DVP oyuncu bazli pozisyon secimi yayin paketine eklendi; Kasa modeli korunuyor')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--site',default='public')
    patch(ap.parse_args().site)
