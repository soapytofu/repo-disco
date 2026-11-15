"""Offline/fake-only admission checks. No subprocess/provider/verifier is run."""
import copy
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import next_admission as a

HERE=Path(__file__).resolve().parent
WINDOW=HERE.parent
REPO=WINDOW.parent.parent


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(a.canonical(value)+b'\n')


class ActualFrozenBundle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory()
        cls.window=Path(cls.temporary.name)/'window';cls.window.mkdir()
        for name in ('execution-runtime','runtime','session-runtime-002'):
            shutil.copytree(WINDOW/name,cls.window/name)
        shutil.copyfile(WINDOW/'scope.json',cls.window/'scope.json')
        (cls.window/'batches').mkdir()
        cls.output=Path(cls.temporary.name)/'prepared'
        cls.descriptor=a.prepare(cls.window,REPO,cls.output)

    @classmethod
    def tearDownClass(cls): cls.temporary.cleanup()

    def test_actual_frozen_bundle_all_32_slots_decode_exactly_without_verification(self):
        bundle=self.window/'batches'/a.BATCH;driver=a.driver(self.window)
        plan,parents,trials=driver.batch.validate_bundle(bundle)
        self.assertEqual(len(trials),32)
        self.assertEqual(a.descriptor_for(self.window,bundle),self.descriptor)
        self.assertEqual(len(self.descriptor['input_sha256']),1207)
        self.assertEqual([x['trial_id'] for x in self.descriptor['slots']],[x['trial_id'] for x in trials])
        for trial in trials:
            _,task,base,template=driver.batch.parent_parts(bundle,trial)
            guard,_=driver.batch.policy(bundle)
            bodies={}
            for name in task['editable_files']:
                prefix,suffix=guard.split_seed(template[name].decode())
                bodies[name]=base[name].decode()[len(prefix):-len(suffix)]
            candidate,decision=driver.batch.decode(json.dumps(bodies),bundle,trial)
            self.assertEqual(candidate,base)
            self.assertFalse(decision['semantic_verification_performed'])
        self.assertFalse((self.window/'admissions').exists())
        self.assertFalse((self.window/'budget').exists())

    def test_extra_input_and_repeated_prepare_rejected(self):
        with self.assertRaisesRegex(ValueError,'restart'):a.prepare(self.window,REPO,self.output)
        bundle=self.window/'batches'/a.BATCH
        path=bundle/'inputs/extra.json';path.write_text('{}')
        try:
            with self.assertRaises(ValueError):a.descriptor_for(self.window,bundle)
        finally:path.unlink()

    def test_actual_published_predecessor_receipts_and_coordinator_paths(self):
        previous=REPO/'experiments/repair-diversity-pilot-002'
        for name in ('admissions',):shutil.copytree(WINDOW/name,self.window/name)
        shutil.copytree(WINDOW/'batches'/a.FIRST,self.window/'batches'/a.FIRST)
        shutil.copytree(previous/'window-evidence-001/session',self.window/'session-001')
        shutil.copytree(previous/'window-evidence-001/budget',self.window/'budget')
        shutil.copytree(previous/'model-001',self.window/'session-001/runs'/a.FIRST_RUN)
        for name in ('submission-001.lock','submission-001.json'):
            shutil.copyfile(previous/'window-evidence-001'/name,self.window/name)
        d=a.driver(self.window)
        scope=a.load(self.window/'scope.json')
        freeze=a.load(self.window/'execution-runtime/runtime-freeze.json')
        old_ids={s['trial_id'] for s in a.load(self.window/'admissions/000001.json')['slots']}
        self.assertFalse(old_ids & {s['trial_id'] for s in self.descriptor['slots']})
        owner=a.load(self.window/'budget/ledger.json')['owner_session']
        probe=lambda:dict(job_id=a.JOB,state='RUNNING',node=owner['host'].split('.')[0],workdir=a.REMOTE)
        # The only stub is the remote absolute-path execution check. All actual
        # code pins, receipts, source inventories and ledger fields are read.
        with patch.object(d,'validate_execution',return_value=(scope,freeze)),patch.object(a,'driver',return_value=d):
            result=a.audit(self.window,self.descriptor,staged=True,job_probe=probe,clock=lambda:a.DEADLINE-100)
        self.assertEqual(result['completed'],32)
        self.assertEqual(result['remaining_before'],96)

    def test_operator_ambiguous_mutation_is_called_once_then_inspect_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);save(out/'descriptor.json',self.descriptor)
            calls=[]
            def transport(action,*args):
                calls.append(action)
                if action=='inspect':return {'read_only':True}
                raise TimeoutError('Synthetic ambiguous SSH result')
            with self.assertRaises(TimeoutError):a.operator_action('admit',self.window,out,transport=transport)
            self.assertTrue((out/'admit-attempt.lock').is_file())
            self.assertEqual(a.load(out/'admit-unconfirmed.json')['inspect_only'],True)
            with self.assertRaises(FileExistsError):a.operator_action('admit',self.window,out,transport=transport)
            self.assertEqual(calls,['admit'])
            self.assertEqual(a.operator_action('inspect',self.window,out,transport=transport),{'read_only':True})
            self.assertEqual(calls,['admit','inspect'])

    def test_remote_command_uses_stdin_for_inventory_and_hard_timeout_fake_only(self):
        fake=SimpleNamespace(returncode=0,stdout=b'{"synthetic":true}\n',stderr=b'')
        with patch.object(a.subprocess,'run',return_value=fake) as run:
            self.assertEqual(a.remote_call('check',self.descriptor),{'synthetic':True})
        args,kwargs=run.call_args
        self.assertEqual(kwargs['timeout'],120)
        self.assertEqual(kwargs['input'],a.canonical(self.descriptor)+b'\n')
        self.assertLess(len(args[0][-1]),128*1024)
        self.assertNotIn('repair-selection-01',args[0][-1])


