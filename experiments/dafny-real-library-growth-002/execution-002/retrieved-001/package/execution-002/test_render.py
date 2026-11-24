"""Manifest-only, actual-source renderer smoke; all outcomes explicitly synthetic."""
import json
from pathlib import Path
import sys
import time


def worker(root,scope_path):
    root=Path(root).resolve()
    sys.path.insert(0,str(root/'execution-002'))
    from runtime import load_renderer,read_json,guard,native,sha,canonical,source_files
    from build_runtime import validate_complete
    from run_pilot import Runner
    from test_runner import FakeHost,FakeTransport
    freeze=root/'execution-002/runtime-freeze.json';digest=sha(freeze.read_bytes())
    _,scope,stages=validate_complete(root,scope_path,freeze,digest)
    renderer=load_renderer(root,scope['renderer'])
    assert Path(renderer.__file__).resolve()==root/'pilot/render.py'
    assert Path(guard.__file__).resolve()==root/'common/guard.py'
    assert not hasattr(renderer,'render_stage2')
    host,transport=FakeHost(),FakeTransport()
    for index,slot in enumerate(scope['slots'],1):
        stage=stages[(slot['project'],1)]
        body=('assert true;' if stage.edit_profile['addition']['kind']=='method' else '0')
        body+=' // SYNTHETIC plumbing only, not a native proof '+str(index)+'\n'
        transport.responses[index]=dict(text=json.dumps({'body':body}),content=[],
            usage={'inputTokens':1,'outputTokens':1},stop_reason='end_turn',
            request_id='SYNTHETIC-REQUEST-'+str(index),retry_attempts=0,raw_response={'synthetic':True})
    output=root.parent/'synthetic-smoke'
    runner=Runner(scope,stages,renderer,host,transport,output,deadline=time.time()+90,
        integrity_check=lambda:validate_complete(root,scope_path,freeze,digest),renderer_root=root,
        offline=True,run_id='SYNTHETIC-EIGHT-INDEPENDENT-TRIALS')
    summary=runner.run()
    assert summary['status']=='COMPLETE' and summary['synthetic'] is True,summary
    assert summary['reserved']==summary['completed']==summary['accepted_stages']==8
    assert not any(output.rglob('parent-receipt.json'))
    task_payloads={};inspected=0;synthetic_rejections=0
    for slot in scope['slots']:
        saved=output/'slots'/slot['id'];stage=stages[(slot['project'],1)]
        prompt=read_json(saved/'prompt.json');payload=prompt['payload']
        text=payload['messages'][0]['content'][0]['text']
        for name,raw in stage.base_sources.items():
            view='--- FILE '+name+' ---\n'+raw.decode('utf-8')+'\n--- END FILE ---'
            assert view in text
        assert stage.edit_profile['addition']['template_utf8'] in text
        candidate=source_files(saved/'candidate')
        assert all(candidate[name]==raw for name,raw in stage.base_sources.items())
        if slot['project'] in task_payloads:assert payload==task_payloads[slot['project']]
        else:task_payloads[slot['project']]=payload
        inspected+=1
        profile=read_json(saved/'native-profile.json');record=read_json(saved/'native/record.json')
        raw={p.relative_to(saved/'native/raw').as_posix():p.read_bytes() for p in (saved/'native/raw').rglob('*') if p.is_file()}
        pins=native.EvidencePins(sha(canonical(profile)),sha(canonical(record)),sha(canonical(native.hashes(candidate))),
            tuple(sorted(native.hashes(raw).items())),record['run_id'],record['origin'])
        try:native.review(profile,candidate,record,raw,pins)
        except native.EvidenceError:synthetic_rejections+=1
        else:raise AssertionError('Default replay admitted synthetic proof evidence')
    assert inspected==synthetic_rejections==8
    assert len(transport.calls)==len(host.calls)==8
    assert read_json(output/'requests/ledger.json')['closed'] is True
    print(json.dumps(dict(mode='smoke',synthetic=True,provider_calls=0,native_processes=0,
        fake_transport_dispatches=8,fake_native_observations=8,reserved=8,completed=8,
        accepted_synthetic_stages=8,exact_base_view_assertions=8,default_synthetic_rejection_assertions=8,
        actual_renderer=scope['renderer'],staged_module_path_verified=True,manifest_sha256=digest),sort_keys=True))

if __name__=='__main__':
    assert len(sys.argv)==4 and sys.argv[1]=='--smoke','Explicit manifest-only synthetic mode required'
    worker(sys.argv[2],sys.argv[3])
