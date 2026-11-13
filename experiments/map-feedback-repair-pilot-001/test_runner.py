"""Fake transport/verifier only: exact frozen dispatch and real isolated revisions."""
import copy,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import run_pilot as r
import bounded_requests as bounded

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.plan,self.parents,self.trials=r.validate_bundle()
        self.sent=[];self.checked=[]

    def response(self,index,**changes):
        trial=self.trials[index];_,task,base,template=r.parent_parts(r.ROOT,trial)
        bodies={};guard,_=r.policy()
        # A syntax-admitted fake alteration; mathematical behavior is injected.
        for n in task['editable_files']:
            pre,suf=guard.split_seed(template[n].decode())
            bodies[n]=base[n].decode()[len(pre):-len(suf)]+'\n'
        result=dict(text=json.dumps(bodies),request_id=f'fake-{index}',retry_attempts=0,
                    stop_reason='end_turn',usage=dict(inputTokens=1,outputTokens=2,totalTokens=3))
        result.update(changes);result['content']=[dict(text=result['text'])]
        result['raw_response']=dict(output=dict(message=dict(content=result['content'])),usage=result['usage'],
            stopReason=result['stop_reason'],ResponseMetadata=dict(RequestId=result['request_id'],RetryAttempts=result['retry_attempts']))
        return result

    def transport(self,request):
        index=len(self.sent)
        self.assertEqual(request,r.load(r.ROOT/'frozen-001'/self.trials[index]['request_path']))
        self.sent.append(copy.deepcopy(request));return self.response(index)

    def collect(self,out,transport=None,verifier=None,**kwargs):
        return r.collect(out,transport or self.transport,verifier or self.verifier,100,
                         clock=lambda:0,check_runtime=False,**kwargs)

    def test_eight_exact_requests_fresh_stores_and_promotions(self):
        with tempfile.TemporaryDirectory() as d:
            rows=self.collect(d);self.assertEqual(len(rows),8);self.assertEqual(len(self.sent),8)
            revisions=set()
            for trial in self.trials:
                folder=Path(d)/trial['trial_id'];initial=r.load(folder/'initial.json');accepted=r.load(folder/'accepted.json')
                self.assertEqual(initial['revision'],accepted['base_revision']);self.assertNotEqual(initial['revision'],accepted['revision'])
                revisions.add(initial['revision']);revisions.add(accepted['revision'])
                self.assertEqual(r.load(folder/'final-head.json')['revision'],accepted['revision'])
                parent=r.parent_parts(r.ROOT,trial)[2]
                self.assertEqual(r.files(folder/'store/revisions'/initial['revision']/'files'),parent)
            self.assertEqual(len(revisions),16)
            ledger=r.load(Path(d)/'requests/ledger.json');self.assertTrue(ledger['closed'])
            self.assertEqual([x['attempt_id'] for x in ledger['reservations']],[t['trial_id'] for t in self.trials])
            self.assertTrue(r.load(Path(d)/'summary.json')['all_trials_processed'])

    def test_noop_repair_verified_once_without_promotion(self):
        trial=self.trials[0];row,task,base,template=r.parent_parts(r.ROOT,trial)
        response=r.load(r.ROOT/'frozen-001/parents'/trial['parent_trial']/'response.json')
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);store,snapshot=r.create_store(folder,r.ROOT,trial)
            result=r.evaluate(trial,response,folder,lambda fs:self.verifier(fs,4),r.ROOT,store,snapshot)
            self.assertEqual(result['outcome'],'PROOF_FAILURE');self.assertEqual(len(self.checked),1)
            self.assertEqual(store.snapshot().revision,snapshot.revision)
            self.assertEqual(r.files(folder/'candidate'),base)
            self.assertFalse((folder/'accepted.json').exists())

    def test_stale_promotion_stops_without_replacing_winner(self):
        trial=self.trials[0]
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);store,base=r.create_store(folder,r.ROOT,trial)
            def verifier(fs):
                evidence=self.verifier(fs);_,task,_,_=r.parent_parts(r.ROOT,trial)
                prepared=r.prepared(base,fs,task)
                result=r.RepositoryVerification(r.VerificationOutput(r.VerificationOutcome.SUCCESS,0,evidence['stdout'],''),evidence)
                store.promote(base,prepared,result)
                return evidence
            result=r.evaluate(trial,self.response(0),folder,verifier,r.ROOT,store,base)
            self.assertEqual(result['outcome'],'PROMOTION_REJECTED');self.assertTrue(result['stop'])
            self.assertFalse((folder/'accepted.json').exists());self.assertEqual(len(list((folder/'store/revisions').iterdir())),2)

    def test_missing_measurement_never_promotes(self):
        def bad(files):
            ev=self.verifier(files);ev['csv']={};ev['csv_sha256']={};return ev
        with tempfile.TemporaryDirectory() as d:
            rows=self.collect(d,verifier=bad);self.assertEqual(len(self.sent),1);self.assertTrue(rows[0]['stop'])
            folder=Path(d)/self.trials[0]['trial_id'];self.assertFalse((folder/'accepted.json').exists())

    def test_exact_analyst_replay_and_protected_edits_rejected(self):
        guard,envelope=r.policy()
        for trial in self.trials:
            row,task,base,template=r.parent_parts(r.ROOT,trial)
            repaired=r.files(r.ROOT/'inputs/experiments/map-order-diagnostic-002/fixtures'/(trial['parent_trial']+'-reordered'))
            self.assertEqual(len(repaired),9)
            bodies={}
            for name in task['editable_files']:
                prefix,suffix=guard.split_seed(template[name].decode())
                bodies[name]=repaired[name].decode()[len(prefix):-len(suffix)]
            candidate,_=r.decode(json.dumps(bodies),r.ROOT,trial);self.assertEqual(candidate,repaired)
            for body in ('assume false;','lemma Prove() ensures true {}','reveal K.Restrict;'):
                with self.assertRaises(r.OutputRejected):r.decode(json.dumps(dict.fromkeys(task['editable_files'],body)),r.ROOT,trial)
            altered=dict(base);altered['Kernel.dfy']+=b'\n'
            with self.assertRaises(ValueError):
                r.repair_protocol.apply_response(json.dumps(bodies),{n:b.decode() for n,b in altered.items()},
                    {n:b.decode() for n,b in template.items()},task,row['source_sha256'],guard,envelope)

    def test_no_cross_arm_diagnostic_leakage(self):
        for sharing in ('shared','separate'):
            requests={arm:r.load(r.ROOT/'frozen-001/requests'/f'deep-{sharing}-{arm}.json') for arm in self.plan['feedback_conditions']}
            detailed=requests['verifier_diagnostics'];masked=requests['failure_notice_only']
            self.assertEqual(detailed['system'],masked['system'])
            a=detailed['messages'][0]['content'][0]['text'];b=masked['messages'][0]['content'][0]['text']
            import re
            strip=lambda s:re.sub(r'<verifier_feedback>.*?</verifier_feedback>','MASK',s,flags=re.S)
            self.assertEqual(strip(a),strip(b));self.assertNotIn('a precondition for this call could not be proved',b)


    def verifier(self, files, code=0):
            self.checked.append(copy.deepcopy(files))
            import csv,io,hashlib
            units=r.target_metrics.RESTRICTION_EXPECTED if b'function Merge(' in files.get('Kernel.dfy',b'') else r.target_metrics.EXPECTED
            text=io.StringIO();writer=csv.writer(text);writer.writerow(r.target_metrics.HEADER)
            for symbol,kinds in units.items():
                for kind in sorted(kinds):
                    writer.writerow([f'{symbol} ({kind})','Failed' if code==4 and symbol=='HelperA.Prove' else 'Passed','00:00:00.001','1','0'])
            raw=text.getvalue();count=sum(len(k) for k in units.values())
            return dict(exit_code=code, source_sha256=r.hashes(files),
                        stdout=f'Dafny program verifier finished with {count-(code==4)} verified, {int(code==4)} errors\n',
                        stderr='', attempts=1, model_calls=0, elapsed_seconds=0.1,
                        csv={'fake.csv':raw},csv_sha256={'fake.csv':hashlib.sha256(raw.encode()).hexdigest()},
                        command=['timeout', '-k', '5s', '60s', 'dafny', 'verify', '--verify-included-files', '--log-format','csv','All.dfy'])

    def test_transport_timeout_stops_and_cannot_resume(self):
            def fail(request):
                self.sent.append(request)
                raise TimeoutError('FAKE')
            with tempfile.TemporaryDirectory() as d:
                rows = self.collect(d, transport=fail)
                self.assertEqual(len(self.sent), 1)
                self.assertEqual(rows[0]['outcome'], 'REQUEST_STOP')
                self.assertEqual(r.load(Path(d) / 'requests/ledger.json')['reservations'][0]['status'],
                                 'AMBIGUOUS_OR_UNSAVED')
                with self.assertRaises(FileExistsError):
                    self.collect(d)
                self.assertEqual(len(self.sent), 1)

    def test_rejections_and_truncations_consume_all_slots(self):
            for mode in ('OUTPUT_REJECTED', 'OUTPUT_TRUNCATED'):
                self.sent = []
                def invalid(request):
                    index = len(self.sent)
                    self.sent.append(request)
                    changes = {'text': 'not JSON'} if mode == 'OUTPUT_REJECTED' else {'stop_reason': 'max_tokens'}
                    return self.response(index, **changes)
                with tempfile.TemporaryDirectory() as d:
                    rows = self.collect(d, transport=invalid)
                    self.assertEqual(len(self.sent), 8)
                    self.assertEqual({x['outcome'] for x in rows}, {mode})
                    self.assertFalse(self.checked)

    def test_verifier_failure_classification_and_timeouts(self):
            for code, expected, count in [(4, 'PROOF_FAILURE', 8), (2, 'FRONTEND_ERROR', 8),
                                           (124, 'VERIFIER_STOP', 1)]:
                self.sent, self.checked = [], []
                with tempfile.TemporaryDirectory() as d:
                    rows = self.collect(d, verifier=lambda fs: self.verifier(fs, code))
                    self.assertEqual(len(self.sent), count)
                    self.assertEqual({x['outcome'] for x in rows}, {expected})
            warning = self.verifier({})
            warning.update(exit_code=2, stderr='program.dfy(1,0): Warning: missing trigger\n'
                           'Compilation failed because warnings were found and --allow-warnings is false')
            self.assertEqual(r.outcome_for_evidence(warning), 'WARNING_ONLY')
            warning['stdout'] = 'unresolved identifier'
            self.assertEqual(r.outcome_for_evidence(warning), 'FRONTEND_ERROR')

    def test_metadata_errors_stop(self):
            for duplicate in (True, False):
                self.sent, self.checked = [], []
                def invalid(request):
                    index = len(self.sent)
                    self.sent.append(request)
                    return self.response(index, request_id='same', retry_attempts=0 if duplicate else 1)
                with tempfile.TemporaryDirectory() as d:
                    rows = self.collect(d, transport=invalid)
                    self.assertEqual(len(self.sent), 2 if duplicate else 1)
                    self.assertEqual(rows[-1]['outcome'], 'REQUEST_METADATA_STOP')

    def test_runtime_drift_stops_before_next_request(self):
            times = []
            def validate(root):
                times.append(root)
                if len(times) == 3:
                    raise ValueError('fake runtime drift')
            with tempfile.TemporaryDirectory() as d, patch.object(r, 'validate_runtime', side_effect=validate):
                with self.assertRaises(ValueError):
                    r.collect(d, self.transport, self.verifier, 100, clock=lambda: 0)
                self.assertEqual(len(self.sent), 1)
                self.assertEqual(r.load(Path(d) / 'summary.json')['reserved_calls'], 1)

    def test_sdk_attempts_and_payload(self):
            request = r.load(r.ROOT / 'frozen-001' / self.trials[0]['request_path'])
            seen = {}
            response = self.response(0)
            class Client:
                def converse(self, **kwargs):
                    seen['payload'] = kwargs
                    return response['raw_response']
            def factory(service, **kwargs):
                seen.update(service=service, config=kwargs['config'])
                return Client()
            reply = bounded.bedrock_transport(self.plan, client_factory=factory,
                                               config_factory=lambda **kwargs: kwargs)(request)
            self.assertEqual(seen['config']['retries']['total_max_attempts'], 1)
            self.assertEqual(seen['payload'], request)
            self.assertEqual(reply['retry_attempts'], 0)

    def test_deadline_after_each_reservation_step(self):
            for ticks in ([2], [0, 0, 2], [0, 0, 0, 0, 2]):
                clock = iter(ticks)
                with tempfile.TemporaryDirectory() as d:
                    gate = bounded.RequestGate(Path(d) / 'requests', 8, 1, self.transport,
                                               clock=lambda: next(clock))
                    with self.assertRaises(bounded.GateClosed):
                        gate.invoke({}, task_id='t', attempt_id='a')
                    self.assertFalse(self.sent)
                    self.assertTrue(gate.closed)
                    self.assertTrue(all('dispatch_started_at_epoch' not in x for x in gate.state['reservations']))

    def test_spending_cap_and_persistence_failure(self):
            with tempfile.TemporaryDirectory() as d:
                sent = []
                gate = bounded.RequestGate(Path(d) / 'limit', 1, 100, lambda p: sent.append(p) or {}, clock=lambda: 0)
                gate.invoke({}, task_id='t', attempt_id='a')
                with self.assertRaises(bounded.GateClosed):
                    gate.invoke({}, task_id='t', attempt_id='b')
                self.assertEqual(len(sent), 1)
                gate = bounded.RequestGate(Path(d) / 'disk', 8, 100, lambda p: sent.append(p) or {}, clock=lambda: 0)
                with patch.object(bounded, 'durable_json', side_effect=OSError('FAKE DISK')):
                    with self.assertRaises(OSError):
                        gate.invoke({}, task_id='t', attempt_id='a')
                with self.assertRaises(bounded.GateClosed):
                    gate.invoke({}, task_id='t', attempt_id='b')
                self.assertEqual(len(sent), 1)

    def test_response_persistence_failure_closes_gate(self):
            original = bounded.durable_json
            def write(path, value):
                if path.name.startswith('response-'):
                    raise OSError('FAKE')
                original(path, value)
            with tempfile.TemporaryDirectory() as d:
                sent = []
                gate = bounded.RequestGate(Path(d) / 'requests', 8, 100, lambda p: sent.append(p) or {}, clock=lambda: 0)
                with patch.object(bounded, 'durable_json', side_effect=write):
                    with self.assertRaises(OSError):
                        gate.invoke({}, task_id='t', attempt_id='a')
                with self.assertRaises(bounded.GateClosed):
                    gate.invoke({}, task_id='t', attempt_id='b')
                self.assertEqual(len(sent), 1)

    def test_authorization_and_seed_pins(self):
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / 'runtime-freeze.json').write_text('{}')
                auth = dict(authorized=True, max_calls=8, automatic_retries=False, reassign_unused=False,
                            authorization_basis='FAKE TEST', expires_at_epoch=100,
                            proposal_freeze_sha256=r.PROPOSAL_SHA,
                            runtime_freeze_sha256=r.sha(root / 'runtime-freeze.json'))
                bounded.durable_json(root / 'authorization.json', auth)
                self.assertEqual(r.validate_authorization(root, 0)[1], 100)
                for change in ({'max_calls': 9}, {'automatic_retries': True}, {'expires_at_epoch': 0},
                               {'runtime_freeze_sha256': 'wrong'}, {'reassign_unused': True}):
                    bounded.durable_json(root / 'authorization.json', dict(auth, **change))
                    with self.assertRaises(ValueError):
                        r.validate_authorization(root, 0)
                shutil.copytree(r.ROOT / 'inputs', root / 'inputs')
                shutil.copytree(r.ROOT / 'frozen-001', root / 'frozen-001')
                candidate = root / 'frozen-001/parents/map-balanced-04/base/ClientA.dfy'
                candidate.write_text(candidate.read_text() + '\n')
                with self.assertRaises(ValueError):
                    r.validate_bundle(root)


    def reviewed_fake_run(self,root,code=0):
        import review_results
        shutil.copytree(r.ROOT/'frozen-001',root/'frozen-001');shutil.copytree(r.ROOT/'inputs',root/'inputs')
        (root/'runtime-freeze.json').write_text('{}');out=root/'model-001';out.mkdir()
        shutil.copytree(root/'frozen-001',out/'frozen-001');shutil.copytree(root/'inputs',out/'inputs')
        shutil.copy2(root/'runtime-freeze.json',out/'runtime-freeze.json');(out/'runtime').mkdir()
        (out/'runtime/marker.py').write_text('fake audit fixture')
        pins=dict(runtime_sha256=r.inventory(out/'runtime'))
        r.durable_json(out/'authorization.json',dict(authorized=True,max_calls=8,automatic_retries=False,reassign_unused=False,
            expires_at_epoch=100,proposal_freeze_sha256=r.PROPOSAL_SHA,runtime_freeze_sha256=r.sha(root/'runtime-freeze.json')))
        r.durable_json(out/'environment.json',dict(dafny=self.plan['verifier']['toolchain'],z3=self.plan['verifier']['z3'],job_id='FAKE',host='fake-compute'))
        self.collect(out,verifier=lambda fs:self.verifier(fs,code),root=root)
        return review_results,pins,out

    def test_review_replays_promoted_and_failed_runs(self):
        for code in (0,4):
            self.sent=[];self.checked=[]
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);reviewer,pins,out=self.reviewed_fake_run(root,code)
                with patch.object(r,'validate_runtime',return_value=pins):report=reviewer.review(root)
                self.assertEqual(report['strict_passes'],8 if code==0 else 0)
                self.assertEqual(report['unique_returned_requests'],8)
                self.assertEqual(report['protected_file_comparisons'],60)
                self.assertEqual(report['protected_body_boundaries'],12)

    def test_review_rejects_altered_original_revision(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);reviewer,pins,out=self.reviewed_fake_run(root)
            folder=out/self.trials[0]['trial_id'];initial=r.load(folder/'initial.json')
            source=folder/'store/revisions'/initial['revision']/'files/Kernel.dfy';source.write_bytes(source.read_bytes()+b'\n')
            with patch.object(r,'validate_runtime',return_value=pins),self.assertRaises(ValueError):reviewer.review(root)

if __name__=='__main__':unittest.main()
