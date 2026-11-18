"""Offline replay of complete reference evidence; never releases later controls."""
import json
from pathlib import Path
import sys

import common as c
from capture import write
from gates.vmc import protocol as dg
from score import observe
from verify_references import files, make_command, profile_for


def review_verification(project, root=c.ROOT):
    c.validate_package(root)
    entry = c.reference(project, root)
    name = entry['id']
    out = root / ('verification-' + project + '-001')
    env = c.read(out / 'environment.json')
    submission = c.read(root / 'submissions' / (project + '.json'))
    c.require(env['job_id'] == submission['job_id'], 'Job provenance differs')
    c.require(env['project'] == project and env['cpus'] == 1 and env['model_calls'] == 0,
              'Worker scope/resources differ')
    c.require(env['partition'] == submission['partition'] and submission['no_requeue'] is True,
              'Partition/submission provenance differs')
    c.require(env['plan_sha256'] == c.sha(root / 'plan.json') and
              env['runtime_sha256'] == c.sha(root / 'runtime-freeze.json') == submission['runtime_sha256'],
              'Worker or submission package differs')
    c.require({p.name for p in out.iterdir() if p.is_dir()} == {name}, 'Unexpected reference folders')
    original = c.project_sources(project, root)
    c.require(c.read(out / 'parent-source-audit.json') == dict(expected=original, observed=original, match=True),
              'Parent source audit differs')
    expected_profile = profile_for(project, root)
    expected = expected_profile['source_sha256']
    c.require(c.read(out / 'prepared-source-audit.json') == dict(expected=expected, observed=expected, match=True),
              'Prepared source audit differs')
    d = out / name
    profile, bound, native = (c.read(d / n) for n in ('profile.json', 'bound-record.json', 'record.json'))
    raw = {n: (d / n).read_bytes() for n in bound['raw_sha256']}
    dg.check_record(bound, profile, env['job_id'] + ':' + name, raw)
    c.require(profile == expected_profile, 'Reference/source profile differs')
    remote_root = Path(env['execution_root'])
    command, logical, limit, _ = make_command(project, remote_root / 'work' / project / name, root)
    # Remap only the local task's outputs/experiments anchor to the recorded remote anchor.
    command = [x.replace(str(root.parents[1]), str(remote_root.parents[1])) for x in command]
    c.require(native['command'] == command and native['cwd'] == str(remote_root), 'Native command differs')
    c.require(native['model_calls'] == 0 and native['attempts'] == 1 and
              native['exit_code'] == bound['exit_code'] and native['elapsed_seconds'] == bound['elapsed_seconds'],
              'Native result differs')
    c.require(native['timeout'] == (native['exit_code'] == 124), 'Timeout marker differs')
    c.require(native['artifacts'] == {n: dg.sha(raw[n]) for n in ('stdout.txt', 'stderr.txt', 'resources.txt')},
              'Native artifact bindings differ')
    intent = dict(project=project, case=name, command=command, native_wall_seconds=limit, model_calls=0,
                  maximum_native_invocations=1, profile_sha256=dg.sha(dg.canonical(profile)))
    c.require(c.read(out / 'invocation-intent.json') == intent, 'Invocation intent differs')
    c.require(c.read(d / 'source-after.json') == dict(source_sha256=expected, match=True), 'Post-run source differs')
    c.check_pins(d / 'overlay', entry['overlay_sha256'])
    c.require(files(d / 'overlay') == entry['overlay_sha256'], 'Saved overlay has extra/missing bytes')
    before, after = c.read(out / 'tools-before.json'), c.read(out / 'tools-after.json')
    c.require(before == after and before['toolchain'] == c.base_profile(project, root)['toolchain'],
              'Tool identity changed')
    image = 'container-003' if project == 'dafny-vmc' else 'vest-container-004'
    closure = ('coverage-001/results/tool-closure.json' if project == 'dafny-vmc'
               else 'vest-container-004/results/verus-tool-closure.json')
    c.require(before == dict(project=project,
          image=str(remote_root.parents[1] / 'real-repository-qualification-001' / image / 'runtime.sif'),
          image_sha256=c.read(root / 'tool-image-pins.json')[image]['sif_sha256'],
          closure_path=closure, closure_manifest_sha256=c.sha(root / 'qualification' / closure),
          checked_tool_files=len(c.read(root / 'qualification' / closure)),
          toolchain=c.base_profile(project, root)['toolchain']), 'Tool evidence binding differs')
    observation = observe(project, native, raw, root)
    c.require(c.read(d / 'observation.json') == observation, 'Observation replay differs')
    row = dict(project=project, case=name, category=observation['category'],
               reference_ready_for_human_inventory_review=observation['reference_ready_for_human_inventory_review'],
               coverage_complete=observation['coverage_complete'], exit_code=native['exit_code'],
               elapsed_seconds=native['elapsed_seconds'], controls_released=False,
               observation_sha256=c.sha(d / 'observation.json'))
    c.require(c.read(out / 'complete.json') == dict(project=project, model_calls=0, native_invocations=1,
          results=[row], controls_released=False, release_requires_explicit_review=True), 'Summary differs')
    c.require(not (out / 'failure.json').exists() and not list(out.rglob('accepted.json')),
              'Contradictory failure/acceptance record')
    return dict(status='REFERENCE_EVIDENCE_REPLAY_PASSED', project=project, result=row,
                raw_files=files(out), growth_inventory_review=observation['growth_inventory_review'],
                warning_review=observation['warning_review'], native_invocations=1, model_calls=0,
                evidence_valid_does_not_imply_proof_success=True, controls_released=False,
                next_gate='Root must separately pin source-bound outcome and actual unit inventory; no release file is created.')


if __name__ == '__main__':
    c.require(len(sys.argv) == 2 and sys.argv[1] in c.PROJECTS, 'Choose reference project')
    report = review_verification(sys.argv[1])
    write(c.ROOT / ('review-' + sys.argv[1] + '-001.json'), report)
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ('raw_files', 'growth_inventory_review', 'warning_review')}, indent=2))
