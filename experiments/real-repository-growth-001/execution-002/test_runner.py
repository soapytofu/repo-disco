"""Synthetic transport/native tests only. No API, key, SSH or verifier execution."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import runtime as r
import run_pilot as host
from bounded_requests import RequestGate, GateClosed, bedrock_transport

REPO = Path(__file__).resolve().parents[3]


def response(text, number=1, stop='end_turn', retries=0):
    usage = dict(inputTokens=100, outputTokens=10, totalTokens=110)
    content = [dict(text=text)]
    raw = dict(output=dict(message=dict(role='assistant', content=content)), usage=usage, stopReason=stop,
               ResponseMetadata=dict(RequestId=f'SYNTHETIC-{number}', RetryAttempts=retries, HTTPStatusCode=200))
    return dict(text=text, content=content, usage=usage, stop_reason=stop,
                request_id=f'SYNTHETIC-{number}', retry_attempts=retries, raw_response=raw)


class FakeNative:
    synthetic = True

    def __init__(self, outcomes=None):
        self.outcomes, self.calls = outcomes or {}, []

    def verify(self, slot, sources, destination, run_id):
        from test_native_host import fixture_result
        self.calls.append(slot['slot_id'])
        return fixture_result(slot, sources, REPO, run_id=run_id,
                              outcome=self.outcomes.get(slot['slot_id'], 'pass'))


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer, cls.api = r.load_context(REPO)
        cls.package = dict(runtime_sha256='0'*64, proposal_sha256=r.PILOT_SHA,
            protocol_sha256=r.PROTOCOL_SHA, policy_sha256=cls.api.b.policy_digest(),
            order=cls.renderer.order(), settings=r.read(REPO/r.PILOT/'frozen-001/settings.json'))
        cls.bodies = {}
        for project, case, sid in [('dafny-vmc','move-alternative','vmc-move'),
                                  ('dafny-vmc','pair-alternative','vmc-pair'),
                                  ('vest','frame-alternative','vest-frame'),
                                  ('vest','batch-alternative','vest-batch')]:
            _, _, sources, _ = cls.api.control_material(project,case,REPO)
            stage, _, _ = cls.api.b.stage_spec(sid)
            cls.bodies[sid] = cls.api.b.source_body(sid,sources[stage['path']])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.out = self.base/'simulation'
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def transport(self, payload):
        self.calls.append(copy.deepcopy(payload))
        text = payload['messages'][0]['content'][0]['text']
        stage = next(s for s in self.bodies if ('CURRENT TARGET FILE '+
                     self.api.b.stage_spec(s)[0]['path']+'\n') in text)
        return response(json.dumps(dict(replacement=self.bodies[stage])),len(self.calls))

    def run_sim(self, transport=None, verifier=None, **kwargs):
        return host.simulate(REPO,self.out,transport or self.transport,verifier or FakeNative(),
            deadline=2000,clock=lambda:1000,package=self.package,validate=kwargs.pop('validate',lambda:None),
            acknowledge_synthetic=True,run_id='synthetic-run',**kwargs)

    def test_all_eight_fresh_slots_accept_and_full_saved_replay_is_explicitly_synthetic(self):
        import review
        result=self.run_sim()
        self.assertEqual((result['status'],result['transport_reservations'],result['completed_lineages']),
                         ('SYNTHETIC_COMPLETE',8,4))
        self.assertEqual(result['model_requests_reserved'],0)
        with self.assertRaises(ValueError):review.review_run(REPO,self.out,expected_package=self.package)
        replay=review.review_run(REPO,self.out,allow_synthetic=True,expected_package=self.package)
        self.assertEqual(replay['accepted_stages'],8)
        for child,parent in [('slot-03','slot-01'),('slot-04','slot-02'),('slot-07','slot-05'),('slot-08','slot-06')]:
            rendering=r.read(self.out/child/'rendering.json')
            self.assertTrue(rendering['parent_source_used_without_body_change'])
            parent_slot=r.read(self.out/parent/'slot.json')
            parent_path=self.api.b.stage_spec(parent_slot['stage_id'])[0]['path']
            self.assertEqual(rendering['actual_parent_source_sha256'],
                             r.read(self.out/parent/'source-manifest.json')['source_sha256'][parent_path])
            self.assertEqual(rendering['parent_audit']['parent_run_id'],'synthetic-run:'+parent)
        import shutil
        shutil.rmtree(self.out/'accepted-heads')
        manifest={p.relative_to(self.out).as_posix():r.sha(p.read_bytes()) for p in r.archive_files(self.out)}
        (self.out/'archive-manifest.json').write_bytes(r.encode(manifest))
        with self.assertRaisesRegex(ValueError,'Missing required accepted-heads'):
            review.review_run(REPO,self.out,allow_synthetic=True,expected_package=self.package)

    def test_files_only_stopped_archive_may_omit_empty_accepted_heads_directory(self):
        import review
        def fail(payload):
            raise RuntimeError('Synthetic pre-response failure')
        self.run_sim(fail)
        (self.out/'accepted-heads').rmdir()
        # No manifest rewrite: directories were never manifest members.
        replay=review.review_run(REPO,self.out,allow_synthetic=True,expected_package=self.package)
        self.assertFalse(replay['experiment_complete'])
        self.assertEqual(replay['reserved'],1)
        self.assertEqual(replay['completed_responses'],0)
        self.assertIsNone(replay['reservation_audit'][0]['proof_score'])

    def test_guard_rejections_block_only_children_and_never_reassign_capacity(self):
        native=FakeNative()
        def bad(payload):
            self.calls.append(payload);return response('{"replacement":"assume false;"}',len(self.calls))
        result=self.run_sim(bad,native)
        self.assertEqual(len(self.calls),4);self.assertEqual(native.calls,[])
        self.assertEqual(result['blocked_children'],['slot-03','slot-04','slot-07','slot-08'])
        self.assertEqual(result['unused_capacity_never_reassigned'],4)

    def test_one_failed_parent_blocks_its_exact_child_and_other_lineages_continue(self):
        result=self.run_sim(verifier=FakeNative({'slot-01':'proof_failure'}))
        self.assertEqual(result['transport_reservations'],7)
        self.assertEqual(result['blocked_children'],['slot-03'])
        self.assertEqual(result['completed_lineages'],3)

    def test_ambiguous_transport_reserves_once_stops_and_cannot_restart(self):
        import review
        def fail(payload):
            self.calls.append(payload)
            if len(self.calls)==2:raise TimeoutError('private transport error text is not archived')
            return response('{"replacement":"assume false;"}',1)
        result=self.run_sim(fail)
        self.assertEqual((result['transport_reservations'],result['completed_responses'],result['ambiguous_or_unsaved']),(2,1,1))
        self.assertEqual(result['status'],'SYNTHETIC_STOPPED')
        with self.assertRaises(FileExistsError):self.run_sim(fail)
        self.assertEqual(len(self.calls),2)
        self.assertNotIn('private transport error text',(self.out/'stop.json').read_text())
        audited=review.review_run(REPO,self.out,allow_synthetic=True,expected_package=self.package)
        self.assertFalse(audited['experiment_complete'])
        self.assertIsNone(audited['reservation_audit'][-1]['proof_score'])

    def test_duplicate_provider_id_stops_before_further_dispatch(self):
        import review
        def duplicate(payload):
            self.calls.append(payload);return response('{"replacement":"assume false;"}',1)
        result=self.run_sim(duplicate)
        self.assertEqual(result['transport_reservations'],2)
        self.assertEqual(result['status'],'SYNTHETIC_STOPPED')
        audited=review.review_run(REPO,self.out,allow_synthetic=True,expected_package=self.package)
        self.assertFalse(audited['reservation_audit'][-1]['metadata_valid'])
        self.assertIsNone(audited['reservation_audit'][-1]['proof_score'])

    def test_reviewer_checks_all_returned_responses_and_scored_metadata(self):
        import review
        def bad(payload):
            self.calls.append(payload);return response('{"replacement":"assume false;"}',len(self.calls))
        self.run_sim(bad)
        review.review_run(REPO,self.out,allow_synthetic=True,expected_package=self.package)
        def refresh():
            manifest={p.relative_to(self.out).as_posix():r.sha(p.read_bytes()) for p in r.archive_files(self.out)}
            (self.out/'archive-manifest.json').write_bytes(r.encode(manifest))
        response_file=self.out/'requests/response-001.json';old=response_file.read_bytes()
        response_file.unlink();refresh()
        with self.assertRaisesRegex(ValueError,'no full saved response'):
            review.review_run(REPO,self.out,allow_synthetic=True,expected_package=self.package)
        response_file.write_bytes(old)
        path=self.out/'slot-01/response.json';old=path.read_bytes();value=r.read(path);value['text']='different response'
        path.write_bytes(r.encode(value));refresh()
        with self.assertRaisesRegex(ValueError,'canonical ledger response'):
            review.review_run(REPO,self.out,allow_synthetic=True,expected_package=self.package)
        path.write_bytes(old)
        rows=r.read(self.out/'results.json');rows[0]['request_id']='invented-row-id'
        (self.out/'results.json').write_bytes(r.encode(rows));(self.out/'slot-01/result.json').write_bytes(r.encode(rows[0]));refresh()
        with self.assertRaisesRegex(ValueError,'provider identity or usage'):
            review.review_run(REPO,self.out,allow_synthetic=True,expected_package=self.package)

    def test_incomplete_native_execution_preserves_terminal_no_score(self):
        import review
        from native_host import NativeResult
        class Incomplete(FakeNative):
            def verify(self,slot,sources,destination,run_id):
                return NativeResult(None,{},None,'TERMINAL_NATIVE_INTEGRITY_OR_EXECUTION_ERROR',True,
                                    destination,True,native_invocations=0,invocation_attempted=False)
        result=self.run_sim(verifier=Incomplete())
        self.assertEqual(result['status'],'SYNTHETIC_STOPPED')
        self.assertEqual(result['transport_reservations'],1)
        self.assertEqual(result['accepted_stages'],0)
        audited=review.review_run(REPO,self.out,allow_synthetic=True,expected_package=self.package)
        self.assertIsNone(audited['reviewed_rows'][0]['proof_score'])

    def test_nonzero_sdk_retry_metadata_stops_without_verification(self):
        native=FakeNative()
        result=self.run_sim(lambda _:response('{}',1,retries=1),native)
        self.assertEqual(result['transport_reservations'],1);self.assertFalse(native.calls)
        self.assertEqual(result['status'],'SYNTHETIC_STOPPED')

    def test_truncation_is_returned_output_failure_not_a_retry(self):
        def truncated(payload):
            self.calls.append(payload);return response('{',len(self.calls),stop='max_tokens')
        result=self.run_sim(truncated)
        self.assertEqual(result['status'],'SYNTHETIC_COMPLETE')
        self.assertEqual(result['transport_reservations'],4)
        self.assertEqual(len(result['blocked_children']),4)
        self.assertEqual(r.read(self.out/'slot-01/result.json')['outcome'],'OUTPUT_TRUNCATED')

    def test_saved_parent_response_tampering_stops_before_child_call(self):
        count=0
        def validate():
            nonlocal count
            count+=1
            if count==5:
                path=self.out/'slot-01/response.json'
                value=r.read(path);value['text']='changed outside request owner'
                path.write_bytes(r.encode(value))
        result=self.run_sim(validate=validate)
        self.assertEqual(result['transport_reservations'],2)
        self.assertEqual(result['status'],'SYNTHETIC_STOPPED')
        self.assertFalse((self.out/'slot-03/request.json').exists())

    def test_policy_drift_after_response_is_terminal_not_model_guard_rejection(self):
        checks=0
        def validate():
            nonlocal checks
            checks+=1
            if checks==2:raise ValueError('Runtime pin changed')
        result=self.run_sim(lambda _:response('invalid JSON'),validate=validate)
        self.assertEqual(result['status'],'SYNTHETIC_STOPPED')
        self.assertEqual(r.read(self.out/'results.json'),[])

    def test_scope_claim_prevents_reusing_approval_with_missing_or_new_output(self):
        root=self.base/'remote';repo=root/'repo';repo.mkdir(parents=True)
        authpath=root/'auth.json';authpath.write_text('{}')
        auth=dict(authorized_runtime_root=str(root),expires_at_epoch=2000)
        argv=['--repo',str(repo),'--output',str(root/'model-001'),'--authorization',str(authpath)]
        with patch.object(r,'validate_authorization',return_value=auth),patch.object(r,'validate_package',return_value=self.package),\
             patch.dict(os.environ,{'SLURM_JOB_ID':'999999','SLURM_CPUS_PER_TASK':'1'}),\
             patch.object(host.socket,'gethostname',return_value='synthetic-compute'),\
             patch.object(host,'_execute',side_effect=RuntimeError('synthetic interruption before key')),\
             patch('native_host.NativeVerifier'),patch.object(host,'load_private_token') as key:
            with self.assertRaises(RuntimeError):host.main(argv)
            self.assertTrue((root/'execution.claim.json').is_file())
            with self.assertRaises(FileExistsError):host.main(argv)
            changed=list(argv);changed[3]=str(root/'alternate-output')
            with self.assertRaises(ValueError):host.main(changed)
            key.assert_not_called()

    def test_authorization_exact_budget_scope_and_expiry(self):
        auth=dict(schema='repodisco-growth-execution-authorization-v1',execution_authorized=True,
            approved_by='Sophie Zeng',human_basis='Unit-test fixture, never staged',max_new_requests=8,
            no_retries=True,no_reassignment=True,pilot_freeze_sha256=r.PILOT_SHA,
            runtime_freeze_sha256=self.package['runtime_sha256'],execution_id=r.EXECUTION_ID,
            authorized_runtime_root=str(self.base),output_relative_path='model-001',issued_at_epoch=900,expires_at_epoch=2000)
        path=self.base/'test-auth.json'
        with patch.object(r,'validate_package',return_value=self.package):
            path.write_bytes(r.encode(auth));self.assertEqual(r.validate_authorization(path,REPO,1000),auth)
            for key,value in [('max_new_requests',9),('no_retries',False),('execution_authorized',False),
                              ('execution_id','another-budget'),('expires_at_epoch',999),('expires_at_epoch',90000)]:
                changed=dict(auth);changed[key]=value;path.write_bytes(r.encode(changed))
                with self.assertRaises(ValueError):r.validate_authorization(path,REPO,1000)

    def test_archive_excludes_only_declared_cargo_cache_not_native_logs(self):
        root=self.base/'archive';(root/'slot-01/native/fresh-target').mkdir(parents=True)
        (root/'slot-01/native/fresh-target/link').symlink_to('/nonexistent-test-target')
        (root/'slot-01/native/stdout.txt').write_text('full raw evidence')
        self.assertEqual([p.relative_to(root).as_posix() for p in r.archive_files(root)],['slot-01/native/stdout.txt'])
        (root/'slot-01/native/bad-link').symlink_to('/nonexistent-test-target')
        with self.assertRaises(ValueError):r.archive_files(root)

    def test_sdk_factory_pins_one_attempt_and_sends_exact_payload(self):
        captured={}
        class Client:
            def converse(self,**kwargs):captured['payload']=kwargs;return response('ok')['raw_response']
        def config(**kwargs):captured['config']=kwargs;return object()
        def factory(*args,**kwargs):captured['client']=(args,kwargs);return Client()
        transport=bedrock_transport(self.package['settings'],client_factory=factory,config_factory=config)
        payload=self.renderer.render_stage1('slot-01')['payload'];returned=transport(payload)
        self.assertEqual(captured['config']['retries']['total_max_attempts'],1)
        self.assertEqual(captured['payload'],payload);self.assertEqual(returned['retry_attempts'],0)

    def test_gate_cap_deadline_and_durable_failure_never_invoke_extra_transport(self):
        calls=[]
        gate=RequestGate(self.base/'gate',1,2000,lambda p:calls.append(p) or response('{}'),clock=lambda:1000)
        gate.invoke({'frozen':'payload'},task_id='task',attempt_id='one')
        with self.assertRaises(GateClosed):gate.invoke({},task_id='task',attempt_id='two')
        self.assertEqual(len(calls),1)
        with self.assertRaises(FileExistsError):RequestGate(self.base/'gate',1,2000,lambda p:None)
        expired=RequestGate(self.base/'expired',1,999,lambda p:calls.append(p),clock=lambda:1000)
        with self.assertRaises(GateClosed):expired.invoke({},task_id='task',attempt_id='one')
        self.assertEqual(len(calls),1)

    def test_durable_reservation_write_failure_closes_gate_without_transport(self):
        calls=[]
        gate=RequestGate(self.base/'write-failure',1,2000,lambda p:calls.append(p),clock=lambda:1000)
        with patch('bounded_requests.durable_json',side_effect=OSError('Synthetic disk full')):
            with self.assertRaises(OSError):gate.invoke({},task_id='task',attempt_id='one')
        with self.assertRaises(GateClosed):gate.invoke({},task_id='task',attempt_id='two')
        self.assertEqual(calls,[])


if __name__=='__main__':unittest.main()
