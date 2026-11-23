"""Synthetic qualification tests; never invoke SSH, Slurm, Dafny or a model."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import collect
import ops
import review
import native_scorer


def config_fixture(project='stdlib'):
    value=copy.deepcopy(json.loads((Path(__file__).parent/'tool-profiles.json').read_bytes())[project])
    value.update(schema='dafny-growth-reference-qualification-v1',freeze='freezes/'+project+'.json',
                 references_only=True,cases=[])
    for index,ident in enumerate(collect.REFERENCE_IDS[project]):
        raw=('module Synthetic'+str(index)+' {}\n').encode()
        value['cases'].append(dict(id=ident,task_id=project+'-task-'+str(index),role='reference',
            workspace_dir=project+'/cases/'+ident+'/workspace',source_sha256={'Synthetic.dfy':collect.sha(raw)},
            command_files=['Synthetic.dfy']))
    return value


def accounting(job='123',state='COMPLETED',step='COMPLETED'):
    header='|'.join(ops.ACCOUNTING_FIELDS)
    row=lambda ident,outcome:'|'.join([ident,outcome,'00:00:01','1','0:0','1','00:00:01','1','1K','synthetic-compute'])
    return header+'\n'+row(job,state)+'\n'+row(job+'.batch',step)+'\n'


class CollectorTests(unittest.TestCase):
    def test_only_two_exact_references_and_pinned_settings_are_dispatchable(self):
        for project in ('stdlib',):
            valid=config_fixture(project);collect.validate_config(valid)
            variants=[]
            value=copy.deepcopy(valid);value['cases'].append(copy.deepcopy(value['cases'][0]));variants.append(value)
            value=copy.deepcopy(valid);value['cases'][0]['role']='control';variants.append(value)
            value=copy.deepcopy(valid);value['cases'][0]['id']='negative';variants.append(value)
            value=copy.deepcopy(valid);value['options']+=['--no-verify'];variants.append(value)
            value=copy.deepcopy(valid);value['wall_seconds']+=1;variants.append(value)
            for value in variants:
                with self.subTest(project=project,value=value['cases'][0]['id']),self.assertRaises(ValueError):
                    collect.validate_config(value)

    def test_omitted_duplicate_or_unsafe_inputs_are_rejected(self):
        for inputs in ([],['Synthetic.dfy','Synthetic.dfy'],['../outside.dfy']):
            value=config_fixture();value['cases'][0]['command_files']=inputs
            with self.subTest(inputs=inputs),self.assertRaises(ValueError):collect.validate_config(value)

    def test_native_capture_requires_compute_and_one_cpu(self):
        with mock.patch.dict(os.environ,{'SLURM_JOB_ID':'synthetic','SLURM_CPUS_PER_TASK':'1'}), \
                mock.patch.object(collect.socket,'gethostname',return_value='holylogin'),self.assertRaises(ValueError):
            collect.run(Path('never-read'),Path('never-written'),'0'*64)
        with mock.patch.dict(os.environ,{'SLURM_JOB_ID':'synthetic','SLURM_CPUS_PER_TASK':'2'}), \
                mock.patch.object(collect.socket,'gethostname',return_value='synthetic-compute'),self.assertRaises(ValueError):
            collect.run(Path('never-read'),Path('never-written'),'0'*64)

    def run_fake(self,project,timeout_index=None,change_source=False):
        with tempfile.TemporaryDirectory() as folder:
            package=Path(folder).resolve();q=package/'qualification-005';q.mkdir()
            config=config_fixture(project)
            executable=package/'synthetic-tool-not-executed';executable.write_text('SYNTHETIC ONLY\n')
            config['dafny']=str(executable)
            profiles=json.loads((Path(__file__).parent/'tool-profiles.json').read_bytes())
            profiles[project]['dafny']=str(executable)
            ops.save(q/'tool-profiles.json',profiles)
            for index,case in enumerate(config['cases']):
                ops.write(package/case['workspace_dir']/'Synthetic.dfy',('module Synthetic'+str(index)+' {}\n').encode())
            config_path=q/'configs'/f'{project}.json';ops.save(config_path,config)
            pins={p.relative_to(package).as_posix():collect.sha(p.read_bytes()) for p in package.rglob('*') if p.is_file()}
            freeze_path=q/'freezes'/f'{project}.json'
            ops.save(freeze_path,dict(schema='dafny-growth-reference-freeze-v1',project=project,
                reference_case_ids=collect.REFERENCE_IDS[project],files=pins,synthetic=True))
            invocations=[]
            def capture(argv,cwd,seconds,stream_paths):
                index=len(invocations);invocations.append((argv,cwd,seconds))
                self.assertEqual(seconds,360 if project=='stdlib' else 900)
                self.assertEqual(argv[4:],[str(executable),'verify']+config['options']+['Synthetic.dfy'])
                Path(argv[3]).write_bytes(b'SYNTHETIC RESOURCE RECORD\n')
                stream_paths[0].write_bytes(b'SYNTHETIC STDOUT\n');stream_paths[1].write_bytes(b'')
                (cwd/'synthetic.csv').write_bytes(b'SYNTHETIC CSV,not proof evidence\n')
                if change_source:(cwd/'Synthetic.dfy').write_bytes(b'module Altered {}\n')
                timeout=index==timeout_index
                return dict(exit_code=-15 if timeout else 0,timeout=timeout,elapsed_seconds=.01),b'SYNTHETIC STDOUT\n',b''
            output=q/f'output-{project}'
            with mock.patch.object(collect,'ROOT',q), \
                    mock.patch.dict(os.environ,{'SLURM_JOB_ID':'synthetic','SLURM_CPUS_PER_TASK':'1'}), \
                    mock.patch.object(collect.socket,'gethostname',return_value='synthetic-compute'), \
                    mock.patch.object(collect,'capture_version',side_effect=lambda exe,flag,out,label:
                        config['expected_version'] if label=='tool' else 'Z3 synthetic'), \
                    mock.patch.object(collect,'tool_fingerprint',return_value=config['expected_tool_fingerprint']), \
                    mock.patch.object(collect,'capture',side_effect=capture), contextlib.redirect_stdout(io.StringIO()):
                if change_source:
                    with self.assertRaisesRegex(ValueError,'Verifier source changed'):
                        collect.run(config_path,output,collect.sha(freeze_path.read_bytes()))
                    self.assertTrue((output/config['cases'][0]['id']/'record.json').exists())
                    self.assertEqual(len(invocations),1)
                    return
                collect.run(config_path,output,collect.sha(freeze_path.read_bytes()))
            summary=ops.read(output/'summary.json');count=len(config['cases']) if timeout_index is None else timeout_index+1
            self.assertEqual(summary['native_calls'],count)  # Intercepted synthetic calls only.
            self.assertEqual(summary['model_calls'],0)
            self.assertEqual(summary['all_planned_cases_recorded'],count==len(config['cases']))
            for case in config['cases'][:count]:
                record=ops.read(output/case['id']/'record.json')
                self.assertEqual(record['attempts'],1)
                self.assertEqual(record['source_before_sha256'],case['source_sha256'])
                self.assertEqual(record['source_after_sha256'],case['source_sha256'])
                self.assertIn('csv/synthetic.csv',record['raw_sha256'])
            self.assertEqual(len(invocations),count)
            for case in config['cases'][count:]:self.assertFalse((output/case['id']).exists())

    def test_fake_references_retain_all_streams_and_exact_commands(self):
        for project in ('stdlib',):self.run_fake(project)

    def test_timeout_stops_tail_without_retry(self):self.run_fake('stdlib',timeout_index=0)

    def test_aws_is_not_a_dispatchable_project(self):
        with self.assertRaises(ValueError):ops.settings('aws')
        value=config_fixture();value['project']='aws'
        with self.assertRaises(ValueError):collect.validate_config(value)

    def test_passed_filter_is_not_dispatchable_or_repeated(self):
        self.assertEqual(collect.REFERENCE_IDS,{'stdlib':['splice-reference']})
        value=config_fixture();value['cases'][0]['id']='filter-reference'
        with self.assertRaises(ValueError):collect.validate_config(value)
        value=config_fixture();extra=copy.deepcopy(value['cases'][0]);extra['id']='filter-reference'
        value['cases'].append(extra)
        with self.assertRaises(ValueError):collect.validate_config(value)
    def test_source_drift_is_preserved_before_failure(self):self.run_fake('stdlib',change_source=True)

    def test_process_streams_timeout_and_exclusive_records(self):
        with tempfile.TemporaryDirectory() as folder:
            result,out,err=collect.capture([sys.executable,'-c','import sys;print("synthetic");sys.exit(4)'],folder,5)
            self.assertEqual((result['exit_code'],out,err),(4,b'synthetic\n',b''))
            result,out,err=collect.capture([sys.executable,'-c','import time;print("start",flush=True);time.sleep(30)'],folder,.1)
            self.assertTrue(result['timeout']);self.assertLess(result['elapsed_seconds'],6)
            path=Path(folder)/'record.json';collect.write(path,{'synthetic':True})
            with self.assertRaises(FileExistsError):collect.write(path,{'replace':True})

    def test_solver_version_uses_single_dash_and_retains_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with mock.patch.object(collect,'capture',return_value=(dict(exit_code=1,timeout=False,
                    elapsed_seconds=.1),b'partial',b'error')) as capture,self.assertRaises(ValueError):
                collect.capture_version('/synthetic/z3','-version',root,'solver')
            self.assertEqual(capture.call_args.args[0],['/synthetic/z3','-version'])
            self.assertEqual((root/'solver-version.stderr').read_bytes(),b'error')

    def test_native_child_never_inherits_provider_environment(self):
        dummy={'AWS_ACCESS_KEY_ID':'SYNTHETIC-NOT-A-KEY','AWS_SECRET_ACCESS_KEY':'SYNTHETIC-NOT-A-SECRET',
               'AWS_SESSION_TOKEN':'SYNTHETIC-NOT-A-TOKEN','AWS_REGION':'synthetic-region',
               'BOTO_CONFIG':'synthetic-config','BOTO_PATH':'synthetic-path',
               'BEDROCK_API_KEY':'SYNTHETIC-NOT-A-KEY','SYNTHETIC_RETAIN':'retained'}
        code=('import os; assert not any(k.startswith("AWS_") or k in '
              '{"BOTO_CONFIG","BOTO_PATH","BEDROCK_API_KEY"} for k in os.environ); '
              'assert os.environ["SYNTHETIC_RETAIN"]=="retained"; print("environment boundary passed")')
        with tempfile.TemporaryDirectory() as folder,mock.patch.object(collect.os,'environ',dummy):
            result,out,err=collect.capture([sys.executable,'-c',code],folder,5)
        self.assertEqual((result['exit_code'],out,err),(0,b'environment boundary passed\n',b''))


class OpsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name).resolve()
        self.selected=ops.settings('stdlib');self.selected['root']=str(self.base/'remote')
        self.files={'qualification-005/run.sbatch':b'# SYNTHETIC NEVER SUBMIT\n','source/A.dfy':b'module A {}\n'}
        frozen=dict(schema='dafny-growth-reference-freeze-v1',project='stdlib',
            reference_case_ids=collect.REFERENCE_IDS['stdlib'],files={n:ops.sha(v) for n,v in self.files.items()})
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

    def test_existing_output_is_reported_and_blocks_mutation(self):
        root=Path(self.selected['root'])
        output=root/Path(self.selected['freeze']).parent.parent/'output-stdlib'
        output.mkdir(parents=True)
        with mock.patch.object(ops,'command',return_value=''):
            state=ops.inspect_state(self.selected)
        self.assertTrue(state['output_exists']);self.assertEqual(state['output_path'],str(output))
        with self.assertRaises(ValueError):ops.fresh_state(state,self.selected)

    def test_generated_inspection_uses_exact_frozen_output_location(self):
        root=Path(self.selected['root']);output=root/'qualification-005/output-stdlib'
        output.mkdir(parents=True)
        program=ops.remote_program('inspect',self.selected,self.digest)
        captured=io.StringIO()
        with mock.patch.object(subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'',b'')), \
                contextlib.redirect_stdout(captured):
            exec(compile(program,'synthetic-stdin-inspection','exec'),{})
        state=json.loads(captured.getvalue())
        self.assertTrue(state['output_exists']);self.assertEqual(state['output_path'],str(output))

    def test_partition_must_be_live_nonpreemptible_and_large_enough(self):
        ops.check_partition('PartitionName=test State=UP PreemptMode=OFF MaxTime=01:00:00')
        for text in ('PartitionName=test State=UP PreemptMode=REQUEUE MaxTime=12:00:00',
                     'PartitionName=shared State=UP PreemptMode=OFF MaxTime=12:00:00',
                     'PartitionName=test State=DOWN PreemptMode=OFF MaxTime=12:00:00',
                     'PartitionName=test State=UP PreemptMode=OFF MaxTime=00:59:59'):
            with self.subTest(text=text),self.assertRaises(ValueError):ops.check_partition(text)

    def test_submit_once_pins_one_cpu_and_no_requeue(self):
        root=self.ready()
        with mock.patch.object(ops,'command',side_effect=self.fake_cluster), \
                mock.patch.object(ops.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'123\n',b'')) as run:
            record=ops.submit_remote(self.selected,self.digest)
            self.assertEqual(record['job_id'],'123');run.assert_called_once()
            for arg in ('--cpus-per-task=1','--mem=4G','--time=01:00:00','--no-requeue'):
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
        ops.write(root/'qualification-005/output-stdlib/record.json',b'{"synthetic":true}')
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


class ReviewTests(unittest.TestCase):
    def synthetic_record(self,root,*,outcome='Passed',code=0,warning=False):
        source=b'module Synthetic {}\n';sources={'Synthetic.dfy':collect.sha(source)}
        config=dict(dafny='/synthetic/not-executed',options=['--cores','1'])
        case=dict(id='synthetic-reference',task_id='synthetic-task',source_sha256=sources,
                  command_files=['Synthetic.dfy'])
        tools={'synthetic':'not-a-tool-measurement'}
        inherited=dict(required_units={'Synthetic.Base (correctness)':'Synthetic.dfy'},
            unlogged_definitions=[],inherited_warnings=[],toolchain=tools,
            csv_columns=list(native_scorer.BASE_COLUMNS)+['RandomSeed'],random_seed=0)
        ops.write(root/'workspace/Synthetic.dfy',source)
        passed=2 if outcome=='Passed' else 1;failed=0 if outcome=='Passed' else 1
        text=(('Error: synthetic proof failure\n' if failed else '')
              +('Warning: synthetic warning\n' if warning else '')
              +f'Dafny program verifier finished with {passed} verified, {failed} errors\n')
        resources=('User time (seconds): 0.1\nSystem time (seconds): 0.0\n'
            'Elapsed (wall clock) time (h:mm:ss or m:ss): 0:00.1\n'
            'Maximum resident set size (kbytes): 1\nExit status: '+str(code)+'\n')
        csv=(','.join(inherited['csv_columns'])+'\n'
            'Synthetic.Base (correctness),Passed,00:00:00.001,1,0\n'
            f'Synthetic.New (correctness),{outcome},00:00:00.001,1,0\n')
        raw={'stdout.txt':text.encode(),'stderr.txt':b'','resources.txt':resources.encode(),
             'csv/synthetic.csv':csv.encode()}
        for name,data in raw.items():ops.write(root/'raw'/name,data)
        record=dict(schema='dafny-library-native-record-v1',origin='analyst_qualification',attempts=1,
            model_calls=0,run_id='123:synthetic-reference',host=dict(job_id='123',cpus_per_task=1,
            hostname='synthetic-compute',partition='synthetic'),source_before_sha256=sources,
            source_after_sha256=sources,argv=[config['dafny'],'verify']+config['options']+['Synthetic.dfy'],
            toolchain=tools,toolchain_after=tools,raw_sha256=native_scorer.hashes(raw),exit_code=code,
            timeout=False,elapsed_seconds=.1)
        ops.save(root/'record.json',record)
        annotation={'required_targets':['Synthetic.New'],'new_fixed_declarations':['Synthetic.Unlogged']}
        return config,case,annotation,inherited

    def test_success_is_only_observed_inventory_never_qualified_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);config,case,annotation,inherited=self.synthetic_record(root)
            result=review.review_case(config,case,root,annotation,inherited,{'synthetic':True},'123')
            self.assertEqual(result['category'],'NATIVE_SUCCESS_INVENTORY_PENDING')
            self.assertFalse(result['qualified_success']);self.assertFalse(result['acceptance_issued'])
            self.assertFalse(result['native_inventory_qualified'])
            self.assertEqual([r['name'] for r in result['new_observed_rows']],['Synthetic.New (correctness)'])
            self.assertEqual(result['missing_inherited_units'],[])
            self.assertFalse(result['new_declarations_without_logged_units'][0]['counted_as_pass'])

    def test_proof_failures_and_warning_only_are_not_successes(self):
        for outcome,code,warning,category in [('Failed',4,False,'PROOF_FAILURE'),('Passed',2,True,'WARNING_ONLY')]:
            with self.subTest(category=category),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);config,case,annotation,inherited=self.synthetic_record(root,outcome=outcome,code=code,warning=warning)
                result=review.review_case(config,case,root,annotation,inherited,{},'123')
                self.assertEqual(result['category'],category);self.assertFalse(result['qualified_success'])

    def test_stale_source_raw_and_job_identity_are_rejected(self):
        for target in ('source','raw','job'):
            with self.subTest(target=target),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);config,case,annotation,inherited=self.synthetic_record(root)
                if target=='source':(root/'workspace/Synthetic.dfy').write_bytes(b'changed')
                elif target=='raw':(root/'raw/stdout.txt').write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    review.review_case(config,case,root,annotation,inherited,{},'124' if target=='job' else '123')


if __name__=='__main__':unittest.main(verbosity=2)
