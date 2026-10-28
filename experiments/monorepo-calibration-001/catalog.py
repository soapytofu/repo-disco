"""Read the additive 16-task development catalog; no verifier or model calls."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def tasks():
 out=[]
 for folder in [ROOT,ROOT/'remaining-families-001',ROOT/'remaining-families-001/revision-002']:
  for t in json.loads((folder/'tasks.json').read_text()):
   if folder==ROOT/'remaining-families-001' and t['family']=='sequence_induction':continue
   t=dict(t);t['fixture_root']=str(folder.relative_to(ROOT))
   if t['family']=='conditional_preconditions':
    t['variables']=['x','y'];t['calls']=({'End.Direct':2} if t['depth']=='shallow' else {'S1.Start':2,'S2.Advance':2,'End.Finish':2})
   t['editable_scope']='Prove bodies only; exact immutable bytes and calibration-body-v1 grammar'
   out.append(t)
 return out

def sources(task,variant='empty'):
 return {p.name:p.read_text() for p in (ROOT/task['fixture_root']/'fixtures'/task['task_id']/variant).glob('*.dfy')}
