"""Five fresh VMC coverage invocations, following the saved pinned native baseline."""
import csv,json,os,shutil,socket,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
sys.path.insert(0,str(BASE))
from baseline import capture,digest,write,pins
import protocol as gate

def main():
    assert os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower()
    pins()
    for n,h in json.loads((ROOT/'manifest.json').read_bytes()).items():assert digest((ROOT/n).read_bytes())==h,n
    out=ROOT/'results';out.mkdir(exist_ok=False);env=dict(os.environ)
    base=json.loads((ROOT/'profile.json').read_bytes())
    image=BASE/'container-003/runtime.sif';assert digest(image.read_bytes())==base['toolchain']['image_sha256']
    for n,h in base['toolchain']['binary_sha256'].items():assert digest((BASE/n).read_bytes())==h,n
    archive=BASE/'toolchains/dafny-vmc/dafny.zip';installed=BASE/'toolchains/dafny-vmc/unpacked'
    closure={}
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if item.is_dir():continue
            expected=digest(z.read(item));assert digest((installed/item.filename).read_bytes())==expected,item.filename
            closure[item.filename]=expected
    assert set(closure)=={p.relative_to(installed).as_posix() for p in installed.rglob('*') if p.is_file()}
    write(out/'tool-closure.json',closure)
    patches=json.loads((ROOT/'patches.json').read_bytes())
    write(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),model_calls=0,manifest_sha256=digest((ROOT/'manifest.json').read_bytes())))
    observations=[]
    try:
        for case,mode in [('vmc_baseline','adapter'),('vmc_broken_swap','native'),('vmc_broken_swap','adapter'),('vmc_detached','native-omitted'),('vmc_detached','adapter')]:
            label=case+'-'+mode;work=ROOT/'work'/label;shutil.copytree(BASE/'upstream/dafny-vmc',work)
            changes=patches.get(case,{})
            for n,h in changes.items():
                raw=(ROOT/'patches'/case/n).read_bytes();assert digest(raw)==h
                target=work/n;target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes(raw)
            expected=gate.expected_files(base['source_sha256'],changes)
            actual={p.relative_to(work).as_posix():digest(p.read_bytes()) for p in work.rglob('*') if p.is_file()}
            gate.check_sources(actual,expected)
            declared=base['explicit_sources']+(['tests/QualificationDetached.dfy'] if case=='vmc_detached' else [])
            if mode=='adapter':inputs=['dfyconfig.toml']+sorted(declared)
            else:inputs=base['native_inputs']
            command=['verify',*inputs,'--resource-limit','20000','--log-format','csv']
            profile={**base,'case':case,'mode':mode,'logical_command':command,'source_sha256':expected}
            profile['required_units']=dict(base['required_units'])
            if case=='vmc_detached':profile['required_units']['QualificationDetached.Fails (correctness)']='tests/QualificationDetached.dfy'
            prefix=['singularity','exec','--cleanenv','--bind',str(BASE)+':'+str(BASE),'--pwd',str(work),'--env','DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1',str(image),str(BASE/'toolchains/dafny-vmc/unpacked/dafny/dafny')]
            record=capture(label,prefix+command,ROOT,out,env,180)
            directory=out/label;raw={n:(directory/n).read_bytes() for n in ['stdout.txt','stderr.txt','resources.txt']}
            for p in work.rglob('*.csv'):
                n='csv/'+p.relative_to(work).as_posix();raw[n]=p.read_bytes();target=directory/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw[n])
            after={p.relative_to(work).as_posix():digest(p.read_bytes()) for p in work.rglob('*') if p.is_file() and not p.relative_to(work).as_posix().startswith('TestResults/')}
            gate.check_sources(after,expected)
            run_id=os.environ['SLURM_JOB_ID']+':'+label
            bound=dict(run_id=run_id,profile_sha256=gate.sha(gate.canonical(profile)),source_sha256=actual,source_after_sha256=after,
              logical_command=command,toolchain=base['toolchain'],raw_sha256={n:gate.sha(b) for n,b in sorted(raw.items())},model_calls=0,attempts=1,
              exit_code=record['exit_code'],elapsed_seconds=record['elapsed_seconds'])
            write(directory/'profile.json',profile);write(directory/'bound-record.json',bound)
            gate.check_record(bound,profile,run_id,raw)
            parsed=gate.dafny_observation(record['exit_code'],raw['stdout.txt'],raw['stderr.txt'],{n:b for n,b in raw.items() if n.startswith('csv/')},profile['required_units'])
            parsed['warnings_match_upstream']=sorted(parsed['warnings'])==sorted(base['upstream_warnings'])
            parsed['qualified_scope_pass']=parsed['proof_pass'] and parsed['warnings_match_upstream']
            write(directory/'observation.json',parsed)
            observations.append(dict(label=label,category=parsed['category'],coverage_complete=parsed['coverage_complete'],proof_pass=parsed['proof_pass']))
        write(out/'complete.json',dict(model_calls=0,invocations=len(observations),observations=observations))
    except Exception as e:
        write(out/'failure.json',dict(type=type(e).__name__,message=str(e),model_calls=0));raise

if __name__=='__main__':main()
