"""Offline evidence review; never invokes a verifier, transport or model."""
import json
import re
from pathlib import Path

import body_guard as policy
from gates.vmc import protocol as dg
from gates.vest import protocol_v2 as vg

ROOT = Path(__file__).resolve().parent
QUAL = ROOT.parent / 'real-repository-qualification-001'
RUNTIME = ROOT / 'runtime-002'
TARGETS = {
    'vmc-swap': 'FisherYates.Model.Swap (well-formedness)',
    'vmc-small-shuffle': 'FisherYates.Equivalence.ShuffleElseClause (correctness)',
    'vest-roundtrip': 'vest_lib::core::proof::impl&%0::C::theorem_serialize_parse_roundtrip',
    'vest-pair': 'vest_lib::combinators::tuple::Pair::theorem_serialize_dps_parse_roundtrip',
}


def read(path):
    return json.loads(path.read_bytes())


def pinmap(root, pins):
    for name, expected in pins.items():
        assert dg.safe_name(name) and dg.sha((root / name).read_bytes()) == expected, name


def raw_files(folder, dafny):
    raw = {n: (folder / n).read_bytes() for n in ['stdout.txt', 'stderr.txt', 'resources.txt']}
    if dafny:
        raw.update({p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted((folder / 'csv').rglob('*.csv'))})
    return raw


def observe(folder, project, required):
    raw = raw_files(folder, project == 'dafny-vmc')
    native = read(folder / 'record.json')
    if project == 'dafny-vmc':
        observation = dg.dafny_observation(native['exit_code'], raw['stdout.txt'], raw['stderr.txt'],
                                           {n: b for n, b in raw.items() if n.startswith('csv/')}, required)
    else:
        observation = vg.verus_observation(native['exit_code'], raw['stdout.txt'], raw['stderr.txt'], required)
    return json.loads(json.dumps(observation)), raw, native


