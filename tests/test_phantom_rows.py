"""Hayalet (oynamayan oyuncu) satirlari icin regresyon testi. Ag yok, dosya yazmaz.

Sorun: NBA CDN box score'unda "played"/"starter" bayraklari "0"/"1" METNI gelir.
Python'da bool("0") True oldugu icin oynamayan (INACTIVE) oyunculara 0 dakikayla ilk 5
satiri yazildi. Sayfa "X yokken" filtresini "o gun X'in satiri var mi" kuralina gore
hesapladigindan X'in oynamadigi maclar filtreden dusuyordu
(ornek: Jared McCain / Ajay Mitchell, 13 Kasim 2026 @LAC).
"""
import copy
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from nba_cdn_source import flag, normalize_boxscore, played_in_game  # noqa: E402
from update_nba_cdn import merge  # noqa: E402
from clean_phantom_rows import clean, is_phantom  # noqa: E402

COLS = ['pid', 'd', 't', 'o', 'home', 'win', 'min', 'pts', 'reb', 'ast', 'stl', 'blk', 'fg3m', 'fg3a',
        'tov', 'start', 'pot', 'rc', 'margin', 'rcon', 'runc', 'rdef', 'fga', 'fta', 'oreb']


def stats(minutes='PT20M30.00S'):
    return {'points': 10, 'assists': 2, 'reboundsTotal': 4, 'reboundsOffensive': 1, 'reboundsDefensive': 3,
            'threePointersMade': 1, 'threePointersAttempted': 2, 'fieldGoalsMade': 4, 'fieldGoalsAttempted': 7,
            'freeThrowsMade': 2, 'freeThrowsAttempted': 3, 'steals': 1, 'blocks': 0, 'turnovers': 1,
            'minutes': minutes}


def cdn_player(pid, played='1', starter='0', minutes='PT20M30.00S', **extra):
    # Gercek CDN gibi: bayraklar METIN.
    p = {'personId': pid, 'name': f'Player {pid}', 'played': played, 'starter': starter,
         'statistics': stats(minutes)}
    p.update(extra)
    return p


def cdn_raw(home_players, away_players, gid='0022600200'):
    return {'game': {'gameId': gid, 'gameStatus': 3,
                     'homeTeam': {'teamTricode': 'CHI', 'score': 100, 'players': home_players},
                     'awayTeam': {'teamTricode': 'MIN', 'score': 90, 'players': away_players}}}


def starters(base, n=5):
    return [cdn_player(base + i, starter='1' if i < n else '0') for i in range(8)]


class FlagTest(unittest.TestCase):
    def test_string_flags(self):
        for v in ('1', 'true', 'True', 1, True, 'Y'):
            self.assertTrue(flag(v), v)
        for v in ('0', '', 'false', 0, False, None, 'INACTIVE'):
            self.assertFalse(flag(v), v)

    def test_played_in_game(self):
        self.assertTrue(played_in_game({'played': '1'}))
        self.assertFalse(played_in_game({'played': '0'}))
        self.assertFalse(played_in_game({'played': '1', 'status': 'INACTIVE'}))
        self.assertFalse(played_in_game({'played': '1', 'notPlayingReason': 'INACTIVE_INJURY'}))


class NormalizeTest(unittest.TestCase):
    def test_inactive_players_never_become_rows(self):
        home = starters(100) + [cdn_player(900, played='0', starter='1', minutes='PT00M00.00S',
                                           status='INACTIVE', notPlayingReason='INACTIVE_INJURY'),
                                cdn_player(901, played='0', starter='0', minutes='PT00M00.00S', status='INACTIVE')]
        away = starters(200)
        out = normalize_boxscore(cdn_raw(home, away))
        ids = {p['nba_player_id'] for p in out['players']}
        self.assertNotIn('900', ids)
        self.assertNotIn('901', ids)
        self.assertEqual(len(ids), 16)
        self.assertFalse(any(p['minutes'] in ('PT00M00.00S',) for p in out['players']))

    def test_starter_string_flag(self):
        out = normalize_boxscore(cdn_raw(starters(100), starters(200)))
        for team in ('CHI', 'MIN'):
            self.assertEqual(sum(p['starter'] for p in out['players'] if p['team'] == team), 5)


