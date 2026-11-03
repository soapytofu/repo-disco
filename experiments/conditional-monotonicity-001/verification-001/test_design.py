"""Offline semantic-design and runtime-construction checks; no Dafny/models."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

import build

ROOT = Path(__file__).resolve().parent
TASKS = json.loads((ROOT / 'tasks.json').read_text())
CHECKS = json.loads((ROOT / 'checks.json').read_text())


class ConstructionTests(unittest.TestCase):
    def test_four_cells_and_declared_control_counts(self):
        from collections import Counter
        self.assertEqual({(t['depth'],t['sharing']) for t in TASKS},
                         {('shallow','shared'),('shallow','separate'),('deep','shared'),('deep','separate')})
        self.assertEqual(Counter(c['expected'] for c in CHECKS),
                         {'success':4,'proof_failure':24,'resolution_failure':4})
        self.assertEqual(len({(c['task_id'],c['variant']) for c in CHECKS}),32)

    def test_provider_client_contracts_match_across_cells(self):
        fixed = ['Kernel.dfy','Ops1.dfy','Ops2.dfy','Api.dfy','ClientA.dfy','ClientB.dfy','All.dfy']
        baseline = build.sources('shallow','shared','reference')
        for task in TASKS:
            for check in [c for c in CHECKS if c['task_id']==task['task_id']]:
                actual = {p.name:p.read_text() for p in (ROOT/check['path']).glob('*.dfy')}
                self.assertEqual(build.hashes(actual),check['source_sha256'])
                for name in fixed:self.assertEqual(actual[name],baseline[name])
                for name in ['HelperA.dfy','HelperB.dfy']:
                    self.assertIn(build.SIGNATURE,actual[name])
                    self.assertEqual(actual[name].count('{'),actual[name].count('}'))
                if task['sharing']=='shared':
                    self.assertEqual(actual['HelperB.dfy'],baseline['HelperB.dfy'])

    def test_branch_guards_and_depth_calls_in_reference(self):
        shallow = build.proof('shallow','reference')
        deep = build.proof('deep','reference')
        for variable in ('x','y'):
            for source in (shallow,deep):
                self.assertIn(f'if {variable} < l',source)
                self.assertIn(f'else if {variable} <= h',source)
            self.assertEqual(shallow.count(f'A.Below({variable},l,h)'),1)
            self.assertEqual(shallow.count(f'A.Within({variable},l,h)'),1)
            self.assertEqual(shallow.count(f'A.Above({variable},l,h)'),1)
        self.assertEqual(deep.count('A.Assemble('),6)
        self.assertEqual(deep.count('O1.'),6)
        self.assertEqual(deep.count('O2.'),6)
        for source in (shallow,deep):
            for forbidden in ('assume','reveal','{:','assert false','while'):self.assertNotIn(forbidden,source)

    def test_targeted_mutations_and_hidden_views(self):
        for depth in ('shallow','deep'):
            reference = build.proof(depth,'reference')
            for variant in build.VARIANTS[1:]:self.assertNotEqual(build.proof(depth,variant),reference)
            boundary = build.proof(depth,'boundary')
            self.assertEqual(boundary,reference.replace('if x < l','if x <= l',1))
            only = build.proof(depth,'only_first')
            self.assertEqual(only,build.observation('x',depth))
            hidden = build.sources(depth,'shared','hidden_shortcut')['HelperA.dfy']
            self.assertIn('A.Assemble(x,l,h,x,x)' if depth=='shallow' else 'A.Below(x,l,h)',hidden)
            self.assertIn('Api`Shallow' if depth=='shallow' else 'Api`Deep',hidden)

    def test_isolated_import_and_fake_verifier_staging(self):
        script = '''import sys,json,subprocess
from pathlib import Path
from unittest.mock import patch
root=Path(sys.argv[1]);sys.path.insert(0,str(root));import preflight
checks=preflight.load(root/'checks.json');assert preflight.selected(checks,'all')==checks
check=checks[0];sources={p.name:p.read_bytes() for p in (root/check['path']).glob('*.dfy')}
def fake(command,**kwargs):
 assert command==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy']
 assert {p.name:p.read_bytes() for p in Path(kwargs['cwd']).glob('*.dfy')}==sources
 return subprocess.CompletedProcess(command,0,'fake only','')
with patch('subprocess.run',side_effect=fake) as proc:
 result=preflight.verify_repository(sources,'All.dfy',60)
 assert proc.call_count==1 and result.evidence['exit_code']==0
print('isolated runtime and fake staging passed; no real verifier/model call')
'''
        result = subprocess.run([sys.executable,'-I','-B','-c',script,str(ROOT)],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':unittest.main(verbosity=2)
