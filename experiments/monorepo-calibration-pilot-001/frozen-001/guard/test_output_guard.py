import json,unittest
import catalog,output_guard as g
class Guard(unittest.TestCase):
 def setUp(self):self.tasks=catalog.tasks()
 def test_reference_replay_all_16(self):
  for t in self.tasks:
   seeds=catalog.sources(t);ref=catalog.sources(t,'reference');files={n:ref[n] for n in t['editable_files']}
   out,meta=g.parse_response('Proof follows.\n```json\n'+json.dumps(files)+'\n```',seeds,t)
   self.assertEqual(out,files);self.assertEqual(meta['version'],'calibration-body-v1')
 def test_preserves_immutable_bytes(self):
  for t in self.tasks:
   seeds=catalog.sources(t);ref=catalog.sources(t,'reference');files={n:ref[n] for n in t['editable_files']};n=t['editable_files'][0]
   for old,new in [('ensures','requires'),('induction false','induction true'),('Kernel`Public','Kernel`Internal'),('lemma','lemma {:verify false}')]:
    changed=dict(files);changed[n]=changed[n].replace(old,new,1)
    with self.assertRaises(ValueError):g.validate_files(changed,seeds,t)
 def test_bypasses_rejected_all_families(self):
  for t in self.tasks:
   seeds=catalog.sources(t)
   for body in ['assume false;','assert true by { assume false; }','reveal K.Total();','return;','while false {}','forall x :: true','var x := 0;','{:verify false}','H.Prove(x,y);','K.Total();','End.K.Direct(x,y);','assert {:axiom} false;','// comment','/* comment */','} lemma Escape() {']:
    files={n:seeds[n] for n in t['editable_files']};n=t['editable_files'][0];a,b=g.split_seed(seeds[n]);files[n]=a+'\n'+body+'\n'+b
    with self.assertRaises(ValueError,msg=(t['task_id'],body)):g.validate_files(files,seeds,t)
 def test_ordinary_wrong_proofs_remain_evaluation_outcomes(self):
  for t in self.tasks:
   seeds=catalog.sources(t)
   for v in ['empty','wrong_argument','missing_prerequisite']:
    candidate=catalog.sources(t,v);files={n:candidate[n] for n in t['editable_files']}
    g.validate_files(files,seeds,t)
 def test_payload_ambiguity_and_names(self):
  t=self.tasks[0];s=catalog.sources(t);n=t['editable_files'][0];value=json.dumps(s[n]);p=json.dumps({n:s[n]})
  for raw in [p+p,'{"'+n+'":'+value+',"'+n+'":'+value+'}',json.dumps({'files':{n:s[n]}}),json.dumps({'../HelperA.dfy':s[n]}),'{bad '+p,json.dumps({n:3}),p+'}']:
   with self.assertRaises(ValueError):g.parse_response(raw,s,t)
 def test_empty_and_extra_file_sets(self):
  for t in self.tasks:
   s=catalog.sources(t)
   for files in [{},s,{**{n:s[n] for n in t['editable_files']},'All.dfy':'include "X.dfy"'}]:
    with self.assertRaises(ValueError):g.validate_files(files,s,t)
 def test_expression_forms_and_limits(self):
  for t in self.tasks:
   g.Grammar('assert (1 + 2) == 3; if 0 <= 1 { assert true; } else { assert false; }',t).sequence()
   for b in ['assert 1234567890123 == 0;','assert '+('('*40)+'0'+(')'*40)+' == 0;','assert true;'*257]:
    with self.assertRaises(ValueError):g.Grammar(b,t).sequence()
  with self.assertRaises(ValueError):g.extract(' '*262145,['x'])
 def test_hidden_calls_and_cross_helper_delegation(self):
  for t in self.tasks:
   if t['depth']=='deep':
    with self.assertRaises(ValueError):g.Grammar('End.Direct(0, 0);',t).sequence()
   with self.assertRaises(ValueError):g.Grammar('HelperA.Prove(0,0);',t).sequence()
if __name__=='__main__':unittest.main()
