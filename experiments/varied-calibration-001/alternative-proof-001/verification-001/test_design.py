"""Alternative-proof source, guard, and isolated-runtime checks without Dafny."""
import json,subprocess,sys,unittest
from pathlib import Path
import build
ROOT=Path(__file__).resolve().parent
TASKS=json.loads((ROOT/'tasks.json').read_text());CHECKS=json.loads((ROOT/'checks.json').read_text())

class Tests(unittest.TestCase):
    def test_inventory_exact_guard_replay_and_protected_bytes(self):
        self.assertEqual(len(CHECKS),16);self.assertEqual(len({c['task_id'] for c in CHECKS}),16)
        for t,c in zip(TASKS,CHECKS):
            seed=build.definition.sources(t['semantic_instance'],t['depth'],t['sharing'],'empty')
            raw=(ROOT/'responses'/t['task_id']/'response.txt').read_text()
            got,decision=build.extract_response.parse_response(raw,seed,t,build.guard)
            self.assertEqual(got,{p.name:p.read_text() for p in (ROOT/c['path']).glob('*.dfy')})
            self.assertEqual(decision['body_guard']['candidate_sha256'],c['source_sha256'])
            reference=build.definition.sources(t['semantic_instance'],t['depth'],t['sharing'],'reference')
            for n in got:
                if n not in t['editable_files']:self.assertEqual(got[n],seed[n])
                else:
                    a,z=build.guard.split_seed(seed[n]);self.assertTrue(got[n].startswith(a) and got[n].endswith(z))
                    self.assertNotEqual(got[n],reference[n])
    def test_four_distinct_strategy_changes(self):
        for depth in ['shallow','deep']:
            self.assertIn('if b <= t-c then b else t-c',build.alternative('bounded_allocation',depth))
            self.assertIn('if k==j',build.alternative('map_swap',depth))
            self.assertNotIn('if x<=y',build.alternative('clamp_distance',depth))
            self.assertIn('if j==0',build.alternative('prefix_split',depth))
            self.assertIn('s[i..],0',build.alternative('prefix_split',depth))
    def test_isolated_runtime_fake_process(self):
        code='''import sys,subprocess
from pathlib import Path
from unittest.mock import patch
r=Path(sys.argv[1]);sys.path.insert(0,str(r));import preflight
checks=preflight.load(r/'checks.json');assert len(preflight.selected(checks,'core'))==16
files={p.name:p.read_bytes() for p in (r/checks[0]['path']).glob('*.dfy')}
def fake(command,**kwargs):
 assert command==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy']
 assert {p.name:p.read_bytes() for p in Path(kwargs['cwd']).glob('*.dfy')}==files
 return subprocess.CompletedProcess(command,0,'fake only','')
with patch('subprocess.run',side_effect=fake) as mocked:
 preflight.verify_repository(files,'All.dfy',60);assert mocked.call_count==1
'''
        p=subprocess.run([sys.executable,'-I','-B','-c',code,str(ROOT)],capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)

if __name__=='__main__':unittest.main(verbosity=2)
