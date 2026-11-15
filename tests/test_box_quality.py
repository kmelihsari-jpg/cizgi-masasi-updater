"""Box score butunlugu testleri: eksik veri != oynamadi. Ag yok, dosya yazmaz."""
import json, pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from box_quality import closure, partial_games, absence_status  # noqa: E402


class ClosureTest(unittest.TestCase):
    def test_regulation_and_overtime(self):
        self.assertTrue(closure([48] * 5)['ok'])
        self.assertTrue(closure([53] * 5 + [0])['ok'])           # 1 uzatma = 265
        self.assertEqual(closure([53] * 5)['overtimes'], 1)

    def test_short_roster_that_closes_is_complete(self):
        # IND 2 Kasim 2026: 6 oyuncu, 241 dk -> tam
        self.assertTrue(closure([42, 40, 35, 45, 38, 41])['ok'])

    def test_missing_players_detected(self):
        cl = closure([42, 35, 45, 38])                           # 160 dk
        self.assertFalse(cl['ok'])
        self.assertGreater(cl['missing_minutes'], 30)

    def test_exact_minutes_tighter_tolerance(self):
        self.assertTrue(closure([40.5, 39.5, 40.0, 40.0, 40.0, 40.0])['ok'])
        self.assertFalse(closure([40.5, 39.5, 40.0, 40.0, 40.0, 36.5])['ok'])


class SeedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((ROOT / 'seed' / 'data.json').read_text(encoding='utf-8'))

    def test_no_partial_team_games(self):
        bad = partial_games(self.d)
        self.assertEqual(bad, {}, f'Eksik box score suphesi: {sorted(bad)}')

    def test_ind_nov2_is_complete_and_absences_verified(self):
        pid = {p[1]: p[0] for p in self.d['players']}
        self.assertEqual(absence_status(self.d, pid['Tyrese Haliburton'], '2026-11-02', 'IND'), 'absent_verified')
        self.assertEqual(absence_status(self.d, pid['Ajay Mitchell'], '2026-11-13', 'OKC'), 'absent_verified')

    def test_partial_game_gives_unknown_not_absent(self):
        d = self.d
        c = {n: i for i, n in enumerate(d['cols'])}
        pid = {p[1]: p[0] for p in d['players']}
        ti, di = d['teams'].index('IND'), d['dates'].index('2026-11-02')
        drop = {pid['Jay Huff'], pid['Braden Smith']}
        d2 = dict(d)
        d2['rows'] = [r for r in d['rows'] if not (r[c['d']] == di and r[c['t']] == ti and r[0] in drop)]
        self.assertEqual(absence_status(d2, pid['Tyrese Haliburton'], '2026-11-02', 'IND'), 'unknown_partial')


if __name__ == '__main__':
    unittest.main(verbosity=2)
