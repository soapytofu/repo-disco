"""Synthetic fixed-control dispatch/gate/archive checks; no native or network calls."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import collect
import ops
import review
import native_scorer


def configured_projects():
    projects=sorted(path.stem for path in (Path(__file__).parent/'configs').glob('*.json'))
    if not projects or not set(projects)<={'stdlib','aws'}:
        raise AssertionError('No exact control project configuration is packaged')
    return projects


def accounting(job='123',state='COMPLETED',step='COMPLETED'):
    header='|'.join(ops.ACCOUNTING_FIELDS)
    row=lambda ident,outcome:'|'.join([ident,outcome,'00:00:01','1','0:0','1','00:00:01','1','1K','synthetic-compute'])
    return header+'\n'+row(job,state)+'\n'+row(job+'.batch',step)+'\n'


class OpsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name).resolve()
        self.selected=ops.settings('stdlib');self.selected['root']=str(self.base/'remote')
        self.files={'qualification-002/run.sbatch':b'# SYNTHETIC NEVER SUBMIT\n','source/A.dfy':b'module A {}\n'}
        frozen=dict(schema='dafny-growth-controls-freeze-v1',project='stdlib',
            control_case_ids=collect.CONTROL_IDS['stdlib'],files={n:ops.sha(v) for n,v in self.files.items()})
        self.freeze=ops.canonical(frozen);self.digest=ops.sha(self.freeze)
        self.members=dict(self.files);self.members[self.selected['freeze']]=self.freeze
        self.payload=ops.make_archive(self.members)

    def tearDown(self):self.temp.cleanup()

    def stage(self):
        with mock.patch.object(ops,'command',return_value=''):
            return ops.stage_remote(self.selected,self.digest,self.payload)

    def ready(self):
        self.stage();root=Path(self.selected['root'])
        ops.save(root/'preflight-001.json',dict(runtime_sha256=self.digest,exit_code=0,timeout=False))
        return root

    def fake_cluster(self,argv,seconds=20):
        if argv[0]=='squeue':return ''
        if argv[0]=='scontrol':return 'PartitionName=test State=UP PreemptMode=OFF MaxTime=12:00:00 MaxMemPerNode=8192'
        if argv[0]=='sacct':return accounting()
        raise AssertionError('Unexpected synthetic command '+repr(argv))

    def test_exact_stage_is_exclusive_and_rejects_unpinned_members(self):
        self.stage()
        with mock.patch.object(ops,'command',return_value=''),self.assertRaises(ValueError):
            ops.stage_remote(self.selected,self.digest,self.payload)
        other=dict(self.selected,root=str(self.base/'other'))
        bad=dict(self.members);bad['extra.txt']=b'not pinned'
        with mock.patch.object(ops,'command',return_value=''),self.assertRaises(ValueError):
            ops.stage_remote(other,self.digest,ops.make_archive(bad))
        self.assertFalse(Path(other['root']).exists())

    def test_matching_queue_blocks_mutation(self):
        queue='123|'+self.selected['root']+'|other|RUNNING\n'
        with mock.patch.object(ops,'command',return_value=queue),self.assertRaises(ValueError):
            ops.stage_remote(self.selected,self.digest,self.payload)
        self.assertFalse(Path(self.selected['root']).exists())

    def test_partition_must_be_live_nonpreemptible_and_large_enough(self):
        ops.check_partition('PartitionName=test State=UP PreemptMode=OFF MaxTime=02:00:00',self.selected)
        for text in ('PartitionName=test State=UP PreemptMode=REQUEUE MaxTime=12:00:00',
                     'PartitionName=shared State=UP PreemptMode=OFF MaxTime=12:00:00',
                     'PartitionName=test State=DOWN PreemptMode=OFF MaxTime=12:00:00',
                     'PartitionName=test State=UP PreemptMode=OFF MaxTime=00:59:59'):
            with self.subTest(text=text),self.assertRaises(ValueError):ops.check_partition(text,self.selected)

    def test_submit_once_pins_one_cpu_and_no_requeue(self):
        root=self.ready()
        with mock.patch.object(ops,'command',side_effect=self.fake_cluster), \
                mock.patch.object(ops.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'123\n',b'')) as run:
            record=ops.submit_remote(self.selected,self.digest)
            self.assertEqual(record['job_id'],'123');run.assert_called_once()
            for arg in ('--cpus-per-task=1','--mem=4G','--time=02:00:00','--no-requeue'):
                self.assertIn(arg,record['argv'])
            with self.assertRaises(ValueError):ops.submit_remote(self.selected,self.digest)
            run.assert_called_once()
        self.assertTrue((root/'submission.intent.json').exists())

    def test_ambiguous_submit_retains_intent_and_is_not_retried(self):
        root=self.ready()
        with mock.patch.object(ops,'command',side_effect=self.fake_cluster), \
                mock.patch.object(ops.subprocess,'run',side_effect=subprocess.TimeoutExpired(['synthetic-sbatch'],30)) as run:
            record=ops.submit_remote(self.selected,self.digest)
            self.assertTrue(record['ambiguous_submission']);self.assertNotIn('job_id',record)
            with self.assertRaises(ValueError):ops.submit_remote(self.selected,self.digest)
            run.assert_called_once()
        self.assertEqual(ops.read(root/'submission.json')['error_type'],'TimeoutExpired')

    def test_all_relevant_steps_must_be_terminal(self):
        self.assertTrue(ops.terminal_accounting(accounting(),'123')['all_relevant_rows_terminal'])
        for state in ('RUNNING','PENDING','SUSPENDED','STOPPED','UNKNOWN','REQUEUE_FED','OUT_OF_ME+'):
            with self.subTest(state=state),self.assertRaises(ValueError):ops.terminal_accounting(accounting(step=state),'123')
        with self.assertRaises(ValueError):ops.terminal_accounting(accounting()+accounting().splitlines()[1]+'\n','123')

    def test_full_archive_preserves_inventory_and_remote_exclusive_intent(self):
        root=self.ready();ops.save(root/'submission.json',{'job_id':'123'})
        ops.write(root/'qualification-002/output-stdlib/record.json',b'{"synthetic":true}')
        with mock.patch.object(ops,'command',side_effect=self.fake_cluster):
            files,estimate=ops.transfer_files(self.selected,self.digest,'123')
            archive=ops.fetch_remote(self.selected,self.digest,'123',estimate)
            self.assertEqual(ops.archive_members(archive),files)
            with self.assertRaises(ValueError):ops.fetch_remote(self.selected,self.digest,'123',estimate)
        self.assertTrue((root/'fetch.intent.json').exists())

    def test_evidence_drift_blocks_fetch_before_remote_claim(self):
        root=self.ready();ops.save(root/'submission.json',{'job_id':'123'})
        with mock.patch.object(ops,'command',side_effect=self.fake_cluster):
            _,estimate=ops.transfer_files(self.selected,self.digest,'123')
            (root/'source/A.dfy').write_bytes(b'module Changed {}\n')
            with self.assertRaises(ValueError):ops.fetch_remote(self.selected,self.digest,'123',estimate)
        self.assertFalse((root/'fetch.intent.json').exists())

    def test_large_program_and_stage_payload_use_stdin_not_command_argument(self):
        fake_freeze=self.base/'freeze.json';fake_freeze.write_bytes(self.freeze)
        inventory={'job_id':'123','inventory':{('long/'+str(i)+'x'*100):{'bytes':1,'sha256':'a'*64} for i in range(1200)}}
        with mock.patch.object(ops,'identity',return_value=(self.selected,fake_freeze,{})), \
                mock.patch.object(ops.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'SYNTHETIC',b'')) as run:
            ops.remote('stdlib','fetch',job='123',inventory=inventory)
            data=run.call_args.kwargs['input'];argv=run.call_args.args[0]
            self.assertGreater(len(data),131072)
            self.assertEqual(data,ops.remote_program('fetch',self.selected,self.digest,job='123',inventory=inventory).encode())
            self.assertEqual(shlex.split(argv[-1]),[ops.PYTHON,'-B','-'])
            self.assertTrue(all(len(x.encode())<4096 for x in argv))
            self.assertEqual(run.call_args.kwargs['timeout'],240)
            ops.remote('stdlib','stage',payload=self.payload)
            self.assertIn(b'base64.b64decode(PAYLOAD,validate=True)',run.call_args.kwargs['input'])
            self.assertEqual(run.call_args.kwargs['timeout'],180)

    def test_actual_stdin_stage_program_only_uses_mocked_cluster_process(self):
        program=ops.remote_program('stage',self.selected,self.digest,payload=self.payload)
        with mock.patch.object(subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'',b'')) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            exec(compile(program,'synthetic-stdin-stage','exec'),{})
        self.assertEqual(run.call_count,1)
        self.assertEqual(run.call_args.args[0][0],'squeue')
        self.assertEqual((Path(self.selected['root'])/'source/A.dfy').read_bytes(),self.files['source/A.dfy'])

    def test_transport_timeout_no_retry_and_payload_actions_restricted(self):
        fake_freeze=self.base/'freeze.json';fake_freeze.write_bytes(self.freeze)
        with mock.patch.object(ops,'identity',return_value=(self.selected,fake_freeze,{})), \
                mock.patch.object(ops.subprocess,'run',side_effect=subprocess.TimeoutExpired(['synthetic-ssh'],45)) as run:
            with self.assertRaises(subprocess.TimeoutExpired):ops.remote('stdlib','inspect')
            run.assert_called_once()
        for action in ('submit','fetch','status','preflight'):
            with self.assertRaises(ValueError):ops.remote_program(action,self.selected,self.digest,payload=b'forbidden')

    def test_local_mutations_have_exclusive_intents(self):
        with mock.patch.object(ops,'ROOT',self.base):
            for action,path in [('stage','stages/stdlib.intent.json'),('preflight','preflight/stdlib.intent.json'),
                                ('submit','submissions/stdlib.intent.json'),('fetch','fetch/stdlib.intent.json')]:
                ops.local_fresh('stdlib',action);ops.write(self.base/path,b'{}')
                with self.assertRaises(ValueError):ops.local_fresh('stdlib',action)


class ControlScopeTests(unittest.TestCase):
    def test_exact_remaining_sets_and_omission_inputs(self):
        for project in configured_projects():
            total={'stdlib':15,'aws':12}[project]
            config=ops.read(Path(__file__).parent/'configs'/f'{project}.json')
            collect.validate_config(config)
            self.assertEqual(len(config['cases']),total)
            self.assertFalse(set(c['id'] for c in config['cases']) & set(collect.TASK_REFERENCES.values()))
            metadata=ops.read(Path(__file__).parent/'control-metadata'/f'{project}.json')
            for case,meta in zip(config['cases'],metadata['cases']):
                self.assertEqual(set(case['source_sha256'])-set(case['command_files']),set(meta['omit_from_command']))
            for mutation in ('extra','reference','omission','limit'):
                bad=copy.deepcopy(config)
                if mutation=='extra':bad['cases'].append(copy.deepcopy(bad['cases'][0]))
                elif mutation=='reference':bad['cases'][0]['id']='filter-reference'
                elif mutation=='omission':bad['cases'][0]['command_files']=bad['cases'][0]['command_files'][:-1]
                else:bad['options']+=['--no-verify']
                with self.subTest(project=project,mutation=mutation),self.assertRaises(ValueError):
                    collect.validate_config(bad)

    def test_project_walltimes_are_fixed_and_live_limits_checked(self):
        std=ops.settings('stdlib');aws=ops.settings('aws')
        self.assertEqual((std['job_seconds'],std['slurm_time']),(7200,'02:00:00'))
        self.assertEqual((aws['job_seconds'],aws['slurm_time']),(14400,'04:00:00'))
        ops.check_partition('PartitionName=test State=UP PreemptMode=OFF MaxTime=04:00:00',aws)
        with self.assertRaises(ValueError):
            ops.check_partition('PartitionName=test State=UP PreemptMode=OFF MaxTime=03:59:59',aws)

    def test_no_real_gate_exists_or_can_be_fabricated_by_dispatch(self):
        # The preparation phase intentionally has no gate or freeze. This test
        # remains valid after real gating by checking a fresh empty package.
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):collect.validate_reference_gate(Path(folder),Path(folder))

    def run_fake_controls(self,project,timeout_index=None):
        here=Path(__file__).parent;original=here.parent
        config=ops.read(here/'configs'/f'{project}.json')
        profiles=ops.read(here/'tool-profiles.json');calls=[]
        with tempfile.TemporaryDirectory() as folder:
            package=Path(folder).resolve();q=package/'qualification-002';q.mkdir()
            executable=package/'synthetic-not-a-verifier';executable.write_bytes(b'NEVER EXECUTED\n')
            config['dafny']=str(executable);profiles[project]['dafny']=str(executable)
            ops.save(q/'tool-profiles.json',profiles)
            ops.save(q/'control-metadata'/f'{project}.json',ops.read(here/'control-metadata'/f'{project}.json'))
            for case in config['cases']:
                shutil.copytree(original/case['workspace_dir'],package/case['workspace_dir'])
            config_path=q/'configs'/f'{project}.json';ops.save(config_path,config)
            pins={p.relative_to(package).as_posix():ops.sha(p.read_bytes()) for p in package.rglob('*') if p.is_file()}
            freeze_path=q/'freezes'/f'{project}.json'
            ops.save(freeze_path,dict(schema='dafny-growth-controls-freeze-v1',project=project,
                control_case_ids=collect.CONTROL_IDS[project],reference_gate_sha256='f'*64,files=pins,synthetic=True))
            def capture(argv,cwd,seconds,streams):
                index=len(calls);calls.append(argv)
                case=config['cases'][index]
                self.assertEqual(argv[4:],[str(executable),'verify']+config['options']+case['command_files'])
                self.assertEqual(seconds,360 if project=='stdlib' else 900)
                self.assertEqual(collect.sources(cwd),case['source_sha256'])
                Path(argv[3]).write_bytes(b'SYNTHETIC RESOURCES\n')
                streams[0].write_bytes(b'SYNTHETIC STDOUT\n');streams[1].write_bytes(b'')
                (cwd/'synthetic.csv').write_bytes(b'SYNTHETIC: not proof evidence\n')
                timed=index==timeout_index
                return dict(exit_code=-15 if timed else 4,elapsed_seconds=.01,timeout=timed),b'SYNTHETIC STDOUT\n',b''
            output=q/f'output-{project}'
            with mock.patch.object(collect,'ROOT',q), \
                    mock.patch.dict(os.environ,{'SLURM_JOB_ID':'SYNTHETIC','SLURM_CPUS_PER_TASK':'1'}), \
                    mock.patch.object(collect.socket,'gethostname',return_value='synthetic-compute'), \
                    mock.patch.object(collect,'validate_reference_gate',return_value=({'gate_sha256':'f'*64},{'synthetic':True})), \
                    mock.patch.object(collect,'capture_version',side_effect=lambda exe,flag,out,label:
                        config['expected_version'] if label=='tool' else 'Synthetic Z3'), \
                    mock.patch.object(collect,'tool_fingerprint',return_value=config['expected_tool_fingerprint']), \
                    mock.patch.object(collect,'capture',side_effect=capture),contextlib.redirect_stdout(io.StringIO()):
                collect.run(config_path,output,ops.sha(freeze_path.read_bytes()))
            summary=ops.read(output/'summary.json');count=len(config['cases']) if timeout_index is None else timeout_index+1
            self.assertEqual(summary['native_calls'],count)  # Intercepted fake attempts only.
            self.assertEqual(len(calls),count);self.assertEqual(summary['model_calls'],0)
            self.assertEqual(summary['all_planned_cases_recorded'],timeout_index is None)
            self.assertEqual([row['case'] for row in summary['cases']],collect.CONTROL_IDS[project][:count])
            for case in config['cases'][count:]:self.assertFalse((output/case['id']).exists())

    def test_full_control_dispatch_exact_order_and_native_caps(self):
        for project in configured_projects():self.run_fake_controls(project)

    def test_control_timeout_retains_prefix_and_blocks_tail(self):
        self.run_fake_controls(configured_projects()[0],timeout_index=1)

    def gate_fixture(self,root):
        package=root/'package';q=package/'qualification-002';q.mkdir(parents=True)
        inputs={};manifests={};bindings={};observations={}
        def put(name,raw):
            ops.write(package/name,raw);return dict(path=name,sha256=ops.sha(raw))
        for project in ('stdlib','aws'):
            raw=ops.canonical({'synthetic':True,'project':project});pin=put(project+'/manifest.json',raw)
            inputs[pin['path']]=pin['sha256'];manifests[project]=pin
            cases=ops.canonical([]);put(project+'/cases.json',cases)
            ops.save(q/'control-metadata'/f'{project}.json',dict(source_path=project+'/cases.json',source_sha256=ops.sha(cases),cases=[]))
        for task,ref in collect.TASK_REFERENCES.items():
            inherited={'stdlib-filter':56,'stdlib-splice':58,'aws-batch':77,'aws-tagged':77}[task]
            count=inherited+1;folder='synthetic-native/'+task+'/'+ref
            source=b'module Synthetic {}\n';sources={'A.dfy':source};source_hashes=native_scorer.hashes(sources)
            columns=list(native_scorer.BASE_COLUMNS)+['RandomSeed']
            unit_names=['Synthetic.Unit'+str(i)+' (correctness)' for i in range(count)]
            profile=dict(schema=native_scorer.PROFILE_SCHEMA,synthetic=True,project=task,stage=1,stage_id=task,
                inventory_status='qualified',command=['synthetic-dafny','verify','A.dfy'],verification_inputs=['A.dfy'],
                toolchain={'synthetic':True},csv_columns=columns,random_seed=0,
                required_units={name:'A.dfy' for name in unit_names},unitless_files={},inherited_warnings=[],unlogged_definitions=[])
            profile_pin=put('native-profiles-001/'+task+'.json',ops.canonical(profile))
            profile_pin['canonical_sha256']=native_scorer.sha(native_scorer.canonical(profile))
            csv=(','.join(columns)+'\n'+''.join(name+',Passed,00:00:00.001,1,0\n' for name in unit_names)).encode()
            raw={'stdout.txt':f'Dafny program verifier finished with {count} verified, 0 errors\n'.encode(),
                 'stderr.txt':b'','csv/synthetic.csv':csv,
                 'resources.txt':b'User time (seconds): 0.1\nSystem time (seconds): 0.0\nElapsed (wall clock) time (h:mm:ss or m:ss): 0:00.1\nMaximum resident set size (kbytes): 1\nExit status: 0\n'}
            raw_pins={name:put(folder+'/raw/'+name,data) for name,data in raw.items()}
            source_pins={name:put(folder+'/workspace/'+name,data) for name,data in sources.items()}
            record=dict(schema=native_scorer.RECORD_SCHEMA,origin='synthetic_offline',run_id='SYNTHETIC:'+ref,
                source_before_sha256=source_hashes,source_after_sha256=source_hashes,argv=profile['command'],
                toolchain=profile['toolchain'],toolchain_after=profile['toolchain'],attempts=1,model_calls=0,
                timeout=False,exit_code=0,elapsed_seconds=.1,host=dict(job_id='SYNTHETIC',hostname='synthetic-compute',partition='synthetic',cpus_per_task=1),
                raw_sha256=native_scorer.hashes(raw))
            record_pin=put(folder+'/record.json',ops.canonical(record));record_pin['canonical_sha256']=native_scorer.sha(native_scorer.canonical(record))
            pins=native_scorer.EvidencePins(profile_sha256=profile_pin['canonical_sha256'],record_sha256=record_pin['canonical_sha256'],
                source_revision_sha256=native_scorer.sha(native_scorer.canonical(source_hashes)),raw_sha256=tuple(sorted(native_scorer.hashes(raw).items())),
                run_id=record['run_id'],origin='synthetic_offline')
            replay=native_scorer.review(profile,sources,record,raw,pins,allow_synthetic=True)
            targets={'Synthetic.Unit'+str(count-1):[unit_names[-1]]}
            wrapper=dict(replay=replay,qualified_success=True,inherited_inventory_unchanged=True,
                exact_guarded_reconstruction=True,source_sha256=source_hashes,actual_target_units=targets,new_units=[unit_names[-1]])
            review_pin=put('native-profiles-001/replays/'+task+'.json',ops.canonical(wrapper))
            edit_pin=put('synthetic-edits/'+task+'.json',ops.canonical({'synthetic':True,'task':task}))
            evidence={pin['path']:pin['sha256'] for pin in [profile_pin,record_pin,review_pin,edit_pin,*raw_pins.values(),*source_pins.values()]}
            inputs.update(evidence)
            bindings[task]=dict(reference_case_id=ref,profile_path=profile_pin['path'],profile_sha256=profile_pin['sha256'])
            observations[task]=dict(reference_case_id=ref,qualified_success=True,native_profile=profile_pin,
                native_review=review_pin,reference_record=record_pin,reference_raw=raw_pins,reference_sources=source_pins,
                native_run_id=record['run_id'],raw_fingerprint_sha256=replay['raw_fingerprint_sha256'],edit_profile=edit_pin,
                base_sources=source_pins,inherited_unit_count=inherited,named_units=count,actual_target_units=targets,input_files=evidence)
        gate=dict(synthetic=True,status='PASS',all_references_match=True,model_calls=0,tasks=observations,input_files=inputs)
        gate_path='native-profiles-001/reference-gate.json';ops.save(package/gate_path,gate)
        binding=dict(schema='dafny-growth-controls-gate-binding-v1',synthetic=True,gate_path=gate_path,
            gate_sha256=ops.sha((package/gate_path).read_bytes()),fixture_manifests=manifests,tasks=bindings)
        ops.save(q/'reference-gate-binding.json',binding)
        return package,q,binding,gate

    def test_synthetic_gate_rejected_by_default_and_explicit_fixture_replays(self):
        with tempfile.TemporaryDirectory() as folder:
            package,q,binding,gate=self.gate_fixture(Path(folder))
            with self.assertRaises(ValueError):collect.validate_reference_gate(package,q)
            self.assertEqual(collect.validate_reference_gate(package,q,allow_synthetic=True),(binding,gate))

    def test_gate_evidence_and_fixture_drift_block_even_synthetic_replay(self):
        for changed in ('raw','gate','cases','profile'):
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as folder:
                package,q,binding,gate=self.gate_fixture(Path(folder))
                path={'raw':'aws/manifest.json','gate':binding['gate_path'],'cases':'stdlib/cases.json',
                      'profile':'native-profiles-001/aws-batch.json'}[changed]
                with (package/path).open('ab') as stream:stream.write(b'changed')
                with self.assertRaises(ValueError):collect.validate_reference_gate(package,q,allow_synthetic=True)


class ControlReviewTests(unittest.TestCase):
    def report(self,category='PROOF_FAILURE'):
        return dict(category=category,qualified_success=False,
            units=[dict(name='Helper.Transfer (correctness)',outcome='Failed'),
                   dict(name='Client.Target (correctness)',outcome='Passed')],
            proof_coverage_complete=True,missing_units=[],extra_units=[],failed_units=1,
            passed_units=1,summaries=[(1,1)],resources={'exit_status':4},warning_policy_matches=True)

    def test_helper_failure_cannot_be_masked_by_passing_client(self):
        metadata=dict(expected_category='PROOF_FAILURE',expected_failed_targets=['Helper.Transfer'],
                      expected_passed_targets=[],inspect_targets=['Client.Target'])
        result=review.expectation(self.report(),metadata,{'required_units':{}},
                                  {'stdout.txt':b'Error: synthetic','stderr.txt':b''})
        self.assertTrue(result['expected_match'])
        self.assertEqual(result['inspect_targets']['Client.Target'],['Passed'])

    def test_frontend_warning_and_resource_failures_never_count_as_proof_failures(self):
        metadata=dict(expected_category='PROOF_FAILURE',expected_failed_targets=['Helper.Transfer'])
        for category in ('FRONTEND_PARSE_FAILURE','FRONTEND_RESOLUTION_FAILURE','WARNING_ONLY','RESOURCE_FAILURE','TIMEOUT'):
            with self.subTest(category=category):
                self.assertFalse(review.expectation(self.report(category),metadata,{'required_units':{}},
                    {'stdout.txt':b'','stderr.txt':b''})['expected_match'])

    def test_omitted_failing_source_needs_exact_missing_inventory(self):
        profile={'required_units':{'Base.Check (correctness)':'Base.dfy','New.Check (correctness)':'New.dfy'}}
        metadata={'expected_category':'COVERAGE_OMISSION','omitted_source_all_units':['New.dfy']}
        report=dict(category='COVERAGE_FAILURE',qualified_success=False,
            units=[dict(name='Base.Check (correctness)',outcome='Passed')],missing_units=['New.Check (correctness)'],
            extra_units=[],failed_units=0,passed_units=1,summaries=[(1,0)],resources={'exit_status':0},warning_policy_matches=True)
        raw={'stdout.txt':b'Dafny program verifier finished with 1 verified, 0 errors\n','stderr.txt':b''}
        self.assertTrue(review.expectation(report,metadata,profile,raw)['expected_match'])
        report['missing_units'].append('Base.Check (correctness)')
        self.assertFalse(review.expectation(report,metadata,profile,raw)['expected_match'])

    def test_unlogged_declarations_require_unchanged_definition_line(self):
        source=b'module A {\n  datatype Flag = One\n  method M() { }\n}\n'
        profile=dict(command=['dafny','verify','A.dfy'],verification_inputs=['A.dfy'],
            unlogged_definitions=[dict(name='A.Flag',file='A.dfy',source_sha256='0'*64,
                source_line='  datatype Flag = One',counted_as_pass=False)])
        case={'command_files':['A.dfy']};meta={'omit_from_command':[]}
        current,changes=review.materialize_control_profile(profile,case,meta,{'A.dfy':source})
        self.assertEqual(current['unlogged_definitions'][0]['source_sha256'],ops.sha(source))
        self.assertFalse(changes[0]['counted_as_pass'])
        with self.assertRaises(ValueError):review.materialize_control_profile(profile,case,meta,{'A.dfy':b'module A {}'})


if __name__=='__main__':unittest.main(verbosity=2)

