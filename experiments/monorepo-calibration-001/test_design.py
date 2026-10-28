import json,re,sys,unittest
from pathlib import Path
from build_conditional import ROOT,snapshot,CONTRACT
sys.path.insert(0,str(ROOT.parents[1]/'scripts'))
from repository_map_metrics import measure

class DesignTests(unittest.TestCase):
 def test_matching_clients_and_kernel(self):
  allfiles=[snapshot(d,s,'reference') for d in ['shallow','deep'] for s in ['shared','separate']]
  for key in ['Kernel.dfy','Stage1.dfy','Stage2.dfy','Stage3.dfy','ClientA.dfy','ClientB.dfy','All.dfy']:
   self.assertEqual(len({f[key] for f in allfiles}),1,key)
  self.assertEqual(len({tuple(sorted(f)) for f in allfiles}),1)
 def test_sources_and_manifest_and_maps(self):
  tasks=json.loads((ROOT/'tasks.json').read_text());checks=json.loads((ROOT/'checks.json').read_text())
  self.assertEqual(len(tasks),4);self.assertEqual(len(checks),26)
  for t in tasks:
   for c in ['ClientA','ClientB']:self.assertGreater(measure(t['imports'],c)['root_import_depth'],0)
   for name,includes in t['includes'].items():self.assertTrue(set(includes)<=set(t['source_sha256']))
   self.assertEqual(t['editable_files'],['HelperA.dfy'] if t['sharing']=='shared' else ['HelperA.dfy','HelperB.dfy'])
  for c in checks:
   fs=snapshot(*c['task_id'].split('-')[1:],c['variant'])
   for name,content in fs.items():self.assertEqual((ROOT/c['path']/name).read_text(),content)
 def test_empty_and_targeted_controls_preserve_signatures(self):
  for depth in ['shallow','deep']:
   for sharing in ['shared','separate']:
    ref=snapshot(depth,sharing,'reference')
    for variant in ['empty','wrong_argument','missing_prerequisite']:
     fs=snapshot(depth,sharing,variant)
     for name in ['HelperA.dfy','HelperB.dfy']:
      self.assertIn('ensures '+CONTRACT,fs[name])
      self.assertEqual(fs[name].split('  {\n')[0],ref[name].split('  {\n')[0])
     for name in ['ClientA.dfy','ClientB.dfy','Kernel.dfy']:self.assertEqual(fs[name],ref[name])
 def test_sharing_and_depth_are_explicit(self):
  shared=snapshot('deep','shared','reference');separate=snapshot('deep','separate','reference')
  self.assertIn('H.Prove(x, y);',shared['HelperB.dfy']);self.assertNotIn('import H = HelperA',separate['HelperB.dfy'])
  self.assertNotIn('End.Direct(',shared['HelperA.dfy']);self.assertIn('End.Direct(',snapshot('shallow','shared','reference')['HelperA.dfy'])
  self.assertNotIn('S2.Advance(',snapshot('deep','shared','missing_prerequisite')['HelperA.dfy'])
if __name__=='__main__':unittest.main()
