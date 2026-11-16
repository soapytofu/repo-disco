"""Versioned completion of a pinned partial download and isolated container setup."""
import json,os,shutil,socket,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
sys.path.insert(0,str(BASE))
from baseline import capture,checked,download,digest,write,pins,unpack

def main():
    assert os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower()
    pins()
    for n,h in json.loads((ROOT/'manifest.json').read_bytes()).items():assert digest((ROOT/n).read_bytes())==h,n
    out=ROOT/'results';out.mkdir(exist_ok=False)
    env=dict(os.environ);write(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],hostname=socket.gethostname(),model_calls=0,
        source_manifest_sha256=digest((BASE/'source-manifest.json').read_bytes()),manifest_sha256=digest((ROOT/'manifest.json').read_bytes())))
    try:
        container=BASE/'container-003/runtime.sif';image=json.loads((BASE/'container-003/results/image.json').read_bytes())
        assert digest(container.read_bytes())==image['sif_sha256'];write(out/'image.json',image)
        original=BASE/'toolchains/vest/verus.zip';partial=json.loads((ROOT/'partial-pin.json').read_bytes())
        assert original.stat().st_size==partial['bytes'] and digest(original.read_bytes())==partial['sha256']
        tools=ROOT/'tools';tools.mkdir();archive=tools/'verus.zip';shutil.copyfile(original,archive)
        metadata=json.loads((BASE/'upstream/vest/verus.json').read_bytes())
        url='https://github.com/verus-lang/verus/releases/download/release/'+metadata['version']+'/verus-'+metadata['version']+'-x86-linux.zip'
        checked('resume-download',['curl','--proto','=https','--tlsv1.2','--fail','--location','--silent','--show-error','--retry','0',
                   '--http1.1','--max-time','600','--continue-at','-',url,'-o',archive],ROOT,out,env,610)
        actual=digest(archive.read_bytes());write(out/'archive.json',dict(url=url,sha256=actual,bytes=archive.stat().st_size,original_partial=partial))
        assert actual==metadata['artifacts']['x86-linux']['sha256'];unpack(archive,tools/'unpacked')
        files=list((tools/'unpacked').rglob('version.json'));assert len(files)==1
        version=json.loads(files[0].read_bytes());write(out/'verus-release-version.json',version)
        assert version['verus']['version']==metadata['version'] and version['verus']['commit']==metadata['commit']
        verus=files[0].parent
        url='https://static.rust-lang.org/rustup/archive/1.28.2/x86_64-unknown-linux-gnu/rustup-init'
        checksum=tools/'rustup-init.sha256';download('download-rustup-sha',url+'.sha256',checksum,out,env)
        installer=tools/'rustup-init';download('download-rustup',url,installer,out,env,checksum.read_text().split()[0]);installer.chmod(0o700)
        work=ROOT/'work';shutil.copytree(BASE/'upstream/vest',work)
        path=str(verus)+':'+str(tools/'cargo/bin')+':/usr/bin:/bin'
        prefix=['singularity','exec','--cleanenv','--bind',str(BASE)+':'+str(BASE),'--pwd',str(work),
                '--env','RUSTUP_HOME='+str(tools/'rustup'),'--env','CARGO_HOME='+str(tools/'cargo'),
                '--env','PATH='+path,'--env','RUSTUP_MAX_RETRIES=0','--env','CARGO_NET_RETRY=0',str(container)]
        checked('install-rustup',prefix+[str(installer),'-y','--no-modify-path','--default-toolchain','none','--profile','minimal'],ROOT,out,env,180)
        checked('install-rust',prefix+[str(tools/'cargo/bin/rustup'),'toolchain','install',metadata['rust'],'--profile','minimal'],ROOT,out,env,900)
        prefix=prefix[:-1]+['--env','RUSTUP_TOOLCHAIN='+metadata['rust'],str(container)]
        checked('rustc-version',prefix+['rustc','--version','--verbose'],ROOT,out,env)
        checked('cargo-version',prefix+['cargo','--version'],ROOT,out,env)
        checked('verus-version',prefix+[str(verus/'verus'),'--version','--output-json'],ROOT,out,env)
        checked('z3-version',prefix+[str(verus/'z3'),'-version'],ROOT,out,env)
        checked('cargo-verus-help',prefix+['cargo','verus','verify','--help'],ROOT,out,env)
        write(out/'invocation-prefix.json',dict(prefix=prefix))
        for package in ['vest_lib','vest_dev']:
            capture('native-'+package,prefix+['cargo','verus','verify','-p',package,'--locked','--check-toolchain',
              '--target-dir',str(ROOT/('target-'+package)),'--','--expand-errors','--output-json','--time-expanded'],ROOT,out,env,1200)
        project=next(p for p in json.loads((BASE/'source-manifest.json').read_bytes()) if p['id']=='vest')
        assert all(digest((work/n).read_bytes())==h for n,h in project['files'].items())
        assert digest(original.read_bytes())==partial['sha256']
        write(out/'complete.json',dict(model_calls=0,source_unchanged=True,partial_preserved=True,baseline_success_not_inferred=True))
    except Exception as e:
        write(out/'failure.json',dict(type=type(e).__name__,message=str(e),model_calls=0));raise

if __name__=='__main__':main()
