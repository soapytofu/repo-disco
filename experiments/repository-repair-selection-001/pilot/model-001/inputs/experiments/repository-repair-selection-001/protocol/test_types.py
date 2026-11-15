"""Offline tests of the prospective per-file grammar/signature boundary."""
from pathlib import Path
import hashlib
import unittest
import body_guard as guard


def rules(variables, calls=None, pure=None):
    calls, pure = calls or {}, pure or {}
    return dict(variables=list(variables), parameter_types=variables,
        calls={name: len(args) for name, args in calls.items()}, call_types=calls,
        pure={name: len(signature[0]) for name, signature in pure.items()},
        pure_types={name: {'arguments': args, 'result': result} for name, (args, result) in pure.items()})


INTEGER_A = rules({'a': 'int', 'b': 'int', 'c': 'int', 'd': 'int'},
    {'O.Left': ['int', 'int', 'int']}, {'K.Max': (['int', 'int'], 'int')})
INTEGER_B = rules({'a': 'int', 'b': 'int', 'c': 'int', 'd': 'int', 'g': 'int'},
    {'H.Prove': ['int'] * 4, 'O.Gap': ['int'] * 3}, {'K.Max': (['int', 'int'], 'int')})
MAP = 'map<int,int>'
SET = 'set<int>'
MAP_A = rules({'m': MAP, 'p': 'int', 'q': 'int'},
    {'O.PutKeys': [MAP, 'int', 'int'], 'O.PutAt': [MAP, 'int', 'int', 'int']},
    {'K.Put': ([MAP, 'int', 'int'], MAP), 'K.Inverse': ([MAP, MAP], 'bool')})
MAP_B = rules({'m': MAP, 'n': MAP, 'p': 'int', 'q': 'int'},
    {'H.Prove': [MAP, 'int', 'int']},
    {'K.Put': ([MAP, 'int', 'int'], MAP), 'K.Inverse': ([MAP, MAP], 'bool')})


def parse(body, policy):
    parser = guard.Grammar(body, policy)
    tree = parser.sequence()
    if parser.peek() is not None:
        raise ValueError('Trailing body tokens')
    guard.Types(policy).statements(tree)
    return tree


