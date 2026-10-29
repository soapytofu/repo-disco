import collections,hashlib,json,unittest
from pathlib import Path
import catalog,freeze_pilot,output_guard
ROOT=Path(__file__).resolve().parent
class Freeze(unittest.TestCase):
 def test_prompts_are_only_seed_sources_and_declared_context(self):
  for t in catalog.tasks():
   fs=catalog.sources(t);p=freeze_pilot.prompt(t,fs)
   for n,s in fs.items():self.assertIn('FILE '+n+'\n```dafny\n'+s+'```',p)
   self.assertNotIn('reference_depth',p);self.assertNotIn('wrong_argument',p)
   for n in t['editable_files']:
    a,b=output_guard.split_seed(fs[n]);self.assertEqual(fs[n],a+'\n'+b)
 @unittest.skipUnless((ROOT/'frozen-001').exists(),'Freeze requires completed verifier review')
 def test_frozen_hashes_and_exact_prompts(self):
  root=ROOT/'frozen-001';manifest=json.loads((root/'freeze.json').read_text())
  names={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}-{'freeze.json'}
  self.assertEqual(names,set(manifest['files']))
  for n,h in manifest['files'].items():self.assertEqual(hashlib.sha256((root/n).read_bytes()).hexdigest(),h,n)
  for t in json.loads((root/'tasks.json').read_text()):
   fs={p.name:p.read_text() for p in (root/'tasks'/t['task_id']).glob('*.dfy')}
   self.assertEqual({n:freeze_pilot.sha(s.encode()) for n,s in fs.items()},t['source_sha256'])
   self.assertEqual((root/'tasks'/t['task_id']/'prompt.txt').read_text(),freeze_pilot.prompt(t,fs))
   self.assertEqual(fs,catalog.sources(t))
 @unittest.skipUnless((ROOT/'frozen-001').exists(),'Freeze requires completed verifier review')
 def test_order_and_budget(self):
  root=ROOT/'frozen-001';trials=json.loads((root/'trials.json').read_text());settings=json.loads((root/'settings.json').read_text())
  self.assertEqual(len(trials),32);self.assertEqual(len({t['trial_id'] for t in trials}),32)
  self.assertEqual(set(collections.Counter(t['task_id'] for t in trials).values()),{2})
  self.assertEqual(settings['max_calls'],32);self.assertFalse(settings['automatic_retries']);self.assertFalse(settings['reassign_unused'])
  for family in freeze_pilot.FAMILIES:
   a=[t for t in trials if t['family']==family and t['sample']==1];b=[t for t in trials if t['family']==family and t['sample']==2]
   self.assertEqual([t['cell'] for t in a],[t['cell'] for t in b][::-1])
   for x in a:
    y=next(t for t in b if t['task_id']==x['task_id']);self.assertEqual(x['prompt_sha256'],y['prompt_sha256'])
  for sample in [1,2]:
   for pos in range(4):self.assertEqual({t['cell'] for t in trials if t['sample']==sample and t['within_family_position']==pos},set(freeze_pilot.CELLS))
  for t in trials:self.assertTrue(t['fresh_context']);self.assertFalse(t['feedback'])
 @unittest.skipUnless((ROOT/'frozen-001').exists(),'Freeze requires completed verifier review')
 def test_all_selected_preflights_and_reference_guards(self):
  reviewed=freeze_pilot.gate(catalog.tasks());self.assertEqual(len(reviewed),16)
  self.assertEqual(sum(x['control_count'] for x in reviewed),118)
if __name__=='__main__':unittest.main()
