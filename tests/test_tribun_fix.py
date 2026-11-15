import json, pathlib, sys, tempfile, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from karne_tribun_temizle import cleanup
class TribunTest(unittest.TestCase):
 def test_only_pending_tribun_and_kasa_preserved(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'karne.json'
   kasa={'id':1,'mk':'PTS'};sh={'id':2,'mk':'AST'}
   p.write_text(json.dumps({'startBalance':100,'docs':[{'date':'2026-11-16','picks':[kasa],'shadow':[sh],'first':[kasa,sh]},{'date':'2026-11-14','picks':[],'shadow':[sh]},{'date':'2026-11-17','picks':[],'shadow':[sh],'searly':[7]}]}))
   self.assertTrue(cleanup(p,'2026-11-15'))
   v=json.loads(p.read_text())['docs']
   self.assertEqual(v[0]['picks'],[kasa]);self.assertEqual(v[0]['shadow'],[]);self.assertEqual(v[0]['first'],[kasa]);self.assertEqual(v[1]['shadow'],[sh]);self.assertEqual(v[2]['shadow'],[sh]);self.assertTrue(p.with_name('karne-tribun-yedek.json').exists())
