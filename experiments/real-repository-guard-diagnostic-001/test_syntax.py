import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import body_guard as g
import common as c
import prepare
from gates.vmc import protocol as dg

class SyntaxTests(unittest.TestCase):
    def test_saved_replay_and_three_groups(self):
        report,groups=prepare.replay()
        self.assertEqual((report['legacy_admitted'],report['legacy_rejected'],report['new_admitted']),(9,7,16))
        self.assertEqual([x['mapped_saved_slots'] for x in groups],[[1,2,15,16],[7,10],[12]])
        self.assertEqual(report,c.read(c.ROOT/'offline-replay.json'))
    def test_update_expressions(self):
        for b in ['s[i := s[j]][j := s[i]]','s[(i) := s[j]]','s[i := s[j := s[i]][0]]','(s)[i := s[j]]']:
            with self.subTest(b=b):g.validate_body(b,'vmc-swap')
    def test_protected_assignments(self):
        for b in ['i := 0; s','s[i] := 0; s','(s)[i] := 0; s','s.x := 0; s',
                  '(i, x) := (0, 0); s','s[i := (i := 0; s[j])]',
                  's[i := s[j]; j := s[i]]','s[i := s[j]] := s; s']:
            with self.subTest(b=b),self.assertRaises(ValueError):g.validate_body(b,'vmc-swap')
    def test_receiver_assignment(self):
        for b in ['self.0 = v;','(self).0 = v;','v[0] = v;','(v, x) = (v, v);','obuf[0] = v;']:
            with self.subTest(b=b),self.assertRaises(ValueError):g.validate_body(b,'vest-pair')
    def test_dafny_unary_negation(self):
        for b in ['assert !(|oldASeq| - 0 > 1);','assert !false;','if !false { assert true; }']:
            g.validate_body(b,'vmc-small-shuffle')
    def test_macro_bans_remain(self):
        for tid,b in [('vest-pair','assert!(true);'),('vest-pair','foo!{}'),
                      ('vmc-small-shuffle','foo!(true);'),('vest-pair','assert_by_contradiction!{}')]:
            with self.subTest(b=b),self.assertRaises(ValueError):g.validate_body(b,tid)
    def test_extensional_equality_exact(self):
        self.assertIn('=~=',g.tokens('assert(obuf =~= obuf);'))
        g.validate_body('assert(obuf =~= obuf);','vest-pair')
        for tid,b in [('vest-pair','assert(obuf =~~= obuf);'),('vest-pair','assert(~obuf);'),
                      ('vmc-swap','s =~= s')]:
            with self.subTest(b=b),self.assertRaises(ValueError):g.validate_body(b,tid)
    def test_contract_and_proof_bypasses(self):
        bad=['assert(false) by { assume(false); }','let x = arbitrary();','reveal_with_fuel(x, 100);',
             'self.0 = self.1;','#[verifier::external_body]','let v = self;','assert(false) by(nonlinear_arith);']
        for b in bad:
            with self.subTest(b=b),self.assertRaises(ValueError):g.validate_body(b,'vest-pair')
    def test_unchanged_headers_and_rules(self):
        old=prepare.legacy(c.ROOT)
        self.assertEqual(g.RULES,old.RULES);self.assertEqual(g.FORBIDDEN,old.FORBIDDEN)
        for tid in g.RULES:
            t=g.task(tid);body=(c.ROOT/'fixtures'/tid/'reference-body.txt').read_text()
            candidate,_=g.reconstruct(tid,body)
            self.assertEqual(g.sha(candidate),t['upstream_file_sha256'])
    def test_stale_evidence_and_missing_sources(self):
        profile=dict(source_sha256={'a':'x','b':'y'},logical_command=['verify','a','b'],toolchain={'version':'pinned'})
        raw={'stdout.txt':b'pass'}
        record=dict(run_id='job:1',profile_sha256=dg.sha(dg.canonical(profile)),source_sha256=profile['source_sha256'],
                    source_after_sha256=profile['source_sha256'],logical_command=profile['logical_command'],
                    toolchain=profile['toolchain'],raw_sha256={'stdout.txt':dg.sha(b'pass')},
                    model_calls=0,attempts=1,exit_code=0,elapsed_seconds=1)
        dg.check_record(record,profile,'job:1',raw)
        for field,value in [('run_id','old:1'),('source_sha256',{'a':'x'}),('source_after_sha256',{'a':'x','b':'z'}),
                            ('logical_command',['verify','a']),('raw_sha256',{}),('attempts',2),('model_calls',1)]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                dg.check_record({**record,field:value},profile,'job:1',raw)

if __name__=='__main__':unittest.main(verbosity=2)
