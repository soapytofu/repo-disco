"""Offline preparation checks, also replayed against the actual frozen bytes."""
import collections
import copy
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import build_freeze as b
import body_guard as policy
from gates.vmc import protocol as dg

R = Path(__file__).resolve().parent


class PreparationTests(unittest.TestCase):
    def test_exact_context_projection_and_seed_boundary(self):
        for t in b.read(R/'tasks.json'):
            text, manifest = b.source_context(t)
            selected = [x for x in manifest if x['seed_substituted']]
            self.assertEqual(len(selected), 1)
            self.assertEqual(selected[0]['candidate_file_sha256'], t['source_sha256'])
            self.assertGreaterEqual(selected[0]['end_byte'], t['boundary']['end'])
            self.assertIn((R/'fixtures'/t['id']/'seed-body.txt').read_text(), text)
            self.assertEqual(len(manifest), 28 if t['project']=='dafny-vmc' else (3 if t['id']=='vest-roundtrip' else 6))
            for x in manifest:
                self.assertEqual(policy.sha((b.QUAL/'upstream'/t['project']/x['file']).read_bytes()),x['original_sha256'])

    def test_reference_body_not_copied_into_own_prompt_context(self):
        for t in b.read(R/'tasks.json'):
            context, _ = b.source_context(t)
            reference = (R/'fixtures'/t['id']/'reference-body.txt').read_text()
            self.assertNotIn(re.sub(r'\s+','',reference), re.sub(r'\s+','',context), t['id'])
            common = b.common_prompt(t, context)
            self.assertNotIn(t['fault_label_audit_only'], common)
            self.assertNotIn('reference-body.txt', common)

    def test_balanced_counterbalanced_independent_order(self):
        order = b.slot_order()
        self.assertEqual([s['slot'] for s in order], list(range(1,17)))
        groups = collections.Counter((s['task'],s['arm']) for s in order)
        self.assertEqual(len(groups),8); self.assertEqual(set(groups.values()),{2})
        for tid in policy.RULES:
            first = [[s for s in order if s['task']==tid and s['repeat']==rep][0]['arm'] for rep in [1,2]]
            self.assertNotEqual(*first)
        self.assertTrue(all(s['max_requests']==1 and s['independent_context'] for s in order))

    def test_payload_budget_is_proposal_only(self):
        self.assertFalse(b.SETTINGS['execution_authorized'])
        self.assertFalse(b.SETTINGS['availability_tested'])
        self.assertEqual(b.SETTINGS['sdk_total_max_attempts_if_executed'],1)
        self.assertEqual(b.SETTINGS['inference_config'],dict(temperature=1.0,maxTokens=4096))
        self.assertTrue(b.NOTICE.strip().endswith('failed.'))
        self.assertNotIn('repair hint',b.SYSTEM)

    def test_exact_response_shape_accepts_upstream_bodies(self):
        for t in b.read(R/'tasks.json'):
            body = (R/'fixtures'/t['id']/'reference-body.txt').read_text()
            candidate, receipt = policy.parse_response(json.dumps({'replacement':body}),t['id'])
            self.assertEqual(policy.sha(candidate),t['upstream_file_sha256'])
            self.assertFalse(receipt['semantics_checked'])

    def test_evidence_binding_rejects_changed_stale_missing(self):
        raw={'stdout.txt':b'proof failed\n'}
        p=dict(source_sha256={'x.dfy':'a'},logical_command=['verify','x.dfy'],toolchain={'version':'pinned'})
        r=dict(run_id='new',profile_sha256=dg.sha(dg.canonical(p)),source_sha256=p['source_sha256'],
               source_after_sha256=p['source_sha256'],logical_command=p['logical_command'],toolchain=p['toolchain'],
               raw_sha256={n:dg.sha(v) for n,v in raw.items()},model_calls=0,attempts=1,exit_code=4,elapsed_seconds=1.0)
        dg.check_record(r,p,'new',raw)
        for key,value in [('run_id','old'),('source_sha256',{}),('source_after_sha256',{}),('logical_command',['verify','other']),('toolchain',{}),('raw_sha256',{}),('attempts',2)]:
            changed=copy.deepcopy(r);changed[key]=value
            with self.subTest(field=key),self.assertRaises(ValueError):dg.check_record(changed,p,'new',raw)

    def test_missing_or_partial_control_gate_cannot_freeze(self):
        with patch.object(b.evidence,'review',side_effect=ValueError('missing actual control evidence')):
            with self.assertRaises(ValueError):b.artifacts()

    @unittest.skipUnless((R/'frozen-001/manifest.json').exists(),'Actual freeze has not been constructed yet')
    def test_actual_freeze_exact_rebuild_pairing_and_pins(self):
        actual = b.artifacts()
        manifest = b.read(R/'frozen-001/manifest.json')
        self.assertEqual(set(actual),set(manifest))
        for name,raw in actual.items():
            self.assertEqual((R/'frozen-001'/name).read_bytes(),raw,name)
            self.assertEqual(policy.sha(raw),manifest[name],name)
        for t in b.read(R/'tasks.json'):
            d=json.loads(actual['payloads/'+t['id']+'--diagnostics.json'])
            n=json.loads(actual['payloads/'+t['id']+'--failure_notice.json'])
            self.assertNotEqual(d['messages'][0]['content'][1],n['messages'][0]['content'][1])
            d['messages'][0]['content'][1]=n['messages'][0]['content'][1]
            self.assertEqual(d,n)
            feedback=actual['feedback/'+t['id']+'.txt'].decode()
            self.assertNotIn(t['id']+'-seed',feedback)
            self.assertNotIn('reference-body',feedback)
        for name,h in b.read(R/'frozen-001/inputs.json').items():
            self.assertEqual(policy.sha((b.REPO/name).read_bytes()),h,name)
        scope=b.read(R/'frozen-001/scope.json')
        self.assertEqual(scope['proposed_max_new_requests'],16)
        self.assertFalse(scope['execution_authorized'])
        self.assertEqual(scope['model_calls_made'],0)


if __name__=='__main__':unittest.main(verbosity=2)
