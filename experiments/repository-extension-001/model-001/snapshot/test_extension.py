import json,unittest
from pathlib import Path
from extension import prepare,sources,ROOT
TASKS=json.loads((ROOT/'tasks.json').read_text())
class ExtensionTests(unittest.TestCase):
 def test_reference_and_negative_acceptance(self):
  for task in TASKS:
   seed=sources(ROOT/'seeds'/task['family']);original=dict(seed)
   for label in ['reference','empty','negative']:
    result=prepare(seed,task,(ROOT/'controls'/task['id']/(label+'.json')).read_text())
    self.assertEqual(seed,original);self.assertEqual(set(result)-set(seed),{'ClientC.dfy'})
    for k in seed:
     self.assertEqual(result[k],seed[k]+b'include "ClientC.dfy"\n' if k=='All.dfy' else seed[k])
 def test_contract_and_extra_file_rejected(self):
  for task in TASKS:
   seed=sources(ROOT/'seeds'/task['family']);payload=json.loads((ROOT/'controls'/task['id']/'reference.json').read_text())
   with self.assertRaises(ValueError):prepare(seed,task,json.dumps({**payload,'Facts.dfy':'bad'}))
   payload['ClientC.dfy']=payload['ClientC.dfy'].replace('ensures ','ensures true || ')
   with self.assertRaises(ValueError):prepare(seed,task,json.dumps(payload))
 def test_bypasses_duplicates_and_extra_declarations(self):
  for task in TASKS:
   seed=sources(ROOT/'seeds'/task['family'])
   for body in ['assume false;','assert false;','reveal F.Total();','while true {}','{ : verify false }','F.AppendA(s, t); method Bad() {}']:
    with self.assertRaises(ValueError):prepare(seed,task,json.dumps({'ClientC.dfy':task['prefix']+body+task['suffix']}))
   with self.assertRaises(ValueError):prepare(seed,task,'{"ClientC.dfy":"x","ClientC.dfy":"y"}')
 def test_stale_seed_and_existing_file(self):
  task=TASKS[0];seed=sources(ROOT/'seeds'/task['family']);raw=(ROOT/'controls'/task['id']/'reference.json').read_text()
  with self.assertRaises(ValueError):prepare({**seed,'Facts.dfy':b'wrong'},task,raw)
  with self.assertRaises(ValueError):prepare({**seed,'ClientC.dfy':b''},task,raw)
if __name__=='__main__':unittest.main()
