"""Read-only completed-batch archive plus an explicitly timed window snapshot."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile
import session_ops as ops

ROOT=Path(__file__).resolve().parent

def fetch(batch_id,sequence):
    reviewed={('repair-diversity-pilot-002',1):ROOT.parent/'repair-diversity-pilot-002',
              ('repository-repair-selection-001',2):ROOT.parent/'repository-repair-selection-001/pilot'}
    assert (batch_id,sequence) in reviewed,'Unreviewed batch archive request'
    dest=reviewed[(batch_id,sequence)]
    assert not (dest/'transfer-001.json').exists(),'Completed transfer already recorded'
    code='BATCH='+repr(batch_id)+'\nSEQUENCE='+repr(sequence)+'\n'+'''import datetime,hashlib,io,json,subprocess,sys,tarfile
session=ROOT/'session-001';batch=session/'runs'/f'{SEQUENCE:04}-{BATCH}'
assert (batch/'completion.json').is_file(),'No durable completion receipt yet'
before=(session/'status.json').read_bytes();state=json.loads(before)
assert BATCH in state['completed_batch_ids'] and state['active_batch_id'] is None,state
ledger_before=(ROOT/'budget/ledger.json').read_bytes()
files={}
def addtree(source,prefix):
 assert source.is_dir() and not source.is_symlink()
 for path in sorted(source.rglob('*')):
  assert not path.is_symlink()
  if path.is_file():files[prefix+'/'+path.relative_to(source).as_posix()]=path.read_bytes()
addtree(batch,'model-001')
addtree(ROOT/'budget','window-evidence-001/budget')
for name in ['events','queue']:
 addtree(session/name,'window-evidence-001/session/'+name)
for path in sorted(session.iterdir()):
 assert not path.is_symlink()
 if path.is_file():files['window-evidence-001/session/'+path.name]=path.read_bytes()
if SEQUENCE==2:
 assert state['completed_batch_ids']==['repair-diversity-pilot-002',BATCH],state
 addtree(ROOT/'admissions','window-evidence-001/admissions')
 for seq,identifier in [(1,'repair-diversity-pilot-002'),(2,BATCH)]:
  path=session/'runs'/f'{seq:04}-{identifier}'/'completion.json'
  assert path.is_file() and not path.is_symlink()
  files['window-evidence-001/completions/'+identifier+'.json']=path.read_bytes()
submission=json.loads((ROOT/'submission-001.json').read_text());job=submission['job_id']
for name in ['scope.json','launch-manifest.json','session.sbatch','session_ops.py','submission-001.json','submission-001.lock',
 'stage-002.json','execution-preflight-001.json',f'session-{job}.log',f'session-{job}.err']:
 path=ROOT/name;assert path.is_file() and not path.is_symlink()
 files['window-evidence-001/'+name]=path.read_bytes()
accounting=subprocess.check_output(['sacct','-j',job,'--format=JobID,State,Elapsed,ExitCode,NodeList','-P'],timeout=12)
files['window-evidence-001/accounting-snapshot.txt']=accounting
assert before==(session/'status.json').read_bytes() and ledger_before==(ROOT/'budget/ledger.json').read_bytes(),'Window changed during snapshot; do not publish a mixed ledger'
assert files['window-evidence-001/budget/ledger.json']==ledger_before
if SEQUENCE==2:
 for seq,identifier in [(1,'repair-diversity-pilot-002'),(2,BATCH)]:
  assert files[f'window-evidence-001/admissions/{seq:06}.json']==(ROOT/'admissions'/f'{seq:06}.json').read_bytes()
  assert files['window-evidence-001/completions/'+identifier+'.json']==(session/'runs'/f'{seq:04}-{identifier}'/'completion.json').read_bytes()
record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),batch_id=BATCH,
 session_still_running=state['phase'] not in ['error','closed'],credential_access=False,
 files={name:hashlib.sha256(data).hexdigest() for name,data in files.items()})
files['window-evidence-001/snapshot-manifest.json']=(json.dumps(record,indent=2,sort_keys=True)+'\\n').encode()
b=io.BytesIO()
with tarfile.open(fileobj=b,mode='w:gz') as tar:
 for name,data in sorted(files.items()):
  info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;tar.addfile(info,io.BytesIO(data))
sys.stdout.buffer.write(b.getvalue())
'''
    raw=ops.remote(code,timeout=90);inventory={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
        for member in tar.getmembers():
            p=PurePosixPath(member.name)
            assert member.isfile() and not p.is_absolute() and '..' not in p.parts
            assert p.parts[0] in ['model-001','window-evidence-001']
            data=tar.extractfile(member).read();path=dest/member.name
            if path.exists():assert path.is_file() and path.read_bytes()==data
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as f:f.write(data)
            inventory[member.name]=hashlib.sha256(data).hexdigest()
    record=dict(compressed_bytes=len(raw),archive_sha256=hashlib.sha256(raw).hexdigest(),files=inventory)
    with (dest/'transfer-001.json').open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(files=len(inventory),compressed_bytes=len(raw),destination=str(dest))))

if __name__=='__main__':
    if len(sys.argv)==1:fetch('repair-diversity-pilot-002',1)
    else:
        assert sys.argv[1:]==['repository-repair-selection-001','2']
        fetch('repository-repair-selection-001',2)
