"""Prepare/validate an unexecuted proposal from reviewed evidence. No network/Dafny."""
import argparse,json,runpy,tempfile
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent;EXP=HERE.parent;REPO=EXP.parent
TASK=EXP/'witness-map-strengthening-001';ENVELOPE=EXP/'reasoning-envelope-policy-001'
common=runpy.run_path(str(EXP/'monorepo-reasoning-calibration-001/prepare.py'))
load,save,sha,require,inventory=(common[k] for k in ['load','save','sha','require','inventory'])

def validate_plan(plan,tasks):
 ids={t['task_id'] for t in tasks};byid={t['task_id']:t for t in tasks};blocks=plan['blocks']
 require(len(ids)==8 and len(blocks)==2 and all(len(b)==8 and set(b)==ids for b in blocks),'Eight distinct variants per block')
 for a,b in zip(*blocks):
  require(all(byid[a][k]!=byid[b][k] for k in ['semantic_instance','depth','sharing']),'Family and factors must reverse by position')
 for block in blocks:
  require(all(byid[a]['semantic_instance']!=byid[b]['semantic_instance'] for a,b in zip(block,block[1:])),'Alternate families within blocks')
 order=sum(blocks,[]);require(all(a!=b for a,b in zip(order,order[1:])),'Adjacent identical prompt')
 require(Counter(order)=={i:2 for i in ids},'Two samples each')
 require(plan['proposed_calls']==16 and plan['samples_per_workspace']==2 and plan['max_output_tokens_total']==16*plan['inference_config']['maxTokens'],'Call/token bound')
 require(plan['fresh_context_per_request'] and plan['sdk_total_max_attempts']==1,'Fresh/no retry')
 require(not any(plan[k] for k in ['execution_authorized','feedback','reassign_unused','slurm_requeue']),'No execution authorization or budget reuse')

def prompt(task,seeds,rules):
 parts=['Complete the empty Prove bodies so the entire supplied workspace verifies.',
  'Required response keys and shape: '+json.dumps(dict.fromkeys(task['editable_files'],'')),
  (HERE/'syntax.txt').read_text().strip(),
  'Parameters: '+', '.join(rules['variables']),
  'Allowed lemma calls (argument counts): '+json.dumps(rules['calls'],sort_keys=True),
  'Allowed pure functions (argument counts): '+json.dumps(rules['pure'],sort_keys=True),
  'Declared include/import map:\n'+json.dumps(common['source_map'](seeds),indent=2)]
 parts.extend(f'FILE {n}\n```dafny\n{s}```' for n,s in sorted(seeds.items()))
 return '\n\n'.join(parts)+'\n'

