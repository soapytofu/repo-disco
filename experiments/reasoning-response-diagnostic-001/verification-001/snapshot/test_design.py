"""Offline diagnostic identity and protected-source tests; no verification."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PILOT=ROOT.parent/'monorepo-reasoning-calibration-pilot-001'
sys.path.insert(0,str(PILOT));import run_pilot as r
CASES=r.load(ROOT/'cases.json');TASKS={t['task_id']:t for t in r.load(PILOT/'frozen-001/tasks.json')}

class Design(unittest.TestCase):
 def test_exact_six_cases_and_original_response_hashes(self):
  self.assertEqual([x['original_trial'] for x in CASES],['reasoning-cal-02','reasoning-cal-08','reasoning-cal-18','reasoning-cal-21','reasoning-cal-24','reasoning-cal-03'])
  for case in CASES:
   folder=PILOT/'model-001'/case['original_trial']
   self.assertEqual(r.sha(folder/'response.json'),case['original_response_sha256'])
   self.assertEqual(r.sha(folder/'result.json'),case['original_result_sha256'])
  self.assertEqual(r.load(PILOT/'results-review.json')['verified'],18)
 def test_five_bodies_unchanged_one_explicit_statement_added(self):
  guard=r.guard_module(PILOT)
  for case in CASES:
   task=TASKS[case['task_id']];seed=r.sources(PILOT,task)
   raw=r.load(PILOT/'model-001'/case['original_trial']/'response.json')['text'];bodies=json.loads(raw)
   actual={p.name:p.read_bytes() for p in (ROOT/case['path']).glob('*.dfy')}
   self.assertEqual(r.hashes(actual),case['candidate_sha256'])
   self.assertEqual(r.hashes(seed),case['original_seed_sha256'])
   expected=dict(seed)
   for name,body in bodies.items():
    prefix,suffix=guard.split_seed(seed[name].decode())
    if case['mutation']:
     anchor='if q == j {\n        assert lhs[q] == y;'
     self.assertEqual(body.count(anchor),1)
     body=body.replace(anchor,'if q == j {\n        O2.PutAt(m,j,y,q);\n        assert lhs[q] == y;')
    expected[name]=(prefix+body+suffix).encode()
   self.assertEqual(actual,expected)
   for name in set(seed)-set(task['editable_files']):self.assertEqual(actual[name],seed[name])
 def test_original_guard_results_remain_rejections_and_repair_admits(self):
  guard=r.guard_module(PILOT)
  for case in CASES:
   task=TASKS[case['task_id']];seed={n:b.decode() for n,b in r.sources(PILOT,task).items()}
   raw=r.load(PILOT/'model-001'/case['original_trial']/'response.json')['text']
   if case['unchanged_body_strings']:
    with self.assertRaises(ValueError):guard.parse_response(raw,seed,task)
   else:
    guard.parse_response(raw,seed,task)
    candidate={p.name:p.read_text() for p in (ROOT/case['path']).glob('*.dfy')};body={}
    for name in task['editable_files']:
     pre,suf=guard.split_seed(seed[name]);body[name]=candidate[name][len(pre):-len(suf)]
    self.assertEqual(guard.parse_response(json.dumps(body),seed,task)[0],candidate)
if __name__=='__main__':unittest.main(verbosity=2)
