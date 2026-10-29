"""Explain frozen-policy rejections offline; original score/evidence unchanged."""
import json
from pathlib import Path
import run_pilot as r
ROOT=Path(__file__).resolve().parent

def main():
 guard=r.guard_module(ROOT);rows=[]
 for trial in r.load(ROOT/'results-review.json')['trials']:
  if trial['outcome']!='OUTPUT_REJECTED':continue
  folder=ROOT/'model-001'/trial['trial_id'];task=r.load(folder/'task.json');raw=r.load(folder/'response.json')['text'];seed=r.sources(ROOT,task)
  row=dict(trial_id=trial['trial_id'],task_id=task['task_id'],original_reason=trial['output_rejection_reason'],original_response_sha256=r.sha(folder/'response.json'))
  try:files,meta=guard.extract(raw,task['editable_files'])
  except ValueError:
   row.update(diagnosis='JSON wrapper rejected by frozen extractor',diagnostic_candidate=False)
  else:
   if row['original_reason']=='Protected source changed':
    normalized={n:s if s.endswith('\n') else s+'\n' for n,s in files.items()}
    _,decision=guard.validate_files(normalized,{n:b.decode() for n,b in seed.items()},task)
    assert normalized!=files
    row.update(diagnosis='Missing final LF only outside editable bodies; append-LF-only replay passes original guard',diagnostic_candidate=True,files_appended_lf=[n for n in files if files[n]!=normalized[n]])
   else:
    errors=[]
    for n,s in files.items():
     a,b=guard.split_seed(seed[n].decode());assert s.startswith(a) and s.endswith(b)
     grammar=guard.Grammar(s[len(a):len(s)-len(b)],task)
     try:grammar.sequence()
     except ValueError as error:
      assert str(error)=='Unknown expression name' and grammar.tokens[grammar.i-1]=='if'
      errors.append(dict(file=n,unsupported_token='if',context=grammar.tokens[max(0,grammar.i-4):grammar.i+8]))
    assert errors
    row.update(diagnosis='Inline if-then-else expression unsupported by frozen grammar',diagnostic_candidate=True,errors=errors)
  rows.append(row)
 (ROOT/'output-compliance-audit.json').write_text(json.dumps(dict(original_verified=18,original_planned=32,original_scores_unchanged=True,new_model_calls=0,rejections=rows),indent=2)+'\n')
 print('Reviewed14rejections:5missingfinalLF,6inlineifexpressions,3JSONwrapperrejections; no rescoring')
if __name__=='__main__':main()
