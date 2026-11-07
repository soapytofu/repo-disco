"""Pinned response round-trips and protected bytes; no actual verifier/model."""
import json,unittest
from pathlib import Path
import body_guard,extract_response
ROOT=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_eight_distinct_reference_alternatives(self):
  tasks=json.loads((ROOT/'tasks.json').read_text());checks=json.loads((ROOT/'checks.json').read_text())
  self.assertEqual(len(tasks),8);self.assertEqual(len(checks),8)
  for t,c in zip(tasks,checks):
   files={p.name:p.read_text() for p in (ROOT/c['path']).glob('*.dfy')}
   seeds={p.name:p.read_text() for p in (ROOT/'seeds'/t['task_id']).glob('*.dfy')}
   self.assertEqual({n:body_guard.digest(s) for n,s in seeds.items()},t['source_sha256'])
   raw=(ROOT/'responses'/t['task_id']/'response.txt').read_text()
   actual,decision=extract_response.parse_response(raw,seeds,t,body_guard)
   self.assertEqual(actual,files);self.assertEqual(decision['body_guard']['candidate_sha256'],c['source_sha256'])
   original=json.loads((ROOT/'responses'/t['task_id']/'decision.json').read_text());self.assertEqual(original,decision)
 def test_isolated_runtime_dependencies(self):
  import subprocess,sys
  script='''import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import preflight
assert len(preflight.load(Path(sys.argv[1])/'checks.json'))==8
'''
  p=subprocess.run([sys.executable,'-I','-B','-c',script,str(ROOT)],capture_output=True,text=True,timeout=15);self.assertEqual(p.returncode,0,p.stdout+p.stderr)
if __name__=='__main__':unittest.main(verbosity=2)
