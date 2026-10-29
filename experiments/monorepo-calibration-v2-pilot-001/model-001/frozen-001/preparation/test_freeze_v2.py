import collections,hashlib,json,unittest
from pathlib import Path
from unittest.mock import patch
import catalog_v2,freeze_pilot
ROOT=Path(__file__).resolve().parent
class FreezeV2(unittest.TestCase):
 def test_catalog_matching_and_reference_protocol_replay(self):
  tasks=catalog_v2.tasks();self.assertEqual(len(tasks),16);self.assertEqual(len({t['task_id'] for t in tasks}),16)
  self.assertEqual(set(collections.Counter(t['family'] for t in tasks).values()),{4})
  for family in freeze_pilot.FAMILIES:
   protected=None
   for t in [t for t in tasks if t['family']==family]:
    fs=catalog_v2.sources(t);ref=catalog_v2.sources(t,'reference')
    out,_=freeze_pilot.body_protocol.parse_response(freeze_pilot.reference_payload(t,fs,ref),fs,t)
    self.assertEqual(out,ref)
    rest={n:s for n,s in fs.items() if not n.startswith('Helper')}
    if protected is None:protected=rest
    self.assertEqual(rest,protected)
 def test_prompts_only_seed_context_and_body_protocol(self):
  for t in catalog_v2.tasks():
   fs=catalog_v2.sources(t);p=freeze_pilot.prompt(t,fs)
   self.assertIn('BODY STRINGS',p);self.assertNotIn('reference_depth',p);self.assertNotIn('wrong_witness',p);self.assertNotIn('control_count',p)
   for n,s in fs.items():self.assertIn('FILE '+n+'\n```dafny\n'+s+'```',p)
   for n in t['editable_files']:
    pre,suf=freeze_pilot.grammar.split_seed(fs[n]);self.assertEqual(fs[n],pre+'\n'+suf)
 def test_common_protocol_blocks_bypasses_and_accepts_no_proof_repair(self):
  for t in catalog_v2.tasks():
   fs=catalog_v2.sources(t);bodies={n:'' for n in t['editable_files']}
   for bad in ['assume false;','reveal K.Safe();','assert {:axiom} false;','} lemma Bad() ensures false {} {','var x := 0;','H.Prove();','assert true;\\nassert true;']:
    edited={**bodies,t['editable_files'][0]:bad}
    with self.assertRaises(ValueError):freeze_pilot.body_protocol.parse_response(json.dumps(edited),fs,t)
   with self.assertRaises(ValueError):freeze_pilot.body_protocol.parse_response('Explanation\n'+json.dumps(bodies),fs,t)
 def test_counterbalance_before_freeze(self):
  meta=[{**t,'prompt_sha256':'test-only'} for t in catalog_v2.tasks()];trials,design=freeze_pilot.make_order(meta)
  self.assertEqual(len(trials),32);self.assertEqual(len({t['trial_id'] for t in trials}),32)
  self.assertEqual(set(collections.Counter(t['task_id'] for t in trials).values()),{2})
  for sample in [1,2]:
   for pos in range(4):self.assertEqual({t['cell'] for t in trials if t['sample']==sample and t['within_family_position']==pos},set(freeze_pilot.CELLS))
  for family in freeze_pilot.FAMILIES:
   a=[t['cell'] for t in trials if t['family']==family and t['sample']==1];b=[t['cell'] for t in trials if t['family']==family and t['sample']==2];self.assertEqual(a,b[::-1])
  for t in trials:self.assertTrue(t['fresh_context']);self.assertFalse(t['feedback'])
 @unittest.skipUnless((ROOT/'remaining-families-001/results-review.json').exists(),'Await compute review')
 def test_complete_evidence_gate_and_fail_closed_on_bad_log(self):
  reports=freeze_pilot.gate(catalog_v2.tasks());self.assertEqual(sum(r['control_count'] for r in reports),136)
  original=freeze_pilot.load
  def bad(path):
   d=original(path)
   if path.name.endswith('-reference.json'):d={**d,'matched':False}
   return d
  with patch.object(freeze_pilot,'load',side_effect=bad):
   with self.assertRaises(ValueError):freeze_pilot.gate(catalog_v2.tasks())
 @unittest.skipUnless((ROOT/'frozen-001').exists(),'Await freeze')
 def test_frozen_exact_file_set_hashes_order_and_sources(self):
  r=ROOT/'frozen-001';manifest=freeze_pilot.load(r/'freeze.json');settings=freeze_pilot.load(r/'settings.json')
  self.assertEqual(manifest['model_calls'],0);self.assertEqual(settings['status'],'FROZEN_PROPOSAL_NO_MODEL_AUTHORIZATION');self.assertEqual(settings['max_calls'],32);self.assertFalse(settings['automatic_retries']);self.assertFalse(settings['reassign_unused'])
  names={str(p.relative_to(r)) for p in r.rglob('*') if p.is_file()}-{'freeze.json'};self.assertEqual(names,set(manifest['files']))
  for n,h in manifest['files'].items():self.assertEqual(hashlib.sha256((r/n).read_bytes()).hexdigest(),h,n)
  metadata=freeze_pilot.load(r/'tasks.json');trials,order=freeze_pilot.make_order(metadata)
  self.assertEqual(trials,freeze_pilot.load(r/'trials.json'));self.assertEqual(order,freeze_pilot.load(r/'order-design.json'))
  for t in metadata:
   seed={p.name:p.read_text() for p in (r/'tasks'/t['task_id']).glob('*.dfy')}
   self.assertEqual(seed,catalog_v2.sources(t));prompt=(r/'tasks'/t['task_id']/'prompt.txt').read_text();self.assertEqual(prompt,freeze_pilot.prompt(t,seed));self.assertEqual(hashlib.sha256(prompt.encode()).hexdigest(),t['prompt_sha256'])
if __name__=='__main__':unittest.main()
