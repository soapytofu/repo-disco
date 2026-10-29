"""Selected v2 development tasks; original conditional instance retained."""
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'monorepo-calibration-001'
spec=importlib.util.spec_from_file_location('legacy_catalog',OLD/'catalog.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
def tasks():
 out=[]
 for t in legacy.tasks():
  if t['family']=='conditional_preconditions':out.append({**t,'fixture_root':'../monorepo-calibration-001'})
 for folder in [ROOT,ROOT/'remaining-families-001',ROOT/'remaining-families-001/revision-002']:
  for t in json.loads((folder/'tasks.json').read_text()):
   if folder==ROOT/'remaining-families-001' and t['family']=='interval_witness':continue
   out.append({**t,'fixture_root':str(folder.relative_to(ROOT))})
 return out

def sources(t,variant='empty'):
 return {p.name:p.read_text() for p in (ROOT/t['fixture_root']/'fixtures'/t['task_id']/variant).glob('*.dfy')}