def review():
    # Preserve the initial dependency failure as a distinct, non-mathematical run.
    pinmap(ROOT, read(ROOT / 'runtime-manifest.json'))
    pinmap(ROOT, read(ROOT / 'transfer.json')['files'])
    assert 'FileNotFoundError' in (ROOT / 'controls-61335974.err').read_text()
    assert not (ROOT / 'verification-001').exists()
    pinmap(RUNTIME, read(RUNTIME / 'runtime-manifest.json'))
    pinmap(RUNTIME, read(RUNTIME / 'transfer.json')['files'])
    assert read(ROOT / 'runtime-002-rationale.json')['task_fixture_policy_scorer_unchanged'] is True
    parent = read(ROOT / 'runtime-manifest.json')
    changed = [n for n in parent if (ROOT / n).read_bytes() != (RUNTIME / n).read_bytes()]
    assert changed == ['run_controls.py', 'test_policy.py'], changed
    pinmap(QUAL, read(ROOT / 'qualification-pins.json'))
    for n in ['coverage-001/review-001.json', 'vest-coverage-001/review-001.json']:
        assert (QUAL / n).read_bytes() == (RUNTIME / 'qualification-evidence' / n).read_bytes()

    profiles = {p: read(QUAL / f) for p, f in [('dafny-vmc', 'coverage-001/profile.json'), ('vest', 'vest-coverage-001/profile.json')]}
    projects = {p['id']: p for p in read(QUAL / 'source-manifest.json')}
    tasks = {t['id']: t for t in read(ROOT / 'tasks.json')}
    references = {}
    baseline_observations = {}
    for project, phase, label in [('dafny-vmc', 'coverage-001', 'vmc_baseline-adapter'), ('vest', 'vest-coverage-001', 'baseline-adapter')]:
        pinmap(QUAL / phase, read(QUAL / phase / 'transfer.json')['files'])
        d = QUAL / phase / 'results' / label
        p = read(d / 'profile.json')
        r = read(d / 'bound-record.json')
        required = profiles[project]['required_units' if project == 'dafny-vmc' else 'required']
        o, raw, native = observe(d, project, required)
        dg.check_record(r, p, read(QUAL / phase / 'submission.json')['job_id'] + ':' + label, raw)
        assert p['source_sha256'] == projects[project]['files']
        assert native['exit_code'] == r['exit_code'] and native['attempts'] == 1
        saved = read(d / 'observation.json')
        assert all(saved[k] == v for k, v in o.items())
        assert o['proof_pass'] and saved['qualified_scope_pass'] and saved['warnings_match_upstream']
        assert sorted(o['warnings']) == sorted(profiles[project]['upstream_warnings'])
        baseline_observations[project] = o

    for tid, t in tasks.items():
        original = (QUAL / 'upstream' / t['project'] / t['file']).read_bytes()
        assert dg.sha(original) == t['upstream_file_sha256'] == projects[t['project']]['files'][t['file']]
        reconstructed, receipt = policy.reconstruct(tid, (ROOT / 'fixtures' / tid / 'reference-body.txt').read_text())
        assert reconstructed == original
        o = baseline_observations[t['project']]
        assert o['units'][TARGETS[tid]] in ('Passed', True)
        clients = {n: v for n, v in o['units'].items() if n == t['client_audit_label'] or n.startswith(t['client_audit_label'] + ' (')}
        assert clients and all(v in ('Passed', True) for v in clients.values())
        references[tid] = dict(target=TARGETS[tid], target_pass=True, client_observations=clients,
                               exact_upstream_reconstruction=receipt, reused=True, new_verifier_invocations=0)

    job = read(RUNTIME / 'submission.json')['job_id']
    assert job + '|COMPLETED|' in (RUNTIME / 'accounting.txt').read_text()
    output = RUNTIME / 'verification-001'
    assert (output / 'complete.json').exists() and not (output / 'failure.json').exists()
    env = read(output / 'environment.json')
    assert env['job_id'] == job and env['model_calls'] == 0 and 'login' not in env['host']
    assert env['manifest_sha256'] == dg.sha((RUNTIME / 'runtime-manifest.json').read_bytes())
    remote_qual = Path('/n/home13/sophiezeng/formal-disco/outputs/real-repository-qualification-001')
    remote = remote_qual.parent / ROOT.name / RUNTIME.name
    reviews = {}
    controls = read(ROOT / 'controls.json')
    assert {p.name for p in output.iterdir() if p.is_dir()} == {c['id'] for c in controls}
    for c in controls:
        tid, label = c['task'], c['id']
        t = tasks[tid]; project = t['project']; base = profiles[project]; d = output / label
        candidate = (ROOT / c['fixture']).read_bytes()
        assert dg.sha(candidate) == c['sha256']
        b = t['boundary']; seed = (ROOT / 'fixtures' / tid / 'source.txt').read_bytes()
        assert candidate[:b['start']] == seed[:b['start']] and candidate.endswith(seed[b['end']:])
        body = candidate[b['start']:len(candidate)-len(seed[b['end']:])].decode()
        guarded, receipt = policy.reconstruct(tid, body)
        assert guarded == candidate
        expected_sources = {**projects[project]['files'], t['file']: c['sha256']}
        required = base['required_units' if project == 'dafny-vmc' else 'required']
        if project == 'dafny-vmc':
            logical = ['verify', 'dfyconfig.toml', *sorted(base['explicit_sources']), '--resource-limit', '20000', '--log-format', 'csv']
            prefix = ['singularity', 'exec', '--cleanenv', '--bind', str(remote_qual.parent)+':'+str(remote_qual.parent), '--pwd', str(remote/'work'/label), '--env', 'DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1', str(remote_qual/'container-003/runtime.sif'), str(remote_qual/'toolchains/dafny-vmc/unpacked/dafny/dafny')]
        else:
            logical = ['cargo','verus','verify','-p','vest_dev','--locked','--offline','--check-toolchain','--target-dir','<FRESH_TARGET>','--','--expand-errors','--output-json','--time-expanded','--num-threads','3']
            prefix = read(QUAL/'vest-container-004/results/invocation-prefix.json')['prefix']
            prefix[prefix.index('--bind')+1] = str(remote_qual.parent)+':'+str(remote_qual.parent)
            prefix[prefix.index('--pwd')+1] = str(remote/'work'/label)
            prefix[-1:-1] = ['--env','CARGO_BUILD_JOBS=4']
        p = read(d/'profile.json')
        assert p == dict(task=t, control=c, source_sha256=expected_sources, logical_command=logical, toolchain=base['toolchain'], required=required)
        o, raw, native = observe(d, project, required)
        bound = read(d/'bound-record.json')
        dg.check_record(bound, p, job+':'+label, raw)
        assert native['command'] == prefix+[str(remote/'targets'/label) if x=='<FRESH_TARGET>' else x for x in logical]
        assert native['cwd'] == str(remote) and native['attempts'] == 1 and native['model_calls'] == 0
        assert native['exit_code'] == bound['exit_code'] and native['elapsed_seconds'] == bound['elapsed_seconds']
        assert native['artifacts'] == {n: dg.sha(raw[n]) for n in ['stdout.txt','stderr.txt','resources.txt']}
        assert o == read(d/'observation.json')
        assert o['category'] == c['expected'] == 'PROOF_FAILURE' and not o['proof_pass'], label
        assert o['units'].get(TARGETS[tid]) in ('Failed', False), label
        failed = sorted(n for n,v in o['units'].items() if v in ('Failed', False))
        clients = {n:v for n,v in o['units'].items() if n == t['client_audit_label'] or n.startswith(t['client_audit_label']+' (')}
        rss = re.search(r'Maximum resident set size \(kbytes\): (\d+)', raw['resources.txt'].decode())
        reviews[label] = dict(task=tid, target=TARGETS[tid], target_failed=True, failed_labels=failed,
            category=o['category'], coverage_complete=o['coverage_complete'], full_scope_success=False,
            client_observations=clients, absent_client_is_not_a_pass=not bool(clients),
            guarded_candidate=receipt, exit_code=native['exit_code'], elapsed_seconds=native['elapsed_seconds'],
            max_rss_kib=int(rss[1]) if rss else None, warning_count=len(o['warnings']),
            raw_sha256=bound['raw_sha256'], source_files_bound=len(expected_sources))
    return dict(status='ALL_SIX_NEGATIVE_CONTROLS_MATCH', job_id=job, model_calls=0,
                new_verifier_invocations=6, reused_reference_sites=4, reused_positive_runs=2,
                initial_startup_failure_preserved='61335974', references=references, controls=reviews,
                caution='Induced development failures; reference outcomes reused, not new independent trials. Missing downstream reports are not passing clients.')


if __name__ == '__main__':
    result = review()
    with (ROOT/'controls-review-001.json').open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True); f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('references','controls')}, indent=2))
