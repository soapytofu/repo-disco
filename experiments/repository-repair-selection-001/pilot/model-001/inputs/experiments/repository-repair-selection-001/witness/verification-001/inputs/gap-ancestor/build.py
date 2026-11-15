"""Construct exact-gap interval witness repair fixtures. No verifier/model code."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
INSTANCE = "exact_gap_pair"
SIGNATURE = "a: int, b: int, c: int, d: int, gap: int"
ARGS = "a,b,c,d,gap"
REQUIRES = "0 < gap && a <= b && c <= d && a + gap <= d && c <= b + gap"
GOAL = "K.Feasible(a,b,c,d,gap)"

KERNEL = '''module Kernel {
  export Public provides Left, Right, Offset, Feasible
  export Internal reveals Left, Right, Offset, Candidate, Feasible
  opaque predicate Left(a: int, b: int, u: int) { a <= u <= b }
  opaque predicate Right(c: int, d: int, v: int) { c <= v <= d }
  opaque predicate Offset(gap: int, u: int, v: int) { 0 < gap && v == u + gap }
  opaque predicate Candidate(a: int, b: int, c: int, d: int, gap: int, u: int, v: int) {
    a <= u <= b && c <= v <= d && 0 < gap && v == u + gap
  }
  opaque ghost predicate Feasible(a: int, b: int, c: int, d: int, gap: int) {
    exists u: int, v: int {:trigger Candidate(a,b,c,d,gap,u,v)} :: Candidate(a,b,c,d,gap,u,v)
  }
}
'''

OPS = '''include "Kernel.dfy"
module Ops {
  export Public provides K, Left, Right, Offset
  export Hidden provides K, HiddenBounds
  import K = Kernel`Internal
  lemma Left(a: int, b: int, u: int)
    requires a <= u <= b
    ensures K.Left(a,b,u)
  { reveal K.Left(); }
  lemma Right(c: int, d: int, v: int)
    requires c <= v <= d
    ensures K.Right(c,d,v)
  { reveal K.Right(); }
  lemma Offset(gap: int, u: int, v: int)
    requires 0 < gap && v == u + gap
    ensures K.Offset(gap,u,v)
  { reveal K.Offset(); }
  lemma HiddenBounds(a: int, b: int, u: int)
    requires a <= u <= b
    ensures K.Left(a,b,u)
  { Left(a,b,u); }
}
'''

API = '''include "Kernel.dfy"
module Api {
  export Public provides K, Finish
  import K = Kernel`Internal
  lemma Finish(a: int, b: int, c: int, d: int, gap: int, u: int, v: int)
    requires K.Left(a,b,u) && K.Right(c,d,v) && K.Offset(gap,u,v)
    ensures K.Feasible(a,b,c,d,gap)
  {
    reveal K.Left(); reveal K.Right(); reveal K.Offset(); reveal K.Candidate();
    assert K.Candidate(a,b,c,d,gap,u,v);
    reveal K.Feasible();
    assert exists p: int, q: int {:trigger K.Candidate(a,b,c,d,gap,p,q)} :: K.Candidate(a,b,c,d,gap,p,q);
  }
}
'''

REFERENCE = '''    var u := if a + gap < c then c - gap else a;
    var v := u + gap;
    O.Left(a,b,u);
    O.Right(c,d,v);
    O.Offset(gap,u,v);
    A.Finish(a,b,c,d,gap,u,v);
'''
ALTERNATIVE = '''    var v := if b + gap <= d then b + gap else d;
    var u := v - gap;
    O.Offset(gap,u,v);
    O.Right(c,d,v);
    O.Left(a,b,u);
    A.Finish(a,b,c,d,gap,u,v);
'''
VARIANTS = {
    "reference": REFERENCE,
    "alternative": ALTERNATIVE,
    "empty": "",
    "faulty": REFERENCE.replace("if a + gap < c then c - gap else a", "a"),
    "upper_endpoint": REFERENCE.replace("if a + gap < c then c - gap else a", "b"),
    "short_gap": REFERENCE.replace("var v := u + gap;", "var v := u + gap - 1;"),
    "missing_left": REFERENCE.replace("    O.Left(a,b,u);\n", ""),
    "missing_right": REFERENCE.replace("    O.Right(c,d,v);\n", ""),
    "missing_offset": REFERENCE.replace("    O.Offset(gap,u,v);\n", ""),
    "hidden_shortcut": REFERENCE.replace("O.Left(a,b,u);", "O.HiddenBounds(a,b,u);"),
}


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def hashes(files):
    return {name: sha(source) for name, source in sorted(files.items())}


def helper(name, body, forward=False):
    header = 'include "Kernel.dfy"\ninclude "Ops.dfy"\ninclude "Api.dfy"\n'
    if forward:
        header += 'include "HelperA.dfy"\n'
    imports = '  import K = Kernel`Public\n  import O = Ops`Public\n  import A = Api`Public\n'
    if forward:
        imports += '  import H = HelperA\n'
        body = '    H.Prove(' + ARGS + ');\n'
    return (header + 'module ' + name + ' {\n' + imports
            + '  lemma {:induction false} Prove(' + SIGNATURE + ')\n'
            + '    requires ' + REQUIRES + '\n    ensures ' + GOAL + '\n'
            + '  {\n' + body + '  }\n}\n')


def clients():
    files = {}
    for name, helper_name in [('ClientA', 'HelperA'), ('ClientB', 'HelperB')]:
        args = ARGS if name == 'ClientA' else 'a+shift,b+shift,c+shift,d+shift,gap'
        signature = SIGNATURE if name == 'ClientA' else SIGNATURE + ', shift: int'
        files[name + '.dfy'] = ('include "' + helper_name + '.dfy"\nmodule ' + name + ' {\n'
            + '  import K = Kernel`Public\n  import H = ' + helper_name + '\n'
            + '  lemma {:induction false} Target(' + signature + ')\n'
            + '    requires ' + REQUIRES + '\n    ensures K.Feasible(' + args + ')\n'
            + '  { H.Prove(' + args + '); }\n}\n')
    return files


def sources(sharing, variant):
    assert sharing in ('shared', 'separate')
    body = VARIANTS[variant]
    return {'Kernel.dfy': KERNEL, 'Ops.dfy': OPS, 'Api.dfy': API,
            'HelperA.dfy': helper('HelperA', body),
            'HelperB.dfy': helper('HelperB', body, forward=sharing == 'shared'),
            **clients(), 'All.dfy': 'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}


def body_boundary(source):
    """The generator owns this unique lemma body; offsets are UTF-8 byte offsets."""
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
        tasks.append({'task_id': task_id, 'semantic_instance': INSTANCE, 'family': 'constraint_witness',
            'plan_id': 'D3-new-exact-gap', 'development_only': True, 'held_out': False,
            'ancestor_group': 'integer_interval_witness_development', 'sharing': sharing,
            'depth': 'fixed_interface', 'entry': 'All.dfy', 'editable_files': editable,
            'source_sha256': hashes(template), 'body_boundaries': {n: body_boundary(template[n]) for n in editable},
            'requires': REQUIRES, 'goal': GOAL, 'repair_seed': 'faulty',
            'failure_type': 'always choosing the first lower endpoint violates second lower bound',
            'feasibility_derivation': {
                'equivalent_intersection': '[a,b] intersect [c-gap,d-gap] is nonempty and gap>0',
                'necessary': ['u<=b and c<=u+gap imply c<=b+gap',
                              'a<=u and u+gap<=d imply a+gap<=d',
                              'interval membership implies a<=b and c<=d'],
                'sufficient': 'u=max(a,c-gap), v=u+gap; the four bounds imply u<=min(b,d-gap)',
                'alternative': 'u=min(b,d-gap), v=u+gap; equivalently v=min(b+gap,d)'},
            'counterexamples': {
                'faulty': {'a': 0, 'b': 5, 'c': 4, 'd': 8, 'gap': 2, 'u': 0, 'v': 2, 'violation': 'v<c'},
                'upper_endpoint': {'a': 0, 'b': 5, 'c': 1, 'd': 4, 'gap': 2, 'u': 5, 'v': 7, 'violation': 'v>d'},
                'short_gap': {'a': 0, 'b': 5, 'c': 1, 'd': 4, 'gap': 2, 'u': 0, 'v': 1, 'violation': 'v!=u+gap'}},
            'reference_path': 'arithmetic choice -> three independent opaque certificates -> existential packaging',
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
                    else 'postcondition' if variant == 'empty' else 'precondition'),
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
