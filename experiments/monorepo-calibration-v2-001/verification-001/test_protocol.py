import importlib.util,json,unittest
from pathlib import Path
import body_protocol as protocol
from grammar import split_seed
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'monorepo-calibration-001'
spec=importlib.util.spec_from_file_location('catalog',OLD/'catalog.py')
catalog=importlib.util.module_from_spec(spec);spec.loader.exec_module(catalog)

def bodies_from_sources(files,seeds,task):
 bodies={}
 for n in task['editable_files']:
  prefix,suffix=split_seed(seeds[n]);s=files[n]
  assert s.startswith(prefix) and s.endswith(suffix)
  bodies[n]=s[len(prefix):-len(suffix)]
 return bodies

class ProtocolTests(unittest.TestCase):
 def setUp(self):
  self.task=catalog.tasks()[0];self.seeds=catalog.sources(self.task)
  self.reference=catalog.sources(self.task,'reference')
  self.bodies=bodies_from_sources(self.reference,self.seeds,self.task)
 def test_16_verified_reference_sources_replayed_exactly(self):
  for task in catalog.tasks():
   seeds=catalog.sources(task);ref=catalog.sources(task,'reference')
   candidate,meta=protocol.parse_response(json.dumps(bodies_from_sources(ref,seeds,task)),seeds,task)
   self.assertEqual(candidate,ref);self.assertEqual(meta['version'],'body-json-v2')
 def test_11_prior_diagnostic_candidates_replayed_exactly(self):
  parent=ROOT.parent/'monorepo-calibration-pilot-001'
  for c in json.loads((parent/'diagnostic-001/cases.json').read_text()):
   task=c['task'];seeds={p.name:p.read_text() for p in (parent/'frozen-001/tasks'/task['task_id']).glob('*.dfy')}
   ref={p.name:p.read_text() for p in (parent/'diagnostic-001'/c['path']).glob('*.dfy')}
   candidate,_=protocol.parse_response(json.dumps(bodies_from_sources(ref,seeds,task)),seeds,task)
   self.assertEqual(candidate,ref)
 def test_4_new_reference_bodies_accepted_not_semantically_verified(self):
  for task in json.loads((ROOT/'tasks.json').read_text()):
   base=ROOT/'fixtures'/task['task_id'];seeds={p.name:p.read_text() for p in (base/'empty').glob('*.dfy')};ref={p.name:p.read_text() for p in (base/'reference').glob('*.dfy')}
   self.assertEqual(protocol.parse_response(json.dumps(bodies_from_sources(ref,seeds,task)),seeds,task)[0],ref)
 def test_optional_fence_and_body_whitespace_do_not_touch_host_source(self):
  for wrapper in [('',''),('```json\n','\n```'),('```\n','\n```')]:
   raw=wrapper[0]+json.dumps(self.bodies)+wrapper[1]
   self.assertEqual(protocol.parse_response(raw,self.seeds,self.task)[0],self.reference)
  compact={n:b.strip() for n,b in self.bodies.items()}
  candidate,meta=protocol.parse_response(json.dumps(compact),self.seeds,self.task)
  for n,s in candidate.items():
   if n not in compact:self.assertEqual(s,self.seeds[n]);continue
   pre,suf=split_seed(self.seeds[n]);self.assertEqual(s,pre+compact[n]+suf)
 def test_no_escape_repair_or_nested_json_or_prose_search(self):
  raw=json.dumps(self.bodies);n=self.task['editable_files'][0]
  invalid=['Explanation\n'+raw,raw+'\nMore',raw+raw,json.dumps(raw),raw.replace('{','{"extra":0,',1),'```python\n'+raw+'\n```',json.dumps({n:'assert true;\\nassert true;'}),'{}',json.dumps({n:None}),'NaN']
  for value in invalid:
   with self.subTest(value=value[:50]),self.assertRaises(ValueError):protocol.parse_response(value,self.seeds,self.task)
  dup='{'+json.dumps(n)+': "", '+json.dumps(n)+': ""}'
  with self.assertRaises(ValueError):protocol.parse_response(dup,self.seeds,self.task)
 def test_bypass_and_boundary_injections_rejected(self):
  n=self.task['editable_files'][0]
  bad=['assume false;','assert {:axiom} false;','reveal K.Safe();','} lemma X() ensures false {} {','assert false by { assume false; }','while true {}','var x := 0;','H.Prove(x,y);','End.K.Internal(x,y);','// comment\nassert true;','/* comment */','assert (if true then assume false else 0) == 0;','assert (if true then End.Direct(x,y) else 0) == 0;','assert (if true then 1) == 1;','assert true; }','{ assert true; }',self.reference[n]]
  for b in bad:
   d=dict(self.bodies);d[n]=b
   with self.subTest(body=b),self.assertRaises(ValueError):protocol.parse_response(json.dumps(d),self.seeds,self.task)
 def test_file_set_contract_and_seed_hash_protection(self):
  for name in self.seeds:
   changed=dict(self.seeds);changed[name]+='\n'
   with self.assertRaises(ValueError):protocol.parse_response(json.dumps(self.bodies),changed,self.task)
  extra=dict(self.bodies);extra['Kernel.dfy']=''
  with self.assertRaises(ValueError):protocol.parse_response(json.dumps(extra),self.seeds,self.task)
  task=dict(self.task);task['editable_files']=task['editable_files']*2
  with self.assertRaises(ValueError):protocol.parse_response(json.dumps(self.bodies),self.seeds,task)
 def test_resource_limits_and_empty_body_valid_syntax(self):
  n=self.task['editable_files'][0]
  for b in [' ' * 65537,'assert '+ '(' * 40+'true'+')'*40+';','assert true;' * 257]:
   d=dict(self.bodies);d[n]=b
   with self.assertRaises(ValueError):protocol.parse_response(json.dumps(d),self.seeds,self.task)
  result,_=protocol.parse_response(json.dumps({n:'\n' for n in self.task['editable_files']}),self.seeds,self.task)
  self.assertEqual(result,self.seeds)
 def test_matched_clients_and_provider_bytes(self):
  tasks=json.loads((ROOT/'tasks.json').read_text());reference=None
  for task in tasks:
   fs={p.name:p.read_text() for p in (ROOT/'fixtures'/task['task_id']/'empty').glob('*.dfy')}
   protected={n:s for n,s in fs.items() if not n.startswith('Helper')}
   if reference is None:reference=protected
   self.assertEqual(reference,protected)
  checks=json.loads((ROOT/'checks.json').read_text());self.assertEqual(len(checks),38)
  self.assertEqual(sum(c['expected']=='success' for c in checks),4)
  self.assertEqual(sum(c['expected']=='resolution_failure' for c in checks),2)
if __name__=='__main__':unittest.main()
