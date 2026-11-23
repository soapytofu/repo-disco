"""Compute-only native evidence capture, one attempt per declared case.

This collector does not score or accept candidates and makes no provider calls.
Every source, command, result, CSV and resource record is retained, including
frontend and resource failures. No native retry or limit escalation is provided.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(obj, stream, indent=2, sort_keys=True)
        stream.write('\n')


def sources(folder):
    found = {}
    for path in sorted(folder.rglob('*.dfy')):
        assert not path.is_symlink(), str(path)
        found[path.relative_to(folder).as_posix()] = sha(path.read_bytes())
    assert found, 'No source files'
    return found


def capture(argv, cwd, seconds, stream_paths=None):
    started = time.monotonic()
    handles = [p.open('xb') for p in stream_paths] if stream_paths else []
    process = subprocess.Popen(argv, cwd=cwd, stdout=handles[0] if handles else subprocess.PIPE,
                               stderr=handles[1] if handles else subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        out, err = process.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            out, err = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            out, err = process.communicate(timeout=10)
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass
    finally:
        for handle in handles: handle.close()
    if handles: out,err=(p.read_bytes() for p in stream_paths)
    return dict(exit_code=process.returncode, elapsed_seconds=time.monotonic()-started,
                timeout=timed_out), out, err


def tool_fingerprint(config):
    folder = Path(config['toolchain_root']).expanduser()
    files = {p.relative_to(folder).as_posix():sha(p.read_bytes())
             for p in sorted(folder.rglob('*')) if p.is_file()}
    assert files, 'Missing pinned toolchain directory'
    solver = Path(config['solver']).expanduser()
    assert solver.is_file()
    return dict(dafny_package_sha256=files, solver_sha256=sha(solver.read_bytes()))


def run(config_path, output, expected_freeze_sha):
    assert os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower()
    assert os.environ.get('SLURM_CPUS_PER_TASK') == '1'
    config = json.loads(config_path.read_bytes())
    assert config['schema'] == 'dafny-library-qualification-v1'
    package = ROOT.parent
    freeze_path = ROOT / config['freeze']
    assert sha(freeze_path.read_bytes()) == expected_freeze_sha
    freeze = json.loads(freeze_path.read_bytes())
    for name, digest in freeze['files'].items():
        assert sha((package/name).read_bytes()) == digest, name
    output.mkdir(exist_ok=False)
    exe = Path(config['dafny']).expanduser()
    assert exe.is_file()
    tool_meta, out, err = capture([str(exe), '--version'], ROOT, 30)
    (output/'tool-version.stdout').write_bytes(out)
    (output/'tool-version.stderr').write_bytes(err)
    version = out.decode().strip()
    assert tool_meta['exit_code'] == 0 and not tool_meta['timeout'] and not err
    assert version == config['expected_version'], (version, config['expected_version'])
    solver_meta, solver_out, solver_err = capture([config['solver'], '--version'], ROOT, 30)
    assert solver_meta['exit_code'] == 0 and not solver_meta['timeout'] and not solver_err
    (output/'solver-version.stdout').write_bytes(solver_out)
    toolchain = dict(dafny_version=version, executable_sha256=sha(exe.read_bytes()),
                     solver_version=solver_out.decode().strip(),
                     source_pin=config['source_pin'], **tool_fingerprint(config))
    assert tool_fingerprint(config) == config['expected_tool_fingerprint']
    host = dict(job_id=os.environ['SLURM_JOB_ID'], hostname=socket.gethostname(),
                partition=os.environ.get('SLURM_JOB_PARTITION'),
                cpus_per_task=int(os.environ['SLURM_CPUS_PER_TASK']))
    write(output/'environment.json', dict(toolchain=toolchain, host=host,
        config_sha256=sha(config_path.read_bytes()), freeze_sha256=sha(freeze_path.read_bytes())))
    results = []
    for case in config['cases']:
        destination = output/case['id']; destination.mkdir()
        template = package/case['workspace_dir']
        workspace = destination/'workspace'
        shutil.copytree(template, workspace)
        before = sources(workspace)
        assert before == case['source_sha256'], case['id']
        source_args = case['command_files']
        assert source_args and len(set(source_args)) == len(source_args)
        assert set(source_args) <= set(before)
        argv = [str(exe), 'verify'] + config['options'] + source_args
        rawdir = destination/'raw'; rawdir.mkdir()
        resources = rawdir/'resources.txt'
        invocation = ['/usr/bin/time','-v','-o',str(resources.resolve())] + argv
        meta, stdout, stderr = capture(invocation, workspace, config['wall_seconds'],
                                      [rawdir/'stdout.txt',rawdir/'stderr.txt'])
        csvs = sorted(workspace.rglob('*.csv'))
        for path in csvs:
            relative = path.relative_to(workspace)
            target = rawdir/'csv'/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
        after = sources(workspace)
        after_toolchain = dict(toolchain, **tool_fingerprint(config))
        raw_hashes = {p.relative_to(rawdir).as_posix():sha(p.read_bytes())
                      for p in sorted(rawdir.rglob('*')) if p.is_file()}
        record = dict(schema='dafny-library-native-record-v1',
            run_id=host['job_id']+':'+case['id'], origin='analyst_qualification',
            source_before_sha256=before, source_after_sha256=after, argv=argv,
            toolchain=toolchain, toolchain_after=after_toolchain,
            raw_sha256=raw_hashes, attempts=1, model_calls=0,
            host=host, **meta)
        write(destination/'record.json', record)
        row = dict(case=case['id'], **meta, csv_files=len(csvs), source_unchanged=before==after)
        results.append(row); print(json.dumps(row), flush=True)
        assert before == after, 'Verifier source changed'
        assert toolchain == after_toolchain, 'Verifier installation changed'
        if meta['timeout'] or meta['exit_code'] < 0 or meta['exit_code'] >= 128:
            break
    write(output/'summary.json', dict(project=config['project'], cases=results,
        native_calls=len(results), model_calls=0, all_planned_cases_recorded=len(results)==len(config['cases'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--expected-freeze-sha', required=True)
    args = parser.parse_args()
    run(args.config, args.output, args.expected_freeze_sha)
