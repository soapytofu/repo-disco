"""Deterministic construction of two explicit internal-API migrations; no tools."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
TARGETS = ['Helper.Transfer','Client.Target']

ARITHMETIC_KERNEL = '''module Kernel {
  function Endpoint(start: int, length: int, cap: int): int {
    if start + length <= cap then start + length else cap
  }
}
'''
MAP_KERNEL = '''module Kernel {
  function Erase(m: map<int,int>, key: int): map<int,int> {
    map x | x in m && x != key :: m[x]
  }
  function Entry(m: map<int,int>, key: int): map<int,int> {
    map x | x in m && x == key :: m[x]
  }
  function Exclude(m: map<int,int>, patch: map<int,int>): map<int,int> {
    map x | x in m && x !in patch :: m[x]
  }
}
'''

AH_OLD = '''    if start + length <= cap {
      r := start + length;
    } else {
      r := cap;
    }
'''
AH_NEW = '''    if length <= cap - start {
      r := length;
    } else {
      r := cap - start;
    }
'''
AH_ALT = '''    var endpoint := if start + length < cap then start + length else cap;
    r := endpoint - start;
'''
AC_OLD = '''    result := H.Transfer(start,length,cap);
'''
AC_NEW = '''    if start <= cap {
      var delta := H.Transfer(start,length,cap);
      result := start + delta;
    } else {
      result := cap;
    }
'''
AC_ALT = '''    if cap < start {
      result := cap;
    } else {
      var amount := H.Transfer(start,length,cap);
      result := amount + start;
    }
'''
AC_UNGUARDED = '''    var delta := H.Transfer(start,length,cap);
    result := start + delta;
'''
AC_LOST = AC_NEW.replace('result := start + delta;', 'result := delta;')

MH_OLD = '''    r := K.Erase(m,key);
'''
MH_NEW = '''    r := map[key := m[key]];
'''
MH_ALT = '''    r := map x | x in m && x == key :: m[x];
'''
MC_OLD = '''    remaining := H.Transfer(m,key);
    removed := K.Entry(m,key);
'''
MC_NEW = '''    if key in m {
      removed := H.Transfer(m,key);
      remaining := K.Exclude(m,removed);
      assert removed == K.Entry(m,key);
      assert remaining.Keys == K.Erase(m,key).Keys;
      assert forall x | x in remaining :: remaining[x] == K.Erase(m,key)[x];
      assert remaining == K.Erase(m,key);
    } else {
      remaining := m;
      removed := map[];
    }
'''
MC_ALT = '''    if key !in m {
      removed := map[];
      remaining := m;
    } else {
      var patch := H.Transfer(m,key);
      var keep := m.Keys - patch.Keys;
      remaining := map x | x in keep :: m[x];
      removed := patch;
      assert remaining.Keys == K.Erase(m,key).Keys;
      assert forall x | x in remaining :: remaining[x] == K.Erase(m,key)[x];
      assert remaining == K.Erase(m,key);
    }
'''
MC_UNGUARDED = '''    removed := H.Transfer(m,key);
    remaining := K.Exclude(m,removed);
    assert remaining.Keys == K.Erase(m,key).Keys;
    assert forall x | x in remaining :: remaining[x] == K.Erase(m,key)[x];
    assert remaining == K.Erase(m,key);
'''
MC_LOST = '''    if key in m {
      removed := H.Transfer(m,key);
      remaining := removed;
    } else {
      remaining := m;
      removed := map[];
    }
'''


def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(path,value): Path(path).write_text(json.dumps(value,indent=2)+'\n')
def hashes(source): return {name:sha(text.encode()) for name,text in sorted(source.items())}


def header(module,signature,requires,ensures,imports):
    includes = ['Kernel'] + (['Helper'] if module=='Client' else [])
    text = ''.join('include "'+name+'.dfy"\n' for name in includes)
    text += 'module '+module+' {\n'
    text += ''.join('  import '+alias+' = '+target+'\n' for alias,target in imports)
    text += '  method '+signature+'\n'
    text += ''.join('    requires '+clause+'\n' for clause in requires)
    text += ''.join('    ensures '+clause+'\n' for clause in ensures)
    return text


def definition(task_id):
    if task_id=='capped_endpoint_return_migration':
        signature = 'Transfer(start: int, length: int, cap: int) returns (r: int)'
        public = 'Target(start: int, length: int, cap: int) returns (result: int)'
        old = header('Helper',signature,['0 <= length'],['r == K.Endpoint(start,length,cap)'],[('K','Kernel')])
        new = header('Helper',signature,['0 <= length','start <= cap'],
                     ['0 <= r <= length','start + r == K.Endpoint(start,length,cap)'],[('K','Kernel')])
        client = header('Client',public,['0 <= length'],['result == K.Endpoint(start,length,cap)'],[('K','Kernel'),('H','Helper')])
        return dict(task_id=task_id,family='conditional_arithmetic_development',kernel=ARITHMETIC_KERNEL,
                    helper_old=old,helper_new=new,client_header=client,
                    bodies=dict(old_h=AH_OLD,new_h=AH_NEW,alt_h=AH_ALT,bad_h='    r := length;\n',
                                old_c=AC_OLD,new_c=AC_NEW,alt_c=AC_ALT,unguarded_c=AC_UNGUARDED,lost_c=AC_LOST))
    if task_id=='extracted_entry_return_migration':
        signature = 'Transfer(m: map<int,int>, key: int) returns (r: map<int,int>)'
        public = 'Target(m: map<int,int>, key: int) returns (remaining: map<int,int>, removed: map<int,int>)'
        old = header('Helper',signature,[],['r == K.Erase(m,key)'],[('K','Kernel')])
        new = header('Helper',signature,['key in m'],['r == K.Entry(m,key)','r.Keys == {key}'],[('K','Kernel')])
        client = header('Client',public,[],['remaining == K.Erase(m,key)','removed == K.Entry(m,key)'],[('K','Kernel'),('H','Helper')])
        return dict(task_id=task_id,family='finite_maps_development',kernel=MAP_KERNEL,
                    helper_old=old,helper_new=new,client_header=client,
                    bodies=dict(old_h=MH_OLD,new_h=MH_NEW,alt_h=MH_ALT,bad_h='    r := map[key := 0];\n',
                                old_c=MC_OLD,new_c=MC_NEW,alt_c=MC_ALT,unguarded_c=MC_UNGUARDED,lost_c=MC_LOST))
    raise ValueError('Unknown migration task')


TASK_IDS = ['capped_endpoint_return_migration','extracted_entry_return_migration']
VARIANTS = {
    'reference': ('old','old_h','old_c'),
    'paired_repair': ('new','new_h','new_c'),
    'alternative': ('new','alt_h','alt_c'),
    'helper_only': ('new','new_h','old_c'),
    'caller_only': ('old','old_h','new_c'),
    'contract_only': ('new','old_h','new_c'),
    'unguarded_call': ('new','new_h','unguarded_c'),
    'lost_result_transform': ('new','new_h','lost_c'),
    'wrong_helper_implementation': ('new','bad_h','new_c'),
}


def sources(task_id,variant):
    task = definition(task_id)
    version,hbody,cbody = VARIANTS[variant]
    def method(prefix,body): return prefix+'  {\n'+body+'  }\n}\n'
    return {'Kernel.dfy':task['kernel'], 'Helper.dfy':method(task['helper_'+version],task['bodies'][hbody]),
            'Client.dfy':method(task['client_header'],task['bodies'][cbody]), 'All.dfy':'include "Client.dfy"\n'}


def body_boundary(source):
    start = source.index('  {\n')+len('  {\n')
    assert source.endswith('  }\n}\n')
    end = len(source)-len('  }\n}\n')
    prefix,suffix = source[:start],source[end:]
    return dict(start=len(prefix.encode()),end=len(source[:end].encode()),
                protected_sha256=sha((prefix+'<BODY>\n'+suffix).encode()))


def assert_construction_scope(task_id,source):
    """Offline fixture assertion, not a model guard or authorization to edit code."""
    task = definition(task_id)
    assert set(source)=={'Kernel.dfy','Helper.dfy','Client.dfy','All.dfy'}
    assert source['Kernel.dfy']==task['kernel'] and source['All.dfy']=='include "Client.dfy"\n'
    client = source['Client.dfy']
    assert client.startswith(task['client_header']+'  {\n') and client.endswith('  }\n}\n'), 'Public contract changed'
    helper = source['Helper.dfy']
    assert any(helper.startswith(task['helper_'+v]+'  {\n') for v in ('old','new')), 'Unplanned internal API contract'
    assert helper.endswith('  }\n}\n')
    for text in source.values():
        assert not re.search(r'\bassume\b|\{:\s*(?:axiom|verify|extern)\b',text)
        assert text.count('{')==text.count('}'), 'Unbalanced source braces'
        assert 'TODO' not in text and '// ' not in text


def generate(root=ROOT,design_path=None):
    root = Path(root)
    root.mkdir(parents=True,exist_ok=True)
    design = json.loads(Path(design_path or ROOT/'design.json').read_bytes())
    assert [t['task_id'] for t in design['tasks']]==TASK_IDS
    expected = {c['variant']:c for c in design['required_controls']}
    instance_design = {t['task_id']:t for t in design['tasks']}
    assert set(expected)==set(VARIANTS)
    tasks,cases = [],[]
    for task_id in TASK_IDS:
        task = definition(task_id)
        public_header = task['client_header']+'  {\n'
        tasks.append(dict(task_id=task_id,family=task['family'],development_only=True,held_out=False,
            entry='All.dfy',named_targets=TARGETS,public_target='Client.Target',internal_target='Helper.Transfer',
            public_contract_sha256=sha(public_header.encode()),public_contract_prefix=public_header,
            internal_api_versions={v:dict(header=task['helper_'+v],sha256=sha(task['helper_'+v].encode())) for v in ('old','new')},
            model_protocol_defined=False,verification_status='not_run',
            interpretation='Chosen one-sided API migration is insufficient; no mathematical necessity of multi-file repair.'))
        for variant in VARIANTS:
            source = sources(task_id,variant)
            assert_construction_scope(task_id,source)
            case_id = task_id+'-'+variant
            path = 'fixtures/'+task_id+'/'+variant
            for name,text in source.items():
                target = root/path/name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text(text)
            requirement = expected[variant]
            failure = requirement.get('failed_target')
            cases.append(dict(case_id=case_id,task_id=task_id,variant=variant,path=path,entry='All.dfy',
                expected=requirement['expected'],expected_exit=0 if failure is None else 4,
                expected_diagnostic=instance_design[task_id].get('diagnostic_overrides',{}).get(variant,requirement.get('diagnostic','none')),
                expected_local_targets={name:name!=failure for name in TARGETS},
                expected_failed_targets=[] if failure is None else [failure],
                internal_api_version=VARIANTS[variant][0],source_sha256=hashes(source),
                public_contract_sha256=sha(public_header.encode()),
                body_boundaries={n:body_boundary(source[n]) for n in ('Helper.dfy','Client.dfy')}))
    cases.sort(key=lambda c:c['expected']!='success')
    save(root/'tasks.json',tasks)
    save(root/'cases.json',cases)
    pins = {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in sorted((root/'fixtures').rglob('*.dfy'))}
    pins.update({name:sha((root/name).read_bytes()) for name in ('tasks.json','cases.json')})
    save(root/'fixture-manifest.json',pins)
    return dict(tasks=2,distinct_workspaces=len(cases),expected_success=6,expected_proof_failure=12,
                model_calls=0,verifier_invocations=0,verification_status='not_run')


if __name__=='__main__':
    print(json.dumps(generate(),sort_keys=True))
