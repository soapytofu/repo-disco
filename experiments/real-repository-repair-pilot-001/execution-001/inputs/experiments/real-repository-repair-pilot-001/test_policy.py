import json,unittest
from pathlib import Path
import body_guard as g
R=Path(__file__).resolve().parent;Q=R.parent/'real-repository-qualification-001'
class PolicyTests(unittest.TestCase):
 def test_exact_reference_reconstruction(self):
  for t in json.loads((R/'tasks.json').read_bytes()):
   with self.subTest(task=t['id']):
    raw,_=g.parse_response(json.dumps({'replacement':(R/'fixtures'/t['id']/'reference-body.txt').read_text()}),t['id'])
    self.assertEqual(raw,(Q/'upstream'/t['project']/t['file']).read_bytes())
 def test_all_math_negative_bodies_admitted(self):
  for t in json.loads((R/'tasks.json').read_bytes()):g.reconstruct(t['id'],(R/'fixtures'/t['id']/'seed-body.txt').read_text())
  for tid in ('vmc-small-shuffle','vest-roundtrip','vest-pair'):g.reconstruct(tid,'\n')
 def test_empty_function_rejected_before_verifier(self):
  with self.assertRaises(ValueError):g.reconstruct('vmc-swap','')
 def test_alpha_renaming_and_alternative_order_are_not_answer_matching(self):
  b=(R/'fixtures/vest-roundtrip/reference-body.txt').read_text().replace('empty','buffer')
  # Rename only the value local, retaining Seq::empty's API name.
  b=b.replace('Seq::buffer','Seq::empty').replace('on_buffer','on_empty')
  g.reconstruct('vest-roundtrip',b)
  g.reconstruct('vest-roundtrip','self.lemma_serialize_len(v); self.lemma_serialize_equiv_on_empty(v); self.theorem_serialize_dps_parse_roundtrip(v, Seq::empty());')
 def test_envelopes_and_duplicate_keys(self):
  raw=json.dumps({'replacement':'s'});a,_=g.parse_response(raw,'vmc-swap');b,_=g.parse_response('```json\n'+raw+'\n```','vmc-swap');self.assertEqual(a,b)
  for payload in ['{"replacement":"s","replacement":"t"}',raw+'\n'+raw,'[{}]','{"replacement":null}','{"replacement":"s","path":"../x"}']:
   with self.subTest(payload=payload),self.assertRaises(ValueError):g.parse_response(payload,'vmc-swap')
 def test_boundary_escape_and_headers_rejected(self):
  for body in ['} lemma X() ensures false {} {','} #[verifier::external_body] fn x() {','{ s','s }','s /*','s //','"s"','s #','s \\','s \u200b']:
   with self.subTest(body=body),self.assertRaises(ValueError):g.reconstruct('vmc-swap',body)
 def test_trust_escape_declarations_recursion_and_macros_rejected(self):
  bad=['assume(false);','admit();','assert(false) by { assume(false); }','unsafe { }','panic!("x");','loop {}','while true {}','return;','fn x() {}','use vstd::prelude::*;','let f = |x| x;','self.theorem_serialize_parse_roundtrip(v);','vstd::prelude::admit();','include!("x");','assert_by_contradiction();']
  for body in bad:
   with self.subTest(body=body),self.assertRaises(ValueError):g.reconstruct('vest-roundtrip',body)
 def test_shadowing_and_unknown_calls_rejected(self):
  for body in ['let self = v;','let Seq = v;','let v = self;','mystery(v);','let f = v; f();','let x = self; x.lemma_serialize_len(v);']:
   with self.subTest(body=body),self.assertRaises(ValueError):g.reconstruct('vest-roundtrip',body)
 def test_named_reveals_only(self):
  g.reconstruct('vmc-small-shuffle','reveal aLength; reveal aInvariant; reveal sInvariant;')
  for b in ['reveal *;','reveal Anything;']:
   with self.assertRaises(ValueError):g.reconstruct('vmc-small-shuffle',b)
 def test_source_and_span_tampering_rejected(self):
  from unittest.mock import patch
  t=g.task('vmc-swap');t['source_sha256']='0'*64
  with patch.object(g,'task',return_value=t),self.assertRaises(ValueError):g.reconstruct('vmc-swap','s')
  t=g.task('vmc-swap');t['boundary']['start']+=1
  with patch.object(g,'task',return_value=t),self.assertRaises(ValueError):g.reconstruct('vmc-swap','s')
 def test_limits(self):
  for b in [' '*17000,'(' * 33 + 's'+')'*33,'s; '*2100]:
   with self.assertRaises(ValueError):g.reconstruct('vmc-swap',b)
if __name__=='__main__':unittest.main(verbosity=2)
