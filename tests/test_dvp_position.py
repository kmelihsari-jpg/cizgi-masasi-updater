import unittest, tempfile, pathlib, subprocess
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from dvp_position_patch import patch,MARKER
ROOT=pathlib.Path(__file__).resolve().parents[1]
class DvpTest(unittest.TestCase):
    def test_patches_without_touching_global_model(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)
            (p/'gorunum-oyuncu.js').write_bytes((ROOT/'tests/fixture-gorunum-oyuncu.js').read_bytes())
            (p/'index.html').write_bytes((ROOT/'tests/fixture-index.html').read_bytes())
            patch(p)
            src=(p/'gorunum-oyuncu.js').read_text(encoding='utf-8')
            self.assertIn('S.pos=cmDvpReadPosition(id)',src)
            self.assertIn('cmDvpOriginalRenderMatchup=renderMatchup',src)
            self.assertIn('cmDvpWritePosition(S.pid',src)
            self.assertIn(MARKER,src)
            self.assertIn('cm-dvp-position-v1.css', (p/'index.html').read_text(encoding='utf-8'))
            n=len(src);patch(p);self.assertEqual(n,len((p/'gorunum-oyuncu.js').read_text(encoding='utf-8')))
            if subprocess.run(['which','node'],capture_output=True).returncode==0:
                subprocess.run(['node','--check',str(p/'gorunum-oyuncu.js')],check=True)
    def test_safe_fail_if_source_changed(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)
            (p/'gorunum-oyuncu.js').write_text('function openPlayer(){}')
            (p/'index.html').write_text('<head></head>')
            with self.assertRaisesRegex(RuntimeError,'uyusmuyor'):
                patch(p)
            self.assertNotIn(MARKER,(p/'gorunum-oyuncu.js').read_text())
if __name__=='__main__':unittest.main()
