"""Construct restriction/right-biased override repair fixtures. No live execution."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
INSTANCE = 'overlap_override_restrict'
SIGNATURE = 'm: map<int,int>, n: map<int,int>, keep: set<int>'
ARGS = 'm,n,keep'
GOAL = 'K.Restrict(K.Override(m,n),keep) == K.Override(K.Restrict(m,keep),K.Restrict(n,keep))'

KERNEL = '''module Kernel {
  export Public provides Override, Restrict
  export Internal reveals Override, Restrict
  opaque function Override(m: map<int,int>, n: map<int,int>): map<int,int> {
    map q | q in m.Keys + n.Keys :: if q in n then n[q] else m[q]
  }
  opaque function Restrict(m: map<int,int>, keep: set<int>): map<int,int> {
    map q | q in m && q in keep :: m[q]
  }
}
'''

DOMAINS = '''include "Kernel.dfy"
module Domains {
  export Public provides K, OverrideKeys, RestrictKeys
  import K = Kernel`Internal
  lemma OverrideKeys(m: map<int,int>, n: map<int,int>)
    ensures K.Override(m,n).Keys == m.Keys + n.Keys
  { reveal K.Override(); }
  lemma RestrictKeys(m: map<int,int>, keep: set<int>)
    ensures K.Restrict(m,keep).Keys == m.Keys * keep
  { reveal K.Restrict(); }
}
'''

VALUES = '''include "Kernel.dfy"
module Values {
  export Public provides K, OverrideAt, RestrictAt
  import K = Kernel`Internal
  lemma OverrideAt(m: map<int,int>, n: map<int,int>, q: int)
    requires q in m || q in n
    ensures q in K.Override(m,n)
    ensures K.Override(m,n)[q] == (if q in n then n[q] else m[q])
  { reveal K.Override(); }
  lemma RestrictAt(m: map<int,int>, keep: set<int>, q: int)
    requires q in m && q in keep
    ensures q in K.Restrict(m,keep)
    ensures K.Restrict(m,keep)[q] == m[q]
  { reveal K.Restrict(); }
}
'''

API = '''include "Kernel.dfy"
module Api {
  export Public provides K, Equal
  export Hidden provides K, ObserveOverride
  import K = Kernel`Internal
  lemma Equal(left: map<int,int>, right: map<int,int>)
    requires left.Keys == right.Keys
    requires forall q :: q in left ==> q in right && left[q] == right[q]
    ensures left == right
  { }
  lemma ObserveOverride(m: map<int,int>, n: map<int,int>)
    ensures K.Override(m,n).Keys == m.Keys + n.Keys
    ensures forall q :: q in K.Override(m,n) ==>
      K.Override(m,n)[q] == (if q in n then n[q] else m[q])
  { reveal K.Override(); }
}
'''

PREFIX = '''    var merged := K.Override(m,n);
    var left := K.Restrict(merged,keep);
    var rm := K.Restrict(m,keep);
    var rn := K.Restrict(n,keep);
    var right := K.Override(rm,rn);
    D.OverrideKeys(m,n);
    D.RestrictKeys(merged,keep);
    D.RestrictKeys(m,keep);
    D.RestrictKeys(n,keep);
    D.OverrideKeys(rm,rn);
    assert left.Keys == right.Keys;
'''
REFERENCE = PREFIX + '''    forall q | q in left ensures q in right && left[q] == right[q] {
      V.RestrictAt(merged,keep,q);
      V.OverrideAt(m,n,q);
      if q in n {
        V.RestrictAt(n,keep,q);
      } else {
        V.RestrictAt(m,keep,q);
      }
      V.OverrideAt(rm,rn,q);
    }
    A.Equal(left,right);
'''
ALTERNATIVE = PREFIX + '''    forall q | q in left ensures q in right && left[q] == right[q] {
      V.OverrideAt(rm,rn,q);
      if q in rn {
        V.RestrictAt(n,keep,q);
      } else {
        V.RestrictAt(m,keep,q);
      }
      V.OverrideAt(m,n,q);
      V.RestrictAt(merged,keep,q);
    }
    A.Equal(left,right);
'''
FAULTY = PREFIX + '''    forall q | q in left ensures q in right && left[q] == right[q] {
      V.RestrictAt(merged,keep,q);
      V.OverrideAt(m,n,q);
      if q in m {
        V.RestrictAt(m,keep,q);
        assert merged[q] == m[q];
      } else {
        V.RestrictAt(n,keep,q);
      }
      V.OverrideAt(rm,rn,q);
    }
    A.Equal(left,right);
'''
VARIANTS = {
    'reference': REFERENCE,
    'alternative': ALTERNATIVE,
    'empty': '',
    'faulty': FAULTY,
    'missing_inner_right': REFERENCE.replace('        V.RestrictAt(n,keep,q);\n', ''),
    'missing_inner_left': REFERENCE.replace('        V.RestrictAt(m,keep,q);\n', ''),
    'missing_outer': REFERENCE.replace('      V.RestrictAt(merged,keep,q);\n', ''),
    'collision_assumption': REFERENCE.replace('    assert left.Keys == right.Keys;\n',
        '    assert forall q :: q in m ==> q !in n;\n    assert left.Keys == right.Keys;\n'),
    'missing_keys': REFERENCE.replace('    D.OverrideKeys(m,n);\n', ''),
    'hidden_shortcut': REFERENCE.replace('    D.OverrideKeys(m,n);\n', '    A.ObserveOverride(m,n);\n'),
}


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def hashes(files):
    return {name: sha(source) for name, source in sorted(files.items())}


def helper(name, body, forward=False):
    header = 'include "Kernel.dfy"\ninclude "Domains.dfy"\ninclude "Values.dfy"\ninclude "Api.dfy"\n'
    if forward:
        header += 'include "HelperA.dfy"\n'
    imports = ('  import K = Kernel`Public\n  import D = Domains`Public\n'
               '  import V = Values`Public\n  import A = Api`Public\n')
    if forward:
        imports += '  import H = HelperA\n'
        body = '    H.Prove(' + ARGS + ');\n'
    return (header + 'module ' + name + ' {\n' + imports
            + '  lemma {:induction false} Prove(' + SIGNATURE + ')\n'
            + '    ensures ' + GOAL + '\n  {\n' + body + '  }\n}\n')


def clients():
    files = {}
    for name, helper_name in [('ClientA', 'HelperA'), ('ClientB', 'HelperB')]:
        args = ARGS if name == 'ClientA' else 'n,m,keep'
        goal = GOAL if name == 'ClientA' else GOAL.replace('(m,n)', '(n,m)').replace('Restrict(m,keep),K.Restrict(n,keep)', 'Restrict(n,keep),K.Restrict(m,keep)')
        files[name + '.dfy'] = ('include "' + helper_name + '.dfy"\nmodule ' + name + ' {\n'
            + '  import K = Kernel`Public\n  import H = ' + helper_name + '\n'
            + '  lemma {:induction false} Target(' + SIGNATURE + ')\n'
            + '    ensures ' + goal + '\n  { H.Prove(' + args + '); }\n}\n')
    return files


def sources(sharing, variant):
    assert sharing in ('shared', 'separate')
    body = VARIANTS[variant]
    return {'Kernel.dfy': KERNEL, 'Domains.dfy': DOMAINS, 'Values.dfy': VALUES, 'Api.dfy': API,
            'HelperA.dfy': helper('HelperA', body),
            'HelperB.dfy': helper('HelperB', body, forward=sharing == 'shared'),
            **clients(), 'All.dfy': 'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}


def body_boundary(source):
    marker = '  {\n'
    start = source.index(marker, source.index('lemma {:induction false} Prove')) + len(marker)
    end = source.rindex('  }\n}\n')
    return {'start': len(source[:start].encode()), 'end': len(source[:end].encode()),
            'protected_sha256': sha(source[:start] + '<EDITABLE_BODY>\n' + source[end:])}


def generate(root):
    root = Path(root)
    tasks, cases = [], []
    for sharing in ('shared', 'separate'):
        task_id = INSTANCE + '-' + sharing
        template = sources(sharing, 'empty')
        editable = ['HelperA.dfy'] + (['HelperB.dfy'] if sharing == 'separate' else [])
        tasks.append({'task_id': task_id, 'semantic_instance': INSTANCE, 'family': 'finite_map',
            'plan_id': 'D4-new-overlap-override', 'development_only': True, 'held_out': False,
            'ancestor_group': 'finite_map_update_restriction_development', 'sharing': sharing,
            'depth': 'fixed_interface', 'entry': 'All.dfy', 'editable_files': editable,
            'source_sha256': hashes(template), 'body_boundaries': {n: body_boundary(template[n]) for n in editable},
            'requires': None, 'goal': GOAL, 'repair_seed': 'faulty',
            'failure_type': 'wrong left-map priority on overlapping keys',
            'counterexample': {'m': {'0': 1}, 'n': {'0': 2}, 'keep': [0],
                'merged_value_at_0': 2, 'faulty_asserted_value_at_0': 1},
            'reference_path': 'union/intersection domain facts -> input-specific pointwise values -> generic extensionality',
            'reference_depth_not_minimal': True, 'guard_registry_status': 'pending integration',
            'verification_status': 'not_run'})
        for variant in VARIANTS:
            files = sources(sharing, variant)
            rel = 'fixtures/' + task_id + '/' + variant
            folder = root / rel
            folder.mkdir(parents=True, exist_ok=True)
            for name, source in files.items():
                (folder / name).write_text(source)
            expected = ('success' if variant in ('reference', 'alternative') else
                        'resolution_failure' if variant == 'hidden_shortcut' else 'proof_failure')
            cases.append({'case_id': task_id + '-' + variant, 'task_id': task_id, 'variant': variant,
                'path': rel, 'entry': 'All.dfy', 'expected': expected,
                'expected_exit': 0 if expected == 'success' else 2 if expected == 'resolution_failure' else 4,
                'expected_diagnostic': ('none' if expected == 'success' else 'missing export member' if expected == 'resolution_failure'
                    else 'assertion' if variant in ('faulty', 'collision_assumption', 'missing_keys') else 'postcondition'),
                'expected_warnings': 0 if expected == 'success' else None,
                'source_sha256': hashes(files),
                'body_boundaries': {n: body_boundary(files[n]) for n in editable}})
        folder = root / 'templates' / task_id
        folder.mkdir(parents=True, exist_ok=True)
        for name, source in template.items():
            (folder / name).write_text(source)
    for name, value in [('tasks.json', tasks), ('cases.json', cases)]:
        (root / name).write_text(json.dumps(value, indent=2) + '\n')
    inventory = {str(p.relative_to(root)): sha(p.read_bytes())
                 for top in ('fixtures', 'templates') for p in sorted((root / top).rglob('*.dfy'))}
    (root / 'manifest.json').write_text(json.dumps({'schema': 'repair-task-fixtures-v1',
        'verification_status': 'not_run', 'source_files': inventory,
        'generator_sha256': sha(Path(__file__).read_bytes()),
        'tasks_sha256': sha((root / 'tasks.json').read_bytes()),
        'cases_sha256': sha((root / 'cases.json').read_bytes())}, indent=2) + '\n')
    return {'tasks': len(tasks), 'checks': len(cases), 'source_files': len(inventory),
            'expected_success': sum(c['expected'] == 'success' for c in cases),
            'expected_proof_failure': sum(c['expected'] == 'proof_failure' for c in cases),
            'expected_resolution_failure': sum(c['expected'] == 'resolution_failure' for c in cases),
            'verification_status': 'not_run', 'model_calls': 0}


if __name__ == '__main__':
    print(json.dumps(generate(ROOT), sort_keys=True))
