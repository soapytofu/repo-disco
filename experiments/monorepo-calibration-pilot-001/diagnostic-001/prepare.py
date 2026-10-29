"""Separate saved-response diagnostic. No model transport; no original rescoring."""
import hashlib,json,sys
from pathlib import Path
import guard
ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 (ROOT/'fixtures').mkdir(exist_ok=False);cases=[]
 audit=json.loads((PARENT/'output-compliance-audit.json').read_text())
 for row in audit['rejections']:
  if not row['diagnostic_candidate']:continue
  tid=row['trial_id'];p=PARENT/'model-001'/tid;task=json.loads((p/'task.json').read_text());response=json.loads((p/'response.json').read_text());raw=response['text']
  original,extraction=guard.extract(raw,task['editable_files'])
  edited={n:s if s.endswith('\n') else s+'\n' for n,s in original.items()}
  seeds={q.name:q.read_text() for q in (PARENT/'frozen-001/tasks'/task['task_id']).glob('*.dfy')}
  guarded,decision=guard.validate_files(edited,seeds,task)
  candidate=dict(seeds);candidate.update(guarded);d=ROOT/'fixtures'/tid;d.mkdir()
  for n,s in candidate.items():(d/n).write_text(s)
  cases.append(dict(trial_id=tid,task=task,original_response_sha256=sha((p/'response.json').read_bytes()),original_reason=row['original_reason'],normalization='append one final LF only if absent; no other source or escape repair',appended_lf=[n for n in original if original[n]!=edited[n]],original_edit_sha256={n:sha(s.encode()) for n,s in original.items()},candidate_sha256={n:sha(s.encode()) for n,s in candidate.items()},parent_sha256={n:sha(s.encode()) for n,s in seeds.items()},guard_decision=decision,extraction=extraction,path=str(d.relative_to(ROOT))))
 assert len(cases)==11
 (ROOT/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');print('Prepared11savedresponses;3wrapperrejections excluded;original18/32unchanged;zero modelcalls')
if __name__=='__main__':main()
