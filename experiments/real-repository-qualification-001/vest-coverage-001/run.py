"""Compute-only Vest native/adapter and module/provider coverage controls.

This draft cannot execute until an actual reviewed native baseline profile and
all pinned inputs are frozen in manifest.json. No model/client SDK is imported.
"""
import json,os,shutil,socket,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
sys.path.insert(0,str(BASE))
from baseline import capture,digest,write,pins
import protocol as gate

def candidate(work,case,base,patches):
    shutil.copytree(BASE/'upstream/vest',work)
    for n,h in patches.get(case,{}).items():
        raw=(ROOT/'patches'/case/n).read_bytes();assert digest(raw)==h
        p=work/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    expected=gate.expected_files(base['source_sha256'],patches.get(case,{}))
    observed={p.relative_to(work).as_posix():digest(p.read_bytes()) for p in work.rglob('*') if p.is_file()}
    gate.check_sources(observed,expected);return expected

def main():
    assert os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower()
    pins()
    for n,h in json.loads((ROOT/'manifest.json').read_bytes()).items():assert digest((ROOT/n).read_bytes())==h,n
    out=ROOT/'results';out.mkdir(exist_ok=False);env=dict(os.environ)
    base=json.loads((ROOT/'profile.json').read_bytes());patches=json.loads((ROOT/'patches.json').read_bytes())
    for n,h in base['baseline_pins'].items():assert digest((BASE/n).read_bytes())==h,n
    native=json.loads((BASE/base['baseline_phase']/'results/invocation-prefix.json').read_bytes())['prefix']
    image=Path(native[-1]);assert digest(image.read_bytes())==base['toolchain']['image_sha256']
    archive=BASE/'vest-container-002/tools/verus.zip';assert digest(archive.read_bytes())==base['toolchain']['verus_archive_sha256']
    installed=BASE/'vest-container-002/tools/unpacked';closure={}
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if item.is_dir():continue
            h=digest(z.read(item));assert digest((installed/item.filename).read_bytes())==h;closure[item.filename]=h
    write(out/'verus-tool-closure.json',closure)
    write(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),model_calls=0,manifest_sha256=digest((ROOT/'manifest.json').read_bytes())))
    observations=[]
    try:
        for item in base['invocations']:
            label=item['id'];case=item['case'];mode=item['mode'];package=item['package']
            work=ROOT/'work'/label;expected=candidate(work,case,base,patches)
            target=ROOT/'targets'/label;assert not target.exists()
            prefix=list(native);prefix[prefix.index('--pwd')+1]=str(work)
            action='focus' if mode=='client-focus-diagnostic' else 'verify'
            # Adapter command is selected from its trusted frozen profile, not supplied by a candidate.
            if mode=='adapter':logical=list(base['adapter_commands'][package])
            else:logical=['cargo','verus',action,'-p',package,'--locked','--offline','--check-toolchain','--target-dir','<FRESH_TARGET>','--','--expand-errors','--output-json','--time-expanded']
            require_args=['--locked','--offline','--check-toolchain','--output-json','--time-expanded']
            assert all(a in logical for a in require_args)
            args=[str(target) if a=='<FRESH_TARGET>' else a for a in logical]
            profile={**base,'case':case,'mode':mode,'package':package,'logical_command':logical,'source_sha256':expected,'required_functions':item['required_functions']}
            result=capture(label,prefix+args,ROOT,out,env,900)
            folder=out/label;raw={n:(folder/n).read_bytes() for n in ['stdout.txt','stderr.txt','resources.txt']}
            after={p.relative_to(work).as_posix():digest(p.read_bytes()) for p in work.rglob('*') if p.is_file()}
            gate.check_sources(after,expected)
            run_id=os.environ['SLURM_JOB_ID']+':'+label
            bound=dict(run_id=run_id,profile_sha256=gate.sha(gate.canonical(profile)),source_sha256=expected,source_after_sha256=after,
                logical_command=logical,toolchain=base['toolchain'],raw_sha256={n:gate.sha(b) for n,b in sorted(raw.items())},model_calls=0,attempts=1,exit_code=result['exit_code'],elapsed_seconds=result['elapsed_seconds'])
            write(folder/'profile.json',profile);write(folder/'bound-record.json',bound)
            gate.check_record(bound,profile,run_id,raw)
            o=gate.verus_observation(result['exit_code'],raw['stdout.txt'],raw['stderr.txt'],profile['required_functions'])
            o['full_dependency_command']=action=='verify'
            o['qualified_scope_pass']=o['proof_pass'] and action=='verify'
            write(folder/'observation.json',o)
            observations.append(dict(id=label,category=o['category'],coverage_complete=o['coverage_complete'],qualified_scope_pass=o['qualified_scope_pass']))
        write(out/'complete.json',dict(model_calls=0,invocations=len(observations),observations=observations))
    except Exception as e:
        write(out/'failure.json',dict(type=type(e).__name__,message=str(e),model_calls=0));raise

if __name__=='__main__':main()
