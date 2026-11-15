import tempfile,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from site_update_status import deploy,build
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);site=root/'public';seed=root/'seed';site.mkdir();seed.mkdir()
    (site/'index.html').write_text('<html><head></head><body><section id="cm-v1-vitrin"></section></body></html>',encoding='utf-8')
    (seed/'data.json').write_text(json.dumps({'updated':'2026-11-15T08:35:00Z'}))
    (seed/'iddaa-lines.json').write_text(json.dumps({'ts':1794742200000}))
    patches=Path(__file__).resolve().parents[1]/'site-patches'
    a=deploy(site,seed,patches);b=deploy(site,seed,patches)
    assert len(a['entries'])==6
    assert a['entries'][0]['updated_at']=='2026-11-15T08:35:00Z'
    assert a['entries'][1]['updated_at'] is None
    assert b==a
    assert (site/'index.html').read_text().count('cm-update-status.js')==1
    assert (site/'index.html').read_text().count('cm-update-status.css')==1
    assert (site/'cm-updates.json').exists()
print('PASS: site status JSON, null status, timestamp parsing, idempotent UI injection')
