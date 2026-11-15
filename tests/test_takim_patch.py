"""Takim 'yokken' yamasi testleri (ag yok, dosya yazmaz)."""
import pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from takim_yokken_patch import patch, MARKER  # noqa: E402

SRC = ("function x(){}\nfunction withoutTable(t,both){for(const m of keys){const mg=1;"
       "const span=mg.map(x=>x.ds).sort(),lo=span[0],hi=span.at(-1);\n  const teamDays=1}}\n"
       "function renderTeam(){}\n")


class PatchTest(unittest.TestCase):
    def test_applies_once_and_is_idempotent(self):
        out = patch(SRC)
        self.assertIn(MARKER, out)
        self.assertIn('teamDS(t)', out)
        self.assertEqual(patch(out), out)
        self.assertEqual(out.count('hi=span.at(-1)'), 0)

    def test_only_touches_without_table(self):
        extra = SRC + "const other=lo=span[0],hi=span.at(-1);"
        self.assertEqual(patch(extra).count('hi=span.at(-1);'), 1)

    def test_fails_closed_when_code_changed(self):
        with self.assertRaises(RuntimeError):
            patch(SRC.replace('hi=span.at(-1)', 'hi=something.else'))
        with self.assertRaises(RuntimeError):
            patch('function nothing(){}')

    def test_current_injury_gap_is_counted(self):
        """Markkanen: 13 takim maci, ilk 8'ini oynadi (arada 10-28 yok) -> yama oncesi 1, sonrasi 5 kacirilan."""
        team = ['10-21', '10-23', '10-25', '10-26', '10-28', '10-31', '11-02', '11-04', '11-06', '11-08', '11-10', '11-11', '11-13']
        played = {'10-21', '10-23', '10-25', '10-26', '10-31', '11-02', '11-04', '11-06'}
        lo, last = min(played), max(played)
        before = [d for d in team if lo <= d <= last and d not in played]
        after = [d for d in team if lo <= d <= max(team) and d not in played]
        self.assertEqual((len(before), len(after)), (1, 5))
        self.assertLess(len(before), 2)   # eski kural: esigin (2) altinda -> tablodan dusuyordu
        self.assertGreaterEqual(len(after), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
