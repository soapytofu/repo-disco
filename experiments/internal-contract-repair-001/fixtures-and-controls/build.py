"""Deterministic two-seed construction from exact reviewed local parent bytes."""
from pathlib import Path, PurePosixPath
import argparse
import base64
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parent
PARENT_STUDY = 'experiments/internal-contract-propagation-001'
OLD_IDS = ('capped_endpoint_return_migration','extracted_entry_return_migration')
REUSED = ('paired_repair','alternative','helper_only','contract_only')
FILES = ('All.dfy','Client.dfy','Helper.dfy','Kernel.dfy')
EDITABLE = ('Helper.dfy','Client.dfy')
REVIEW = 'reviews/review-002/results-review.json'


def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(path): return json.loads(Path(path).read_bytes())
def save(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')
def hashes(files): return {n:sha(b) for n,b in sorted(files.items())}
def safe(root,name):
    rel=PurePosixPath(name)
    assert rel.parts and not rel.is_absolute() and '..' not in rel.parts
    p=Path(root)/str(rel)
    assert not p.is_symlink() and p.resolve().is_relative_to(Path(root).resolve())
    return p
def workspace(parent,old_id,variant):
    folder=parent/'fixtures'/old_id/variant
    result={p.name:p.read_bytes() for p in sorted(folder.glob('*.dfy'))}
    assert set(result)==set(FILES)
    return result


def body_boundary(raw):
    """Locate this fixed one-method source using balanced braces, not greedy regex."""
    assert isinstance(raw,bytes) and b'// ' not in raw and b'/*' not in raw
    marker=b'  {\n'; assert raw.count(marker)==1
    start=raw.index(marker)+len(marker)
    depth=1; closing=None
    for position in range(start,len(raw)):
        if raw[position:position+1]==b'{': depth+=1
        elif raw[position:position+1]==b'}':
            depth-=1
            if depth==0:
                closing=position; break
    assert closing is not None
    end=raw.rfind(b'\n',start,closing)+1
    assert raw[end:]==b'  }\n}\n'
    return {'start':start,'end':end,
            'protected_sha256':sha(raw[:start]+b'<BODY>\n'+raw[end:])}


def body(raw):
    span=body_boundary(raw);return raw[span['start']:span['end']]


def snapshot_inputs(parent,root):
    parent=Path(parent).resolve();root=Path(root).resolve()
    report=read(parent/REVIEW)
    assert report['all_expected'] is True and report['job_id']=='60723362'
    assert report['planned']==report['reviewed']==18 and report['model_calls']==0
    cases={c['case_id']:c for c in read(parent/'cases.json')}
    review={c['case_id']:c for c in report['checks']}
    names={'tasks.json','cases.json','design.json','lineage.json','build.py','verify.py',
           'fixture-manifest.json','runtime-manifest.json','review-v2-scope.json',
           REVIEW,'reviews/review-002/evidence-sha256.json'}
    for old_id in OLD_IDS:
        for variant in ('reference',*REUSED):
            case=cases[old_id+'-'+variant]
            sources=workspace(parent,old_id,variant)
            assert hashes(sources)==case['source_sha256']
            names.update(case['path']+'/'+name for name in FILES)
            if variant=='reference': continue
            record_name='verification-001/'+case['case_id']+'.json'
            record=read(parent/record_name); reviewed=review[case['case_id']]
            assert reviewed['matched'] and reviewed['named_expected_match']
            assert sha((parent/record_name).read_bytes())==reviewed['evidence_sha256']
            assert record['source_sha256']==case['source_sha256']
            names.add(record_name)
            for stream in ('stdout','stderr'):
                name='verification-001/raw/'+case['case_id']+'/'+stream+'.txt'
                raw=(parent/name).read_bytes()
                assert raw==base64.b64decode(record[stream+'_base64'],validate=True)
                assert sha(raw)==record[stream+'_sha256']; names.add(name)
            for csvname,digest in record['csv_sha256'].items():
                name='verification-001/raw/'+case['case_id']+'/csv/'+csvname
                raw=safe(parent,name).read_bytes()
                assert raw==base64.b64decode(record['csv_base64'][csvname],validate=True)
                assert sha(raw)==digest;names.add(name)
    pins={}
    for name in sorted(names):
        raw=safe(parent,name).read_bytes(); dest=safe(root,'inputs/parent/'+name)
        dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists(): assert dest.read_bytes()==raw, 'Existing parent input differs: '+name
        else: dest.write_bytes(raw)
        pins[name]=sha(raw)
    save(root/'parent-inputs.json',{'schema':'repodisco-exact-parent-inputs-v1',
        'parent_study':PARENT_STUDY,'parent_job_id':'60723362',
        'review_path':REVIEW,'review_sha256':pins[REVIEW],
        'local_prefix':'inputs/parent','files':pins})


def validate_inputs(root):
    inventory=read(root/'parent-inputs.json')
    assert inventory['parent_study']==PARENT_STUDY
    for name,digest in inventory['files'].items():
        assert sha(safe(root,'inputs/parent/'+name).read_bytes())==digest, name
    assert inventory['review_sha256']==inventory['files'][REVIEW]
    report=read(root/'inputs/parent'/REVIEW)
    assert report['all_expected'] is True and report['planned']==report['reviewed']==18
    return inventory


def file_rules(old_id):
    if old_id==OLD_IDS[0]:
        params={'start':'int','length':'int','cap':'int'}
        pure={'K.Endpoint':3}
        ptypes={'K.Endpoint':{'arguments':['int','int','int'],'result':'int'}}
        helper_outputs={'r':'int'}; client_outputs={'result':'int'};result='int'
    else:
        params={'m':'map<int,int>','key':'int'}
        pure={'K.Erase':2,'K.Entry':2,'K.Exclude':2}
        ptypes={'K.Erase':{'arguments':['map<int,int>','int'],'result':'map<int,int>'},
                'K.Entry':{'arguments':['map<int,int>','int'],'result':'map<int,int>'},
                'K.Exclude':{'arguments':['map<int,int>','map<int,int>'],'result':'map<int,int>'}}
        helper_outputs={'r':'map<int,int>'}
        client_outputs={'remaining':'map<int,int>','removed':'map<int,int>'};result='map<int,int>'
    def rule(outputs):
        return {'variables':list(params),'parameter_types':params,'output_types':outputs,
                'pure':pure,'pure_types':ptypes,'calls':{},'call_types':{},'call_returns':{}}
    h,c=rule(helper_outputs),rule(client_outputs)
    c['calls']={'H.Transfer':len(params)};c['call_types']={'H.Transfer':list(params.values())}
    c['call_returns']={'H.Transfer':result}
    return {'Helper.dfy':h,'Client.dfy':c}


def counterexamples(old_id):
    if old_id==OLD_IDS[0]:
        return [
          {'target':'Helper.Transfer','input':{'start':1,'length':1,'cap':5},
           'new_preconditions_hold':True,'old_body_result':2,'new_expected_result':1,
           'violations':['r <= length','start + r == K.Endpoint(start,length,cap)']},
          {'target':'Client.Target','input':{'start':4,'length':1,'cap':3},
           'public_preconditions_hold':True,'violated_call_precondition':'start <= cap'},
          {'target':'Client.Target','input':{'start':1,'length':1,'cap':5},
           'callee_assumed_new_return':1,'old_caller_public_result':1,'public_expected_result':2,
           'interpretation':'Modular caller counterexample under the selected new contract; not execution of the invalid helper.'}]
    return [
      {'target':'Helper.Transfer','input':{'m':[[1,10],[2,20]],'key':1},
       'new_preconditions_hold':True,'old_body_result':[[2,20]],'new_expected_result':[[1,10]],
       'violations':['r == K.Entry(m,key)','r.Keys == {key}']},
      {'target':'Client.Target','input':{'m':[[1,10]],'key':2},
       'public_preconditions_hold':True,'violated_call_precondition':'key in m'},
      {'target':'Client.Target','input':{'m':[[1,10],[2,20]],'key':1},
       'callee_assumed_new_return':[[1,10]],'old_caller_remaining':[[1,10]],'public_expected_remaining':[[2,20]],
       'interpretation':'Modular caller counterexample under the selected new contract; not execution of the invalid helper.'}]


def assert_scope(task,files):
    assert set(files)==set(FILES), 'Workspace membership changed'
    for name in ('Kernel.dfy','All.dfy'):
        assert sha(files[name])==task['source_sha256'][name], 'Protected file changed: '+name
    for name in EDITABLE:
        span=body_boundary(files[name])
        assert span['protected_sha256']==task['body_boundaries'][name]['protected_sha256'], 'Protected method header changed: '+name
    assert sha(files['Client.dfy'][:body_boundary(files['Client.dfy'])['start']])==task['public_contract_sha256']
    assert sha(files['Helper.dfy'][:body_boundary(files['Helper.dfy'])['start']])==task['fixed_helper_prefix_sha256']
    for raw in files.values():
        assert not re.search(rb'\b(?:assume|axiom)\b|{:\s*(?:verify|extern)',raw)


def generate(root,inputs_root=ROOT):
    root=Path(root).resolve();inputs_root=Path(inputs_root).resolve()
    inventory=validate_inputs(inputs_root)
    if root!=inputs_root:
        for name in ('parent-inputs.json',*('inputs/parent/'+n for n in inventory['files'])):
            dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(inputs_root/name,dest)
    parent=root/'inputs/parent'
    oldtasks={t['task_id']:t for t in read(parent/'tasks.json')}
    oldcases={c['case_id']:c for c in read(parent/'cases.json')}
    reviewed={c['case_id']:c for c in read(parent/REVIEW)['checks']}
    tasks=[];cases=[];controls=[]
    for old_id in OLD_IDS:
        tid=old_id+'-dual_fault';oldtask=oldtasks[old_id]
        initial=workspace(parent,old_id,'reference')
        source=dict(initial);source['Helper.dfy']=workspace(parent,old_id,'contract_only')['Helper.dfy']
        assert body(source['Helper.dfy'])==body(initial['Helper.dfy'])
        assert body(source['Client.dfy'])==body(initial['Client.dfy'])
        helper_span=body_boundary(source['Helper.dfy'])
        assert source['Helper.dfy'][:helper_span['start']]==oldtask['internal_api_versions']['new']['header'].encode()+b'  {\n'
        path='fixtures/'+tid+'/seed'
        for name,raw in source.items():
            dest=root/path/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        task={'task_id':tid,'semantic_instance':old_id,'family':oldtask['family'],
              'development_only':True,'held_out':False,'reserved_families_used':False,
              'parent_task_id':old_id,'parent_study':PARENT_STUDY,
              'path':path,'template_path':path,'entry':'All.dfy','files':list(FILES),
              'editable_files':list(EDITABLE),'internal_api_version':'new_fixed_before_repair',
              'source_sha256':hashes(source),'template_sha256':hashes(source),
              'body_boundaries':{n:body_boundary(source[n]) for n in EDITABLE},
              'public_contract_sha256':oldtask['public_contract_sha256'],
              'public_contract_prefix':oldtask['public_contract_prefix'],
              'fixed_helper_prefix':source['Helper.dfy'][:helper_span['start']].decode(),
              'fixed_helper_prefix_sha256':sha(source['Helper.dfy'][:helper_span['start']]),
              'named_targets':['Helper.Transfer','Client.Target'],
              'expected_seed_local_targets':{'Helper.Transfer':False,'Client.Target':False},
              'file_rules':file_rules(old_id),'counterexamples':counterexamples(old_id),
              'model_protocol_defined':False,'new_seed_verification_status':'not_run',
              'metadata_visibility':'Host-only; future prompts must whitelist source and permitted syntax.'}
        assert_scope(task,source);tasks.append(task)
        provider_units=[] if old_id==OLD_IDS[0] else [x+' (well-formedness)' for x in ('Kernel.Erase','Kernel.Entry','Kernel.Exclude')]
        cases.append({'case_id':tid+'-seed','task_id':tid,'variant':'seed','path':path,'entry':'All.dfy',
          'expected':'proof_failure','expected_exit':4,'expected_diagnostic':'precondition',
          'required_diagnostics':['postcondition','precondition'],
          'expected_local_targets':{'Helper.Transfer':False,'Client.Target':False},
          'expected_failed_targets':['Helper.Transfer','Client.Target'],
          'expected_target_diagnostics':{'Helper.Transfer':['postcondition'],'Client.Target':['precondition']},
          'expected_logged_provider_units':provider_units,
          'unlogged_definitions':([{'symbol':'Kernel.Endpoint','source_file':'Kernel.dfy','source_sha256':sha(source['Kernel.dfy']),
                'classification':'unlogged_definition_not_verified_provider_unit'}] if old_id==OLD_IDS[0] else []),
          'source_sha256':hashes(source),'body_boundaries':task['body_boundaries'],
          'public_contract_sha256':task['public_contract_sha256'],
          'new_verifier_observation':True})
        for variant in REUSED:
            cid=old_id+'-'+variant;oldcase=oldcases[cid];evidence=reviewed[cid]
            copied=workspace(parent,old_id,variant);assert_scope(task,copied)
            record_path='inputs/parent/verification-001/'+cid+'.json'
            record=read(root/record_path)
            assert hashes(copied)==oldcase['source_sha256']==record['source_sha256']
            assert sha((root/record_path).read_bytes())==evidence['evidence_sha256']
            assert evidence['matched'] and evidence['named_expected_match']
            changes=[n for n in EDITABLE if copied[n]!=source[n]]
            expected_changes=['Helper.dfy'] if variant=='helper_only' else ['Client.dfy'] if variant=='contract_only' else list(EDITABLE)
            assert changes==expected_changes
            controls.append({'control_id':tid+'-'+variant,'task_id':tid,'parent_case_id':cid,
              'role':{'paired_repair':'coordinated_repair','alternative':'alternative_coordinated_repair',
                      'helper_only':'helper_body_only_repair','contract_only':'client_body_only_repair'}[variant],
              'changed_editable_files':changes,'path':'inputs/parent/'+oldcase['path'],
              'original_source_path':PARENT_STUDY+'/'+oldcase['path'],'source_sha256':hashes(copied),
              'evidence_path':record_path,'evidence_sha256':evidence['evidence_sha256'],
              'original_evidence_path':PARENT_STUDY+'/verification-001/'+cid+'.json',
              'review_path':'inputs/parent/'+REVIEW,'review_sha256':inventory['review_sha256'],
              'original_job_id':'60723362','actual':evidence['actual'],
              'strict_workspace_verified':evidence['strict_workspace_verified'],
              'observed_local_targets':evidence['named_evidence']['local_targets'],
              'observed_named_units':evidence['named_evidence']['units'],
              'raw_csv_sha256':record['csv_sha256'],
              'reused_evidence':True,'new_verifier_observation':False})
    save(root/'tasks.json',tasks);save(root/'cases.json',cases);save(root/'reused-controls.json',controls)
    save(root/'lineage.json',{'schema':'repodisco-fixed-api-dual-body-repair-lineage-v1',
      'parent_study':PARENT_STUDY,'parent_job_id':'60723362','parent_inputs_sha256':sha((root/'parent-inputs.json').read_bytes()),
      'parent_review_sha256':inventory['review_sha256'],'construction':'New fixed Helper header with exact OLD Helper and Client bodies.',
      'new_seed_count':2,'reused_control_count':8,'reused_controls_are_new_observations':False,
      'tree_transition_reservations_used':False,'development_only':True,'held_out':False,
      'original_inputs_modified':False,'future_edit_scope':'Helper.Transfer and Client.Target bodies only; no header/contract edits.',
      'verifier_ancestor_sha256':inventory['files']['verify.py'],
      'verifier_change':'Standard-library adapter adds mandatory per-target CSV outcomes and file-correlated diagnostic checks.',
      'claim_limit':'Insufficiency of the chosen one-sided patches under the selected new API, not mathematical necessity of multi-file repair.'})
    pins={str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted((root/'fixtures').rglob('*.dfy'))}
    for name in ('tasks.json','cases.json','reused-controls.json','lineage.json','parent-inputs.json'):
        pins[name]=sha((root/name).read_bytes())
    for name,digest in inventory['files'].items():pins['inputs/parent/'+name]=digest
    save(root/'fixture-manifest.json',dict(sorted(pins.items())))
    return {'fresh_checks':len(cases),'reused_controls':len(controls),'source_files':8,'model_calls':0}


def freeze_runtime(root=ROOT):
    root=Path(root).resolve()
    pins=read(root/'fixture-manifest.json')
    for name in ('README.md','build.py','verify.py','test_design.py','test_structure.py','verify.sbatch','fixture-manifest.json'):
        pins[name]=sha((root/name).read_bytes())
    save(root/'adapter-preservation-001.json',{'purpose':'Exact prospective source/runtime inputs, not new verification evidence.','files':dict(sorted(pins.items()))})
    pins['adapter-preservation-001.json']=sha((root/'adapter-preservation-001.json').read_bytes())
    save(root/'runtime-manifest.json',dict(sorted(pins.items())))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--parent',type=Path);args=parser.parse_args()
    if args.parent:snapshot_inputs(args.parent,ROOT)
    print(json.dumps(generate(ROOT),sort_keys=True));freeze_runtime()
