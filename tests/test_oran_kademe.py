#!/usr/bin/env python3
"""Oran kademesi: yama idempotent, node ile sozdizimi gecerli, sentetik merdivenle Kasa davranisi dogru."""
import json, pathlib, shutil, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import oran_kademe as ok
import karne_returning as kr

SRC = ROOT / 'tests' / 'fixture-model-oran.js'

def main():
    src = SRC.read_text(encoding='utf-8')
    once = ok.patch_model(src)
    assert ok.patch_model(once) == once, 'idempotent degil'
    assert once.count(ok.MARK) == 1
    # karne_returning.patch_text zinciri de ayni yamayi uygular
    chained = kr.patch_site(src, [])
    assert ok.MARK in chained and 'CM-RETURNING-PLAYER-V3' in chained
    assert kr.patch_site(chained, []) == chained, "patch_site tekrar uygulandiginda degisiyor"
    if not shutil.which('node'):
        print('SKIP: node yok, sentetik merdiven testi atlandi (yama ve idempotentlik testleri gecti)');return
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / 'model.js'; f.write_text(once, encoding='utf-8')
        subprocess.run(['node', '--check', str(f)], check=True)
        r = subprocess.run(['node', str(ROOT / 'tests' / 'oran_kademe_harness.js'), str(f)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        res = json.loads(r.stdout.strip().splitlines()[-1])
    # merdiven: en fazla 2.50 oranli normal bahis secilir, 4.0/15 oranlar girmez
    assert len(res['ladder']['pass']) == 1, res['ladder']
    odd = float(res['ladder']['pass'][0].split('|')[2]); assert odd <= 2.5, res['ladder']
    assert res['long']['pass'] == [], res['long']
    assert res['surAgree']['pass'] and res['surAgree']['pass'][0].split('|')[1] == 'surpriz', res['surAgree']
    assert res['surDis']['pass'] == [], res['surDis']
    assert res['surNoMkt']['pass'] == [], res['surNoMkt']
    assert len(res['twoSur']['pass']) == 1, res['twoSur']
    assert len(res['sameP']['pass']) == 1 and res['sameP']['pass'][0].split('|')[1] != 'surpriz', res['sameP']
    print('OK test_oran_kademe', json.dumps(res))

if __name__ == '__main__':
    main()
