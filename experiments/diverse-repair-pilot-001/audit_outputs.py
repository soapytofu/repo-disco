"""Read-only post-run content audit. No model calls, candidate writes or verification.

JSON-fence inspection is a separate format diagnosis, never a change to the
frozen full-response extractor or primary scoring.
"""
from pathlib import Path
from collections import Counter
import difflib,json,re
import run_pilot as r
ROOT=Path(__file__).resolve().parent

def scanner_rejection(raw,envelope):
    decoder=json.JSONDecoder(object_pairs_hook=envelope.unique,parse_constant=envelope.reject_constant)
    cursor=0;count=0
    while match:=envelope.START.search(raw,cursor):
        start=match.start();tail=raw[start+1:].lstrip();first=tail[:1];cursor=start+1
        looks=(first in ('"','}') if raw[start]=='{' else bool(first) and (first in '{["-0123456789]' or tail.startswith(('true','false','null'))))
        if not looks:continue
        try:_,length=decoder.raw_decode(raw[start:])
        except (ValueError,RecursionError):return dict(reason='Malformed or duplicate-key JSON container',start_char=start,snippet=raw[start:start+60])
        count+=1
        if count>1:return dict(reason='Multiple JSON containers',start_char=start,snippet=raw[start:start+60])
        cursor=start+length
    raise AssertionError('Expected scanner rejection')

def audit():
    report=r.load(ROOT/'reviewed-results.json');trials={t['trial_id']:t for t in r.load(ROOT/'frozen-001/trials.json')}
    guard,envelope=r.policy();rows=[];diffs=[];distinct=set();verify_counts=Counter()
    for row in report['rows']:
        trial=trials[row['trial_id']];folder=ROOT/'model-001'/row['trial_id'];_,task,base,template=r.parent_parts(ROOT,trial)
        item=dict(trial_id=row['trial_id'],semantic_instance=row['semantic_instance'],sharing=row['sharing'],feedback_condition=row['feedback_condition'],primary_outcome=row['outcome'])
        response=r.load(folder/'response.json');raw=response['text'];item['raw_response_sha256']=r.sha(folder/'response.json')
        if row['admitted']:
            edited=r.files(folder/'candidate');bodies={}
            for n in task['editable_files']:
                pre,suf=guard.split_seed(template[n].decode());bodies[n]=edited[n].decode()[len(pre):-len(suf)]
                diffs.extend(difflib.unified_diff(base[n].decode().splitlines(True),edited[n].decode().splitlines(True),fromfile=row['trial_id']+'/original/'+n,tofile=row['trial_id']+'/candidate/'+n))
            distinct.add(tuple(sorted(r.hashes(edited).items())))
            item.update(body_sha256={n:r.hashes({n:b.encode()})[n] for n,b in bodies.items()},separate_bodies_identical=len(set(bodies.values()))==1 if task['sharing']=='separate' else None)
            ev=r.load(folder/'verification.json');summary=re.findall(r'^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$',ev['stdout']+'\n'+ev['stderr'],re.M)
            assert len(summary)==1 and ev['exit_code']==0 and int(summary[0][1])==0
            item['verified_obligations']=int(summary[0][0]);verify_counts[summary[0][0]]+=1
            item['edit_interpretation']=('Adds the intermediate saturation case; calls Below/Above under their matching preconditions.' if task['semantic_instance']=='threshold_compose' else 'Chooses endpoint a when a differs from e, otherwise endpoint b; a<b proves the second endpoint differs. Calls Bounds then Finish with unchanged goal.')
        else:
            extraction=r.load(folder/'extraction.json');assert extraction['stage']=='envelope'
            trace=scanner_rejection(raw,envelope);assert trace['reason']==extraction['reason']
            matches=list(re.finditer(r'(?m)^```json\s*\n(.*?)^```\s*$',raw,re.S))
            assert len(matches)==1,'Unexpected output wrapper'
            match=matches[0];text=match.group(1)
            obj=json.loads(text,object_pairs_hook=envelope.unique,parse_constant=envelope.reject_constant)
            assert isinstance(obj,dict) and set(obj)==set(task['editable_files']) and all(isinstance(x,str) for x in obj.values())
            assert trace['start_char']<match.start(), 'Rejection was not in explanatory prose'
            item.update(primary_rejection=extraction['reason'],scanner_rejection_in_prose=trace,
                single_fenced_json_object_valid=True,fence_start_char=match.start(),fence_end_char=match.end(),
                exact_expected_keys=True,recursive_tail_call_present={n:bool(re.search(r'\bProve\(\s*s\[1\.\.\]\s*,\s*t\[1\.\.\]\s*\)',b)) for n,b in obj.items()},
                candidate_admitted_by_primary_protocol=False,proof_verified=False,
                note='Format inspection only; no guarded candidate was created or verified and no score was changed.')
        rows.append(item)
    result=dict(job_id='60343569',model_calls_in_this_audit=0,dafny_runs_in_this_audit=0,original_score_unchanged='16/24',
        unique_verified_candidate_workspaces=len(distinct),verified_obligation_count_histogram=dict(verify_counts),
        rejected_envelope_reasons=dict(Counter(x['primary_rejection'] for x in rows if 'primary_rejection' in x)),
        valid_single_json_fences_in_rejected_responses=sum(x.get('single_fenced_json_object_valid',False) for x in rows),rows=rows)
    r.durable_json(ROOT/'content-audit.json',result)
    (ROOT/'source-diffs.patch').write_text(''.join(diffs))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))

if __name__=='__main__':audit()
