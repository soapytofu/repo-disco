"""Audit current evidence, protected bytes and reference-relative structure offline.

This consumes existing observations, not new trials. The trusted generated module
headers have a deliberately simple shape; this is not a general Dafny parser.
"""
import importlib.util,json,re,sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REV=ROOT/'revision-002'
sys.path.insert(0,str(REV))
from preflight import load,save,sha,matches,diagnostic
import review_reference_gate

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

MAP=module('map_metrics',ROOT.parents[1]/'scripts/repository_map_metrics.py')
GUARD=module('varied_guard',ROOT/'protocol/body_guard.py')

PATHS={
 'bounded_allocation':dict(shallow=['A.Direct(a,b,c,d,t,u,w)'],
     deep=['O1.Left(a,b,u) or O1.Right(c,d,w)','O2.Join(a,b,c,d,u,w)','A.Finish(a,b,c,d,t,u,w)'],
     explanation='Opaque individual bounds feed the joined bounds, then the final existence certificate. Balance is an additional independent prerequisite.'),
 'map_swap':dict(shallow=['A.ObserveSwap(m,k,j)','A.ObserveSwap(once,k,j)','A.Equal(m,twice)'],
     deep=['O1.Certify(m,k,j)','O2.SwapKeys(m,k,j)','O1.Certify(once,k,j)','O2.SwapKeys(once,k,j) or O2.SwapAt(once,k,j,q)','A.Equal(m,twice)'],
     explanation='The recorded path uses the first domain certificate and key equality to justify certification of the intermediate map. Inner/outer pointwise value facts are also required by the chosen reference.'),
 'clamp_distance':dict(shallow=['A.Below/Within/Above(l,h,x)'],
     deep=['O1.Below/Within/Above(l,h,x)','O2.ReadBelow/ReadWithin/ReadAbove(l,h,x)'],
     explanation='Per-input guarded facts: the other input is handled independently; arithmetic assertions finish the distance inequality.'),
 'prefix_split':dict(shallow=['A.Observe(s,n)'],deep=['O1.Unfold(s,n)','O2.Expose(s,n)'],
     explanation='Local unfolding only. Prove(s[1..],i-1,j) is a separate recursive contract application. Unbounded i means there is no fixed full recursion-depth number.',
     recursion=dict(call='Prove(s[1..],i-1,j)',decreases='i',whole_proof_depth=None))}

