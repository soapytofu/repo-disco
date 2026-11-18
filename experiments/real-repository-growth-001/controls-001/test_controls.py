"""Synthetic records/fake processes only: no verifier, SSH, provider or SDK."""
import contextlib
import copy
import csv
import io
import json
import re
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import common as c
import review
import score
import verify_controls as worker
from capture import write,digest


def synthetic_native(project,case_id,root=c.ROOT,changes=None,remove=(),counts=None,exit_code=None,frontend=False,empty=False):
    """Full saved baseline identities, entirely synthetic outcomes and timings."""
    entry=c.case(project,case_id,root);base=c.base_profile(project,root)
    original=({n:1 for n in base['required_units']} if project=='dafny-vmc' else base['required']['inventory'])
    inventory={**original,**entry['expected_observed_new_inventory']};inventory.update(counts or {})
    states={k:['Passed']*count for k,count in inventory.items()}
    for key,value in entry['expected_new_outcomes'].items():
        if value!='Missing':states[key]=[value]*inventory[key]
    for key,value in (changes or {}).items():states[key]=[value]*inventory[key]
    for key in remove:states.pop(key,None)
    errors=sum(v=='Failed' for values in states.values() for v in values)
    passed=sum(v=='Passed' for values in states.values() for v in values)
    warnings='\n\n'.join(base['upstream_warnings'])+'\n\n'
    raw={'resources.txt':b'OFFLINE SYNTHETIC resource fixture; no native process\n'}
    if project=='dafny-vmc':
        stream=io.StringIO(newline='');writer=csv.writer(stream)
        writer.writerow(['TestResult.DisplayName','TestResult.Outcome','TestResult.Duration','TestResult.ResourceCount'])
        for key,values in sorted(states.items()):
            for value in values:writer.writerow([key,value,'00:00:00.001','1'])
        raw['csv/TestResults/fake.csv']=stream.getvalue().encode()
        raw['stdout.txt']=(warnings+('1 resolution/type errors detected\n' if frontend else
                                  'Dafny program verifier finished with %d verified, %d errors\n'%(passed,errors))).encode()
        raw['stderr.txt']=b''
    else:
        by_crate={name:{} for name in base['required']['crates']}
        for key,values in sorted(states.items()):
            owner,module,name,mode=json.loads(key)
            units=by_crate[owner].setdefault(module,[])
            units.extend({'function':name,'mode:':mode,'success':value=='Passed'} for value in values)
        reports=[]
        for owner,modules in sorted(by_crate.items()):
            units=[u for values in modules.values() for u in values]
            failed=sum(not u['success'] for u in units)
            reports.append({'verus':base['required']['version'],
                'verification-results':{'encountered-vir-error':False,'encountered-error':bool(failed),
                    'errors':failed,'verified':len(units)-failed,'success':not failed,'is-verifying-entire-crate':True},
                'times-ms':{'num-threads':1,'smt':{'smt-run-module-times':[
                    {'module':name,'function-breakdown':values} for name,values in sorted(modules.items())]}}})
        raw['stdout.txt']=('\n'.join(json.dumps(r,separators=(',',':')) for r in reports)+'\n').encode()
        raw['stderr.txt']=(warnings+('error[E0425]: synthetic unknown item\n' if frontend else '')).encode()
    if empty:raw={'stdout.txt':b'','stderr.txt':b'','resources.txt':raw['resources.txt']}
    code=(2 if frontend else (4 if errors and project=='dafny-vmc' else 1 if errors else 0)) if exit_code is None else exit_code
    command,_,_=worker.make_command(project,case_id,root/'work'/project/case_id,root)
    native={'command':command,'cwd':str(root),'exit_code':code,'elapsed_seconds':0.01,'timeout':code==124,
            'attempts':1,'model_calls':0,'artifacts':{n:digest(raw[n]) for n in ('stdout.txt','stderr.txt','resources.txt')}}
    return native,raw


