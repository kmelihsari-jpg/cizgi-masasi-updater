#!/usr/bin/env python3
import json, pathlib, shutil, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import karne_duzelt_20261127 as kd
def main():
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d); k = d / 'karne.json'; a = d / 'arsiv' / 'duzeltmeler.ndjson'
        k.write_text(json.dumps({'startDate': '2026-11-21', 'startBalance': 100, 'generatedAt': 'x', 'docs': [
            {'date': '2026-11-27', 'first': [{'id': 201572, 'mk': 'PTS'}], 'picks': [
                {'id': 201572, 'name': 'Brook Lopez', 'mk': 'PTS', 'line': 10.5, 'odd': 1.55},
                {'id': 1, 'name': 'Diger', 'mk': 'REB', 'line': 5.5, 'odd': 1.6}], 'shadow': []}]}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        assert kd.run(k, a) is True
        doc = json.loads(k.read_text(encoding='utf-8'))['docs'][0]
        assert [p['name'] for p in doc['picks']] == ['Diger'] and doc['first'][0]['id'] == 201572
        rec = [json.loads(l) for l in a.read_text(encoding='utf-8').splitlines()]
        assert len(rec) == 1 and rec[0]['record']['name'] == 'Brook Lopez'
        assert kd.run(k, a) is False and len(a.read_text(encoding='utf-8').splitlines()) == 1   # idempotent, arsive tekrar yazmaz
        # sonuclanmis kayitta durur
        k2 = d / 'k2.json'; k2.write_text(json.dumps({'docs': [{'date': '2026-11-27', 'early': [1], 'picks': [{'id': 201572, 'mk': 'PTS', 'line': 10.5}]}]}), encoding='utf-8')
        try: kd.run(k2, a); raise SystemExit('sonuclanmis kayitta calisti')
        except RuntimeError: pass
    print('PASS: karne duzeltmesi (cikarma, arsiv ekleme, idempotent, sonuclanmis kayitta durur)')
main()
