"""Pin the correction scope and reuse only identical previously verified bytes."""
import json
from pathlib import Path
import sys
import unittest
from test_design import body_parts
from preflight import sha,selected

ROOT=Path(__file__).resolve().parent
PRIOR=ROOT.parent/'runtime-002'
sys.path.insert(0,str(ROOT.parent/'protocol'))
from body_guard import parse_response,split_seed


class RevisionTests(unittest.TestCase):
    def test_only_reverse_helper_bodies_changed(self):
        changed=[]
        for p in (ROOT/'fixtures').rglob('*.dfy'):
            rel=p.relative_to(ROOT); old=(PRIOR/rel).read_text();new=p.read_text()
            if old!=new:
                self.assertIn('reverse_concat-',str(rel));self.assertTrue(p.name.startswith('Helper'))
                a,b,c=body_parts(old);x,y,z=body_parts(new)
                self.assertEqual((a,c),(x,z));changed.append(str(rel))
        self.assertTrue(changed)
        self.assertEqual((ROOT/'tasks.json').read_bytes(),(PRIOR/'tasks.json').read_bytes())

    def test_prior_gate_evidence_is_exactly_reusable(self):
        summary=json.loads((PRIOR/'verification-001/summary.json').read_text())
        checks={(c['task_id'],c['variant']):c for c in json.loads((ROOT/'checks.json').read_text())}
        reused=[]
        for row in summary['results']:
            if row['matched']:
                self.assertEqual(row['source_sha256'],checks[row['task_id'],row['variant']]['source_sha256'])
                reused.append(row)
        self.assertEqual(len(reused),44)
        all_checks=list(checks.values())
        self.assertEqual(len(selected(all_checks,'references')),4)
        self.assertEqual(len(selected(all_checks,'negatives')),116)

    def test_existing_guard_replays_every_revised_reference(self):
        for task in json.loads((ROOT/'tasks.json').read_text()):
            def files(variant):return {p.name:p.read_text() for p in (ROOT/'fixtures'/task['task_id']/variant).glob('*.dfy')}
            seed=files('empty');reference=files('reference');bodies={}
            for name in task['editable_files']:
                pre,suf=split_seed(seed[name]);text=reference[name]
                self.assertTrue(text.startswith(pre) and text.endswith(suf))
                bodies[name]=text[len(pre):-len(suf)]
            candidate,record=parse_response(json.dumps(bodies),seed,task)
            self.assertEqual(candidate,reference)
            self.assertFalse(record['semantic_verification_performed'])


if __name__=='__main__':unittest.main(verbosity=2)
