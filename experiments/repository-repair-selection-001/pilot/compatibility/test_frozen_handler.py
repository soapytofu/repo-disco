"""One actual 32-slot batch through the unchanged handler; injected fakes only.

No SDK client, credentials, network, verifier process, session or admission is
used. The retained evidence is explicitly synthetic compatibility evidence.
"""
from collections import Counter
from pathlib import Path
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
REPO = PILOT.parents[2]
FROZEN = PILOT/'frozen-001'
RUNTIME = REPO/'experiments/research-window-20261114/execution-runtime'
FREEZE_SHA = '9a3ac2546edc6c79307826766af3517bdc8d9a8fe629a2ba0239660f4ead778a'
RUNTIME_SHA = 'ca24194ab90c932e0c514c1b390a80dd999645ccf07a9c937ea176f82b701b44'


def read(path): return json.loads(path.read_bytes())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value): path.write_text(json.dumps(value,indent=2)+'\n')


def load_handler():
    sys.path.insert(0,str(RUNTIME))
    spec = importlib.util.spec_from_file_location('selection_fake_handler',RUNTIME/'run_batch.py')
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)
    return handler


class FrozenHandler(unittest.TestCase):
    def test_all_frozen_slots_and_both_failure_paths(self):
        self.assertEqual(sha(FROZEN/'freeze.json'),FREEZE_SHA)
        self.assertEqual(sha(RUNTIME/'runtime-freeze.json'),RUNTIME_SHA)
        frozen = read(FROZEN/'freeze.json')
        self.assertFalse(frozen['execution_authorized'])
        artifact = HERE/'fake-run-001'
        self.assertFalse(artifact.exists(),'Never overwrite prior compatibility evidence')
        with tempfile.TemporaryDirectory(prefix='repodisco-selection-fake-') as directory:
            root = Path(directory)
            bundle = root/'bundle'
            bundle.mkdir()
            shutil.copytree(FROZEN,bundle/'frozen-001')
            for name,digest in frozen['repository_inputs_sha256'].items():
                source = REPO/name
                self.assertEqual(sha(source),digest,name)
                target = bundle/'inputs'/name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source,target)
            # A local validator hash fixture, explicitly not an admission/authorization.
            save(bundle/'batch-binding.json',dict(proposal_freeze_sha256=FREEZE_SHA,
                runtime_freeze_sha256=RUNTIME_SHA,authorized=False,fake_test_only=True))
            with patch('socket.socket',side_effect=AssertionError('Network forbidden')), \
                 patch('subprocess.Popen',side_effect=AssertionError('Processes forbidden')):
                batch = load_handler()
                with patch.object(batch,'consume_key',side_effect=AssertionError('Credentials forbidden')), \
                     patch.object(batch,'bedrock_transport',side_effect=AssertionError('SDK factory forbidden')), \
                     patch.object(batch,'verify_logged',side_effect=AssertionError('Dafny forbidden')):
                    settings,parents,trials = batch.validate_bundle(bundle)
                    batch.validate_runtime(bundle)
                    self.assertEqual(len(trials),32)
                    scope = read(bundle/'frozen-001/measurement-scope.json')
                    requested,verified = [],[]
                    sources_by_trial = {}
                    def sources(trial,variant):
                        group = settings['task_groups'][trial['task_id']]
                        inputs = bundle/'inputs'/settings['source_roots'][group]
                        case = next(c for c in read(inputs/'cases.json') if c['case_id']==trial['task_id']+'-'+variant)
                        result = batch.files(inputs/case['path'])
                        self.assertEqual(batch.hashes(result),case['source_sha256'])
                        return result
                    def payload_for(trial,variant):
                        _,task,_,template = batch.parent_parts(bundle,trial)
                        guard,_ = batch.policy(bundle)
                        reference = sources(trial,variant)
                        result = {}
                        for name in task['editable_files']:
                            prefix,suffix = guard.split_seed(template[name].decode())
                            text = reference[name].decode()
                            self.assertTrue(text.startswith(prefix) and text.endswith(suffix))
                            result[name] = text[len(prefix):-len(suffix)]
                        return result
                    def transport(payload):
                        index = len(requested)
                        self.assertLess(index,32)
                        trial = trials[index]
                        self.assertEqual(payload,read(bundle/'frozen-001'/trial['request_path']))
                        requested.append(trial['trial_id'])
                        variant = 'faulty' if index==31 else 'reference'
                        bodies = payload_for(trial,variant)
                        sources_by_trial[trial['trial_id']] = sources(trial,variant)
                        if index==30: bodies['HelperA.dfy'] = 'assume false;'
                        return dict(text=json.dumps(bodies),request_id='FAKE-OFFLINE-'+str(index+1),retry_attempts=0,
                                    stop_reason='end_turn',usage=dict(inputTokens=1,outputTokens=1),synthetic_compatibility_response=True)
                    def verifier(candidate):
                        index = len(requested)-1
                        trial = trials[index]
                        self.assertNotEqual(index,30,'Policy rejection must not reach verifier')
                        self.assertEqual(candidate,sources_by_trial[trial['trial_id']])
                        verified.append(trial['trial_id'])
                        units = scope['tasks'][trial['task_id']]['expected_units']
                        failed = set()
                        if index==31:
                            known = next(r for r in scope['control_measurements'] if r['case_id']==trial['task_id']+'-faulty')
                            failed = {n for n,passed in known['local_targets'].items() if not passed}
                            self.assertEqual(len(failed),1)
                        text = io.StringIO()
                        writer = csv.writer(text,lineterminator='\n')
                        writer.writerow(batch.target_metrics.HEADER)
                        count = 0
                        for name,kinds in units.items():
                            for kind in kinds:
                                count += 1
                                writer.writerow([name+' ('+kind+')','Failed' if name in failed else 'Passed','0:00:00.001','1','0'])
                        diagnostics = ('HelperA.dfy(1,1): Error: synthetic assertion might not hold\n' if failed else '')
                        diagnostics += f'Dafny program verifier finished with {count-len(failed)} verified, {len(failed)} errors\n'
                        csv_files = {'synthetic.csv':text.getvalue()}
                        return dict(command=['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy'],
                            exit_code=4 if failed else 0,stdout=diagnostics,stderr='',source_sha256=batch.hashes(candidate),
                            csv=csv_files,csv_sha256={n:hashlib.sha256(v.encode()).hexdigest() for n,v in csv_files.items()},
                            attempts=1,model_calls=0,synthetic_compatibility_verifier=True)
                    out = root/'fake-output'
                    deadline = read(RUNTIME/'runtime-freeze.json')['deadline_epoch']
                    rows = batch.collect(out,transport,verifier,deadline,root=bundle,clock=lambda:deadline-300)
                    summary,ledger = read(out/'summary.json'),read(out/'requests/ledger.json')
                    self.assertEqual(requested,[t['trial_id'] for t in trials])
                    self.assertEqual(len(verified),31)
                    self.assertEqual(Counter(r['outcome'] for r in rows),{'VERIFIED':30,'OUTPUT_REJECTED':1,'PROOF_FAILURE':1})
                    self.assertTrue(summary['all_trials_processed'])
                    self.assertEqual((summary['reserved_calls'],summary['completed_responses'],summary['verified']),(32,32,30))
                    self.assertEqual((ledger['limit'],ledger['closed'],ledger['closed_reason']),(32,True,'finished'))
                    self.assertEqual(len(ledger['reservations']),32)
                    self.assertTrue(all(r['status']=='COMPLETED' for r in ledger['reservations']))
                    self.assertEqual([r['attempt_id'] for r in ledger['reservations']],requested)
                    self.assertEqual(len({r['request_id'] for r in rows}),32)
                    report_rows = []
                    for trial,row in zip(trials,rows):
                        folder = out/trial['trial_id']
                        parent,task,base,_ = batch.parent_parts(bundle,trial)
                        initial,final = read(folder/'initial.json'),read(folder/'final-head.json')
                        accepted = (folder/'accepted.json').exists()
                        self.assertEqual(accepted,row['outcome']=='VERIFIED')
                        self.assertEqual(final['revision']!=initial['revision'],accepted)
                        if row['outcome']!='OUTPUT_REJECTED':
                            candidate = batch.files(folder/'candidate')
                            self.assertEqual(candidate,sources_by_trial[trial['trial_id']])
                            for name in base:
                                if name not in task['editable_files']: self.assertEqual(candidate[name],base[name])
                            metrics = read(folder/'target-metrics.json')
                            self.assertTrue(metrics['supplied_providers_verified'])
                        if not accepted: self.assertEqual(final['source_sha256'],parent['source_sha256'])
                        report_rows.append(dict(trial_id=trial['trial_id'],task_id=task['task_id'],outcome=row['outcome'],
                                                promoted=accepted,original_sha256=parent['source_sha256'],final_sha256=final['source_sha256']))
                    self.assertEqual(set(r['task_id'] for r in rows[:4]),set(parents))
                    # Existing ledger path cannot be reopened to silently repeat the batch.
                    with self.assertRaises(FileExistsError):
                        batch.RequestGate(out/'requests',32,deadline,transport,clock=lambda:deadline-300)
                    self.assertEqual(len(requested),32)
                    self.assertEqual(sha(FROZEN/'freeze.json'),FREEZE_SHA)
                    self.assertEqual(sha(RUNTIME/'runtime-freeze.json'),RUNTIME_SHA)
                    batch.validate_bundle(bundle)
                    batch.validate_runtime(bundle)
                    artifact.mkdir()
                    for name in ('summary.json','results.json'):
                        shutil.copyfile(out/name,artifact/name)
                    shutil.copytree(out/'requests',artifact/'requests')
                    for trial in trials:
                        source = out/trial['trial_id']
                        dest = artifact/trial['trial_id']
                        dest.mkdir()
                        for name in ('trial.json','result.json','initial.json','final-head.json','extraction.json','target-metrics.json','accepted.json'):
                            if (source/name).exists(): shutil.copyfile(source/name,dest/name)
                    save(artifact/'compatibility-completion.json',dict(synthetic_only=True,real_model_calls=0,real_verifier_calls=0,
                        sdk_clients_created=0,credentials_accessed=False,session_admissions_created=0,
                        proposal_freeze_sha256=FREEZE_SHA,execution_runtime_sha256=RUNTIME_SHA,
                        independent_fake_requests=32,independent_fake_verifications=31,all32_slots_completed=True,
                        frozen_request_order_preserved=True,all_four_tasks_promoted_in_first_block=True,
                        policy_rejection_before_verifier=True,proof_failure_without_promotion=True,
                        unchanged_protected_sources=True,completed_ledger_reopen_refused=True,rows=report_rows,
                        scope='Fake transport/verifier compatibility of unchanged repair-v1 batch handler; not model performance, real verification or global-session admission validation.'))
                    save(artifact/'inventory.json',{p.relative_to(artifact).as_posix():sha(p) for p in sorted(artifact.rglob('*')) if p.is_file()})


if __name__=='__main__':
    unittest.main(verbosity=2)
