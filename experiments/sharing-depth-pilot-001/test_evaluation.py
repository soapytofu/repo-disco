"""Non-paid integration tests; fake verifier only, no compute/model calls."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import evaluation
class EvaluationTests(unittest.TestCase):
 def test_reference_roundtrip_and_preservation(self):
  root=evaluation.ROOT
  for trial in json.loads((root/'plan.json').read_text())[:4]:
   folder=root.parent/'sharing-composition-002/fixtures'/f"{trial['tier']}_{trial['condition']}_reference"
   files={n:(folder/n).read_text() for n in evaluation.CLIENTS};seen=[]
   def fake_verify(out,entry):
    seen.append(entry)
    for n in ['Facts.dfy','All.dfy',*evaluation.CLIENTS]:self.assertEqual((out/n).read_bytes(),(folder/n).read_bytes())
    return dict(command=['fake-verifier',entry],exit_code=0,outcome='SUCCESS',seconds=0,stdout='1 verified, 0 errors',stderr='')
   with tempfile.TemporaryDirectory() as d,patch.object(evaluation,'verify',fake_verify):
    result=evaluation.evaluate(trial,'Proof:\n```json\n'+json.dumps(files)+'\n```',Path(d)/'result')
    self.assertEqual(result['outcome'],'SUCCESS');self.assertEqual(seen,['All.dfy','ClientA.dfy','ClientB.dfy'])
 def test_format_and_guard_failures_do_not_verify(self):
  trial=json.loads((evaluation.ROOT/'plan.json').read_text())[0]
  for raw,expected in [('not json','FORMAT_REJECTED'),(json.dumps({'ClientA.dfy':'bad','ClientB.dfy':'bad'}),'EDIT_REJECTED')]:
   with tempfile.TemporaryDirectory() as d,patch.object(evaluation,'verify') as verifier:
    self.assertEqual(evaluation.evaluate(trial,raw,Path(d)/'result')['outcome'],expected);verifier.assert_not_called()
if __name__=='__main__':unittest.main()
