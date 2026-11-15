"""Actual session/global/per-batch integration with fake model and verifier only."""
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
FIXTURE=REPO/'experiments/repair-diversity-pilot-002/frozen-001'
PRIVATE='FAKE_HANDOFF_SECRET_'+uuid.uuid4().hex


def load_driver(path):
    # Each test imports its isolated copy. This never reads a key or calls SDKs.
    for name in list(sys.modules):
        if name in ('window_budget','coordinator','bounded_requests','logging_verifier','target_metrics','repository_agent') or name=='language' or name.startswith('language.'):
            sys.modules.pop(name,None)
    name='isolated_session_driver'
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec)
    sys.modules[name]=obj;spec.loader.exec_module(obj);return obj


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        if not FIXTURE.is_dir():self.fail('Reviewed 32-trial fixture is required; no skip/fallback')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name).resolve()/'window';self.work.mkdir()
        for sibling in ('runtime','session-runtime-002'):
            shutil.copytree(HERE.parent/sibling,self.work/sibling,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(HERE,self.work/'execution-runtime',ignore=shutil.ignore_patterns('__pycache__','runtime-freeze.json','*.log'))
        self.d=load_driver(self.work/'execution-runtime/session_driver.py')
        d=self.d
        scope=json.loads((HERE.parent/'scope.json').read_text())
        scope['central_ledger_path']=str(self.work/'budget');scope['authorization_basis']='FAKE OFFLINE INTEGRATION ONLY'
        (self.work/'scope.json').write_bytes(d.w.canonical(scope)+b'\n')
        self.scope=scope;self.scope_sha=d.sha(self.work/'scope.json')
        runtime=self.work/'execution-runtime'
        dependencies={}
        for sibling in ('runtime','session-runtime-002'):
            for name,h in d.inventory(self.work/sibling).items():dependencies['../'+sibling+'/'+name]=h
        freeze=dict(schema='repodisco-session-execution-v1',scope_sha256=self.scope_sha,window_id=d.WINDOW_ID,deadline_epoch=d.DEADLINE,
            automatic_retries=False,sdk_total_max_attempts=1,handler_id=d.HANDLER_ID,model_settings=d.model_settings(),
            environment_versions=d.ENVIRONMENT,runtime_sha256=d.inventory(runtime),dependencies_sha256=dependencies)
        (runtime/'runtime-freeze.json').write_bytes(d.w.canonical(freeze)+b'\n')
        self.freeze=freeze;self.freeze_sha=d.sha(runtime/'runtime-freeze.json')
        self.bundle=self.work/'batches/repair-diversity-pilot-002';self.bundle.mkdir(parents=True)
        shutil.copytree(FIXTURE,self.bundle/'frozen-001')
        frozen=d.read_json(FIXTURE/'freeze.json')
        for name,h in frozen['repository_inputs_sha256'].items():
            source=REPO/name;self.assertEqual(d.sha(source),h)
            dest=self.bundle/'inputs'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        shutil.copy2(runtime/'runtime-freeze.json',self.bundle/'runtime-freeze.json')
        binding=dict(window_id=d.WINDOW_ID,batch_id='repair-diversity-pilot-002',max_calls=32,
            proposal_freeze_sha256=d.sha(self.bundle/'frozen-001/freeze.json'),runtime_freeze_sha256=self.freeze_sha,
            authorized=True,automatic_retries=False,max_calls_per_trial=1,model_settings=d.model_settings())
        (self.bundle/'batch-binding.json').write_bytes(d.w.canonical(binding)+b'\n')
        self.plan,self.parents,self.trials=d.batch.validate_bundle(self.bundle)
        self.environment=dict(job_id='1',partition='test',host='FAKE-COMPUTE',python='FAKE',versions=d.ENVIRONMENT,
                              requeue=False,model_connectivity_calls=0)
        self.descriptor=dict(schema=d.coordination.SCHEMA,sequence=1,previous_descriptor_sha256=d.coordination.ZERO,
            batch_id=binding['batch_id'],handler_id=d.HANDLER_ID,handler_binding_sha256=d.w.digest(d.w.canonical(freeze['runtime_sha256'])),
            artifact_directory=binding['batch_id'],freeze_path='frozen-001/freeze.json',freeze_sha256=binding['proposal_freeze_sha256'],
            runtime_path='runtime-freeze.json',runtime_sha256=self.freeze_sha,input_sha256=d.inventory(self.bundle),
            slots=[dict(trial_id=t['trial_id'],request_path='frozen-001/'+t['request_path'],request_sha256=t['request_sha256']) for t in self.trials],
            max_calls=32,sdk_total_max_attempts=1)
        (self.work/'admissions').mkdir();self.write_admission(self.descriptor)
        self.sent=[];self.consumed=[];self.closed=0;self.created=0;self.verifier_calls=0;self.behaviors={};self.now=d.DEADLINE-300
        self.addCleanup(os.environ.pop,'AWS_BEARER_TOKEN_BEDROCK',None)

    def write_admission(self,descriptor):
        path=self.work/'admissions'/f"{descriptor['sequence']:06}.json"
        path.write_bytes(self.d.w.canonical(descriptor)+b'\n')

    def response_text(self,trial):
        d=self.d;parent,task,base,template=d.batch.parent_parts(self.bundle,trial)
        guard,_=d.batch.policy(self.bundle)
        family={'saturating_assoc':'arithmetic','compression_fixed_point':'sequence','exact_gap_pair':'witness','overlap_override_restrict':'maps'}[trial['semantic_instance']]
        reference=self.bundle/'inputs/experiments/repair-diversity-expansion-001'/family/'fixtures'/trial['task_id']/'reference'
        result={}
        for name in task['editable_files']:
            pre,suf=guard.split_seed(template[name].decode());source=(reference/name).read_text()
            self.assertTrue(source.startswith(pre) and source.endswith(suf));result[name]=source[len(pre):len(source)-len(suf)]
        return json.dumps(result)

    def transport(self,payload):
        index=len(self.sent);trial=self.trials[index]
        expected=self.d.read_json(self.bundle/'frozen-001'/trial['request_path'])
        self.assertEqual(self.d.w.canonical(payload),self.d.w.canonical(expected));self.sent.append(payload)
        kind=self.behaviors.get(index,'VERIFIED')
        if kind=='TIMEOUT':raise TimeoutError(PRIVATE)
        if kind=='TAMPER_NEXT':
            p=self.bundle/'frozen-001'/self.trials[index+1]['request_path'];p.write_bytes(p.read_bytes()+b' ')
        text=self.response_text(trial)
        if kind=='OUTPUT_REJECTED':text=json.dumps({'HelperA.dfy':'assume false;'})
        if kind=='DUPLICATE_ID':rid='fake-1'
        else:rid='fake-'+str(index+1)
        return dict(text=text,request_id=rid,retry_attempts=1 if kind=='SDK_RETRY' else 0,
                    stop_reason='max_tokens' if kind=='OUTPUT_TRUNCATED' else 'end_turn',usage={'inputTokens':1,'outputTokens':1})

    def verifier(self,files):
        self.verifier_calls+=1;index=len(self.sent)-1;trial=self.trials[index]
        kind=self.behaviors.get(index,'VERIFIED');d=self.d
        if kind=='VERIFIER_ERROR':raise TimeoutError(PRIVATE)
        scope=d.read_json(self.bundle/'frozen-001/measurement-scope.json')['tasks'][trial['task_id']]
        buffer=io.StringIO();writer=csv.writer(buffer,lineterminator='\n');writer.writerow(d.batch.target_metrics.HEADER)
        units=scope['expected_units'];count=sum(len(v) for v in units.values())
        for name,kinds in units.items():
            for unit in kinds:
                passed=not(kind in ('PROOF_FAILURE','PROVIDER_FAILED','FAILED_TARGET_CSV') and name=='HelperA.Prove')
                if kind=='PROVIDER_FAILED' and name==next(n for n in units if not n.startswith(('Helper','Client'))):passed=False
                writer.writerow([f'{name} ({unit})','Passed' if passed else 'Failed','0:00:00.001','1','0'])
        text=buffer.getvalue();csv_files={'fake.csv':text}
        code=4 if kind in ('PROOF_FAILURE','PROVIDER_FAILED','EMPTY_CODE4') else 2 if kind in ('WARNING_ONLY','FRONTEND_ERROR','UNKNOWN_CODE2') else 0
        errors=1 if kind in ('PROOF_FAILURE','PROVIDER_FAILED') else 0
        stdout=f'Dafny program verifier finished with {count-errors} verified, {errors} errors\n'
        if kind in ('PROOF_FAILURE','PROVIDER_FAILED'):stdout='HelperA.dfy(1,1): Error: assertion might not hold\n'+stdout
        if kind=='WARNING_ONLY':stdout='HelperA.dfy(1,1): Warning: fake trigger\n'+stdout+'--allow-warnings is false\n'
        if kind=='FRONTEND_ERROR':stdout='HelperA.dfy(1,1): Error: FAKE parse error\n1 parse errors detected in All.dfy';csv_files={}
        if kind=='EMPTY_CODE4':stdout='';csv_files={}
        if kind=='UNKNOWN_CODE2':stdout='Unrecognized tool failure';csv_files={}
        if kind=='MISSING_CSV':csv_files={}
        if kind=='INCOHERENT_CSV':csv_files={'fake.csv':'Unexpected,Header\n'}
        source=d.batch.hashes(files)
        if kind=='SOURCE_MISMATCH':source['ClientA.dfy']='0'*64
        return dict(command=['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy'],
                    exit_code=code,stdout=stdout,stderr='',source_sha256=source,csv=csv_files,
                    csv_sha256={n:d.w.digest(v.encode()) for n,v in csv_files.items()},attempts=1,model_calls=0)

    def consume(self,path):
        self.consumed.append(str(path));os.environ['AWS_BEARER_TOKEN_BEDROCK']=PRIVATE

    def factory(self,settings):
        self.created+=1;self.assertEqual(settings,self.d.model_settings());owner=self
        class FakeManaged:
            def __call__(self,payload):return owner.transport(payload)
            def close(self):owner.closed+=1
        return FakeManaged()

    def sleep(self,seconds):
        (self.work/'session-001/SEAL').write_bytes(b'')

    def run_session(self):
        return self.d.execute_session(self.work,self.scope_sha,self.freeze_sha,handoff_path=self.work/'FAKE-HANDOFF',
            environment_probe=lambda:self.environment,key_consumer=self.consume,transport_factory=self.factory,
            verifier=self.verifier,clock=lambda:self.now,sleep=self.sleep)

    def output(self):return self.work/'session-001/runs/0001-repair-diversity-pilot-002'

    def assert_no_secret(self):
        self.assertNotIn('AWS_BEARER_TOKEN_BEDROCK',os.environ)
        for path in self.work.rglob('*'):
            if path.is_file():self.assertFalse(PRIVATE.encode() in path.read_bytes(),str(path))

    def test_all32_actual_frozen_trials_route_through_both_ledgers_and_promote(self):
        self.assertEqual(self.run_session(),'closed');self.assertEqual((len(self.sent),self.created,len(self.consumed),self.closed),(32,1,1,1))
        out=self.output();window=self.d.read_json(self.work/'budget/ledger.json');local=self.d.read_json(out/'requests/ledger.json')
        self.assertEqual(len(window['reservations']),32);self.assertEqual(len(local['reservations']),32)
        self.assertEqual([r['trial_id'] for r in window['reservations']],[t['trial_id'] for t in self.trials])
        for trial in self.trials:
            folder=out/trial['trial_id'];self.assertTrue((folder/'accepted.json').is_file())
            initial=self.d.read_json(folder/'initial.json');final=self.d.read_json(folder/'final-head.json')
            self.assertNotEqual(initial['revision'],final['revision'])
            _,task,base,_=self.d.batch.parent_parts(self.bundle,trial)
            for name in base:
                if name not in task['editable_files']:self.assertEqual(self.d.sha(folder/'candidate'/name),self.d.batch.hashes(base)[name])
        self.assertTrue((out/'window-runtime/window_budget.py').is_file());self.assertTrue((out/'session-runtime/coordinator.py').is_file())
        self.assert_no_secret()

    def test_normal_proof_parser_warning_and_frontend_failures_complete_without_promotion(self):
        self.behaviors={0:'PROOF_FAILURE',1:'OUTPUT_REJECTED',2:'WARNING_ONLY',3:'FRONTEND_ERROR',4:'OUTPUT_TRUNCATED'}
        self.assertEqual(self.run_session(),'closed');self.assertEqual(len(self.sent),32)
        rows=self.d.read_json(self.output()/'results.json')
        self.assertEqual([r['outcome'] for r in rows[:5]],list(self.behaviors.values()))
        for trial in self.trials[:5]:self.assertFalse((self.output()/trial['trial_id']/'accepted.json').exists())
        self.assert_no_secret()

    def test_timeout_is_charged_globally_and_locally_and_stops_without_retry(self):
        self.behaviors={0:'TIMEOUT'}
        with self.assertRaises(ValueError):self.run_session()
        self.assertEqual((len(self.sent),self.created,self.closed),(1,1,1))
        window=self.d.read_json(self.work/'budget/ledger.json');local=self.d.read_json(self.output()/'requests/ledger.json')
        self.assertEqual(len(window['reservations']),1);self.assertEqual(len(local['reservations']),1)
        self.assertIsNotNone(window['terminal_reason']);self.assertFalse(self.d.read_json(self.output()/'summary.json')['all_trials_processed'])
        self.assert_no_secret()

    def test_verifier_infrastructure_failure_stops_after_one_recorded_response(self):
        self.behaviors={0:'VERIFIER_ERROR'}
        with self.assertRaises(ValueError):self.run_session()
        self.assertEqual(len(self.sent),1);self.assertFalse((self.output()/self.trials[0]['trial_id']/'accepted.json').exists());self.assert_no_secret()

    def test_verifier_source_mismatch_cannot_promote_or_continue(self):
        self.behaviors={0:'SOURCE_MISMATCH'}
        with self.assertRaises(ValueError):self.run_session()
        self.assertEqual(len(self.sent),1);self.assertFalse((self.output()/self.trials[0]['trial_id']/'accepted.json').exists())

    def test_input_drift_between_trials_stops_before_second_request(self):
        self.behaviors={0:'TAMPER_NEXT'}
        with self.assertRaises(ValueError):self.run_session()
        self.assertEqual(len(self.sent),1);self.assertIsNotNone(self.d.read_json(self.work/'budget/ledger.json')['terminal_reason'])

    def test_duplicate_request_id_is_terminal_without_retry(self):
        self.behaviors={1:'DUPLICATE_ID'}
        with self.assertRaises(ValueError):self.run_session()
        self.assertEqual(len(self.sent),2);self.assert_no_secret()

    def assert_evidence_stop(self,kind,expected):
        self.behaviors={0:kind}
        with self.assertRaises(ValueError):self.run_session()
        self.assertEqual(len(self.sent),1)
        summary=self.d.read_json(self.output()/'summary.json')
        self.assertEqual(summary['verified'],0);self.assertFalse(summary['all_trials_processed'])
        self.assertEqual(summary['results'][0]['outcome'],expected)
        self.assertFalse((self.output()/self.trials[0]['trial_id']/'accepted.json').exists())
        self.assertIsNotNone(self.d.read_json(self.work/'budget/ledger.json')['terminal_reason'])

    def test_empty_code4_is_evidence_error_not_proof_result(self):
        self.assert_evidence_stop('EMPTY_CODE4','EVIDENCE_MISMATCH')

    def test_unknown_code2_is_evidence_error_not_frontend_result(self):
        self.assert_evidence_stop('UNKNOWN_CODE2','EVIDENCE_MISMATCH')

    def test_failed_immutable_provider_stops_after_model_proof_failure(self):
        self.assert_evidence_stop('PROVIDER_FAILED','MEASUREMENT_STOP')

    def test_exit_zero_missing_csv_is_not_promoted_or_counted(self):
        self.assert_evidence_stop('MISSING_CSV','MEASUREMENT_STOP')

    def test_exit_zero_incoherent_csv_is_not_promoted_or_counted(self):
        self.assert_evidence_stop('INCOHERENT_CSV','MEASUREMENT_STOP')

    def test_exit_zero_failed_target_csv_is_not_promoted_or_counted(self):
        self.assert_evidence_stop('FAILED_TARGET_CSV','MEASUREMENT_STOP')

    def test_duplicate_admission_cannot_rerun_completed_batch(self):
        duplicate=dict(self.descriptor,sequence=2,previous_descriptor_sha256=self.d.w.digest(self.d.w.canonical(self.descriptor)+b'\n'))
        self.write_admission(duplicate)
        with self.assertRaises(ValueError):self.run_session()
        self.assertEqual(len(self.sent),32);self.assertEqual(len(self.consumed),1);self.assertEqual(self.created,1)
        self.assertTrue((self.output()/'completion.json').is_file())
        self.assertIsNotNone(self.d.read_json(self.work/'budget/ledger.json')['terminal_reason'])

    def test_execution_freeze_hash_drift_prevents_key_consumption(self):
        p=self.work/'execution-runtime/runtime-freeze.json';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(ValueError):self.run_session()
        self.assertFalse(self.consumed);self.assertFalse(self.sent)

    def test_preexisting_authority_is_rejected_before_key_consumption(self):
        (self.work/'budget').mkdir()
        with self.assertRaises(ValueError):self.run_session()
        self.assertFalse(self.consumed);self.assertEqual(self.created,0)

    def test_scope_or_model_binding_drift_never_consumes_key(self):
        binding=self.d.read_json(self.bundle/'batch-binding.json');binding['model_settings']['model_id']='UNAPPROVED'
        (self.bundle/'batch-binding.json').write_bytes(self.d.w.canonical(binding))
        with self.assertRaises(ValueError):self.run_session()
        self.assertFalse(self.consumed);self.assertFalse(self.sent)

    def test_protected_source_drift_never_dispatches(self):
        row=self.parents[self.trials[0]['parent_id']];p=self.bundle/'frozen-001'/row['base_path']/'ClientA.dfy';p.write_bytes(p.read_bytes()+b'\n')
        with self.assertRaises(ValueError):self.run_session()
        self.assertFalse(self.consumed);self.assertFalse(self.sent)

    def test_out_of_order_admission_is_rejected_before_key(self):
        (self.work/'admissions/000001.json').rename(self.work/'admissions/000002.json')
        with self.assertRaises(ValueError):self.run_session()
        self.assertFalse(self.consumed)

    def test_admission_descriptor_tampering_never_dispatches(self):
        d=dict(self.descriptor);d['slots']=list(reversed(d['slots']));self.write_admission(d)
        with self.assertRaises(ValueError):self.run_session()
        self.assertFalse(self.consumed)

    def test_no_compute_or_wrong_sdk_environment_rejected_before_key(self):
        self.environment=dict(self.environment,versions=dict(self.d.ENVIRONMENT,boto3='wrong'))
        with self.assertRaises(ValueError):self.run_session()
        self.assertFalse(self.consumed)
        with patch.dict(os.environ,{},clear=True),patch.object(self.d.socket,'gethostname',return_value='holylogin01'):
            with self.assertRaises(ValueError):self.d.live_environment()

    def test_exact_sdk_config_and_single_client_with_fake_sdk(self):
        d=self.d;created=[];sent=[];closed=[];configs=[]
        class FakeClient:
            def converse(self,**payload):
                sent.append(payload);return {'output':{'message':{'content':[{'text':'FAKE'}]}},'ResponseMetadata':{'RequestId':'id','RetryAttempts':0}}
            def close(self):closed.append(True)
        def factory(*args,**kwargs):created.append((args,kwargs));return FakeClient()
        def config(**kwargs):configs.append(kwargs);return kwargs
        transport=d.ManagedTransport(d.model_settings(),client_factory=factory,config_factory=config)
        request=d.read_json(self.bundle/'frozen-001'/self.trials[0]['request_path']);response=transport(request);transport.close()
        self.assertEqual(len(created),1);self.assertEqual(len(sent),1);self.assertEqual(closed,[True]);self.assertEqual(response['retry_attempts'],0)
        self.assertEqual(configs,[dict(connect_timeout=15,read_timeout=180,retries={'mode':'standard','total_max_attempts':1})])
        with self.assertRaises(ValueError):transport(request)


if __name__=='__main__':unittest.main(verbosity=2)
