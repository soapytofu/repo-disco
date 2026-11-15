"""Two prospective multi-helper witness repair fixtures; no verifier/model calls."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
EDITABLE = ['HelperA.dfy', 'HelperB.dfy']
DEPENDENCIES = {'HelperA.Prove': [], 'HelperB.Prove': ['HelperA.Prove'],
                'ClientA.Target': ['HelperB.Prove'], 'ClientB.Target': ['HelperB.Prove']}

INTERSECTION_KERNEL = '''module Kernel {
  export Public provides LeftFact, RightFact, LeftGap, RightGap, Valid, Decided
  export Internal reveals LeftFact, RightFact, LeftGap, RightGap, Valid, Decided
  opaque predicate LeftFact(a: int, b: int, w: int) { a <= w <= b }
  opaque predicate RightFact(c: int, d: int, w: int) { c <= w <= d }
  opaque predicate LeftGap(b: int, c: int) { b < c }
  opaque predicate RightGap(d: int, a: int) { d < a }
  opaque predicate Valid(a: int, b: int, c: int, d: int, kind: int, w: int) {
    (kind == 0 && a <= w <= b && c <= w <= d) ||
    (kind == -1 && b < c) || (kind == 1 && d < a)
  }
  opaque ghost predicate Decided(a: int, b: int, c: int, d: int) {
    exists kind: int, w: int {:trigger Valid(a,b,c,d,kind,w)} :: Valid(a,b,c,d,kind,w)
  }
}
'''
INTERSECTION_OPS = '''include "Kernel.dfy"
module Ops {
  export Membership provides K, Left, Right
  export Gaps provides K, Before, After
  import K = Kernel`Internal
  lemma Left(a: int, b: int, w: int)
    requires a <= w <= b
    ensures K.LeftFact(a,b,w)
  { reveal K.LeftFact(); }
  lemma Right(c: int, d: int, w: int)
    requires c <= w <= d
    ensures K.RightFact(c,d,w)
  { reveal K.RightFact(); }
  lemma Before(b: int, c: int)
    requires b < c
    ensures K.LeftGap(b,c)
  { reveal K.LeftGap(); }
  lemma After(d: int, a: int)
    requires d < a
    ensures K.RightGap(d,a)
  { reveal K.RightGap(); }
}
'''
INTERSECTION_API = '''include "Kernel.dfy"
module Api {
  export Proof provides K, Witness, Gap
  export Clients provides K, Choose
  export Hidden provides K, DirectWitness
  import K = Kernel`Internal
  lemma Witness(a: int, b: int, c: int, d: int, w: int)
    requires K.LeftFact(a,b,w) && K.RightFact(c,d,w)
    ensures K.Decided(a,b,c,d)
  {
    reveal K.LeftFact(); reveal K.RightFact(); reveal K.Valid();
    assert K.Valid(a,b,c,d,0,w);
    reveal K.Decided();
    assert exists tag: int, point: int {:trigger K.Valid(a,b,c,d,tag,point)} :: K.Valid(a,b,c,d,tag,point);
  }
  lemma Gap(a: int, b: int, c: int, d: int, kind: int)
    requires (kind == -1 && K.LeftGap(b,c)) || (kind == 1 && K.RightGap(d,a))
    ensures K.Decided(a,b,c,d)
  {
    reveal K.LeftGap(); reveal K.RightGap(); reveal K.Valid();
    assert K.Valid(a,b,c,d,kind,0);
    reveal K.Decided();
    assert exists tag: int, point: int {:trigger K.Valid(a,b,c,d,tag,point)} :: K.Valid(a,b,c,d,tag,point);
  }
  lemma Choose(a: int, b: int, c: int, d: int) returns (kind: int, w: int)
    requires a <= b && c <= d
    requires K.Decided(a,b,c,d)
    ensures kind == -1 || kind == 0 || kind == 1
    ensures kind == 0 ==> a <= w <= b && c <= w <= d
    ensures (kind == 0) == (a <= d && c <= b)
    ensures (kind == -1) == (b < c)
    ensures (kind == 1) == (d < a)
  {
    reveal K.Decided();
    kind, w :| K.Valid(a,b,c,d,kind,w);
    reveal K.Valid();
  }
  lemma DirectWitness(a: int, b: int, c: int, d: int, w: int)
    requires a <= w <= b && c <= w <= d
    ensures K.Decided(a,b,c,d)
  {
    reveal K.Valid(); assert K.Valid(a,b,c,d,0,w);
    reveal K.Decided();
    assert exists tag: int, point: int {:trigger K.Valid(a,b,c,d,tag,point)} :: K.Valid(a,b,c,d,tag,point);
  }
}
'''
IA = '''    var w := if a < c then c else a;
    O.Left(a,b,w);
    O.Right(c,d,w);
'''
IA_ALT = '''    if c > a {
      O.Right(c,d,c);
      O.Left(a,b,c);
    } else {
      O.Right(c,d,a);
      O.Left(a,b,a);
    }
'''
IB = '''    if b < c {
      O.Before(b,c);
      A.Gap(a,b,c,d,-1);
    } else if d < a {
      O.After(d,a);
      A.Gap(a,b,c,d,1);
    } else {
      H.Prove(a,b,c,d);
      var w := if a < c then c else a;
      A.Witness(a,b,c,d,w);
    }
'''
IB_ALT = '''    if a <= d && c <= b {
      var w := if c <= a then a else c;
      H.Prove(a,b,c,d);
      A.Witness(a,b,c,d,w);
    } else if c > b {
      O.Before(b,c);
      A.Gap(a,b,c,d,-1);
    } else {
      O.After(d,a);
      A.Gap(a,b,c,d,1);
    }
'''
IB_BAD = IB.replace('if b < c {', 'if b <= c {', 1)

SUM_KERNEL = '''module Kernel {
  export Public provides LeftFact, RightFact, SumFact, Balanced, GapFact, Valid, Feasible
  export Internal reveals LeftFact, RightFact, SumFact, Balanced, GapFact, Valid, Feasible
  opaque predicate LeftFact(a: int, b: int, u: int) { a <= u <= b }
  opaque predicate RightFact(c: int, d: int, v: int) { c <= v <= d }
  opaque predicate SumFact(s: int, u: int, v: int) { u + v == s }
  opaque predicate Balanced(a: int, b: int, c: int, d: int, s: int, u: int, v: int) {
    a <= u <= b && c <= v <= d && u + v == s
  }
  opaque predicate GapFact(g: int, u: int, v: int) { 0 < g && u + g <= v }
  opaque predicate Valid(a: int, b: int, c: int, d: int, s: int, g: int, u: int, v: int) {
    a <= u <= b && c <= v <= d && u + v == s && 0 < g && u + g <= v
  }
  opaque ghost predicate Feasible(a: int, b: int, c: int, d: int, s: int, g: int) {
    exists u: int, v: int {:trigger Valid(a,b,c,d,s,g,u,v)} :: Valid(a,b,c,d,s,g,u,v)
  }
}
'''
SUM_OPS = '''include "Kernel.dfy"
module Ops {
  export Bounds provides K, Left, Right, Sum
  export Gaps provides K, Gap
  import K = Kernel`Internal
  lemma Left(a: int, b: int, u: int)
    requires a <= u <= b
    ensures K.LeftFact(a,b,u)
  { reveal K.LeftFact(); }
  lemma Right(c: int, d: int, v: int)
    requires c <= v <= d
    ensures K.RightFact(c,d,v)
  { reveal K.RightFact(); }
  lemma Sum(s: int, u: int, v: int)
    requires u + v == s
    ensures K.SumFact(s,u,v)
  { reveal K.SumFact(); }
  lemma Gap(g: int, u: int, v: int)
    requires 0 < g && u + g <= v
    ensures K.GapFact(g,u,v)
  { reveal K.GapFact(); }
}
'''
SUM_API = '''include "Kernel.dfy"
module Api {
  export Bounds provides K, Balance
  export Proof provides K, Finish
  export Clients provides K, Choose
  export Hidden provides K, DirectFinish
  import K = Kernel`Internal
  lemma Balance(a: int, b: int, c: int, d: int, s: int, u: int, v: int)
    requires K.LeftFact(a,b,u) && K.RightFact(c,d,v) && K.SumFact(s,u,v)
    ensures K.Balanced(a,b,c,d,s,u,v)
  {
    reveal K.LeftFact(); reveal K.RightFact(); reveal K.SumFact(); reveal K.Balanced();
  }
  lemma Finish(a: int, b: int, c: int, d: int, s: int, g: int, u: int, v: int)
    requires K.Balanced(a,b,c,d,s,u,v) && K.GapFact(g,u,v)
    ensures K.Feasible(a,b,c,d,s,g)
  {
    reveal K.Balanced(); reveal K.GapFact(); reveal K.Valid();
    assert K.Valid(a,b,c,d,s,g,u,v);
    reveal K.Feasible();
    assert exists p: int, q: int {:trigger K.Valid(a,b,c,d,s,g,p,q)} :: K.Valid(a,b,c,d,s,g,p,q);
  }
  lemma Choose(a: int, b: int, c: int, d: int, s: int, g: int) returns (u: int, v: int)
    requires K.Feasible(a,b,c,d,s,g)
    ensures a <= u <= b && c <= v <= d
    ensures u + v == s && 0 < g && u + g <= v
  {
    reveal K.Feasible();
    u, v :| K.Valid(a,b,c,d,s,g,u,v);
    reveal K.Valid();
  }
  lemma DirectFinish(a: int, b: int, c: int, d: int, s: int, g: int, u: int, v: int)
    requires a <= u <= b && c <= v <= d && u + v == s && 0 < g && u + g <= v
    ensures K.Feasible(a,b,c,d,s,g)
  {
    reveal K.Valid(); assert K.Valid(a,b,c,d,s,g,u,v);
    reveal K.Feasible();
    assert exists p: int, q: int {:trigger K.Valid(a,b,c,d,s,g,p,q)} :: K.Valid(a,b,c,d,s,g,p,q);
  }
}
'''
SUM_REQUIRES = 'a <= b && c <= d && a <= s - c && s - d <= b'
GAP_REQUIRES = SUM_REQUIRES + ' && 0 < g && a + a + g <= s && (s - d) + (s - d) + g <= s'
SA = '''    var u := if a < s - d then s - d else a;
    var v := s - u;
    O.Left(a,b,u);
    O.Right(c,d,v);
    O.Sum(s,u,v);
    A.Balance(a,b,c,d,s,u,v);
'''
SA_ALT = '''    if s - d <= a {
      O.Sum(s,a,s-a);
      O.Right(c,d,s-a);
      O.Left(a,b,a);
      A.Balance(a,b,c,d,s,a,s-a);
    } else {
      O.Sum(s,s-d,d);
      O.Right(c,d,d);
      O.Left(a,b,s-d);
      A.Balance(a,b,c,d,s,s-d,d);
    }
'''
SB = '''    H.Prove(a,b,c,d,s);
    var u := if a < s - d then s - d else a;
    var v := s - u;
    if a < s - d {
      assert u == s - d;
      assert u + u + g <= s;
    } else {
      assert u == a;
      assert u + u + g <= s;
    }
    assert u + g <= v;
    O.Gap(g,u,v);
    A.Finish(a,b,c,d,s,g,u,v);
'''
SB_ALT = '''    H.Prove(a,b,c,d,s);
    if s - d <= a {
      var u := a;
      var v := s - a;
      O.Gap(g,u,v);
      A.Finish(a,b,c,d,s,g,u,v);
    } else {
      var u := s - d;
      var v := d;
      O.Gap(g,u,v);
      A.Finish(a,b,c,d,s,g,u,v);
    }
'''
SA_BAD = SA.replace('if a < s - d then s - d else a', 'a', 1)


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def hashes(files):
    return {name: sha(source) for name, source in sorted(files.items())}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def body_boundary(source):
    start = source.index('  {\n', source.index('lemma {:induction false} Prove')) + len('  {\n')
    end = source.rindex('  }\n}\n')
    return dict(start=len(source[:start].encode()), end=len(source[:end].encode()),
                protected_sha256=sha(source[:start] + '<EDITABLE_BODY>\n' + source[end:]))


def helper(name, params, requires, ensures, imports, includes, body):
    return (''.join('include "' + n + '.dfy"\n' for n in includes) + 'module ' + name + ' {\n'
            + ''.join('  import ' + n + ' = ' + target + '\n' for n, target in imports)
            + '  lemma {:induction false} Prove(' + ', '.join(n + ': int' for n in params) + ')\n'
            + '    requires ' + requires + '\n'
            + ''.join('    ensures ' + clause + '\n' for clause in ensures)
            + '  {\n' + body + '  }\n}\n')


def intersection_clients():
    result = {}
    for name, shifted in [('ClientA', False), ('ClientB', True)]:
        params = 'a: int, b: int, c: int, d: int' + (', shift: int' if shifted else '')
        a, b, c, d = ('c+shift', 'd+shift', 'a+shift', 'b+shift') if shifted else ('a', 'b', 'c', 'd')
        args = ','.join((a, b, c, d))
        result[name + '.dfy'] = ('include "HelperB.dfy"\ninclude "Api.dfy"\nmodule ' + name + ' {\n'
            + '  import H = HelperB\n  import A = Api`Clients\n'
            + '  lemma Target(' + params + ') returns (kind: int, w: int)\n'
            + '    requires a <= b && c <= d\n'
            + '    ensures kind == -1 || kind == 0 || kind == 1\n'
            + '    ensures kind == 0 ==> ' + a + ' <= w <= ' + b + ' && ' + c + ' <= w <= ' + d + '\n'
            + '    ensures (kind == 0) == (' + a + ' <= ' + d + ' && ' + c + ' <= ' + b + ')\n'
            + '    ensures (kind == -1) == (' + b + ' < ' + c + ')\n'
            + '    ensures (kind == 1) == (' + d + ' < ' + a + ')\n'
            + '  {\n    H.Prove(' + args + ');\n    kind, w := A.Choose(' + args + ');\n  }\n}\n')
    return result


def sum_clients():
    result = {}
    for name, shifted in [('ClientA', False), ('ClientB', True)]:
        params = 'a: int, b: int, c: int, d: int, s: int, g: int' + (', shift: int' if shifted else '')
        a, b, c, d, s = ('a+shift', 'b+shift', 'c+shift', 'd+shift', 's+shift+shift') if shifted else ('a', 'b', 'c', 'd', 's')
        args = ','.join((a, b, c, d, s, 'g'))
        result[name + '.dfy'] = ('include "HelperB.dfy"\ninclude "Api.dfy"\nmodule ' + name + ' {\n'
            + '  import H = HelperB\n  import A = Api`Clients\n'
            + '  lemma Target(' + params + ') returns (u: int, v: int)\n'
            + '    requires ' + GAP_REQUIRES + '\n'
            + '    ensures ' + a + ' <= u <= ' + b + ' && ' + c + ' <= v <= ' + d + '\n'
            + '    ensures u + v == ' + s + ' && 0 < g && u + g <= v\n'
            + '  {\n    H.Prove(' + args + ');\n    u, v := A.Choose(' + args + ');\n  }\n}\n')
    return result


def rules(variables, calls, pure):
    return dict(variables=variables, parameter_types={n: 'int' for n in variables}, calls=calls, pure=pure,
                call_types={name: ['int'] * arity for name, arity in calls.items()},
                pure_types={name: dict(arguments=['int'] * arity, result='bool') for name, arity in pure.items()})


def definitions():
    intersection = dict(instance='intersection_or_separation', lineage='D3-M1', fault_target='HelperB.Prove',
        params={'HelperA.dfy': ['a', 'b', 'c', 'd'], 'HelperB.dfy': ['a', 'b', 'c', 'd']},
        file_rules={
            'HelperA.dfy': rules(['a', 'b', 'c', 'd'], {'O.Left': 3, 'O.Right': 3}, {'K.LeftFact': 3, 'K.RightFact': 3}),
            'HelperB.dfy': rules(['a', 'b', 'c', 'd'], {'H.Prove': 4, 'O.Before': 2, 'O.After': 2, 'A.Witness': 5, 'A.Gap': 5},
                                {'K.LeftFact': 3, 'K.RightFact': 3, 'K.LeftGap': 2, 'K.RightGap': 2, 'K.Valid': 6, 'K.Decided': 4})},
        variants={
            'reference': (IA, IB, [], 'none'), 'alternative': (IA_ALT, IB_ALT, [], 'none'),
            'faulty': (IA, IB_BAD, ['HelperB.Prove'], 'precondition'), 'empty': ('', '', ['HelperA.Prove', 'HelperB.Prove'], 'postcondition'),
            'only_a_repair': (IA_ALT, IB_BAD, ['HelperB.Prove'], 'precondition'),
            'only_b_repair': (IA, IB_ALT, [], 'none'),
            'wrong_witness_a': (IA.replace('if a < c then c else a', 'a'), IB, ['HelperA.Prove'], 'precondition'),
            'missing_right_a': (IA.replace('    O.Right(c,d,w);\n', ''), IB, ['HelperA.Prove'], 'postcondition'),
            'wrong_orientation_b': (IA, IB.replace('A.Gap(a,b,c,d,-1);', 'A.Gap(a,b,c,d,1);', 1), ['HelperB.Prove'], 'precondition'),
            'missing_overlap_call_b': (IA, IB.replace('      H.Prove(a,b,c,d);\n', ''), ['HelperB.Prove'], 'precondition'),
            'missing_gap_fact_b': (IA, IB.replace('      O.Before(b,c);\n', '').replace('      O.After(d,a);\n', ''), ['HelperB.Prove'], 'precondition'),
            'hidden_shortcut_b': (IA, IB.replace('A.Witness(a,b,c,d,w);', 'A.DirectWitness(a,b,c,d,w);'), None, 'missing export member'),
        })
    conserved = dict(instance='conserved_sum_gap', lineage='D3-new-conserved-sum-gap', fault_target='HelperA.Prove',
        params={'HelperA.dfy': ['a', 'b', 'c', 'd', 's'], 'HelperB.dfy': ['a', 'b', 'c', 'd', 's', 'g']},
        file_rules={
            'HelperA.dfy': rules(['a', 'b', 'c', 'd', 's'], {'O.Left': 3, 'O.Right': 3, 'O.Sum': 3, 'A.Balance': 7},
                                {'K.LeftFact': 3, 'K.RightFact': 3, 'K.SumFact': 3, 'K.Balanced': 7}),
            'HelperB.dfy': rules(['a', 'b', 'c', 'd', 's', 'g'], {'H.Prove': 5, 'O.Gap': 3, 'A.Finish': 8},
                                {'K.Balanced': 7, 'K.GapFact': 3, 'K.Valid': 8, 'K.Feasible': 6})},
        variants={
            'reference': (SA, SB, [], 'none'), 'alternative': (SA_ALT, SB_ALT, [], 'none'),
            'faulty': (SA_BAD, SB, ['HelperA.Prove'], 'precondition'), 'empty': ('', '', ['HelperA.Prove', 'HelperB.Prove'], 'postcondition'),
            'only_a_repair': (SA_ALT, SB, [], 'none'),
            'only_b_repair': (SA_BAD, SB_ALT, ['HelperA.Prove'], 'precondition'),
            'lost_sum_a': (SA.replace('var v := s - u;', 'var v := s + u;'), SB, ['HelperA.Prove'], 'precondition'),
            'missing_balance_a': (SA.replace('    A.Balance(a,b,c,d,s,u,v);\n', ''), SB, ['HelperA.Prove'], 'postcondition'),
            'reversed_gap_b': (SA, SB.replace('O.Gap(g,u,v);', 'O.Gap(g,v,u);'), ['HelperB.Prove'], 'precondition'),
            'missing_parent_b': (SA, SB.replace('    H.Prove(a,b,c,d,s);\n', ''), ['HelperB.Prove'], 'precondition'),
            'missing_gap_fact_b': (SA, SB.replace('    O.Gap(g,u,v);\n', ''), ['HelperB.Prove'], 'precondition'),
            'hidden_shortcut_b': (SA, SB.replace('A.Finish(a,b,c,d,s,g,u,v);', 'A.DirectFinish(a,b,c,d,s,g,u,v);'), None, 'missing export member'),
        })
    return [intersection, conserved]


def sources(definition, variant):
    a_body, b_body, _, _ = definition['variants'][variant]
    if definition['instance'] == 'intersection_or_separation':
        witness = '(if a < c then c else a)'
        a = helper('HelperA', definition['params']['HelperA.dfy'], 'a <= b && c <= d && a <= d && c <= b',
                   ['K.LeftFact(a,b,' + witness + ')', 'K.RightFact(c,d,' + witness + ')'],
                   [('K', 'Kernel`Public'), ('O', 'Ops`Membership')], ['Kernel', 'Ops'], a_body)
        b = helper('HelperB', definition['params']['HelperB.dfy'], 'a <= b && c <= d', ['K.Decided(a,b,c,d)'],
                   [('K', 'Kernel`Public'), ('O', 'Ops`Gaps'), ('A', 'Api`Proof'), ('H', 'HelperA')],
                   ['Kernel', 'Ops', 'Api', 'HelperA'], b_body)
        result = {'Kernel.dfy': INTERSECTION_KERNEL, 'Ops.dfy': INTERSECTION_OPS, 'Api.dfy': INTERSECTION_API, **intersection_clients()}
    else:
        u = '(if a < s - d then s - d else a)'
        a = helper('HelperA', definition['params']['HelperA.dfy'], SUM_REQUIRES,
                   ['K.Balanced(a,b,c,d,s,' + u + ',s-' + u + ')'],
                   [('K', 'Kernel`Public'), ('O', 'Ops`Bounds'), ('A', 'Api`Bounds')], ['Kernel', 'Ops', 'Api'], a_body)
        b = helper('HelperB', definition['params']['HelperB.dfy'], GAP_REQUIRES, ['K.Feasible(a,b,c,d,s,g)'],
                   [('K', 'Kernel`Public'), ('O', 'Ops`Gaps'), ('A', 'Api`Proof'), ('H', 'HelperA')],
                   ['Kernel', 'Ops', 'Api', 'HelperA'], b_body)
        result = {'Kernel.dfy': SUM_KERNEL, 'Ops.dfy': SUM_OPS, 'Api.dfy': SUM_API, **sum_clients()}
    return {**result, 'HelperA.dfy': a, 'HelperB.dfy': b, 'All.dfy': 'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}


def semantic_cases():
    return {
        'intersection_or_separation': {
            'touching_is_overlap': dict(a=0, b=2, c=2, d=5, correct_kind=0, correct_w=2, invalid_claim='b<c'),
            'bad_left_endpoint': dict(a=0, b=4, c=2, d=5, bad_w=0, invalid_claim='c<=w'),
            'reversed_orientation': dict(a=0, b=1, c=3, d=4, correct_kind=-1, bad_kind=1, invalid_claim='d<a')},
        'conserved_sum_gap': {
            'bad_endpoint': dict(a=0, b=4, c=0, d=3, s=5, g=1, correct_u=2, correct_v=3, bad_u=0, bad_v=5, invalid_claim='v<=d'),
            'lost_sum': dict(a=0, b=4, c=0, d=3, s=5, g=1, bad_u=2, bad_v=7, invalid_claim='u+v==s'),
            'reversed_gap': dict(a=0, b=4, c=0, d=3, s=5, g=1, u=2, v=3, invalid_claim='v+g<=u'),
            'feasibility': {
                'construction': 'L=max(a,s-d); u=L; v=s-L',
                'balanced_bounds': 'L<=b from a<=b and s-d<=b; L<=s-c from a<=s-c and c<=d. The lower bound L>=s-d gives v<=d.',
                'gap': 'a+a+g<=s and (s-d)+(s-d)+g<=s imply L+L+g<=s; hence L+g<=s-L.',
                'necessity': 'Any valid u is at least both a and s-d, at most b and s-c, and satisfies u+u+g<=s; therefore every stated inequality is necessary as well as sufficient.',
                'translation': 'Translate both intervals and returned witnesses by shift; replace s with s+shift+shift and retain g.'}}}


def generate(root=ROOT):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    tasks, cases = [], []
    for definition in definitions():
        instance = definition['instance']
        tid = instance + '-pipeline'
        template = sources(definition, 'empty')
        task = dict(task_id=tid, semantic_instance=instance, family='constraint_witness', lineage_id=definition['lineage'],
                    sharing='pipeline', depth='two_helper_pipeline', entry='All.dfy', editable_files=EDITABLE,
                    source_sha256=hashes(template), body_boundaries={n: body_boundary(template[n]) for n in EDITABLE},
                    file_rules=definition['file_rules'], file_parameters=definition['params'], target_dependencies=DEPENDENCIES,
                    primary_case_id=tid+'-faulty', development_only=True, adaptive_development=True, held_out=False,
                    guard_registry_status='pending separate per-file guard review', verification_status='not_run',
                    client_interface='Immutable ghost lemma returns a certified witness through a protected choice rule; not executable search.',
                    no_sharing_factor=True, minimum_proof_depth=None)
        tasks.append(task)
        for variant, (_, _, failed, diagnostic) in definition['variants'].items():
            workspace = sources(definition, variant)
            path = 'fixtures/' + tid + '/' + variant
            for name, content in workspace.items():
                target = root / path / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            expected = 'resolution_failure' if failed is None else 'proof_failure' if failed else 'success'
            local = None if failed is None else {n: n not in failed for n in DEPENDENCIES}
            closed = None if local is None else {
                'HelperA.Prove': local['HelperA.Prove'],
                'HelperB.Prove': local['HelperA.Prove'] and local['HelperB.Prove'],
                'ClientA.Target': local['HelperA.Prove'] and local['HelperB.Prove'],
                'ClientB.Target': local['HelperA.Prove'] and local['HelperB.Prove']}
            cases.append(dict(case_id=tid+'-'+variant, task_id=tid, variant=variant, path=path, entry='All.dfy',
                              expected=expected, expected_exit=0 if expected=='success' else 2 if failed is None else 4,
                              expected_diagnostic=diagnostic, expected_failed_targets=failed,
                              expected_local_targets=local, expected_dependency_closed_targets=closed,
                              source_sha256=hashes(workspace), body_boundaries={n: body_boundary(workspace[n]) for n in EDITABLE}))
        for name, content in template.items():
            target = root / 'templates' / tid / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
    # Check all positive workspaces before negative controls; preserve stable order within groups.
    cases.sort(key=lambda case: case['expected'] != 'success')
    save(root/'tasks.json', tasks)
    save(root/'cases.json', cases)
    save(root/'semantic-cases.json', semantic_cases())
    pins = {p.relative_to(root).as_posix(): sha(p.read_bytes()) for folder in ('fixtures', 'templates')
            for p in sorted((root/folder).rglob('*.dfy'))}
    for name in ('tasks.json', 'cases.json', 'semantic-cases.json'):
        pins[name] = sha((root/name).read_bytes())
    save(root/'fixture-manifest.json', pins)
    return dict(tasks=len(tasks), checks=len(cases), expected_success=sum(c['expected']=='success' for c in cases),
                expected_proof_failure=sum(c['expected']=='proof_failure' for c in cases),
                expected_resolution_failure=sum(c['expected']=='resolution_failure' for c in cases),
                verification_status='not_run', model_calls=0)


if __name__ == '__main__':
    print(json.dumps(generate(), sort_keys=True))
