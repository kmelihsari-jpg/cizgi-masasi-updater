import json, pathlib, sys, tempfile, datetime as dt, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from karne_returning import patch_text,records
class ConfirmedReturnTest(unittest.TestCase):
 def setUp(self):
  self.model=(pathlib.Path(__file__).resolve().parents[1]/'tests'/'fixture-model.js').read_text(encoding='utf-8')
 def test_unconfirmed_miss_remains_out(self):
  m=patch_text(self.model,[])
  self.assertIn('!cmReturnAllowed(p,day))continue;',m)
  self.assertIn('!cmReturnAllowed(p,day))return null;',m)
  self.assertIn('if(noBet(inj)||!cmReturnAllowed(p,day))',m)
  self.assertIn('CM_CONFIRMED_RETURNS = [];',m)
 def test_refresh_list_on_republish(self):
  m=patch_text(self.model,[{'id':1,'team':'MIA','date':'2026-11-15','checkedAt':'2026-11-15T10:00:00+00:00'}])
  self.assertIn('"id":1',m)
  m=patch_text(m,[])
  self.assertIn('CM_CONFIRMED_RETURNS = [];',m)
  self.assertNotIn('"id":1',m)
 def test_source_timestamp_and_id_required(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'confirmed.json'
   ok={'id':7,'team':'MIA','date':dt.date.today().isoformat(),'checkedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'confirmed_active','sourceType':'nba_official','sourceUrl':'https://nba.com/something','evidence':'Official active lineup announced'}
   p.write_text(json.dumps({'players':[ok,{**ok,'id':8,'status':'probable'},{**ok,'id':9,'checkedAt':'2025-01-01T00:00:00Z'}]}))
   self.assertEqual([x['id'] for x in records(p)],[7])
if __name__=='__main__':unittest.main()