class FakeLiveState(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in ['admissions','batches/'+a.FIRST,'session-001/queue','session-001/runs/'+a.FIRST_RUN,
                     'runtime','session-runtime-002']:
            (self.root/name).mkdir(parents=True,exist_ok=True)
        (self.root/'runtime/window_budget.py').write_text('synthetic gate')
        (self.root/'session-runtime-002/coordinator.py').write_text('synthetic coordinator')
        self.scope=dict(window_id=a.WINDOW_ID,max_calls=128,deadline_epoch=a.DEADLINE)
        self.job=dict(job_id=a.JOB,state='RUNNING',node='fake-node',workdir=a.REMOTE)
        self.first=dict(batch_id=a.FIRST,sequence=1,runtime_sha256=a.RUNTIME,input_sha256={},freeze_sha256='f'*64,
                        max_calls=32,sdk_total_max_attempts=1,
                        slots=[dict(trial_id=f'old-{i}',request_sha256='a'*64) for i in range(32)])
        save(self.root/'admissions/000001.json',self.first)
        previous=a.sha(self.root/'admissions/000001.json')
        self.addCleanup(patch.stopall)
        patch.object(a,'PREVIOUS',previous).start()
        shutil.copyfile(self.root/'admissions/000001.json',self.root/'session-001/queue'/('0001-'+a.FIRST+'.json'))
        save(self.root/'submission-001.json',{'job_id':a.JOB})
        (self.root/'submission-001.lock').write_text('synthetic existing submission')
        self.status=dict(phase='completed',reason='batch_complete',active_batch_id=None,completed_batch_ids=[a.FIRST],
            window_reservations=32,queued=[dict(batch_id=a.FIRST,descriptor_sha256=previous,sequence=1)],deadline_epoch=a.DEADLINE)
        save(self.root/'session-001/status.json',self.status)
        self.owner=dict(pid=123,host='fake-node.example')
        scope_hash=a.digest(a.canonical(self.scope))
        so=dict(pid=123,scope_sha256=scope_hash,window_gate_sha256=a.sha(self.root/'runtime/window_budget.py'),
                coordinator_sha256=a.sha(self.root/'session-runtime-002/coordinator.py'))
        save(self.root/'session-001/owner.json',so)
        save(self.root/'budget/research-session.lock/owner.json',so)
        save(self.root/'budget/owner.lock/owner.json',self.owner)
        manifest={k:self.first[k] for k in ['batch_id','freeze_sha256','runtime_sha256','max_calls','sdk_total_max_attempts','slots']}
        mh=a.digest(a.canonical(manifest))
        self.rows=[dict(sequence=i+1,status='COMPLETED',batch_id=a.FIRST,manifest_sha256=mh,
                       trial_id=s['trial_id'],request_sha256=s['request_sha256'],request_id=f'fake-request-{i}')
                   for i,s in enumerate(manifest['slots'])]
        self.ledger=dict(schema='synthetic-window-ledger',scope=self.scope,scope_sha256=scope_hash,terminal_reason=None,
                         owner_session=self.owner,batches=[dict(manifest=manifest,manifest_sha256=mh)],reservations=self.rows)
        save(self.root/'budget/ledger.json',self.ledger)
        patch.object(a,'PREVIOUS_LEDGER',a.sha(self.root/'budget/ledger.json')).start()
        receipt=dict(batch_id=a.FIRST,descriptor_sha256=previous,completed_trials=[s['trial_id'] for s in self.first['slots']],
                     request_ids=[r['request_id'] for r in self.rows],evidence_sha256={})
        save(self.root/'session-001/runs'/a.FIRST_RUN/'completion.json',receipt)
        patch.object(a,'PREVIOUS_RECEIPT',a.sha(self.root/'session-001/runs'/a.FIRST_RUN/'completion.json')).start()
        self.entries={'data.json':b'{"synthetic":true}\n'}
        self.descriptor=dict(max_calls=32,input_sha256={n:a.digest(b) for n,b in self.entries.items()},
                             slots=[dict(trial_id=f'new-{i}') for i in range(32)])
        stub=SimpleNamespace(w=SimpleNamespace(SCHEMA='synthetic-window-ledger'),
                            validate_execution=lambda *args:(self.scope,{}))
        patch.object(a,'driver',return_value=stub).start()
        def exact_descriptor(window,bundle):
            a.require(a.inventory(bundle)==self.descriptor['input_sha256'],'Synthetic bundle drift')
            return copy.deepcopy(self.descriptor)
        patch.object(a,'descriptor_for',side_effect=exact_descriptor).start()
        self.probe=lambda:copy.deepcopy(self.job)
        self.clock=lambda:a.DEADLINE-100

    def stage(self):
        archive=io.BytesIO()
        with tarfile.open(fileobj=archive,mode='w:gz') as tar:
            for name,raw in self.entries.items():
                info=tarfile.TarInfo(name);info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
        return a.remote_stage(self.root,self.descriptor,archive.getvalue(),job_probe=self.probe,clock=self.clock)

    def test_staging_has_no_admission_or_budget_mutation_and_cannot_repeat(self):
        before=a.inventory(self.root/'budget')
        result=self.stage()
        self.assertFalse(result['admission_published'])
        self.assertEqual(a.inventory(self.root/'budget'),before)
        self.assertEqual(list((self.root/'admissions').iterdir()),[self.root/'admissions/000001.json'])
        with self.assertRaises(ValueError):self.stage()

    def test_exact_idle_admission_preserves_owner_and_ledger_and_is_exclusive(self):
        self.stage();before=a.inventory(self.root/'budget')
        result=a.remote_admit(self.root,self.descriptor,job_probe=self.probe,clock=self.clock)
        self.assertTrue(result['admission_published'])
        self.assertEqual(a.inventory(self.root/'budget'),before)
        self.assertEqual((self.root/'admissions/000002.json').read_bytes(),a.canonical(self.descriptor)+b'\n')
        self.assertTrue((self.root/'admission-002.lock').exists())
        self.assertEqual((self.root/'admission-002.descriptor.tmp').stat().st_ino,(self.root/'admissions/000002.json').stat().st_ino)
        with self.assertRaises(ValueError):a.remote_admit(self.root,self.descriptor,job_probe=self.probe,clock=self.clock)

    def test_active_terminal_ambiguous_or_different_owner_states_reject(self):
        self.stage()
        for field,value in [('active_batch_id','fake-active'),('phase','closed'),('completed_batch_ids',[])]:
            altered=dict(self.status,**{field:value});save(self.root/'session-001/status.json',altered)
            with self.assertRaises(ValueError):a.audit(self.root,self.descriptor,staged=True,job_probe=self.probe,clock=self.clock)
        save(self.root/'session-001/status.json',self.status)
        for modify in ('ambiguous','extra','terminal','owner'):
            state=copy.deepcopy(self.ledger)
            if modify=='ambiguous':state['reservations'][0]['status']='RESERVED'
            elif modify=='extra':state['batches'].append(copy.deepcopy(state['batches'][0]))
            elif modify=='terminal':state['terminal_reason']='unknown_request'
            else:state['owner_session']['pid']=999
            save(self.root/'budget/ledger.json',state)
            with self.assertRaises(ValueError):a.audit(self.root,self.descriptor,staged=True,job_probe=self.probe,clock=self.clock)
        save(self.root/'budget/ledger.json',self.ledger)
        self.job['state']='COMPLETED'
        with self.assertRaises(ValueError):a.audit(self.root,self.descriptor,staged=True,job_probe=self.probe,clock=self.clock)

    def test_prior_evidence_runtime_input_or_deadline_drift_rejects(self):
        self.stage()
        for name in ['session-001/runs/'+a.FIRST_RUN+'/extra.txt','admissions/000002.json','submission-002.lock',
                     'batches/'+a.BATCH+'/extra.txt','session-001/STOP']:
            path=self.root/name;path.write_text('synthetic drift')
            with self.assertRaises(ValueError):a.audit(self.root,self.descriptor,staged=True,job_probe=self.probe,clock=self.clock)
            path.unlink()
        with self.assertRaises(ValueError):a.audit(self.root,self.descriptor,staged=True,job_probe=self.probe,clock=lambda:a.DEADLINE)

    def test_fsync_failure_after_attempt_retains_lock_without_publication(self):
        self.stage()
        with patch.object(a,'sync_tree',side_effect=OSError('injected fsync failure')):
            with self.assertRaises(OSError):a.remote_admit(self.root,self.descriptor,job_probe=self.probe,clock=self.clock)
        self.assertTrue((self.root/'admission-002.lock').exists())
        self.assertFalse((self.root/'admissions/000002.json').exists())
        with self.assertRaises(FileExistsError):a.remote_admit(self.root,self.descriptor,job_probe=self.probe,clock=self.clock)

    def test_no_clobber_race_is_not_retried(self):
        self.stage()
        original=a.os.link
        def raced(source,destination,**kwargs):
            destination.write_bytes(b'synthetic competing descriptor')
            return original(source,destination,**kwargs)
        with patch.object(a.os,'link',side_effect=raced):
            with self.assertRaises(FileExistsError):a.remote_admit(self.root,self.descriptor,job_probe=self.probe,clock=self.clock)
        self.assertEqual((self.root/'admissions/000002.json').read_bytes(),b'synthetic competing descriptor')
        self.assertTrue((self.root/'admission-002.lock').exists())

    def test_postpublish_fsync_failure_is_ambiguous_and_cannot_repeat(self):
        self.stage();original=a.sync_dir
        def fail(path):
            if path==self.root/'admissions':raise OSError('Injected post-publication fsync failure')
            return original(path)
        with patch.object(a,'sync_dir',side_effect=fail):
            with self.assertRaises(OSError):a.remote_admit(self.root,self.descriptor,job_probe=self.probe,clock=self.clock)
        self.assertTrue((self.root/'admissions/000002.json').exists())
        self.assertTrue((self.root/'admission-002.lock').exists())
        self.assertFalse((self.root/'admission-002.json').exists())
        with self.assertRaises(ValueError):a.remote_admit(self.root,self.descriptor,job_probe=self.probe,clock=self.clock)

    def test_changed_tree_during_sync_and_nonregular_entries_rejected(self):
        self.stage();root=self.root/'batches'/a.BATCH
        with patch.object(a.os,'fsync',side_effect=lambda fd:(root/'data.json').write_text('changed')):
            with self.assertRaises(ValueError):a.sync_tree(root,self.descriptor['input_sha256'])
        (root/'symlink').symlink_to(root/'data.json')
        with self.assertRaises(ValueError):a.inventory(root)


if __name__=='__main__':unittest.main(verbosity=2)
