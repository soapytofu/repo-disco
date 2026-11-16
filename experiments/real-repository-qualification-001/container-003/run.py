"""Deliberate HTTP/1 transport correction after preserved HTTP/2 cancellation."""
import json,os,shutil,socket,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
sys.path.insert(0,str(BASE))
from baseline import capture,checked,digest,write,pins

def main():
    assert os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower()
    pins()
    for n,h in json.loads((ROOT/'manifest.json').read_bytes()).items():assert digest((ROOT/n).read_bytes())==h,n
    out=ROOT/'results';out.mkdir(exist_ok=False)
    env=dict(os.environ);env['GODEBUG']='http2client=0';env['SINGULARITY_CACHEDIR']=str(ROOT/'cache');env['SINGULARITY_TMPDIR']=str(ROOT/'temporary')
    (ROOT/'temporary').mkdir(exist_ok=False)
    write(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),model_calls=0,transport='GODEBUG=http2client=0',parent_phase='container-002',
          source_manifest_sha256=digest((BASE/'source-manifest.json').read_bytes()),manifest_sha256=digest((ROOT/'manifest.json').read_bytes())))
    try:
        image=ROOT/'runtime.sif';assert not image.exists()
        pin=json.loads((ROOT/'image-pin.json').read_bytes())
        checked('singularity-version',['singularity','--version'],ROOT,out,env)
        checked('pull-image',['singularity','pull',str(image),pin['reference']],ROOT,out,env,900)
        write(out/'image.json',dict(reference=pin['reference'],sif_sha256=digest(image.read_bytes()),bytes=image.stat().st_size))
        work=ROOT/'work';shutil.copytree(BASE/'upstream/dafny-vmc',work)
        args=['singularity','exec','--cleanenv','--bind',str(BASE)+':'+str(BASE),'--pwd',str(work),
              '--env','DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1',str(image)]
        dafny=BASE/'toolchains/dafny-vmc/unpacked/dafny/dafny'
        z3=BASE/'toolchains/dafny-vmc/unpacked/dafny/z3/bin/z3-4.12.1'
        write(out/'binary-pins.json',{str(p.relative_to(BASE)):digest(p.read_bytes()) for p in [dafny,z3,BASE/'toolchains/dafny-vmc/dafny.zip']})
        checked('dafny-version',args+[str(dafny),'--version'],ROOT,out,env)
        checked('z3-version',args+[str(z3),'-version'],ROOT,out,env)
        assert (out/'dafny-version/stdout.txt').read_text().strip()=='4.4.0+707b18acee078b3aa4d84c0590a980966bf22428'
        assert 'Z3 version 4.12.1' in (out/'z3-version/stdout.txt').read_text()
        capture('native-baseline',args+[str(dafny),'verify','dfyconfig.toml','docs/dafny/ExamplesRandom.dfy','tests/Tests.dfy',
                 'tests/TestsRandom.dfy','--resource-limit','20000','--log-format','csv'],ROOT,out,env,900)
        for f in work.rglob('*.csv'):
            target=out/'native-baseline/csv'/f.relative_to(work);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
        source=next(p for p in json.loads((BASE/'source-manifest.json').read_bytes()) if p['id']=='dafny-vmc')
        assert all(digest((work/n).read_bytes())==h for n,h in source['files'].items())
        write(out/'complete.json',dict(source_unchanged=True,model_calls=0,baseline_success_not_inferred=True))
    except Exception as e:
        write(out/'failure.json',dict(type=type(e).__name__,message=str(e),model_calls=0));raise

if __name__=='__main__':main()
