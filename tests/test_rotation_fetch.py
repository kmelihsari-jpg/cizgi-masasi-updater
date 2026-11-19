"""rotation_fetch.py: hesap 11 Kasim JS'iyle ayni mi, form/POST akisi dogru mu."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import rotation_fetch as R  # noqa: E402

PAGE = '''<form method="post" action="./rotation-trends" id="form1">
<input type="hidden" name="__EVENTTARGET" id="__EVENTTARGET" value="" />
<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="VS123" />
<input type="hidden" name="__EVENTVALIDATION" value="EV9" />
<select name="ctl00$ContentPlaceHolder1$DDSEASON"><option selected="selected" value="2627">2026-27</option><option value="2526">2025-26</option></select>
<select name="ctl00$ContentPlaceHolder1$DDTEAM">{opts}</select>
<script type="application/json" id="rt-data">{data}</script></form>'''
CODES = ['ATL', 'BOS', 'GS', 'NO', 'NY', 'PHO', 'SA'] + [f'T{i:02d}' for i in range(23)]


def team_json(code):
    return {'season': '2627', 'team': code,
            'games': [{'n': 1, 'date': '2026-11-18'}, {'n': 2, 'date': '2026-11-19'}],
            'players': [{'name': 'A ' + code}, {'name': 'B'}],
            'stints': [[0, 0, 0, 720, 1, 1], [1, 0, 720, 1440, 2, 0], [0, 1, 0, 2880, 4, 1]]}


def page(code):
    sel = ' selected="selected"'
    opts = ''.join(f'<option{sel if c == code else ""} value="{c}">{c}</option>' for c in CODES)
    return PAGE.format(opts=opts, data=json.dumps(team_json(code)))


class Hesap(unittest.TestCase):
    def test_js_ile_ayni(self):
        for case in json.loads((ROOT / 'tests' / 'fixture-rotation.json').read_text()):
            self.assertEqual(json.loads(json.dumps(R.compute(case['j']))), case['expected'])

    def test_js_yuvarlama(self):
        self.assertEqual(R.jround(2.5), 3)
        self.assertEqual(R.fix1(0.25), 0.3)
        self.assertEqual(R.fix1(26.0), 26)

    def test_uzatma_q4_negatif_degil(self):
        j = {'games': [{'n': 1, 'date': 'x'}], 'players': [{'name': 'A'}],
             'stints': [[0, 0, 3000, 3100, 5, 0]]}
        self.assertEqual(R.compute(j)['p'][0]['q4'], 0)


class Akis(unittest.TestCase):
    def test_form_ve_post(self):
        posts = []

        def fake(opener, data=None, tries=3):
            if data is None:
                return page('ATL')
            import urllib.parse
            f = dict(urllib.parse.parse_qsl(data.decode()))
            posts.append(f)
            self.assertEqual(f['__VIEWSTATE'], 'VS123')
            self.assertEqual(f['__EVENTTARGET'], R.TEAM_FIELD)
            self.assertEqual(f['ctl00$ContentPlaceHolder1$DDSEASON'], '2627')
            if f[R.TEAM_FIELD] == 'NY':
                raise RuntimeError('boom')
            return page(f[R.TEAM_FIELD])

        import tempfile
        old_fetch, old_argv = R.fetch, sys.argv
        with tempfile.TemporaryDirectory() as d:
            prev = Path(d) / 'prev.json'
            prev.write_text(json.dumps({'t': {'NYK': {'g': 1, 'd': '2026-11-01', 'p': []}}}))
            out = Path(d) / 'rot.json'
            R.fetch = fake
            sys.argv = ['x', '--out', str(out), '--prev', str(prev), '--delay', '0']
            try:
                R.main()
            finally:
                R.fetch, sys.argv = old_fetch, old_argv
            doc = json.loads(out.read_text())
        self.assertEqual(len(posts), len(CODES) - 1)  # ATL ilk sayfadan
        self.assertEqual(len(doc['t']), 30)
        for c in ('GSW', 'NOP', 'NYK', 'PHX', 'SAS'):
            self.assertIn(c, doc['t'])
        self.assertEqual(doc['t']['NYK']['d'], '2026-11-01')  # eski kayit korundu
        self.assertEqual(doc['season'], '2026-27')
        self.assertEqual(doc['updated'], '2026-11-19')
        self.assertEqual(set(doc['t']['ATL']['p'][0]), {'n', 'gp', 'st', 'mn', 'b', 'q4', 'fe', 'fn', 'l5', 'lg'})


if __name__ == '__main__':
    unittest.main()
