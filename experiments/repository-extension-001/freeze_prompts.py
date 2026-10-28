"""Prepare a fixed four-request proposal offline. This is not execution authority."""
import hashlib,json
from pathlib import Path
from extension import ROOT,sources

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 gate=json.loads((ROOT/'preflight-review.json').read_text())
 if not gate['all_expected'] or gate['checks']!=14:raise ValueError('Preflight gate')
 dest=ROOT/'frozen-001';dest.mkdir(exist_ok=False);rows=[]
 for task in json.loads((ROOT/'tasks.json').read_text()):
  seed=sources(ROOT/'seeds'/task['family'])
  grammar=('Only F.Case0A/Case1A/Case0B/Case1B calls, integer x/y/literal +/- expressions, and if comparison with optional else. Comparisons < <= > >= == !=. Do not parenthesize an entire comparison. No assertions, assumptions, reveals, loops, comments, attributes or declarations. Maximum 64 statements, 2048 body tokens, nesting 24.' if task['family']=='branch' else 'Only F.AppendA(sequence_expression, sequence_expression); calls. Expressions are s, t, u joined by +, without parentheses. At most 16 calls and 8192 body characters. No assertions, assumptions, reveals, loops, comments, attributes or declarations.')
  context=dict(task_id=task['id'],goal='Extend this verified repository by generating a new ClientC.dfy, preserving its required interface. The host will include it in All.dfy and verify the whole repository.',seed_files={k:v.decode() for k,v in sorted(seed.items())},dependency_map={'All.dfy':['ClientA.dfy','ClientB.dfy'],'ClientA.dfy':['Facts.dfy'],'ClientB.dfy':['Facts.dfy'],'Facts.dfy':[]},new_file='ClientC.dfy',required_prefix=task['prefix'],required_suffix=task['suffix'],body_grammar=grammar,output_format='One strict JSON object with exactly ClientC.dfy as key and its COMPLETE source string as value. No Markdown fences, commentary or extra fields. Preserve prefix and suffix byte-for-byte; insert the body between them. Do not return existing files. Maximum 32768 response characters.')
  messages=[{'role':'system','content':'You are an expert Dafny developer. Generate the requested new client module using only the permitted proof grammar and immutable existing APIs. Return strict JSON only.'},{'role':'user','content':json.dumps(context,sort_keys=True,indent=2)}]
  rows.append(dict(sequence=len(rows)+1,task_id=task['id'],seed_revision=task['seed_revision'],seed_sha256=task['seed_sha256'],messages=messages))
 (dest/'prompts.json').write_text(json.dumps(rows,indent=2)+'\n')
 settings=dict(model_id='global.anthropic.claude-opus-4-5-20251101-v1:0',region='us-east-1',inference_config={'maxTokens':4096,'temperature':1.0},max_calls=4,attempts_per_task=1,automatic_retries=False,reassign_unused=False,status='FROZEN_PROPOSAL_REQUIRES_NEW_AUTHORIZATION',verify_timeout_seconds=30,context='full_source_plus_declared_file_map',parser='strict-json-single-new-client-v1',stop_rule='Stop on transport ambiguity, execution error, verifier timeout or interrupted request; no restart. Normal guard/proof failures count as completed trials.')
 (dest/'settings.json').write_text(json.dumps(settings,indent=2)+'\n')
 names=['extension.py','freeze_prompts.py','tasks.json','preflight-review.json','test_extension.py']
 names += [str(p.relative_to(ROOT)) for folder in ['guards','code','seeds'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
 record=dict(artifact_sha256={n:sha(dest/n) for n in ['prompts.json','settings.json']},source_sha256={n:sha(ROOT/n) for n in names},preflight_job='55810726',request_order=[r['task_id'] for r in rows],authorization='NONE',purpose='Freeze exact proposal; no live dispatch adapter is installed by this script.')
 (dest/'freeze.json').write_text(json.dumps(record,indent=2)+'\n')
 print('Four exact prompts frozen offline; zero requests and no execution authorization')
if __name__=='__main__':main()