class ScopeAndScorerTests(unittest.TestCase):
    def test_all_23_exact_overlay_scopes_are_bound_and_completed_references_excluded(self):
        plan=c.validate_inputs()
        self.assertEqual(sum(map(len,plan['cases'].values())),23)
        for project,completed in plan['completed_references_excluded'].items():
            self.assertFalse((c.ROOT/'inputs'/project/completed).exists())
            with self.assertRaisesRegex(ValueError,'completed references'):c.case(project,completed)
        self.assertEqual(c.aggregate_budget('dafny-vmc')['native_cap_total_seconds'],3300)
        self.assertEqual(c.aggregate_budget('vest')['native_cap_total_seconds'],10800)

    def test_all_declared_categories_match_synthetic_named_outcomes(self):
        matched=[]
        for project in c.PROJECTS:
            for entry in c.cases(project):
                with self.subTest(project=project,case=entry['id']):
                    native,raw=synthetic_native(project,entry['id'])
                    result=score.observe(project,entry['id'],native,raw)
                    self.assertTrue(result['expectation_match'],result)
                    self.assertEqual(result['whole_workspace_proof_pass'],entry['expected_kind']=='proof_pass')
                    self.assertTrue(result['original_all_pass']);matched.append(entry['id'])
        self.assertEqual(len(matched),23)

    def test_external_spec_labels_keep_native_report_owner_and_old_failures_reject(self):
        base=c.base_profile('vest');external=[key for key in base['required']['inventory']
            if json.loads(key)[0]!=json.loads(key)[2].split('::')[0]]
        self.assertEqual(sum(base['required']['inventory'][k] for k in external),26)
        native,raw=synthetic_native('vest','frame-reference');outcomes=score.vest_outcomes(raw)
        for key in external:self.assertEqual(outcomes[key],['Passed']*base['required']['inventory'][key])
        result=score.observe('vest','frame-reference',native,raw)
        self.assertTrue(result['original_all_pass']);self.assertTrue(result['expectation_match'])
        native,raw=synthetic_native('vest','frame-reference',changes={external[0]:'Failed'})
        result=score.observe('vest','frame-reference',native,raw)
        self.assertFalse(result['expectation_match']);self.assertIn(external[0],result['original_failed_units'])

    def test_unproved_parent_must_fail_while_actual_child_passes(self):
        for project,cid in [('dafny-vmc','pair-with-unproved-parent'),('vest','batch-unproved-frame')]:
            entry=c.case(project,cid);native,raw=synthetic_native(project,cid)
            result=score.observe(project,cid,native,raw)
            self.assertEqual(result['unproved_parent_observation']['parent_outcome'],['Failed'])
            self.assertEqual(result['unproved_parent_observation']['child_outcome'],['Passed'])
            native,raw=synthetic_native(project,cid,changes={entry['child_target']:'Failed'})
            self.assertFalse(score.observe(project,cid,native,raw)['expectation_match'])

    def test_dafny_negative_requires_summary_and_csv_passed_count_agreement(self):
        native,raw=synthetic_native('dafny-vmc','move-noop')
        self.assertTrue(score.observe('dafny-vmc','move-noop',native,raw)['expectation_match'])
        raw['stdout.txt']=re.sub(rb'finished with (\d+) verified',
            lambda m:b'finished with '+str(int(m.group(1))+1).encode()+b' verified',raw['stdout.txt'])
        observed=score.observe('dafny-vmc','move-noop',native,raw)
        self.assertEqual(observed['category'],'PROOF_FAILURE');self.assertTrue(observed['named_expectations_match'])
        self.assertFalse(observed['native_observation']['count_agreement']);self.assertFalse(observed['expectation_match'])

    def test_precise_omission_requires_native_pass_and_no_missing_old_units(self):
        for project,cid in [('dafny-vmc','detached-omitted'),('vest','frame-omitted'),('vest','batch-omitted')]:
            native,raw=synthetic_native(project,cid);result=score.observe(project,cid,native,raw)
            self.assertTrue(result['native_observation']['proof_pass']);self.assertTrue(result['expectation_match'])
            self.assertFalse(result['required_workspace_coverage']);self.assertFalse(result['whole_workspace_proof_pass'])
            base=c.base_profile(project);key=next(iter(base['required_units'] if project=='dafny-vmc' else base['required']['inventory']))
            native,raw=synthetic_native(project,cid,remove=[key])
            self.assertFalse(score.observe(project,cid,native,raw)['expectation_match'])

    def test_missing_new_target_changed_multiplicity_metadata_and_extra_unit_reject(self):
        for project,cid in [('dafny-vmc','pair-alternative'),('vest','batch-alternative')]:
            entry=c.case(project,cid);key=next(iter(entry['required_new_inventory']))
            native,raw=synthetic_native(project,cid,remove=[key])
            self.assertFalse(score.observe(project,cid,native,raw)['expectation_match'])
        base=c.base_profile('vest');key=next(k for k,v in base['required']['inventory'].items() if v>1)
        native,raw=synthetic_native('vest','frame-reference',counts={key:base['required']['inventory'][key]-1})
        self.assertFalse(score.observe('vest','frame-reference',native,raw)['expectation_match'])
        extra=json.dumps(['vest_dev','new_unapproved','vest_dev::new_unapproved::unexpected','proof'],separators=(',',':'))
        native,raw=synthetic_native('vest','frame-reference',counts={extra:1})
        self.assertFalse(score.observe('vest','frame-reference',native,raw)['expectation_match'])
        native,raw=synthetic_native('vest','frame-reference')
        raw['stdout.txt']=raw['stdout.txt'].replace(b'"num-threads":1',b'"num-threads":2')
        self.assertFalse(score.observe('vest','frame-reference',native,raw)['expectation_match'])

    def test_fixed_frame_specs_are_explicitly_unlogged_never_logged_passes(self):
        for cid in ('frame-reference','batch-alternative','frame-omitted'):
            native,raw=synthetic_native('vest',cid);result=score.observe('vest',cid,native,raw)
            self.assertEqual(len(result['fixed_unlogged_definitions']),6)
            for item in result['fixed_unlogged_definitions']:
                self.assertNotIn(json.dumps(item['unit'],separators=(',',':')),result['actual_inventory'])
                if cid=='frame-omitted':self.assertEqual(item['observation'],'UNREGISTERED_FIXED_SPEC_SOURCE')
                else:self.assertNotIn('Passed',item.values())

    def test_frontend_and_unresolved_native_termination_never_match_controls(self):
        for project,cid in [('dafny-vmc','move-reference'),('vest','frame-reference')]:
            native,raw=synthetic_native(project,cid,frontend=True);result=score.observe(project,cid,native,raw)
            self.assertFalse(result['expectation_match']);self.assertFalse(result['stop_after_case'])
            for code in (-9,-15,124,137,143):
                native,raw=synthetic_native(project,cid,exit_code=code);result=score.observe(project,cid,native,raw)
                self.assertTrue(result['stop_after_case']);self.assertFalse(result['expectation_match'])
                self.assertEqual(result['execution_termination'],'UNRESOLVED_SIGNAL_OR_TIMEOUT')

    def test_commands_have_fixed_caps_full_scope_and_fresh_single_worker_targets(self):
        targets=[]
        for project in c.PROJECTS:
            for entry in c.cases(project):
                cmd,logical,limit=worker.make_command(project,entry['id'],c.ROOT/'work'/project/entry['id'])
                self.assertEqual(limit,300 if project=='dafny-vmc' else 900)
                if project=='vest':
                    self.assertIn('CARGO_BUILD_JOBS=1',cmd);self.assertIn('--offline',cmd)
                    self.assertEqual(cmd[cmd.index('--num-threads')+1],'1')
                    targets.append(cmd[cmd.index('--target-dir')+1]);self.assertIn('vest_dev',cmd)
                else:
                    self.assertEqual(cmd[cmd.index('--resource-limit')+1],'100000')
                    self.assertTrue(set(c.base_profile(project)['explicit_sources'])<=set(logical))
                    for omitted in entry['explicitly_omit_from_command']:self.assertNotIn(omitted,logical)
        self.assertEqual(len(targets),len(set(targets)))

    def test_missing_native_report_is_ambiguous_even_when_process_returns_zero(self):
        for project,cid in [('dafny-vmc','move-reference'),('vest','frame-reference')]:
            native,raw=synthetic_native(project,cid,empty=True,exit_code=0)
            result=score.observe(project,cid,native,raw)
            self.assertTrue(result['stop_after_case']);self.assertFalse(result['expectation_match'])
            self.assertEqual(result['execution_termination'],'AMBIGUOUS_OR_MISSING_NATIVE_EVIDENCE')


