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
CONTROL_IDS = {
    'stdlib': ['filter-alternative','filter-empty','filter-inclusive-threshold','filter-no-tail-pop',
        'filter-wrong-write-index','filter-missing-prefix-invariant','filter-omitted',
        'splice-empty','splice-growth-wrong-order','splice-wrong-replacement-offset',
        'splice-no-tail-pop','splice-missing-growth-call','splice-unproved-seed','splice-omitted'],
    'aws': ['counted-always-failure','counted-missing-tail','counted-omitted','counted-reversed-payloads',
        'counted-unproved-frame','counted-wrong-suffix','tagged-always-failure','tagged-keeps-tag',
        'tagged-omitted','tagged-skips-budget','tagged-skips-tag','tagged-unproved-pair']}
TASK_REFERENCES = {'stdlib-filter':'filter-reference','stdlib-splice':'splice-alternative',
                   'aws-batch':'counted-reference','aws-tagged':'tagged-reference'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def safe_path(name):
    return (isinstance(name, str) and name and not name.startswith(('/', '-'))
            and '\\' not in name and all(part not in {'', '.', '..'} for part in name.split('/'))
            and all(32 <= ord(c) < 127 for c in name))


def validate_config(config, profiles=None, metadata=None):
    profiles = profiles or json.loads((ROOT/'tool-profiles.json').read_bytes())
    project = config.get('project')
    require(project in CONTROL_IDS and config.get('schema') == 'dafny-growth-controls-qualification-v1'
            and config.get('controls_only') is True, 'Fixed remaining-control configuration required')
    require(config.get('freeze') == 'freezes/'+project+'.json', 'Wrong project freeze')
    profile = profiles[project]
    require(all(config.get(k) == v for k, v in profile.items()), 'Pinned tool/profile settings changed')
    require(set(config) == set(profile) | {'schema','freeze','controls_only','cases'},
            'Unexpected configuration options')
    cases = config.get('cases')
    require(isinstance(cases,list) and [c.get('id') for c in cases] == CONTROL_IDS[project],
            'Only the exact remaining controls are dispatchable')
    metadata = metadata or json.loads((ROOT/'control-metadata'/f'{project}.json').read_bytes())
    require([entry['id'] for entry in metadata['cases']]==CONTROL_IDS[project], 'Control metadata order differs')
    require(safe_path(metadata['source_path']), 'Unsafe source-case metadata path')
    workspace_prefix=Path(metadata['source_path']).parent.as_posix()
    require(len({c.get('task_id') for c in cases}) == 2, 'Wrong task grouping')
    for case,original in zip(cases,metadata['cases']):
        require(set(case) == {'id','task_id','role','workspace_dir','source_sha256','command_files'}
                and case['role'] == 'control' and case['task_id'] in TASK_REFERENCES
                and safe_path(case['workspace_dir']), 'Malformed control case')
        expected=dict(id=original['id'],task_id=original.get('task_id',original['project']),role='control',
            workspace_dir=workspace_prefix+'/'+original['workspace_dir'],source_sha256=original['source_sha256'],
            command_files=original['command_files'])
        require(case==expected, 'Control is not an exact fixture projection')
        source_map = case['source_sha256']
        require(isinstance(source_map,dict) and source_map and all(safe_path(name)
                and name.endswith('.dfy') and isinstance(digest,str) and len(digest) == 64
                and all(c in '0123456789abcdef' for c in digest) for name,digest in source_map.items()),
                'Exact source hashes required')
        inputs = case['command_files']
        require(isinstance(inputs,list) and inputs and len(inputs) == len(set(inputs))
                and set(inputs)<=set(source_map), 'Invalid explicit control inputs')
        omitted=set(source_map)-set(inputs)
        require(omitted==set(original.get('omit_from_command',[])), 'Omission differs from fixed control')
        require(bool(omitted)==(original['expected_category']=='COVERAGE_OMISSION'),
                'Only declared omission controls may omit sources')
    return config


def validate_reference_gate(package, root=None, *, allow_synthetic=False):
    """Validate reviewed evidence pins; never construct a gate or profile."""
    import native_scorer as scorer
    package=Path(package);root=Path(root) if root is not None else ROOT
    binding_path=root/'reference-gate-binding.json'
    binding=json.loads(binding_path.read_bytes())
    require(binding.get('schema')=='dafny-growth-controls-gate-binding-v1', 'Unknown gate binding')
    require(not binding.get('synthetic') or allow_synthetic, 'Synthetic gate is ineligible for native dispatch')
    gate_path=binding.get('gate_path')
    require(gate_path=='native-profiles-001/reference-gate.json', 'Unexpected reference gate location')
    raw=(package/gate_path).read_bytes()
    require(sha(raw)==binding.get('gate_sha256'), 'Reference gate differs')
    gate=json.loads(raw)
    require(gate.get('status')=='PASS' and gate.get('all_references_match') is True
            and gate.get('model_calls')==0 and set(gate.get('tasks',{}))==set(TASK_REFERENCES),
            'All four actual reference outcomes must pass review')
    require(not gate.get('synthetic') or allow_synthetic, 'Synthetic reference evidence rejected')
    inputs=gate.get('input_files')
    require(isinstance(inputs,dict) and inputs, 'Gate must bind complete source/raw/profile evidence')
    for name,digest in inputs.items():
        require(safe_path(name), 'Unsafe reference input')
        path=package/name
        require(path.is_file() and not path.is_symlink() and sha(path.read_bytes())==digest,
                'Reference evidence drift: '+name)
    manifests=binding.get('fixture_manifests',{})
    require(set(manifests)=={'stdlib','aws'}, 'Both fixture manifests must be bound')
    for project,entry in manifests.items():
        metadata=json.loads((root/'control-metadata'/f'{project}.json').read_bytes())
        require(safe_path(metadata['source_path']) and metadata['source_path'].startswith(project+'/'),
                'Source metadata is not within its fixed project')
        expected_manifest=(Path(metadata['source_path']).parent/'manifest.json').as_posix()
        require(entry.get('path')==expected_manifest
                and sha((package/entry['path']).read_bytes())==entry.get('sha256')
                and inputs.get(entry['path'])==entry['sha256'], 'Fixture manifest binding differs')
        require(sha((package/metadata['source_path']).read_bytes())==metadata['source_sha256'],
                'Fixed control cases changed after preparation')
    tasks=binding.get('tasks',{})
    require(set(tasks)==set(TASK_REFERENCES), 'Gate task/profile bindings incomplete')
    for task,entry in tasks.items():
        observation=gate['tasks'][task]
        require(observation.get('reference_case_id')==TASK_REFERENCES[task]
                and observation.get('qualified_success') is True,
                'Per-task reference success is missing')
        require(entry.get('reference_case_id')==TASK_REFERENCES[task]
                and entry.get('profile_path')=='native-profiles-001/profiles/'+task+'.json'
                and inputs.get(entry['profile_path'])==entry.get('profile_sha256'),
                'Wrong reference/profile correspondence')
        native_pin=observation.get('native_profile',{})
        require(native_pin.get('path')==entry['profile_path'] and native_pin.get('sha256')==entry['profile_sha256'],
                'Per-task native profile differs from binding')
        evidence=observation.get('input_files')
        require(isinstance(evidence,dict) and evidence
                and all(inputs.get(name)==digest for name,digest in evidence.items()),
                'Per-task evidence must be a complete subset of gate pins')
        edit=observation.get('edit_profile',{})
        require(safe_path(edit.get('path')) and evidence.get(edit['path'])==edit.get('sha256'),
                'Edit profile is not bound to reference evidence')
        base=observation.get('base_sources')
        require(isinstance(base,dict) and base and all(safe_path(logical) and logical.endswith('.dfy')
                and isinstance(pin,dict) and safe_path(pin.get('path'))
                and evidence.get(pin['path'])==pin.get('sha256') for logical,pin in base.items()),
                'Model starting source bindings are incomplete')
        profile=json.loads((package/entry['profile_path']).read_bytes())
        require(native_pin.get('canonical_sha256')==scorer.sha(scorer.canonical(profile)),
                'Canonical native profile identity differs')
        require(profile.get('project')==task and profile.get('inventory_status')=='qualified'
                and isinstance(profile.get('required_units'),dict) and profile['required_units'],
                'Actual qualified native inventory required')
        require(not profile.get('synthetic') or allow_synthetic, 'Synthetic native profile rejected')
        record_pin=observation.get('reference_record',{});record_path=record_pin.get('path')
        require(safe_path(record_path) and evidence.get(record_path)==record_pin.get('sha256'),
                'Exact reference record pin is missing')
        record=json.loads((package/record_path).read_bytes());folder=Path(record_path).parent
        require(record.get('schema')=='dafny-library-native-record-v1'
                and record.get('run_id')==observation.get('native_run_id')
                and record.get('run_id','').endswith(':'+TASK_REFERENCES[task])
                and record_pin.get('canonical_sha256')==scorer.sha(scorer.canonical(record)),
                'Canonical reference observation differs')
        require(record.get('origin')=='analyst_qualification'
                or allow_synthetic and record.get('origin')=='synthetic_offline', 'Wrong reference provenance')
        require(record.get('host',{}).get('cpus_per_task')==1, 'Reference resource provenance differs')
        source_map=record.get('source_before_sha256',{})
        raw_map=record.get('raw_sha256',{})
        source_pins=observation.get('reference_sources',{});raw_pins=observation.get('reference_raw',{})
        require(source_map and raw_map and set(source_pins)==set(source_map) and set(raw_pins)==set(raw_map),
                'Missing reference source/raw inventory')
        sources={};raw_streams={}
        for logical,digest in source_map.items():
            require(safe_path(logical), 'Unsafe reference source path')
            path=(folder/'workspace'/logical).as_posix()
            require(evidence.get(path)==digest and source_pins[logical]==dict(path=path,sha256=digest),
                    'Reference source is absent from gate inputs')
            sources[logical]=(package/path).read_bytes()
        for logical,digest in raw_map.items():
            require(safe_path(logical), 'Unsafe reference raw path')
            path=(folder/'raw'/logical).as_posix()
            require(evidence.get(path)==digest and raw_pins[logical]==dict(path=path,sha256=digest),
                    'Reference raw stream is absent from gate inputs')
            raw_streams[logical]=(package/path).read_bytes()
        pins=scorer.EvidencePins(profile_sha256=scorer.sha(scorer.canonical(profile)),
            record_sha256=scorer.sha(scorer.canonical(record)),
            source_revision_sha256=scorer.sha(scorer.canonical(scorer.hashes(sources))),
            raw_sha256=tuple(sorted(scorer.hashes(raw_streams).items())),
            run_id=record['run_id'],origin=record['origin'])
        reviewed=scorer.review(profile,sources,record,raw_streams,pins,allow_synthetic=allow_synthetic)
        require(reviewed['qualified_success'] and reviewed['proof_coverage_complete']
                and reviewed.get('strict_zero_warning_success') is True,
                'Actual native reference replay is not a strict zero-warning qualified success')
        review_pin=observation.get('native_review',{})
        require(safe_path(review_pin.get('path')) and evidence.get(review_pin['path'])==review_pin.get('sha256'),
                'Saved native review is unpinned')
        saved_review=json.loads((package/review_pin['path']).read_bytes())
        require(scorer.canonical(saved_review.get('replay'))==scorer.canonical(reviewed)
                and saved_review.get('qualified_success') is True
                and saved_review.get('inherited_inventory_unchanged') is True
                and saved_review.get('exact_guarded_reconstruction') is True
                and saved_review.get('source_sha256')==source_map
                and saved_review.get('actual_target_units')==observation.get('actual_target_units')
                and observation.get('raw_fingerprint_sha256')==reviewed['raw_fingerprint_sha256'],
                'Saved native review differs from exact replay')
        inherited={'stdlib-filter':56,'stdlib-splice':58,'aws-batch':77,'aws-tagged':77}[task]
        require(observation.get('inherited_unit_count')==inherited
                and observation.get('named_units')==len(reviewed['units'])
                and len(reviewed['units'])>=inherited and observation.get('actual_target_units'),
                'Reference inventory counts/target observations differ')
    return binding,gate


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
    require(freeze.get('schema') == 'dafny-growth-controls-freeze-v1'
            and freeze.get('project') == config['project']
            and freeze.get('control_case_ids') == CONTROL_IDS[config['project']],
            'Runtime dispatch scope differs')
    for name, digest in freeze['files'].items():
        require(safe_path(name) and sha((package/name).read_bytes()) == digest, name)
    require(config_path.resolve() == (ROOT/'configs'/f"{config['project']}.json").resolve()
            and output.resolve() == (ROOT/f"output-{config['project']}").resolve(),
            'Canonical project config/output required')
    binding,gate=validate_reference_gate(package)
    require(freeze.get('reference_gate_sha256')==binding['gate_sha256'], 'Frozen reference gate differs')
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
        require(before == case['source_sha256'], 'Control source differs: '+case['id'])
        source_args = case['command_files']
        require(source_args and len(set(source_args)) == len(source_args)
                and set(source_args)<=set(before), 'Control command escapes declared scope')
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
