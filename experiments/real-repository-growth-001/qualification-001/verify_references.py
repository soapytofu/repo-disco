"""Exactly one native reference invocation for one project, on compute only.

Adapted from real-repository-guard-diagnostic-001/verify_candidates.py. The
native capture/parsers are copied unchanged. There is no control dispatch API.
"""
import json
import os
from pathlib import Path
import shutil
import sys

import common as c
from capture import capture, write, digest
from gates.vmc import protocol as dg
from score import observe


def files(root, *, ignore_results=False):
    result = {}
    for p in sorted(root.rglob('*')):
        c.require(not p.is_symlink(), 'Symlink in source or evidence inventory')
        if p.is_file():
            name = p.relative_to(root).as_posix()
            if not (ignore_results and name.startswith('TestResults/')):
                result[name] = digest(p.read_bytes())
    return result


def remote_qualification(root=c.ROOT):
    return root.parents[1] / 'real-repository-qualification-001'


def tool_observation(project, root=c.ROOT):
    q = remote_qualification(root)
    if project == 'dafny-vmc':
        image, closure, tool = ('container-003', 'coverage-001/results/tool-closure.json',
                                q / 'toolchains/dafny-vmc/unpacked')
    else:
        image, closure, tool = ('vest-container-004', 'vest-container-004/results/verus-tool-closure.json',
                                q / 'vest-container-002/tools/unpacked')
    pins = c.read(root / 'qualification' / closure)
    image_expected = c.read(root / 'tool-image-pins.json')[image]['sif_sha256']
    actual_image = c.sha(q / image / 'runtime.sif')
    c.require(actual_image == image_expected, 'Pinned container image changed')
    c.check_pins(tool, pins)
    return dict(project=project, image=str(q / image / 'runtime.sif'), image_sha256=actual_image,
                closure_path=closure, closure_manifest_sha256=c.sha(root / 'qualification' / closure),
                checked_tool_files=len(pins), toolchain=c.base_profile(project, root)['toolchain'])


def make_command(project, work, root=c.ROOT):
    q = remote_qualification(root)
    base = c.base_profile(project, root)
    entry = c.reference(project, root)
    resources = c.read(root / 'plan.json')['resources'][project]
    if project == 'dafny-vmc':
        source_args = sorted(set(base['explicit_sources']) | set(entry['overlay_sha256']))
        logical = ['verify', 'dfyconfig.toml', *source_args, '--resource-limit', '100000', '--log-format', 'csv']
        prefix = ['singularity', 'exec', '--cleanenv', '--bind', str(q.parent) + ':' + str(q.parent),
                  '--pwd', str(work), '--env', 'DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1',
                  str(q / 'container-003/runtime.sif'), str(q / 'toolchains/dafny-vmc/unpacked/dafny/dafny')]
    else:
        prefix = list(c.read(root / 'qualification/vest-container-004/results/invocation-prefix.json')['prefix'])
        original_q = prefix[prefix.index('--bind') + 1].split(':')[0]
        prefix = [x.replace(original_q, str(q)) for x in prefix]
        prefix[prefix.index('--bind') + 1] = str(q.parent) + ':' + str(q.parent)
        prefix[prefix.index('--pwd') + 1] = str(work)
        prefix[-1:-1] = ['--env', 'CARGO_BUILD_JOBS=1']
        logical = ['cargo', 'verus', 'verify', '-p', 'vest_dev', '--locked', '--offline', '--check-toolchain',
                   '--target-dir', '<FRESH_TARGET>', '--', '--expand-errors', '--output-json',
                   '--time-expanded', '--num-threads', '1']
    command = prefix + [str(root / 'targets' / project / entry['id']) if x == '<FRESH_TARGET>' else x
                        for x in logical]
    return command, logical, resources['native_wall_seconds'], base


def profile_for(project, root=c.ROOT):
    entry = c.reference(project, root)
    work = root / 'work' / project / entry['id']
    _, logical, _, base = make_command(project, work, root)
    return dict(project=project, reference=entry,
                source_sha256={**c.project_sources(project, root), **entry['overlay_sha256']},
                logical_command=logical, toolchain=base['toolchain'],
                resources=c.read(root / 'plan.json')['resources'][project],
                baseline_profile_sha256=c.sha(root / 'qualification' /
                    ('coverage-001/profile.json' if project == 'dafny-vmc' else 'vest-coverage-001/profile.json')),
                controls_released=False, model_scope_authorized=False)