def build(out):
 plan=load(HERE/'plan.json');tasks=load(TASK/'tasks.json');validate_plan(plan,tasks)
 prior=load(EXP/'conditional-monotonicity-calibration-001/plan.json')
 for k in ['model_id','inference_config','region','verifier']:require(plan[k]==prior[k],'Pinned setting drift: '+k)
 guardpath=TASK/'protocol/body_guard.py';envelopepath=ENVELOPE/'extract_response.py'
 guard=common['guard'](guardpath);envelope=common['guard'](envelopepath)
 require(guard.VERSION==plan['guard_version'] and envelope.VERSION==plan['envelope_version'],'Policy version drift')
 registry=load(TASK/'protocol/registry-freeze.json');require(sha(guardpath)==registry['files']['body_guard.py'] and sha(envelopepath)==registry['envelope_sha256'],'Policy hash drift')
 review=load(TASK/'verification-001-review.json');require(review['all_expected'] and review['matched']==review['planned']==64,'Incomplete primary verifier gate')
 require(Counter(x['diagnostic'] for x in review['rows'])=={'success':8,'proof_failure':48,'resolution_failure':8},'Diagnostic gate')
 altreview=load(TASK/'alternative-proof-001/verification-001-review.json');require(altreview['all_expected'] and altreview['matched']==8,'Alternative proof gate')
 env=load(TASK/'verification-001/environment.json');require(env['dafny']==plan['verifier']['toolchain'] and env['z3']==plan['verifier']['z3'],'Toolchain gate')
 input_files=[HERE/n for n in ['prepare.py','test_plan.py','plan.json','syntax.txt','system.txt']]
 input_files += [guardpath,envelopepath,TASK/'protocol/registry-freeze.json',TASK/'tasks.json',TASK/'verification-001-review.json',TASK/'diagnostic-audit.json',TASK/'verification-001/environment.json',TASK/'REFERENCE-STRUCTURE.md',TASK/'alternative-proof-001/verification-001-review.json',EXP/'monorepo-reasoning-calibration-001/prepare.py',EXP/'conditional-monotonicity-calibration-001/plan.json']
 input_files += sorted((TASK/'code').rglob('*.py'))
 out.mkdir(exist_ok=False);(out/'requests').mkdir();(out/'policy').mkdir()
 (out/'policy/body_guard.py').write_bytes(guardpath.read_bytes());(out/'policy/extract_response.py').write_bytes(envelopepath.read_bytes())
 save(out/'tasks.json',tasks);save(out/'settings.json',plan)
 paths={};sizes=[]
 for task in tasks:
  tid=task['task_id'];seedpath=TASK/'fixtures'/tid/'empty';seeds=common['files'](seedpath)
  require(inventory(seedpath)==task['source_sha256'],'Seed drift: '+tid)
  rules=guard.policy(task);refpath=TASK/'fixtures'/tid/'reference';reference=common['files'](refpath)
  bodies=common['body_payload'](guard,task,seeds,reference)
  candidate,decision=envelope.parse_response('A single answer follows.\n'+json.dumps(bodies),seeds,task,guard)
  recpath=TASK/'verification-001'/(tid+'-reference.json');record=load(recpath)
  require(candidate==reference and decision['body_guard']['candidate_sha256']==record['source_sha256'] and record['exit_code']==0 and record['matched'],'Reference gate drift')
  # Pin exact alternate bytes and prove they still pass the frozen policy offline.
  altpath=TASK/'alternative-proof-001';rawpath=altpath/'responses'/tid/'response.txt'
  altcandidate,altdecision=envelope.parse_response(rawpath.read_text(),seeds,task,guard)
  altrecordpath=altpath/'verification-001'/(tid+'-alternative.json');altrecord=load(altrecordpath)
  require(altdecision['body_guard']['candidate_sha256']==altrecord['source_sha256'] and altrecord['exit_code']==0 and altrecord['matched'],'Alternative gate drift')
  input_files += sorted(seedpath.glob('*.dfy'))+sorted(refpath.glob('*.dfy'))+[recpath,rawpath,altrecordpath]
  request=dict(modelId=plan['model_id'],system=[dict(text=(HERE/'system.txt').read_text())],messages=[dict(role='user',content=[dict(text=prompt(task,seeds,rules))])],inferenceConfig=plan['inference_config'])
  paths[tid]='requests/'+tid+'.json';save(out/paths[tid],request)
  sizes.append(dict(task_id=tid,request_utf8_bytes=(out/paths[tid]).stat().st_size,prompt_utf8_bytes=len(request['messages'][0]['content'][0]['text'].encode()),editable_body_count=len(task['editable_files'])))
 trials=[]
 for block,ids in enumerate(plan['blocks'],1):
  for tid in ids:
   trials.append(dict(trial_id=f'witness-map-{len(trials)+1:02d}',sample=block,task_id=tid,request_path=paths[tid],request_sha256=sha(out/paths[tid])))
 save(out/'trials.json',trials);save(out/'request-sizes.json',sizes)
 save(out/'freeze.json',dict(base_commit=plan['base_commit'],proposed_calls=16,execution_authorized=False,files=inventory(out),repository_inputs_sha256={str(p.relative_to(REPO)):sha(p) for p in sorted(set(input_files))}))

def validate():
 with tempfile.TemporaryDirectory() as tmp:
  rebuilt=Path(tmp)/'frozen';build(rebuilt);require(inventory(rebuilt)==inventory(HERE/'frozen-001'),'Exact freeze mismatch')
 print('PASS: exact eight-request/16-slot proposal rebuild; primary and alternative source/policy/evidence gates; no provider/verifier calls.')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',type=Path);a=p.parse_args()
 if a.write:build(a.write)
 else:validate()
