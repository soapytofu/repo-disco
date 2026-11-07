"""Offline source/contract and diagnostic review. Never dispatches or verifies."""
from collections import Counter
import json
from pathlib import Path
import run_pilot as r
from review_results import review
ROOT=Path(__file__).resolve().parent

def analyze():
 report=review(ROOT);guard=r.guard_module(ROOT);out=ROOT/'model-001';rows=[];protected=0;editable=0;wrappers=Counter()
 witness_fail={1,3,5,10,12,14};expected_pass={2,4,7,8,9,11,13,16}
 for row in report['trials']:
  tid=row['trial_id'];number=int(tid.rsplit('-',1)[1]);folder=out/tid
  task=r.load(folder/'task.json');seed=r.sources(ROOT,task);raw=r.load(folder/'response.json')['text'];decision=r.load(folder/'extraction.json')
  span=decision['envelope'];payload=raw[span['start_char']:span['end_char']];bodies=json.loads(payload)
  if raw.strip()==payload:wrapper='plain object'
  elif raw.strip().startswith('```json\n') and raw.strip().endswith('\n```') and raw.strip()[8:-4]==payload:wrapper='whole-response fence'
  else:wrapper='surrounding prose/fence'
  wrappers[wrapper]+=1
  candidate={p.name:p.read_bytes() for p in (folder/'candidate').glob('*.dfy')}
  for name,source in seed.items():
   if name in task['editable_files']:
    prefix,suffix=guard.split_seed(source.decode());assert candidate[name]==(prefix+bodies[name]+suffix).encode();editable+=1
   else:assert candidate[name]==source;protected+=1
  verification=r.load(folder/'verification.json');text=verification['stdout']+'\n'+verification['stderr']
  errors=[line for line in text.splitlines() if ': Error:' in line]
  warnings=[line for line in text.splitlines() if ': Warning:' in line]
  if number in witness_fail:
   assert row['outcome']=='PROOF_FAILURE' and 'precondition' in text
   assert all('if ' not in b and 'a + gap' in b for b in bodies.values())
   meaning='Unconditional lower witness a need not satisfy c <= a; correct interval width/overlap assumptions do not establish this ordering.'
  elif number==6:
   assert row['outcome']=='PROOF_FAILURE' and len(errors)==2 and all('forall' in e for e in errors)
   assert 'O2.PutAt(m,k,x,q)' not in bodies['HelperA.dfy'].replace(' ','')
   meaning='Pointwise value proof lacks the inner update observation linking K.Put(m,k,x)[q] to m[q] for surviving keys; both forall postconditions fail.'
  elif number==15:
   assert row['outcome']=='WARNING_ONLY' and verification['exit_code']==2 and not errors and len(warnings)==4
   assert '16 verified, 0 errors' in text
   meaning='All obligations verify but concrete map comprehensions emit four missing-trigger warnings; strict exit-zero policy keeps this a non-pass.'
  else:
   assert number in expected_pass and row['outcome']=='VERIFIED' and verification['exit_code']==0 and not errors and not warnings
   meaning='Whole workspace strictly verified under unchanged contracts and source boundary.'
  rows.append(dict(trial_id=tid,task_id=task['task_id'],outcome=row['outcome'],wrapper=wrapper,interpretation=meaning,
   verification_path=str((folder/'verification.json').relative_to(ROOT)),verification_sha256=r.sha(folder/'verification.json'),
   response_sha256=r.sha(folder/'response.json'),candidate_sha256=r.hashes(candidate),
   body_sha256={n:r.hashlib.sha256(b.encode()).hexdigest() for n,b in bodies.items()},
   separate_bodies_identical=len(set(bodies.values()))==1 if task['sharing']=='separate' else None,
   errors=errors,warnings=warnings))
 # An ordinary integer counterexample to the failed witness choice; not a new Dafny trial.
 a,b,c,d,gap=0,2,1,2,1;u,v=a,a+gap
 assert gap>0 and a+gap<=b and c+gap<=d and a+gap<=d and c+gap<=b
 assert not c<=u and a<=c<=b and c<=c+gap<=d and a<=c+gap<=b
 counterexample=dict(a=a,b=b,c=c,d=d,gap=gap,chosen_u=u,chosen_v=v,violated='c <= u',valid_alternative_u=c,valid_alternative_v=c+gap,checked_with='integer arithmetic, no solver/model call')
 assert report['reserved']==report['unique_request_ids']==16 and report['sdk_retries']==0
 assert protected==120 and editable==24
 result=dict(status='REVIEWED',new_model_calls=0,new_verifier_invocations=0,original_primary_score='8/16',
  protected_file_comparisons=protected,protected_body_boundary_comparisons=editable,exact_model_body_strings_preserved=True,
  wrappers=dict(wrappers),witness_counterexample=counterexample,separate_duplicate_body_responses=sum(x['separate_bodies_identical'] is True for x in rows),
  interpretation='Six witness failures share one invalid endpoint choice; one map proof failure and one warning-only result are distinct. No general sharing/depth effect or historical rescore is inferred.',
  report_sha256=r.sha(ROOT/'results-review.json'),analysis_code_sha256=r.sha(Path(__file__)),trials=rows)
 r.durable_json(ROOT/'source-diagnostic-review.json',result)
 print(json.dumps({k:v for k,v in result.items() if k!='trials'},indent=2))
if __name__=='__main__':analyze()