class MergeTest(unittest.TestCase):
    seed = {'season': '2026-27', 'cols': COLS, 'dates': ['2026-11-11'], 'teams': ['CHI', 'MIN'],
            'players': [[10, 'Old Player', 'CHI', 'G']],
            'rows': [[10, 0, 0, 1, 1, 1, 31, 15, 3, 4, 1, 0, 1, 3, 2, 1, 9, 12, 5, 7, 8, 3, 9, 4, 2]]}

    def game(self, extra_home=()):
        home = [{'nba_player_id': str(100 + i), 'name': f'P{100+i}', 'team': 'CHI', 'opponent': 'MIN', 'home': True,
                 'starter': i < 5, 'minutes': 'PT20M30.00S', 'pts': 10, 'ast': 2, 'reb': 4, 'oreb': 1, 'stl': 1,
                 'blk': 0, 'tov': 1, 'fg3m': 1, 'fg3a': 2, 'fga': 7, 'fta': 3} for i in range(6)]
        away = [dict(h, nba_player_id=str(200 + i), name=f'P{200+i}', team='MIN', opponent='CHI', home=False)
                for i, h in enumerate(home)]
        return {'game_id': '0022600201', 'game_date': '2026-11-12',
                'teams': [{'team': 'CHI', 'score': 100}, {'team': 'MIN', 'score': 90}],
                'players': home + away + list(extra_home)}

    def test_zero_minute_starter_is_skipped_and_not_counted(self):
        ghost = dict(self.game()['players'][0], nba_player_id='999', name='Ghost', minutes='PT00M00.00S', starter=True)
        new, rep = merge(self.seed, [self.game([ghost])])
        self.assertEqual(rep['skipped_inactive'], 1)
        self.assertEqual(rep['new_rows'], 12)
        self.assertNotIn(999, [r[0] for r in new['rows']])
        self.assertFalse(any(is_phantom(r, {n: i for i, n in enumerate(COLS)}) for r in new['rows']))
        again, rep2 = merge(new, [self.game([ghost])])
        self.assertEqual(rep2['new_rows'], 0)
        self.assertEqual(again, new)


class CleanTest(unittest.TestCase):
    def data(self):
        def row(pid, d, m, start, pot=None):
            r = [None] * len(COLS)
            for k, v in dict(pid=pid, d=d, t=0, o=1, home=1, win=1, min=m, pts=0, start=start, pot=pot).items():
                r[COLS.index(k)] = v
            return r
        return {'cols': COLS, 'dates': ['2026-11-11', '2026-11-13'], 'teams': ['OKC', 'LAC'],
                'players': [[1, 'McCain', 'OKC', 'G'], [2, 'Mitchell', 'OKC', 'G'], [3, 'OnlyGhost', 'OKC', 'F']],
                'rows': [row(1, 0, 31, 1), row(1, 1, 31, 1), row(2, 0, 28, 1),
                         row(2, 1, 0.0, 1),          # hayalet: 13 Kasim, Mitchell oynamadi
                         row(3, 1, 0.0, 1),          # hayalet, baska satiri yok
                         row(1, 0, 0, 0, pot=0)]}    # eski ESPN kaydi: <1 dk oynadi, korunur

    def test_removes_only_phantoms(self):
        d = self.data()
        before = copy.deepcopy(d)
        new, rep = clean(d)
        self.assertEqual(d, before)  # girdi degismez
        self.assertEqual(rep['removed'], 2)
        self.assertEqual(rep['zero_min_rows_kept'], 1)
        self.assertEqual([p['id'] for p in rep['players_with_no_rows_left']], [3])
        self.assertEqual(len(new['rows']), 4)
        again, rep2 = clean(new)
        self.assertEqual(rep2['removed'], 0)
        self.assertEqual(again, new)

    def test_mccain_mitchell_shape(self):
        """Mitchell'in satiri yoksa McCain'in o maci 'Mitchell yokken' sayilir (sayfa kurali)."""
        new, _ = clean(self.data())
        ci = {n: i for i, n in enumerate(COLS)}
        have = {new['dates'][r[ci['d']]] for r in new['rows'] if r[ci['pid']] == 2}
        mine = {new['dates'][r[ci['d']]] for r in new['rows'] if r[ci['pid']] == 1}
        self.assertEqual(sorted(mine - have), ['2026-11-13'])


class SeedInvariantTest(unittest.TestCase):
    """Gercek seed/data.json uzerinde (otomatik calisan tum guncellemeler icin kapi)."""

    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((ROOT / 'seed' / 'data.json').read_text(encoding='utf-8'))
        cls.ci = {n: i for i, n in enumerate(cls.d['cols'])}

    def test_no_phantom_rows(self):
        bad = [r for r in self.d['rows'] if is_phantom(r, self.ci)]
        self.assertEqual(len(bad), 0, f'{len(bad)} hayalet satir (min=0 ve start=1) var')

    def test_mccain_without_mitchell_real_data(self):
        ci, d = self.ci, self.d
        pid = {p[1]: p[0] for p in d['players']}
        mc, mi = pid['Jared McCain'], pid['Ajay Mitchell']
        rows = lambda who: {d['dates'][r[ci['d']]]: r for r in d['rows'] if r[ci['pid']] == who}
        a, b = rows(mc), rows(mi)
        absent = sorted(day for day in a if day not in b)
        self.assertEqual(absent, ['2026-11-11', '2026-11-13'])
        for day in absent:
            self.assertEqual(a[day][ci['start']], 1)  # McCain ikisinde de ilk 5

    def test_every_row_with_zero_minutes_has_no_start(self):
        for r in self.d['rows']:
            if r[self.ci['min']] == 0:
                self.assertEqual(r[self.ci['start']], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
