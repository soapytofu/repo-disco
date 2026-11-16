"""Deliberate missing-cc correction; same source, Verus, Rust and dependency lock."""
import json,os,shutil,socket,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;PREVIOUS=BASE/'vest-container-002'
sys.path.insert(0,str(BASE))
from baseline import capture,checked,digest,write,pins

def main():
    assert os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower()
    pins()
    for n,h in json.loads((ROOT/'manifest.json').read_bytes()).items():assert digest((ROOT/n).read_bytes())==h,n
    out=ROOT/'results';out.mkdir(exist_ok=False)
    env=dict(os.environ);env.update(GODEBUG='http2client=0',SINGULARITY_CACHEDIR=str(ROOT/'cache'),SINGULARITY_TMPDIR=str(ROOT/'temporary'))
    (ROOT/'temporary').mkdir()
    write(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),model_calls=0,manifest_sha256=digest((ROOT/'manifest.json').read_bytes()),parent_phase='vest-container-002',correction='Supply cc; retain same installed Verus/Rust, source and Cargo.lock; offline dependency reuse with fresh target directories'))
    try:
        tools=PREVIOUS/'tools';metadata=json.loads((BASE/'upstream/vest/verus.json').read_bytes())
        archive=tools/'verus.zip';assert digest(archive.read_bytes())==metadata['artifacts']['x86-linux']['sha256']
        closure={}
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                if item.is_dir():continue
                h=digest(z.read(item));assert digest((tools/'unpacked'/item.filename).read_bytes())==h,item.filename;closure[item.filename]=h
        write(out/'verus-tool-closure.json',closure)
        image=ROOT/'runtime.sif';assert not image.exists()
        pin=json.loads((ROOT/'image-pin.json').read_bytes())
        checked('pull-image',['singularity','pull',str(image),pin['reference']],ROOT,out,env,1200)
        write(out/'image.json',dict(reference=pin['reference'],sif_sha256=digest(image.read_bytes()),bytes=image.stat().st_size))
        work=ROOT/'work';shutil.copytree(BASE/'upstream/vest',work)
        old=json.loads((PREVIOUS/'results/invocation-prefix.json').read_bytes())['prefix']
        assert old[-1]==str(BASE/'container-003/runtime.sif')
        prefix=list(old);prefix[-1]=str(image);prefix[prefix.index('--pwd')+1]=str(work)
        checked('cc-version',prefix+['cc','--version'],ROOT,out,env)
        checked('rustc-version',prefix+['rustc','--version','--verbose'],ROOT,out,env)
        checked('verus-version',prefix+[str(tools/'unpacked/verus-x86-linux/verus'),'--version','--output-json'],ROOT,out,env)
        checked('z3-version',prefix+[str(tools/'unpacked/verus-x86-linux/z3'),'-version'],ROOT,out,env)
        assert (out/'rustc-version/stdout.txt').read_bytes()==(PREVIOUS/'results/rustc-version/stdout.txt').read_bytes()
        assert (out/'verus-version/stdout.txt').read_bytes()==(PREVIOUS/'results/verus-version/stdout.txt').read_bytes()
        assert (out/'z3-version/stdout.txt').read_bytes()==(PREVIOUS/'results/z3-version/stdout.txt').read_bytes()
        write(out/'invocation-prefix.json',dict(prefix=prefix))
        for package in ['vest_lib','vest_dev']:
            target=ROOT/('target-'+package);assert not target.exists()
            capture('native-'+package,prefix+['cargo','verus','verify','-p',package,'--locked','--offline','--check-toolchain','--target-dir',str(target),'--','--expand-errors','--output-json','--time-expanded'],ROOT,out,env,1200)
        project=next(p for p in json.loads((BASE/'source-manifest.json').read_bytes()) if p['id']=='vest')
        assert all(digest((work/n).read_bytes())==h for n,h in project['files'].items())
        write(out/'complete.json',dict(model_calls=0,source_unchanged=True,baseline_success_not_inferred=True))
    except Exception as e:
        write(out/'failure.json',dict(type=type(e).__name__,message=str(e),model_calls=0));raise

if __name__=='__main__':main()
