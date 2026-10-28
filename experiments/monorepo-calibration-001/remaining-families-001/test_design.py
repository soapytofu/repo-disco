import json,unittest
from pathlib import Path
import build
ROOT=Path(__file__).resolve().parent
class Design(unittest.TestCase):
 def test_rebuild_bytes(self):
  for c in json.loads((ROOT/'checks.json').read_text()):
   prefix,depth,sharing=c['task_id'].split('-')
   expected=build.snapshot(build.FAMILIES[prefix](),depth,sharing,c['variant'])
   self.assertEqual(expected,{p.name:p.read_text() for p in (ROOT/c['path']).glob('*.dfy')})
 def test_matched_immutable_sources_and_body_counts(self):
  for maker in build.FAMILIES.values():
   f=maker();base=build.snapshot(f,'shallow','shared','reference')
   for d in ['shallow','deep']:
    for s in ['shared','separate']:
     ref=build.snapshot(f,d,s,'reference');empty=build.snapshot(f,d,s,'empty')
     for n in ['Kernel.dfy','Stage1.dfy','Stage2.dfy','Stage3.dfy','ClientA.dfy','ClientB.dfy','All.dfy']:self.assertEqual(ref[n],base[n]);self.assertEqual(empty[n],ref[n])
     self.assertEqual(sum(ref[n]!=empty[n] for n in ref),1 if s=='shared' else 2)
 def test_boundaries_and_hashes(self):
  for c in json.loads((ROOT/'checks.json').read_text()):
   fs={p.name:p.read_bytes() for p in (ROOT/c['path']).glob('*.dfy')}
   self.assertEqual(c['source_sha256'],{n:build.sha(t) for n,t in fs.items()})
   for t in fs.values():self.assertEqual(t.count(b'{'),t.count(b'}'))
  ts=json.loads((ROOT/'tasks.json').read_text());self.assertEqual(len(ts),12)
  for t in ts:
   self.assertEqual(t['client_count'],2)
   for edges in t['includes'].values():self.assertTrue(set(edges)<=set(t['source_sha256']))
 def test_depth_and_negative_controls(self):
  for maker in build.FAMILIES.values():
   f=maker();deep=f['proof']('deep')
   self.assertIn('S1.',deep);self.assertIn('S2.',deep);self.assertIn('End.Finish',deep)
   for mutation in f['mutations'].values():self.assertNotEqual(mutation(deep,'deep'),deep)
if __name__=='__main__':unittest.main()
