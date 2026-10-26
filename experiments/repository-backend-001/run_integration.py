"""Compute-only LocalAgenda -> repository snapshot -> real Dafny integration."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'code'))
from agenda import LocalAgenda, Object
from language.dafny.repository import snapshot_agenda_repository, verify_repository


def digest(data): return hashlib.sha256(data).hexdigest()
def save(path, value): path.write_text(json.dumps(value, indent=2)+'\n')

async def main():
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():
        raise SystemExit('Requires Slurm compute node')
    output = ROOT / 'verification-001'
    output.mkdir(exist_ok=False)
    shutil.copytree(ROOT/'fixtures', output/'fixtures')
    shutil.copytree(ROOT/'code', output/'code')
    shutil.copy2(__file__, output/'run_integration.py')
    save(output/'environment.json', dict(host=socket.gethostname(), job_id=os.environ['SLURM_JOB_ID'],
        python=sys.version, dafny=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True).stdout.strip(),
        model_calls=0))
    results = []
    for variant in ['shared_reference','shared_empty','separate_reference','separate_empty']:
        source = {p.name:p.read_bytes() for p in (ROOT/'fixtures'/variant).glob('*.dfy')}
        agenda = LocalAgenda(checkpoint_interval=None, benchmark_codebase_time=None)
        try:
            paths = {}
            for name, content in source.items():
                paths[name] = await agenda.create_object(Object(path='sources/'+name, type='dafny-program',content=content))
            snapshot = await snapshot_agenda_repository(agenda, paths, 'All.dfy')
            assert snapshot == source
            result = verify_repository(snapshot, 'All.dfy', timeout=60)
            assert result.evidence['source_sha256'] == {k:digest(v) for k,v in source.items()}
            for name, content in source.items():
                assert (await agenda.get_object(paths[name])).content == content
            expected = 0 if variant.endswith('reference') else 4
            report = dict(variant=variant,expected_exit=expected,
                matched=result.verification.status==expected, agenda_bytes_unchanged=True,
                **result.evidence)
            save(output/(variant+'.json'),report)
            results.append(report)
            print(variant, result.verification.status, 'expected', expected,flush=True)
        finally:
            agenda._patch_executor.shutdown(wait=True)
    save(output/'summary.json',dict(model_calls=0,checks=len(results),matched=sum(r['matched'] for r in results)))
    if not all(r['matched'] for r in results): raise SystemExit(1)

if __name__ == '__main__': asyncio.run(main())
