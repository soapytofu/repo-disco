"""Offline evidence review only; does not invoke models or the verifier."""
import hashlib,json,re
from pathlib import Path
from parser import parse_response,unique,CLIENTS
from validate import validate
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    validate();out=ROOT/'model-001';state=json.loads((out/'ledger.json').read_text());plan=json.loads((ROOT/'plan.json').read_text())
    assert state['max_calls']==8 and 0<=state['calls_dispatched']<=8
    assert state['current'] is None and state.get('finished_at_utc'), 'Run is incomplete; preserve and inspect before review'
    rows=[];ids=[];cells={f'{t}_{c}':dict(attempted=0,success=0,extraction_accepted=0,guard_accepted=0) for t in ['diamond','nested'] for c in ['shared','separate']}
    for p in (out/'snapshot').rglob('*'):
        if p.is_file():assert p.read_bytes()==(ROOT/p.relative_to(out/'snapshot')).read_bytes(),str(p)
    for index,result in enumerate(state['completed']):
        trial=plan[index]
        for key,value in trial.items():assert result[key]==value
        directory=f"{trial['sequence']:02d}-{trial['tier']}-{trial['condition']}-r{trial['repeat']}";folder=out/directory
        assert json.loads((folder/'result.json').read_text())==result
        assert json.loads((folder/'prompt.json').read_text())==json.loads((ROOT/trial['prompt_file']).read_text())
        response=json.loads((folder/'response.json').read_text()) if (folder/'response.json').exists() else None
        strict=False;usage={};matching=None
        if response:
            ids.append(response.get('request_id'));raw=response['text'];usage=response.get('usage') or {}
            content=response['content'];reconstructed=content if isinstance(content,str) else ''.join(b.get('text','') for b in content if isinstance(b,dict) and b.get('type')=='text')
            assert raw==reconstructed
            assert (folder/'evaluation/response.txt').read_text()==raw
            try:
                obj=json.loads(raw,object_pairs_hook=unique);strict=isinstance(obj,dict) and set(obj)==set(CLIENTS) and all(isinstance(v,str) for v in obj.values())
            except ValueError:pass
            if result.get('guard_accepted'):
                fixture=ROOT/trial['fixture'];files,meta=parse_response(raw,{n:(fixture/n).read_text() for n in CLIENTS});assert meta==result['extraction']
                for n,text in files.items():assert (folder/'evaluation'/n).read_text()==text
                for n in ['Facts.dfy','All.dfy']:assert (folder/'evaluation'/n).read_bytes()==(fixture/n).read_bytes()
                for n,h in result['source_sha256'].items():assert sha(folder/'evaluation'/n)==h
                matching={n:re.sub(r'\s+','',text)==re.sub(r'\s+','',(ROOT.parent/'sharing-composition-002/fixtures'/f"{trial['tier']}_{trial['condition']}_reference"/n).read_text()) for n,text in files.items()}
                for check in result['verification']:
                    text=(folder/'evaluation'/(check['entry']+'.stdout.txt')).read_text()
                    if check['outcome']=='SUCCESS':assert check['exit_code']==0 and re.search(r'[1-9][0-9]* verified, 0 errors',text)
                if result['outcome']=='SUCCESS':assert len(result['verification'])==3 and all(c['outcome']=='SUCCESS' for c in result['verification'])
        cell=cells[f"{trial['tier']}_{trial['condition']}"];cell['attempted']+=1
        for key in ['extraction_accepted','guard_accepted']:cell[key]+=int(result.get(key,False))
        cell['success']+=int(result['outcome']=='SUCCESS')
        rows.append(dict(sequence=trial['sequence'],tier=trial['tier'],condition=trial['condition'],repeat=trial['repeat'],outcome=result['outcome'],strict_json_only=strict,usage=usage,reference_match_ignoring_whitespace=matching,verification=result.get('verification',[])))
    assert len(state['completed'])==state['calls_dispatched']
    nonempty=[i for i in ids if i];assert len(set(nonempty))==len(nonempty),'Duplicate request IDs'
    totals={k:sum(r['usage'].get(k,0) or 0 for r in rows) for k in ['input_tokens','output_tokens','total_tokens']}
    summary=dict(calls_dispatched=state['calls_dispatched'],completed=len(rows),cells=cells,usage=totals,distinct_request_ids=len(nonempty),all_response_request_ids_present=len(nonempty)==len(ids),strict_json_only=sum(r['strict_json_only'] for r in rows),guarded_sources_and_prompts_checked=True,new_model_calls_by_review=0)
    (ROOT/'model-review.json').write_text(json.dumps(dict(summary=summary,trials=rows),indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
