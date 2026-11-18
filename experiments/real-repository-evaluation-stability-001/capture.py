"""Pinned upstream baseline, compute only, no providers or model calls."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import socket
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parent
PROJECTS={'dafny-vmc','vest'}

def digest(raw):return hashlib.sha256(raw).hexdigest()
def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')
def pins():
    for name,h in json.loads((ROOT/'runtime-manifest.json').read_bytes()).items():assert digest((ROOT/name).read_bytes())==h,name
    for project in json.loads((ROOT/'source-manifest.json').read_bytes()):
        for name,h in project['files'].items():assert digest((ROOT/'upstream'/project['id']/name).read_bytes())==h,(project['id'],name)
def capture(label,args,cwd,out,env,limit):
    folder=out/label;folder.mkdir()
    command=['/usr/bin/time','-v','-o',str(folder/'resources.txt'),'timeout','-k','10s',str(limit)+'s',*map(str,args)]
    start=time.monotonic()
    with (folder/'stdout.txt').open('xb') as stdout,(folder/'stderr.txt').open('xb') as stderr:
        p=subprocess.run(command,cwd=cwd,env=env,stdout=stdout,stderr=stderr,timeout=limit+25)
    record=dict(command=list(map(str,args)),cwd=str(cwd),exit_code=p.returncode,elapsed_seconds=time.monotonic()-start,
                timeout=p.returncode==124,model_calls=0,attempts=1,
                artifacts={n:digest((folder/n).read_bytes()) for n in ['stdout.txt','stderr.txt','resources.txt']})
    write(folder/'record.json',record);print(json.dumps(dict(label=label,exit_code=p.returncode,seconds=record['elapsed_seconds'])),flush=True)
    return record
def checked(label,args,cwd,out,env,limit=60):
    record=capture(label,args,cwd,out,env,limit)
    if record['exit_code']!=0:raise RuntimeError(label+' failed; see preserved logs')
    return record
def download(label,url,path,out,env,expected=None):
    assert not path.exists()
    checked(label,['curl','--proto','=https','--tlsv1.2','--fail','--location','--silent','--show-error','--retry','0','--max-time','240',url,'-o',path],ROOT,out,env,250)
    h=digest(path.read_bytes());write(out/(label+'-artifact.json'),dict(url=url,sha256=h,bytes=path.stat().st_size,expected_sha256=expected))
    if expected is not None:assert h==expected,'Release digest mismatch'
def unpack(path,dest):
    dest.mkdir()
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            name=PurePosixPath(member.filename);assert not name.is_absolute() and '..' not in name.parts
            assert (member.external_attr>>16)&0o170000!=0o120000,'Symlink in executable archive'
            target=dest/name
            if member.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(member))
            mode=(member.external_attr>>16)&0o777
            if mode:target.chmod(mode)

def main(project):
    assert project in PROJECTS and os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower()
    pins();out=ROOT/'results'/project;out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ);tools=ROOT/'toolchains'/project;tools.mkdir(parents=True,exist_ok=False)
    work=ROOT/'work'/project;work.parent.mkdir(exist_ok=True);shutil.copytree(ROOT/'upstream'/project,work)
    write(out/'environment.json',dict(project=project,job_id=os.environ['SLURM_JOB_ID'],hostname=socket.gethostname(),
          runtime_sha256=digest((ROOT/'runtime-manifest.json').read_bytes()),source_manifest_sha256=digest((ROOT/'source-manifest.json').read_bytes()),model_calls=0))
    try:
        if project=='dafny-vmc':
            url='https://github.com/dafny-lang/dafny/releases/download/v4.4.0/dafny-4.4.0-x64-ubuntu-20.04.zip'
            archive=tools/'dafny.zip';download('download-dafny',url,archive,out,env);unpack(archive,tools/'unpacked')
            dafny=tools/'unpacked/dafny/dafny';assert dafny.exists();dafny.chmod(dafny.stat().st_mode|0o111)
            checked('dafny-version',[dafny,'--version'],work,out,env)
            assert (out/'dafny-version/stdout.txt').read_text().strip().startswith('4.4.0+')
            for i,z3 in enumerate(sorted((tools/'unpacked').rglob('bin/z3'))):
                z3.chmod(z3.stat().st_mode|0o111);checked('z3-version-'+str(i),[z3,'--version'],work,out,env)
            checked('dafny-help',[dafny,'verify','--help'],work,out,env)
            args=[dafny,'verify','dfyconfig.toml','docs/dafny/ExamplesRandom.dfy','tests/Tests.dfy','tests/TestsRandom.dfy',
                  '--resource-limit','20000','--log-format','csv']
            record=capture('native-baseline',args,work,out,env,900)
            for file in sorted(work.rglob('*.csv')):
                target=out/'native-baseline/csv'/file.relative_to(work);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
        else:
            metadata=json.loads((work/'verus.json').read_bytes())
            assert metadata['version']=='0.2026.10.26.d17fbd0' and metadata['rust']=='1.99.1'
            url='https://github.com/verus-lang/verus/releases/download/release/'+metadata['version']+'/verus-'+metadata['version']+'-x86-linux.zip'
            archive=tools/'verus.zip';download('download-verus',url,archive,out,env,metadata['artifacts']['x86-linux']['sha256']);unpack(archive,tools/'unpacked')
            candidates=list((tools/'unpacked').rglob('version.json'));assert len(candidates)==1
            verus=candidates[0].parent;version=json.loads(candidates[0].read_bytes());write(out/'verus-release-version.json',version)
            assert version['verus']['commit']==metadata['commit'] and version['verus']['version']==metadata['version']
            # Bootstrap a versioned rustup into task-owned homes; never changes shell startup or existing installations.
            url='https://static.rust-lang.org/rustup/archive/1.28.2/x86_64-unknown-linux-gnu/rustup-init'
            checksum=tools/'rustup-init.sha256';download('download-rustup-sha',url+'.sha256',checksum,out,env)
            expected=checksum.read_text().split()[0];assert len(expected)==64
            installer=tools/'rustup-init';download('download-rustup',url,installer,out,env,expected);installer.chmod(0o700)
            env.update(RUSTUP_HOME=str(tools/'rustup'),CARGO_HOME=str(tools/'cargo'),RUSTUP_MAX_RETRIES='0',CARGO_NET_RETRY='0')
            checked('install-rustup',[installer,'-y','--no-modify-path','--default-toolchain','none','--profile','minimal'],work,out,env,180)
            env['PATH']=str(verus)+':'+str(tools/'cargo/bin')+':'+env['PATH']
            checked('install-rust',['rustup','toolchain','install',metadata['rust'],'--profile','minimal'],work,out,env,600)
            env['RUSTUP_TOOLCHAIN']=metadata['rust']
            checked('rustc-version',['rustc','--version','--verbose'],work,out,env)
            checked('cargo-version',['cargo','--version'],work,out,env)
            checked('verus-version',[verus/'verus','--version','--output-json'],work,out,env)
            checked('z3-version',[verus/'z3','--version'],work,out,env)
            checked('cargo-verus-help',['cargo','verus','verify','--help'],work,out,env)
            for package in ['vest_lib','vest_dev']:
                target=ROOT/'targets'/('native-'+package)
                args=['cargo','verus','verify','-p',package,'--locked','--check-toolchain','--target-dir',target,'--','--expand-errors','--output-json','--time-expanded']
                record=capture('native-'+package,args,work,out,env,900)
        upstream=next(p for p in json.loads((ROOT/'source-manifest.json').read_bytes()) if p['id']==project)
        assert all(digest((work/n).read_bytes())==h for n,h in upstream['files'].items()),'Baseline mutated source'
        pins();write(out/'complete.json',dict(model_calls=0,source_unchanged=True,baseline_success_not_inferred=True))
    except Exception as error:
        write(out/'failure.json',dict(type=type(error).__name__,message=str(error),model_calls=0))
        raise

if __name__=='__main__':main(sys.argv[1])