@contextlib.contextmanager
def fake_runtime(project):
    """Small temporary parent plus exact overlays; no upstream checkout copied."""
    with tempfile.TemporaryDirectory(prefix='growth-controls-offline-') as temp:
        root=Path(temp)/'outputs/real-repository-growth-001/controls-001';root.mkdir(parents=True)
        for name in ('plan.json','tool-image-pins.json'):
            shutil.copy2(c.ROOT/name,root/name)
        for name in ('qualification','reference-gates'):
            shutil.copytree(c.ROOT/name,root/name)
        shutil.copytree(c.ROOT/'inputs'/project,root/'inputs'/project)
        write(root/'runtime-freeze.json',{'synthetic_fixture':True,'model_calls':0})
        upstream=worker.qualification(root)/'upstream'/project;upstream.mkdir(parents=True)
        (upstream/'Original.txt').write_text('OFFLINE synthetic parent, no mathematical evidence\n')
        parents={'Original.txt':c.sha(upstream/'Original.txt')}
        out=root/('verification-'+project+'-001');out.mkdir();job='90001'
        budget=c.aggregate_budget(project,root);runtime=c.sha(root/'runtime-freeze.json')
        write(out/'environment.json',dict(project=project,job_id=job,partition='test',cpus=1,execution_root=str(root),
                  model_calls=0,plan_sha256=c.sha(root/'plan.json'),runtime_sha256=runtime,aggregate_budget=budget))
        write(root/'submissions'/(project+'.json'),dict(job_id=job,partition='test',no_requeue=True,runtime_sha256=runtime,aggregate_budget=budget))
        def fake_tools(pr,r):
            image='container-003' if pr=='dafny-vmc' else 'vest-container-004'
            closure='coverage-001/results/tool-closure.json' if pr=='dafny-vmc' else 'vest-container-004/results/verus-tool-closure.json'
            return dict(project=pr,image=str(worker.qualification(r)/image/'runtime.sif'),
                image_sha256=c.read(r/'tool-image-pins.json')[image]['sif_sha256'],closure_path=closure,
                closure_manifest_sha256=c.sha(r/'qualification'/closure),checked_tool_files=len(c.read(r/'qualification'/closure)),
                toolchain=c.base_profile(pr,r)['toolchain'])
        with patch.object(c,'validate_package',side_effect=lambda r=c.ROOT:c.read(r/'plan.json')), \
             patch.object(c,'project_sources',side_effect=lambda pr,r=c.ROOT:dict(parents)), \
             patch.object(worker,'tool_observation',side_effect=fake_tools):
            yield root,out,job,upstream