class TypePolicyTests(unittest.TestCase):
    def test_inherited_adapter_and_envelope_are_exact(self):
        root = Path(__file__).resolve().parent
        self.assertEqual(hashlib.sha256((root / 'syntax_guard.py').read_bytes()).hexdigest(), guard.SYNTAX_SHA256)
        self.assertEqual(hashlib.sha256((root / 'repair_protocol.py').read_bytes()).hexdigest(), '00078913c298559740663ae6d870ede56135be6151524d1079834c11fb64c60c')
        self.assertEqual(hashlib.sha256((root / 'extract_response.py').read_bytes()).hexdigest(), '60446deb6d0ec4bcf9d788a3fd0ea7ba9e7275255769c61e61382513cb77e7de')
        self.assertNotEqual(guard.POLICY_ID, guard.VERSION)

    def test_per_file_parameters_and_one_directional_helper_call(self):
        parse('O.Left(a,b,c);', INTEGER_A)
        parse('H.Prove(a,b,c,d); O.Gap(a,c,g);', INTEGER_B)
        for body in ('H.Prove(a,b,c,d);', 'assert g == 0;', 'Prove(a,b,c,d);', 'HelperB.Prove(a,b,c,d);', 'B.Prove(a,b,c,d);'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse(body, INTEGER_A)
        for body in ('H.Prove(a,b,c,d,g);', 'Prove(a,b,c,d,g);', 'HelperA.Prove(a,b,c,d);', 'O.Left(a,b,c);'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse(body, INTEGER_B)

    def test_exact_map_call_types_and_different_helper_parameter_sets(self):
        parse('var mm := K.Put(m,p,q); O.PutKeys(mm,p,q);', MAP_A)
        parse('H.Prove(m,p,q); assert K.Inverse(m,n);', MAP_B)
        for body in ('O.PutKeys(p,p,q);', 'O.PutAt(m,m,q,p);', 'assert K.Inverse(m,p);', 'assert n == m;', 'var mm := K.Put(m,p,true);'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse(body, MAP_A)
        with self.assertRaises(ValueError):
            parse('H.Prove(n,m,q);', MAP_B)

    def test_bounded_integer_witness_branching_and_chains(self):
        parse('var u := if a < c then c else a; assert a <= u <= b; if a < c { O.Left(a,b,u); } else { assert u == a; }', INTEGER_A)
        parse('assert false; O.Left(a,b,c);', INTEGER_A)
        for body in ('if a { assert true; }', 'var u := if true then a else false;', 'assert a;', 'assert a && true;', 'assert a in b;', 'O.Left(a,true,c);'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse(body, INTEGER_A)

    def test_map_set_local_alias_and_quantifier_types(self):
        parse('var mm := map x | x in m :: m[x]; var kk := m.Keys - {p}; var nn := mm[q := p]; assert |nn| >= 0; assert kk + {p} == m.Keys; forall x | x in m ensures m[x] == mm[x] { assert m[x] == mm[x]; } assert forall y :: y in nn ==> nn[y] == nn[y];', MAP_A)
        parse('assert {p} <= m.Keys; assert {} < {p} <= m.Keys; assert m.Keys >= {p};', MAP_A)
        parse('if true { var mm := m; } else { var mm := m; }', MAP_A)
        for body in ('var mm := map x | x in m :: true;', 'var mm := map x | x :: x;', 'var mm := m[p := m];', 'assert m.Keys[p] == 0;', 'assert m[p] == true;', 'assert m < m;', 'assert true <= false;', 'assert {p} <= p;', 'var mm := [];', 'assert m[..] == m;', 'assert forall x :: x;', 'forall x | x ensures true {}', 'var mm := map x | x in m :: m[x]; assert x == 0;', 'if true { var mm := m; } assert mm == m;'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse(body, MAP_A)

    def test_alias_parameter_local_rebinding_and_scope_bypasses(self):
        for body in ('var m := m;', 'var O := 0;', 'var K := 0;', 'var mm := m; var mm := m;', 'var mm := m; if true { var mm := m; }', 'forall m | true ensures true {}', 'assert forall p :: true;', 'var mm := map K | true :: 0;', 'assume false;', 'assert {:axiom} false;', 'assert {:verify false} false;', 'reveal K.Put(m,p,q);', 'expect false;', 'while true {}', 'import H = HelperB', 'lemma Prove() {}', '} module Evil {', 'O.Hidden(m);', 'H.Prove(m,p,q);', 'm := m;', 'assert true; // hidden'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse(body, MAP_A)
        with self.assertRaises(ValueError):
            parse('var H := 0;', MAP_B)

    def test_signature_schema_does_not_allow_self_recursion_or_cycles(self):
        # The declared B -> A edge is permitted, not forced in a proof body.
        parse('', INTEGER_B)
        parse('assert true;', MAP_B)
        for policy, filename in ((INTEGER_A, 'HelperA.dfy'), (INTEGER_B, 'HelperB.dfy'), (MAP_A, 'HelperA.dfy'), (MAP_B, 'HelperB.dfy')):
            self.assertIs(guard.validate_rules(policy, filename), policy)
        invalid = [rules({'a': 'int'}, {'H.Prove': ['int']}), rules({'a': 'int'}, {'HelperB.Prove': ['int']}),
                   rules({'a': 'int'}, {'B.Prove': ['int']}), rules({'a': 'int'}, {'O.Prove': ['int']}),
                   rules({'a': 'int'}, {'Prove': ['int']}), rules({'a': 'int'}, pure={'H.Prove': (['int'], 'int')})]
        for policy in invalid:
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                guard.validate_rules(policy, 'HelperA.dfy')
        with self.assertRaises(ValueError):
            guard.validate_rules(INTEGER_A, 'HelperB.dfy')

    def test_finite_limits_inherited(self):
        for body in (' ' * (guard.MAX_BODY + 1), 'assert true;' * (guard.MAX_STATEMENTS + 1),
                     'assert ' + '(' * 40 + 'true' + ')' * 40 + ';',
                     'if true {' * 26 + 'assert true;' + '}' * 26,
                     'assert 1234567890123 == 0;'):
            with self.subTest(size=len(body)), self.assertRaises(ValueError):
                parse(body, INTEGER_A)


if __name__ == '__main__':
    unittest.main()