def verify_one(project, out, job_id, *, root=c.ROOT, native_capture=capture):
    entry = c.reference(project, root)
    name = entry['id']
    source = root / 'inputs' / project / 'overlays' / name
    c.check_pins(source, entry['overlay_sha256'])
    original = c.project_sources(project, root)
    work = root / 'work' / project / name
    work.parent.mkdir(parents=True, exist_ok=True)
    c.require(not (out / name).exists() and not work.exists() and
              not (root / 'targets' / project / name).exists(), 'Existing work/output: no restart')
    shutil.copytree(remote_qualification(root) / 'upstream' / project, work)
    before = files(work)
    # Preserve the observed parent identity even on mismatch; no native invocation then.
    write(out / 'parent-source-audit.json', dict(expected=original, observed=before, match=before == original))
    c.require(before == original, 'Parent source differs')
    for path in entry['overlay_sha256']:
        target = work / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source / path).read_bytes())
    profile = profile_for(project, root)
    prepared = files(work)
    write(out / 'prepared-source-audit.json', dict(expected=profile['source_sha256'], observed=prepared,
                                                match=prepared == profile['source_sha256']))
    c.require(prepared == profile['source_sha256'], 'Prepared source differs')
    command, logical, limit, base = make_command(project, work, root)
    write(out / 'invocation-intent.json', dict(project=project, case=name, command=command,
          native_wall_seconds=limit, model_calls=0, maximum_native_invocations=1,
          profile_sha256=dg.sha(dg.canonical(profile))))
    native = native_capture(name, command, root, out, dict(os.environ), limit)
    d = out / name
    raw = {n: (d / n).read_bytes() for n in ('stdout.txt', 'stderr.txt', 'resources.txt')}
    if project == 'dafny-vmc':
        for f in sorted(work.rglob('*.csv')):
            n = 'csv/' + f.relative_to(work).as_posix()
            raw[n] = f.read_bytes()
            dest = d / n
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as stream:
                stream.write(raw[n])
    for path in entry['overlay_sha256']:
        target = d / 'overlay' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write((work / path).read_bytes())
    after = files(work, ignore_results=project == 'dafny-vmc')
    write(d / 'profile.json', profile)
    write(d / 'source-after.json', dict(source_sha256=after, match=after == profile['source_sha256']))
    bound = dict(run_id=job_id + ':' + name, profile_sha256=dg.sha(dg.canonical(profile)),
                 source_sha256=prepared, source_after_sha256=after, logical_command=logical,
                 toolchain=base['toolchain'], raw_sha256={n: dg.sha(b) for n, b in sorted(raw.items())},
                 model_calls=0, attempts=1, exit_code=native['exit_code'], elapsed_seconds=native['elapsed_seconds'])
    write(d / 'bound-record.json', bound)
    dg.check_record(bound, profile, job_id + ':' + name, raw)
    try:
        observation = observe(project, native, raw, root)
    except Exception as exc:
        write(d / 'observation-error.json', dict(type=type(exc).__name__, message=str(exc),
              raw_preserved=True, controls_released=False, no_automatic_retry=True))
        raise
    write(d / 'observation.json', observation)
    return dict(project=project, case=name, category=observation['category'],
                reference_ready_for_human_inventory_review=observation['reference_ready_for_human_inventory_review'],
                coverage_complete=observation['coverage_complete'], exit_code=native['exit_code'],
                elapsed_seconds=native['elapsed_seconds'], controls_released=False,
                observation_sha256=c.sha(d / 'observation.json'))


def main():
    c.require(len(sys.argv) == 2 and sys.argv[1] in c.PROJECTS, 'Choose one reference project')
    project = sys.argv[1]
    environment = c.compute_environment(project)
    c.validate_package()
    out = c.ROOT / ('verification-' + project + '-001')
    out.mkdir(exist_ok=False)
    write(out / 'environment.json', dict(**environment, model_calls=0,
          plan_sha256=c.sha(c.ROOT / 'plan.json'), runtime_sha256=c.sha(c.ROOT / 'runtime-freeze.json')))
    try:
        before = tool_observation(project)
        write(out / 'tools-before.json', before)
        row = verify_one(project, out, environment['job_id'])
        after = tool_observation(project)
        write(out / 'tools-after.json', after)
        c.require(before == after, 'Tools changed during verification')
        c.validate_package()
        write(out / 'complete.json', dict(project=project, model_calls=0, native_invocations=1,
              results=[row], controls_released=False, release_requires_explicit_review=True))
    except BaseException as exc:
        write(out / 'failure.json', dict(type=type(exc).__name__, message=str(exc), model_calls=0,
              no_automatic_retry=True, controls_released=False, raw_evidence_preserved=True))
        raise


if __name__ == '__main__':
    main()
