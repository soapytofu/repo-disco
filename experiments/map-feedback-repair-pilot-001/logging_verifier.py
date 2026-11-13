"""Exact measured verify function; called only on compute or with fake process."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import time

def sha(raw): return hashlib.sha256(raw).hexdigest()

def verify(files):
    assert set(files)=={'Kernel.dfy','Api.dfy','Ops1.dfy','Ops2.dfy','HelperA.dfy','HelperB.dfy','ClientA.dfy','ClientB.dfy','All.dfy'}
    assert all(isinstance(b,bytes) for b in files.values())
    command=['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy']
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='repodisco-targets-') as directory:
        folder=Path(directory)
        for name,raw in files.items():(folder/name).write_bytes(raw)
        p=subprocess.run(command,cwd=folder,capture_output=True,text=True)
        csv_files={str(path.relative_to(folder)):path.read_bytes().decode() for path in sorted(folder.rglob('*.csv'))}
    return dict(command=command,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,
                elapsed_seconds=time.monotonic()-started,source_sha256={n:sha(b) for n,b in files.items()},
                csv=csv_files,csv_sha256={n:sha(s.encode()) for n,s in csv_files.items()},model_calls=0,attempts=1)
