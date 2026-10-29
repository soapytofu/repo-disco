"""Separate offline syntax diagnosis of saved responses; no repair or rescoring."""
import collections,hashlib,json
from pathlib import Path
import run_pilot as runner
ROOT=Path(__file__).resolve().parent

def main():
 runner.validate_bundle();runner.validate_runtime();guard=runner.guard_module(ROOT)
 class TraceGrammar(guard.Grammar):
  def take(self,x=None):
   try:return super().take(x)
   except ValueError:
    self.expected=x;self.actual=self.peek();raise
 review=runner.load(ROOT/'results-review.json');rows=[];first=collections.Counter()
 for row in review['trials']:
  p=ROOT/'model-001'/row['trial_id'];task=runner.load(p/'task.json');response=runner.load(p/'response.json');raw=response['text'];text=raw.strip()
  if text.startswith('```'):
   lines=text.splitlines();assert lines[0] in ('```json','```') and lines[-1]=='```';text='\n'.join(lines[1:-1])
  bodies=json.loads(text,object_pairs_hook=guard.unique)
  assert set(bodies)==set(task['editable_files']) and all(isinstance(v,str) for v in bodies.values())
  diagnostics=[]
  for name,body in bodies.items():
   g=TraceGrammar(body,task)
   try:g.sequence()
   except ValueError as e:
    diagnostics.append(dict(file=name,error=str(e),expected=getattr(g,'expected',None),actual=getattr(g,'actual',None),token_index=g.i,nearby_tokens=g.tokens[max(0,g.i-5):g.i+6],body_sha256=hashlib.sha256(body.encode()).hexdigest()))
  if row['outcome']=='OUTPUT_REJECTED':
   assert diagnostics and diagnostics[0]['error']=='Unexpected proof token'
   d=diagnostics[0];first[str(d['expected'])+' expected; '+str(d['actual'])+' received']+=1
  else:assert row['outcome']=='VERIFIED' and not diagnostics
  rows.append(dict(trial_id=row['trial_id'],task_id=task['task_id'],original_outcome=row['outcome'],response_sha256=runner.sha(p/'response.json'),exact_json_and_body_schema_valid=True,body_diagnostics=diagnostics))
 report=dict(model_calls=0,original_strict_score='1/32 unchanged',responses=32,valid_json_and_exact_schema=32,rejected_body_syntax=31,first_failure_categories=dict(first),repair_attempted=False,new_verification=False,rows=rows)
 (ROOT/'output-syntax-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
if __name__=='__main__':main()