def main():
    gate=review_reference_gate.assemble()
    checks=load(REV/'checks.json');tasks=load(REV/'tasks.json')
    core={(r['task_id'],r['variant']):r for r in gate['rows']}
    negative=load(REV/'verification-002-review.json')
    assert negative['all_expected'] and negative['planned']==negative['matched']==94
    assert negative['manifest_sha256']==sha((REV/'manifest.json').read_bytes())
    inventory=[];diagnostics=[];protected_checks=0;boundary_checks=0
    for c in checks:
        key=(c['task_id'],c['variant'])
        path=ROOT/core[key]['evidence'] if c['phase']=='core' else REV/'verification-002'/(c['task_id']+'-'+c['variant']+'.json')
        r=load(path);t=next(t for t in tasks if t['task_id']==c['task_id'])
        current={p.name:p.read_text() for p in (REV/c['path']).glob('*.dfy')}
        archived={p.name:p.read_text() for p in (path.parent/c['path']).glob('*.dfy')}
        assert current==archived
        assert {n:sha(s.encode()) for n,s in current.items()}==r['source_sha256']==c['source_sha256']
        assert r['attempts']==1 and r['model_calls']==0 and r['matched'] and matches(c,r)
        assert r['diagnostic']==diagnostic(r)
        seed={p.name:p.read_text() for p in (REV/'fixtures'/t['task_id']/'empty').glob('*.dfy')}
        for n in current:
            if n not in t['editable_files']:
                assert current[n]==seed[n];protected_checks+=1
            else:
                prefix,suffix=GUARD.split_seed(seed[n])
                assert current[n].startswith(prefix) and current[n].endswith(suffix);boundary_checks+=1
        text=r['stdout']+'\n'+r['stderr']
        tags=[tag for tag,pattern in [('precondition',r'precondition|for this call'),('postcondition',r'postcondition'),('assertion',r'assertion'),('termination',r'decreases|termination'),('resolution',r'does not exist|unresolved|not found|not a member'),('warning',r'warning'),('parse',r'parse errors|syntax error')] if re.search(pattern,text,re.I)]
        assert 'parse' not in tags
        if c['expected']=='success':assert r['exit_code']==0 and 'warning' not in tags
        inventory.append(dict(task_id=c['task_id'],variant=c['variant'],expected=c['expected'],diagnostic=r['diagnostic'],
            evidence=str(path.relative_to(ROOT)),evidence_sha256=sha(path.read_bytes()),source_sha256=c['source_sha256'],
            job_id=load(path.parent/'environment.json')['job_id'],reused_from_original=c['phase']=='core' and core[key]['reused']))
        diagnostics.append(dict(task_id=c['task_id'],variant=c['variant'],exit_code=r['exit_code'],primary=r['diagnostic'],all_tags=tags,
            error_lines=[line.strip() for line in text.splitlines() if re.search(r'Error:|Warning:',line)]))
    assert len(inventory)==126
    structure=[]
    for t in tasks:
        fs={p.name:p.read_text() for p in (REV/'fixtures'/t['task_id']/'reference').glob('*.dfy')}
        modules=[];imports={};views={}
        for name,s in fs.items():
            names=re.findall(r'^module (\w+) \{',s,re.M)
            if name=='All.dfy':assert not names;continue
            assert len(names)==1;mod=names[0];modules.append(mod);imports[mod]={};views[mod]={}
            for alias,target,view in re.findall(r'^  import (\w+) = (\w+)(?:`(\w+))?$',s,re.M):
                imports[mod][alias]=target;views[mod][alias]=view or None
        mapping=dict(modules=sorted(modules),imports=imports)
        sizes={}
        for name in t['editable_files']:
            seed=(REV/'fixtures'/t['task_id']/'empty'/name).read_text();pre,suf=GUARD.split_seed(seed)
            body=fs[name][len(pre):-len(suf)];sizes[name]=len(body.encode())
        paths={'ClientA.Target':['HelperA.Prove'],'ClientB.Target':['HelperB.Prove']}
        if t['sharing']=='shared':paths['ClientB.Target'].append('HelperA.Prove')
        chain=PATHS[t['semantic_instance']][t['depth']]
        structure.append(dict(task_id=t['task_id'],module_map=mapping,export_views=views,
            import_metrics={c:MAP.measure(mapping,c) for c in ['ClientA','ClientB']},
            reference_contract_path=chain,reference_path_stages=len(chain),reference_path_edges=len(chain)-1,
            path_scope='Local reference path excluding clients, the shared forwarding helper and recursive expansion; not a lower bound',
            minimum_proof_depth=None,prompt_tokens=None,client_helper_paths=paths,
            editable_body_bytes=sizes,total_editable_body_bytes=sum(sizes.values()),
            full_reference_source_bytes=sum(len(s.encode()) for s in fs.values())))
    for instance in PATHS:
        for sharing in ['shared','separate']:
            a,b=[next(row for row in structure if row['task_id']==f'{instance}-{depth}-{sharing}') for depth in ['shallow','deep']]
            assert a['module_map']==b['module_map']
            # Import depth is NOT the manipulated reference contract depth.
            assert a['import_metrics']==b['import_metrics']
    report=dict(current_controls=126,all_expected=True,new_model_calls=0,
        outcomes=dict(Counter(c['expected'] for c in checks)),
        protected_file_checks=protected_checks,protected_body_boundary_checks=boundary_checks,
        current_observations_by_job=dict(Counter(r['job_id'] for r in inventory)),
        distinct_actual_verifier_invocations=134,superseded_original_map_checks=8,
        interpretation='126 current control observations; 24 reused unchanged, eight revised map checks, 94 new negatives. The eight original map core outcomes are preserved outside this current inventory.',
        rows=inventory)
    save(ROOT/'current-evidence.json',report);save(ROOT/'diagnostic-audit.json',diagnostics)
    save(ROOT/'structural-audit.json',dict(method='Exact source headers plus existing repository_map_metrics; analyst-annotated sufficient reference paths',
        family_annotations=PATHS,minimum_depth_claim=False,model_effect_claim=False,rows=structure))
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))

if __name__=='__main__':main()
