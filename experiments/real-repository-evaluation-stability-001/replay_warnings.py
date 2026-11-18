"""Reclassify exact saved evidence locally; preserve all historical outputs."""
import json
from pathlib import Path
import common as c
from capture import write
from gates.vmc import protocol as dg
from warning_policy import report

def replay(repo):
    registry=c.read(c.ROOT/'saved-evidence.json');rows=[]
    for entry in registry['entries']:
        c.check_pins(repo,entry['files']);d=repo/entry['directory']
        native=c.read(d/'record.json');profile=c.read(d/'profile.json');bound=c.read(d/'bound-record.json')
        raw={n:(d/n).read_bytes() for n in bound['raw_sha256']}
        dg.check_record(bound,profile,bound['run_id'],raw)
        c.require(native['exit_code']==bound['exit_code'] and native['elapsed_seconds']==bound['elapsed_seconds'],'Native result differs')
        c.require(native['artifacts']=={n:dg.sha(raw[n]) for n in ['stdout.txt','stderr.txt','resources.txt']},'Native log hashes differ')
        base=c.read(c.ROOT/'qualification'/('coverage-001/profile.json' if entry['project']=='dafny-vmc' else 'vest-coverage-001/profile.json'))
        observed=c.verification_observation(entry['project'],native,raw,base)
        c.require(observed==c.read(d/'observation.json'),'Frozen native replay differs')
        result=report(entry['project'],observed,native,base)
        rows.append(dict(id=entry['id'],original_directory=entry['directory'],
                         category=observed['category'],source_manifest_sha256=dg.sha(dg.canonical(profile['source_sha256'])),
                         observation_sha256=c.sha(d/'observation.json'),**result))
    return dict(status='SAVED_WARNING_REPLAY_PASSED',native_observations=len(rows),
                model_calls=0,new_native_calls=0,rows=rows,not_a_new_model_score=True)

if __name__=='__main__':
    result=replay(c.ROOT.parent.parent)
    write(c.ROOT/'warning-replay-001.json',result)
    print(json.dumps(dict(observations=len(result['rows']),
        legacy_accepts=sum(x['legacy_qualified_scope_pass'] for x in result['rows']),
        proof_complete=sum(x['proof_complete'] for x in result['rows']),
        eligible_v2=sum(x['eligible_under_policy_v2'] for x in result['rows']),
        recognized_cleanup_observations=sum(bool(x['operational_warnings']) for x in result['rows']),
        model_calls=0,new_native_calls=0),indent=2))
