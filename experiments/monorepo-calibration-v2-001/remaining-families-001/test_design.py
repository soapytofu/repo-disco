import hashlib,json,unittest
from pathlib import Path
import body_protocol
from grammar import split_seed
ROOT=Path(__file__).resolve().parent
TASKS=json.loads((ROOT/'tasks.json').read_text())
CHECKS=json.loads((ROOT/'checks.json').read_text())
def sources(t,v):return {p.name:p.read_text() for p in (ROOT/'fixtures'/t['task_id']/v).glob('*.dfy')}
def bodies(t,fs,seed):
 out={}
 for n in t['editable_files']:
  pre,suf=split_seed(seed[n]);assert fs[n].startswith(pre) and fs[n].endswith(suf);out[n]=fs[n][len(pre):-len(suf)]
 return out
class Design(unittest.TestCase):
 def test_all_eight_references_exactly_roundtrip(self):
  for t in TASKS:
   seed=sources(t,'empty');ref=sources(t,'reference');got,meta=body_protocol.parse_response(json.dumps(bodies(t,ref,seed)),seed,t)
   self.assertEqual(got,ref);self.assertEqual(meta['version'],'body-json-v2.1')
 def test_negative_reasoning_controls_are_admitted_by_syntax(self):
  for c in CHECKS:
   if c['variant'] in ('hidden_shortcut','weakened_helper_contract'):continue
   t=next(t for t in TASKS if t['task_id']==c['task_id']);seed=sources(t,'empty');fs=sources(t,c['variant'])
   self.assertEqual(body_protocol.parse_response(json.dumps(bodies(t,fs,seed)),seed,t)[0],fs)
 def test_immutable_provider_and_client_bytes_across_cells(self):
  for family in {t['family'] for t in TASKS}:
   protected=None
   for t in [t for t in TASKS if t['family']==family]:
    fs=sources(t,'empty');rest={n:s for n,s in fs.items() if not n.startswith('Helper')}
    if protected is None:protected=rest
    self.assertEqual(rest,protected)
    for c in [c for c in CHECKS if c['task_id']==t['task_id']]:
     f=sources(t,c['variant']);self.assertEqual({n:s for n,s in f.items() if not n.startswith('Helper')},protected)
     if t['sharing']=='shared':self.assertEqual(f['HelperB.dfy'],fs['HelperB.dfy'])
 def test_bypass_contract_escape_and_unknown_calls_rejected(self):
  for t in TASKS:
   seed=sources(t,'empty');ref=sources(t,'reference');bs=bodies(t,ref,seed);n=t['editable_files'][0]
   for bad in ['assume false;','reveal K.Score();','assert {:axiom} false;','} lemma Bad() ensures false {} {','H.Prove();','End.K.Bad();',ref[n]]:
    edited=dict(bs);edited[n]=bad
    with self.subTest(task=t['task_id'],bad=bad),self.assertRaises(ValueError):body_protocol.parse_response(json.dumps(edited),seed,t)
   modified=dict(seed);modified['Kernel.dfy']+='\n'
   with self.assertRaises(ValueError):body_protocol.parse_response(json.dumps(bs),modified,t)
 def test_witness_inline_form_supported_without_reference_rewrite(self):
  t=next(t for t in TASKS if t['task_id']=='witness-shallow-shared');seed=sources(t,'empty')
  candidate,_=body_protocol.parse_response(json.dumps({'HelperA.dfy':'End.Direct(a,b,c,d,if a >= c then a else c);'}),seed,t)
  self.assertIn('if a >= c then a else c',candidate['HelperA.dfy'])
  # Syntax check only; compute references use the explicit branches.
 def test_count_and_expected_categories(self):
  self.assertEqual(len(TASKS),8);self.assertEqual(len(CHECKS),72)
  self.assertEqual(sum(c['expected']=='success' for c in CHECKS),8)
  self.assertEqual(sum(c['expected']=='termination_failure' for c in CHECKS),4)
  self.assertEqual(sum(c['expected']=='resolution_failure' for c in CHECKS),4)
  for c in CHECKS:self.assertEqual(c['source_sha256'],{n:hashlib.sha256(s.encode()).hexdigest() for n,s in sources(next(t for t in TASKS if t['task_id']==c['task_id']),c['variant']).items()})
if __name__=='__main__':unittest.main()