def fake_capture_for(project,root,calls,first=None,mutate_parent=False,malformed=False):
    def capture(label,command,cwd,out,env,limit):
        cid=out.name;calls.append(cid);kwargs=dict(first or {}) if len(calls)==1 else {}
        native,raw=synthetic_native(project,cid,root,**kwargs)
        if malformed and len(calls)==1:raw['csv/TestResults/fake.csv']=b'wrong,csv,header\n'
        folder=out/'native';folder.mkdir(exist_ok=False)
        for name in ('stdout.txt','stderr.txt','resources.txt'):(folder/name).write_bytes(raw[name])
        if project=='dafny-vmc':
            for name,data in raw.items():
                if name.startswith('csv/'):
                    dest=root/'work'/project/cid/name[4:];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        else:
            target=root/'targets'/project/cid;target.mkdir(parents=True,exist_ok=False)
            (target/'fake-build-marker').write_text('isolated offline fake Cargo target\n')
        if mutate_parent:(root/'work'/project/cid/'Original.txt').write_text('tampered during fake process\n')
        write(folder/'record.json',native);return native
    return capture


class FakeWorkerTests(unittest.TestCase):
    def test_all_dafny_cases_once_replay_then_tampered_and_stale_evidence_reject(self):
        with fake_runtime('dafny-vmc') as (root,out,job,_):
            calls=[];result=worker.run_cases('dafny-vmc',out,job,root,fake_capture_for('dafny-vmc',root,calls))
            self.assertEqual(result['state'],'COMPLETE');self.assertEqual(calls,[e['id'] for e in c.cases('dafny-vmc',root)])
            self.assertEqual(review.review_project('dafny-vmc',root)['matched_expectations'],11)
            env=c.read(out/'environment.json');env['project']='vest';(out/'environment.json').write_text(json.dumps(env))
            with self.assertRaisesRegex(ValueError,'project identity'):review.review_project('dafny-vmc',root)
            env['project']='dafny-vmc';(out/'environment.json').write_text(json.dumps(env))
            bound_path=out/calls[0]/'bound-record.json';bound=c.read(bound_path);original_id=bound['run_id']
            bound['run_id']='89999:'+calls[0];bound_path.write_text(json.dumps(bound))
            with self.assertRaisesRegex(ValueError,'Stale run'):review.review_project('dafny-vmc',root)
            bound['run_id']=original_id;bound_path.write_text(json.dumps(bound))
            (out/calls[0]/'native/stdout.txt').write_text('tampered raw evidence\n')
            with self.assertRaisesRegex(ValueError,'Raw evidence'):review.review_project('dafny-vmc',root)
            with self.assertRaisesRegex(ValueError,'no restart or resume'):
                worker.verify_case('dafny-vmc',calls[0],out,job,root,fake_capture_for('dafny-vmc',root,calls))
            self.assertEqual(len(calls),11)

    def test_well_formed_unexpected_frontend_continues_distinct_fixed_cases(self):
        with fake_runtime('dafny-vmc') as (root,out,job,_):
            calls=[];result=worker.run_cases('dafny-vmc',out,job,root,fake_capture_for('dafny-vmc',root,calls,first={'frontend':True}))
            self.assertEqual(result['state'],'COMPLETE');self.assertEqual(len(calls),11)
            self.assertFalse(result['results'][0]['expectation_match']);self.assertEqual(result['results'][0]['category'],'RESOLUTION_OR_TYPE_FAILURE')
            self.assertEqual(review.review_project('dafny-vmc',root)['matched_expectations'],10)

    def test_signal_or_timeout_halts_before_next_case_and_cannot_resume(self):
        for code in (-9,143,124):
            with self.subTest(code=code),fake_runtime('dafny-vmc') as (root,out,job,_):
                calls=[];capture=fake_capture_for('dafny-vmc',root,calls,first={'exit_code':code})
                result=worker.run_cases('dafny-vmc',out,job,root,capture)
                self.assertEqual(calls,['move-reference']);self.assertEqual(result['state'],'STOPPED_NATIVE_TERMINATION')
                self.assertEqual(len(result['undispatched']),10)
                self.assertEqual(review.review_project('dafny-vmc',root)['native_invocations'],1)
                with self.assertRaisesRegex(ValueError,'no restart or resume'):
                    worker.run_cases('dafny-vmc',out,job,root,capture)
                self.assertEqual(calls,['move-reference'])
                self.assertFalse((out/'failure.json').exists())

    def test_malformed_parser_record_preserves_raw_and_stops_before_next_case(self):
        with fake_runtime('dafny-vmc') as (root,out,job,_):
            calls=[]
            with self.assertRaisesRegex(ValueError,'CSV schema'):
                worker.run_cases('dafny-vmc',out,job,root,fake_capture_for('dafny-vmc',root,calls,malformed=True))
            self.assertEqual(calls,['move-reference']);self.assertTrue((out/'failure.json').exists())
            self.assertTrue((out/'move-reference/native/csv/TestResults/fake.csv').exists())
            self.assertTrue((out/'move-reference/observation-error.json').exists())

    def test_empty_native_report_halts_before_next_invocation_and_preserves_tail(self):
        for project in c.PROJECTS:
            with self.subTest(project=project),fake_runtime(project) as (root,out,job,_):
                calls=[];result=worker.run_cases(project,out,job,root,fake_capture_for(project,root,calls,first={'empty':True}))
                self.assertEqual(len(calls),1);self.assertEqual(result['state'],'STOPPED_AMBIGUOUS_NATIVE_EVIDENCE')
                self.assertEqual(len(result['undispatched']),len(c.cases(project,root))-1)
                self.assertEqual(review.review_project(project,root)['native_invocations'],1)
                self.assertEqual((out/calls[0]/'native/stdout.txt').read_bytes(),b'')

    def test_parent_change_before_or_during_execution_stops(self):
        for during in (False,True):
            with self.subTest(during=during),fake_runtime('dafny-vmc') as (root,out,job,upstream):
                calls=[]
                if not during:(upstream/'Original.txt').write_text('changed parent\n')
                with self.assertRaisesRegex(ValueError,'Parent source differs|Source changed during execution'):
                    worker.run_cases('dafny-vmc',out,job,root,fake_capture_for('dafny-vmc',root,calls,mutate_parent=during))
                self.assertEqual(len(calls),1 if during else 0);self.assertTrue((out/'failure.json').exists())

    def test_vest_cases_use_disjoint_fresh_build_and_source_paths(self):
        with fake_runtime('vest') as (root,out,job,_):
            calls=[];capture=fake_capture_for('vest',root,calls)
            for cid in ('frame-reference','frame-empty'):
                row=worker.verify_case('vest',cid,out,job,root,capture);self.assertTrue(row['expectation_match'])
                self.assertEqual(review.review_case('vest',c.case('vest',cid,root),out,c.read(out/'environment.json'),root),row)
            self.assertEqual(len(list((root/'targets/vest').iterdir())),2)
            self.assertEqual(len(list((root/'work/vest').iterdir())),2)
            with self.assertRaisesRegex(ValueError,'no restart or resume'):
                worker.verify_case('vest','frame-reference',out,job,root,capture)
            self.assertEqual(len(calls),2)


if __name__=='__main__':unittest.main()
