"""Offline mathematics and exact migration-scope checks; no verification tools."""
from pathlib import Path
import itertools
import json
import tempfile
import unittest
import build as b

ROOT = Path(__file__).resolve().parent


def read(name): return json.loads((ROOT/name).read_bytes())
def endpoint(start,length,cap): return min(cap,start+length)
def advance(start,length,cap): return min(length,cap-start)
def endpoint_client_new(start,length,cap,helper):
    return cap if start>cap else start+helper(start,length,cap)
def erase(m,key): return {x:y for x,y in m.items() if x!=key}
def entry(m,key): return {x:y for x,y in m.items() if x==key}
def exclude(m,patch): return {x:y for x,y in m.items() if x not in patch}
def map_client_new(m,key,helper):
    if key not in m: return dict(m),{}
    patch = helper(m,key)
    return exclude(m,patch),patch


class Construction(unittest.TestCase):
    def test_reproducibility_distinct_cases_and_positive_gate_first(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = b.generate(root,ROOT/'design.json')
            self.assertEqual(status['distinct_workspaces'],18)
            for name in ('tasks.json','cases.json','fixture-manifest.json'):
                self.assertEqual((ROOT/name).read_bytes(),(root/name).read_bytes())
            for name,digest in read('fixture-manifest.json').items():
                self.assertEqual(b.sha((ROOT/name).read_bytes()),digest)
        cases = read('cases.json')
        inventories = [tuple(sorted(c['source_sha256'].items())) for c in cases]
        self.assertEqual(len(set(inventories)),18)
        self.assertTrue(all(c['expected']=='success' for c in cases[:6]))
        self.assertTrue(all(c['expected']=='proof_failure' for c in cases[6:]))
        self.assertEqual(sum(c['expected_local_targets']['Client.Target'] is False for c in cases),8)
        self.assertEqual(sum(c['expected_local_targets']['Helper.Transfer'] is False for c in cases),4)

    def test_public_contracts_providers_and_signature_remain_exact(self):
        for task in read('tasks.json'):
            tid = task['task_id']
            for variant in b.VARIANTS:
                source = b.sources(tid,variant)
                b.assert_construction_scope(tid,source)
                span = b.body_boundary(source['Client.dfy'])
                self.assertEqual(b.sha(source['Client.dfy'].encode()[:span['start']]),task['public_contract_sha256'])
                self.assertEqual(source['Client.dfy'].encode()[:span['start']].decode(),task['public_contract_prefix'])
            old,new = (task['internal_api_versions'][v]['header'] for v in ('old','new'))
            self.assertEqual(old.split('  method ')[1].split('\n')[0],new.split('  method ')[1].split('\n')[0])
            self.assertNotEqual(old,new)
            self.assertFalse(task['model_protocol_defined'])
            self.assertFalse(task['held_out'])

    def test_chosen_one_sided_edits_and_actual_target_expectations(self):
        cases = {c['case_id']:c for c in read('cases.json')}
        for tid in b.TASK_IDS:
            original = b.sources(tid,'reference')
            helper_only,caller_only = (b.sources(tid,v) for v in ('helper_only','caller_only'))
            self.assertEqual([n for n in original if original[n]!=helper_only[n]],['Helper.dfy'])
            self.assertEqual([n for n in original if original[n]!=caller_only[n]],['Client.dfy'])
            for variant in ('helper_only','caller_only'):
                self.assertEqual(cases[tid+'-'+variant]['expected_local_targets'],{'Helper.Transfer':True,'Client.Target':False})
                self.assertNotIn('expected_dependency_closed_targets',cases[tid+'-'+variant])
            self.assertEqual(cases[tid+'-caller_only']['expected_diagnostic'],
                             'assertion' if tid=='extracted_entry_return_migration' else 'postcondition')
            old_body = b.definition(tid)['bodies']['old_h']
            contract_only = b.sources(tid,'contract_only')['Helper.dfy']
            span = b.body_boundary(contract_only)
            self.assertEqual(contract_only.encode()[span['start']:span['end']].decode(),old_body)
            self.assertEqual(cases[tid+'-contract_only']['expected_local_targets'],{'Helper.Transfer':False,'Client.Target':True})

    def test_public_tamper_and_unplanned_internal_contract_are_rejected_offline(self):
        for tid in b.TASK_IDS:
            candidate = b.sources(tid,'paired_repair')
            altered = dict(candidate)
            lines = altered['Client.dfy'].splitlines(keepends=True)
            first = next(i for i,s in enumerate(lines) if '    ensures ' in s)
            lines[first] = '    ensures true\n'
            altered['Client.dfy'] = ''.join(lines)
            with self.assertRaisesRegex(AssertionError,'Public contract'): b.assert_construction_scope(tid,altered)
            altered = dict(candidate)
            lines = altered['Helper.dfy'].splitlines(keepends=True)
            first = next(i for i,s in enumerate(lines) if '    ensures ' in s)
            lines[first] = '    ensures true\n'
            altered['Helper.dfy'] = ''.join(lines)
            with self.assertRaisesRegex(AssertionError,'Unplanned internal API'): b.assert_construction_scope(tid,altered)

    def test_finite_endpoint_semantics_and_both_wrong_interface_mixes(self):
        count = guarded = 0
        for start,length,cap in itertools.product(range(-2,4),range(5),range(-2,4)):
            original = endpoint(start,length,cap)
            paired = endpoint_client_new(start,length,cap,advance)
            self.assertEqual(original,paired)
            if start<=cap:
                delta = advance(start,length,cap)
                self.assertTrue(0<=delta<=length)
                self.assertEqual(start+delta,original)
                alternative = (start+length if start+length<cap else cap)-start
                self.assertEqual(delta,alternative)
                guarded += 1
            count += 1
        self.assertEqual((count,guarded),(180,105))
        self.assertGreater(4,3)  # helper-only API is not callable at (4,1,3).
        self.assertNotEqual(advance(1,1,5),endpoint(1,1,5))
        self.assertNotEqual(endpoint_client_new(1,1,5,endpoint),endpoint(1,1,5))
        self.assertNotEqual(2+5,endpoint(2,5,4))  # Returning length violates the new result contract.

    def test_finite_map_semantics_and_both_wrong_interface_mixes(self):
        count = present = 0
        keys = (-1,0,1)
        for values in itertools.product((None,-1,0,1),repeat=3):
            m = {key:value for key,value in zip(keys,values) if value is not None}
            for key in range(-2,3):
                expected = (erase(m,key),entry(m,key))
                self.assertEqual(map_client_new(m,key,entry),expected)
                self.assertEqual(exclude(m,entry(m,key)),erase(m,key))
                if key in m:
                    self.assertEqual(set(entry(m,key)),{key})
                    self.assertEqual(entry(m,key)[key],m[key])
                    present += 1
                count += 1
        self.assertEqual((count,present),(320,144))
        m,key = {1:10,2:20},1
        expected = (erase(m,key),entry(m,key))
        self.assertNotEqual((entry(m,key),entry(m,key)),expected)
        self.assertNotEqual(map_client_new(m,key,erase),expected)
        self.assertNotIn(2,{1:10})
        self.assertNotEqual({1:0},entry(m,key))


if __name__=='__main__':
    unittest.main(verbosity=2)
