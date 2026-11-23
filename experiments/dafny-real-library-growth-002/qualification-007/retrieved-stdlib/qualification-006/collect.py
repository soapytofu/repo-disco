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
REFERENCE_IDS = {'stdlib': ['splice-alternative']}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def safe_path(name):
    return (isinstance(name, str) and name and not name.startswith(('/', '-'))
            and '\\' not in name and all(part not in {'', '.', '..'} for part in name.split('/'))
            and all(32 <= ord(c) < 127 for c in name))


def validate_config(config, profiles=None):
    profiles = profiles or json.loads((ROOT/'tool-profiles.json').read_bytes())
    project = config.get('project')
    require(project in REFERENCE_IDS and config.get('schema') == 'dafny-growth-reference-qualification-v1'
            and config.get('references_only') is True, 'Reference-only project configuration required')
    require(config.get('freeze') == 'freezes/'+project+'.json', 'Wrong project freeze')
    profile = profiles[project]
    require(all(config.get(k) == v for k, v in profile.items()), 'Pinned tool/profile settings changed')
    require(set(config) == set(profile) | {'schema','freeze','references_only','cases'},
            'Unexpected configuration options')
    cases = config.get('cases')
    require(isinstance(cases,list) and [c.get('id') for c in cases] == REFERENCE_IDS[project],
            'Exactly the existing splice alternative is dispatchable')
    require(len({c.get('task_id') for c in cases}) == 1, 'Only the splice task is dispatchable')
    for case in cases:
        require(set(case) == {'id','task_id','role','workspace_dir','source_sha256','command_files'}
                and case['role'] == 'reference' and isinstance(case['task_id'],str)
                and case['task_id'] and safe_path(case['workspace_dir']), 'Malformed reference case')
        source_map = case['source_sha256']
        require(isinstance(source_map,dict) and source_map and all(safe_path(name)
                and name.endswith('.dfy') and isinstance(digest,str) and len(digest) == 64
                and all(c in '0123456789abcdef' for c in digest) for name,digest in source_map.items()),
                'Exact source hashes required')
        inputs = case['command_files']
        require(isinstance(inputs,list) and len(inputs) == len(set(inputs))
                and set(inputs) == set(source_map), 'References require every source as an explicit input')
    return config


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
        require(not path.is_symlink() and all(not p.is_symlink() for p in path.parents), str(path))
        found[path.relative_to(folder).as_posix()] = sha(path.read_bytes())
    require(found, 'No source files')
    return found


def native_environment():
    # Test keys before reading a value. Native verifiers/version commands have
    # no reason to inherit provider credentials or alternative SDK config.
    blocked={'BOTO_CONFIG','BOTO_PATH','BEDROCK_API_KEY'}
    return {key:os.environ[key] for key in os.environ
            if not key.startswith('AWS_') and key not in blocked}


def capture(argv, cwd, seconds, stream_paths=None):
    started = time.monotonic()
    handles = [p.open('xb') for p in stream_paths] if stream_paths else []
    process = None
    timed_out = False
    try:
        process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
            stdout=handles[0] if handles else subprocess.PIPE,
            stderr=handles[1] if handles else subprocess.PIPE, start_new_session=True,
            env=native_environment())
        try:
            out, err = process.communicate(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            try: os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            try:
                out, err = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                out, err = process.communicate(timeout=10)
    finally:
        if process is not None:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            if process.poll() is None: process.wait(timeout=10)
        for handle in handles:
            handle.flush();os.fsync(handle.fileno());handle.close()
    if handles: out,err=(p.read_bytes() for p in stream_paths)
    return dict(exit_code=process.returncode, elapsed_seconds=time.monotonic()-started,
                timeout=timed_out), out, err


def tool_fingerprint(config):
    folder = Path(config['toolchain_root']).expanduser()
    files = {}
    for p in sorted(folder.rglob('*')):
        require(not p.is_symlink(), 'Symlink toolchain member')
        if p.is_file():files[p.relative_to(folder).as_posix()] = sha(p.read_bytes())
    require(files, 'Missing pinned toolchain directory')
    solver = Path(config['solver']).expanduser()
    require(solver.is_file() and not solver.is_symlink(), 'Missing regular pinned solver')
    return dict(dafny_package_sha256=files, solver_sha256=sha(solver.read_bytes()))


def capture_version(executable, flag, output, label):
    meta, out, err = capture([str(executable), flag], ROOT, 30)
    (output/(label+'-version.stdout')).write_bytes(out)
    (output/(label+'-version.stderr')).write_bytes(err)
    write(output/(label+'-version.json'), dict(argv=[str(executable), flag], **meta))
    require(meta['exit_code'] == 0 and not meta['timeout'] and not err,
            label+' version check failed; streams preserved')
    return out.decode().strip()


def run(config_path, output, expected_freeze_sha):
    require(os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower(),
            'Native capture requires a Slurm compute allocation')
    require(os.environ.get('SLURM_CPUS_PER_TASK') == '1', 'Exactly one CPU required')
    config = validate_config(json.loads(config_path.read_bytes()))
    package = ROOT.parent
    freeze_path = ROOT / config['freeze']
    require(sha(freeze_path.read_bytes()) == expected_freeze_sha, 'Runtime freeze differs')
    freeze = json.loads(freeze_path.read_bytes())
    require(freeze.get('schema') == 'dafny-growth-reference-freeze-v1'
            and freeze.get('project') == config['project']
            and freeze.get('reference_case_ids') == REFERENCE_IDS[config['project']],
            'Runtime dispatch scope differs')
    for name, digest in freeze['files'].items():
        require(safe_path(name) and sha((package/name).read_bytes()) == digest, name)
    require(config_path.resolve() == (ROOT/'configs'/f"{config['project']}.json").resolve()
            and output.resolve() == (ROOT/f"output-{config['project']}").resolve(),
            'Canonical project config/output required')
    output.mkdir(exist_ok=False)
    exe = Path(config['dafny']).expanduser()
    require(exe.is_file(), 'Pinned verifier absent')
    version = capture_version(exe, '--version', output, 'tool')
    require(version == config['expected_version'], 'Verifier version differs')
    solver_version = capture_version(config['solver'], '-version', output, 'solver')
    toolchain = dict(dafny_version=version, executable_sha256=sha(exe.read_bytes()),
                     solver_version=solver_version,
                     source_pin=config['source_pin'], **tool_fingerprint(config))
    require(tool_fingerprint(config) == config['expected_tool_fingerprint'], 'Toolchain fingerprint differs')
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
        require(before == case['source_sha256'], 'Reference source differs: '+case['id'])
        source_args = case['command_files']
        require(source_args and len(set(source_args)) == len(source_args)
                and set(source_args) == set(before), 'Incomplete explicit reference scope')
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
        require(before == after, 'Verifier source changed')
        require(toolchain == after_toolchain, 'Verifier installation changed')
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
