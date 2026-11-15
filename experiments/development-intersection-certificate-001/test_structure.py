"""Construction/syntax/finite-domain checks only; no Dafny, SSH or model calls."""
from pathlib import Path
import hashlib,importlib.util,itertools,json,tempfile,unittest
from unittest.mock import patch
import build as b
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
GRAMMAR=ROOT/'inputs/experiments/diverse-repair-pilot-001/frozen-001/policy/body_guard.py'

def valid(a,b,c,d,kind,w):
 return (kind==0 and a<=w<=b and c<=w<=d) or (kind==-1 and b<c) or (kind==1 and d<a)
def reference(a,b,c,d):
 if b<c:return -1,0
 if d<a:return 1,0
 return 0,max(a,c)
def alternative(a,b,c,d):
 if a<=d and c<=b:return 0,min(b,d)
 if c>b:return -1,0
 return 1,0

def check_result(a,b,c,d,result):
 kind,w=result
 return (valid(a,b,c,d,kind,w) and ((kind==0)==(a<=d and c<=b))
         and ((kind==-1)==(b<c)) and ((kind==1)==(d<a)))

class StructureTests(unittest.TestCase):
 def test_deterministic_complete_matrix_and_hashes(self):
  with tempfile.TemporaryDirectory() as d:
   tasks,cases,manifest=b.build(d)
   self.assertEqual(len(tasks),2);self.assertEqual(len(cases),20);self.assertEqual(len(manifest)-2,176)
   self.assertEqual(manifest,json.loads((ROOT/'fixture-manifest.json').read_text()))
   self.assertEqual({status:sum(c['expected']==status for c in cases) for status in ('success','proof_failure','resolution_failure')},
                    dict(success=4,proof_failure=14,resolution_failure=2))
 def test_only_selected_helper_bodies_change(self):
  for sharing in ('shared','separate'):
   empty=b.sources(sharing,'empty');editable=['HelperA.dfy']+(['HelperB.dfy'] if sharing=='separate' else [])
   for variant in b.VARIANTS:
    for name,source in b.sources(sharing,variant).items():
     if name not in editable:self.assertEqual(source,empty[name])
     else:
      x=b.boundary(empty[name]);y=b.boundary(source)
      self.assertEqual(x['protected_sha256'],y['protected_sha256'])
      self.assertEqual(source.encode()[:y['start']],empty[name].encode()[:x['start']])
      self.assertEqual(source.encode()[y['end']:],empty[name].encode()[x['end']:])
 def test_matched_semantics_with_explicit_copyable_work_difference(self):
  for variant in b.VARIANTS:
   left,right=b.sources('shared',variant),b.sources('separate',variant)
   for name in left:
    if name!='HelperB.dfy':self.assertEqual(left[name],right[name])
   self.assertIn(b.SIGNATURE,left['HelperB.dfy']);self.assertIn(b.SIGNATURE,right['HelperB.dfy'])
   self.assertEqual(right['HelperA.dfy'].replace('module HelperA','module HelperB'),right['HelperB.dfy'])
  self.assertEqual(b.REQUIRES,'a <= b && c <= d')
  self.assertIn('returns (kind: int, w: int)',b.client('ClientA','HelperA'))
  self.assertIn('H.Prove(c+shift,d+shift,a+shift,b+shift)',b.client('ClientB','HelperB',True))
 def test_opaque_certificate_and_named_exports(self):
  proof=b.API.split('export Proof provides ',1)[1].split('\n',1)[0]
  self.assertEqual(proof,'K, Witness, Gap')
  for hidden in ('Choose','DirectWitness'):self.assertNotIn(hidden,proof)
  self.assertIn('export Hidden provides K, DirectWitness',b.API)
  for token in ('LeftFact','RightFact','LeftGap','RightGap','Valid'):
   self.assertIn('opaque predicate '+token,b.KERNEL)
  self.assertIn('opaque ghost predicate Decided',b.KERNEL)
  for body,_,_ in b.VARIANTS.values():self.assertNotRegex(body,r'\b(?:assume|reveal|axiom|while|lemma|method)\b')
 def test_existing_grammar_with_explicit_proposed_environment(self):
  self.assertEqual(hashlib.sha256(GRAMMAR.read_bytes()).hexdigest(),'c749c53fd11742937adc3cdefa1fa5444ee0232443fa6d1cb7d2b83bea8a6c6b')
  spec=importlib.util.spec_from_file_location('in_memory_proposed_environment',GRAMMAR);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
  tasks=json.loads((ROOT/'tasks.json').read_text());allowed=hidden=0
  for task in tasks:
   rules=dict(variables=task['params'],calls=task['calls'],pure=task['pure'])
   with patch.object(guard,'policy',return_value=rules):
    for variant,(body,expected,_) in b.VARIANTS.items():
     for name in task['editable_files']:
      if expected=='resolution_failure':
       with self.assertRaises(ValueError):guard.Grammar(body,task).sequence()
       hidden+=1
      else:
       parser=guard.Grammar(body,task);parser.sequence();self.assertIsNone(parser.peek());allowed+=1
  self.assertEqual((allowed,hidden),(27,3))
 def test_finite_domain_sound_exhaustive_classification_and_client_translation(self):
  intervals=[(a,z) for a in range(-3,4) for z in range(a,4)];checked=0;tags=set()
  for (a,b_), (c,d) in itertools.product(intervals,repeat=2):
   for choose in (reference,alternative):
    result=choose(a,b_,c,d);self.assertTrue(check_result(a,b_,c,d,result));tags.add(result[0]);checked+=1
    # Negative certificates really exclude every point, not only one bad choice.
    if result[0]!=0:self.assertFalse(set(range(a,b_+1)).intersection(range(c,d+1)))
    for shift in (-2,0,2):
     q=(c+shift,d+shift,a+shift,b_+shift);self.assertTrue(check_result(*q,choose(*q)));checked+=1
  self.assertEqual(checked,6272);self.assertEqual(tags,{-1,0,1})
 def test_touching_singleton_and_negative_counterexamples(self):
  examples=json.loads((ROOT/'semantic-cases.json').read_text())
  for row in examples['valid_inputs']:
   args=tuple(row['intervals']);self.assertTrue(args[0]<=args[1] and args[2]<=args[3])
   for choose in (reference,alternative):
    self.assertEqual(choose(*args)[0],row['kind']);self.assertTrue(check_result(*args,choose(*args)))
  for row in examples['mathematical_counterexamples']:
   a,b_,c,d=row['intervals'];kind,w=row['faulty_result']
   self.assertTrue(a<=b_ and c<=d);self.assertFalse(valid(a,b_,c,d,kind,w),row['variant'])
  self.assertEqual(examples['proof_dependency_controls'],['empty','missing_gap_evidence','missing_right_evidence','no_negative_certificate'])
 def test_original_proposal_and_lineage_are_pinned_without_holdout_claim(self):
  lineage=json.loads((ROOT/'lineage.json').read_text())
  self.assertFalse(lineage['held_out']);self.assertFalse(lineage['new_independent_family_claim'])
  self.assertEqual(lineage['proposal']['id'],'D3-M1')
  for path,digest in lineage['input_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/'inputs'/path).read_bytes()).hexdigest(),digest,path)
  self.assertIn('positive and negative',lineage['logical_delta'])

if __name__=='__main__':unittest.main(verbosity=2)
