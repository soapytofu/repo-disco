"""One namespace-revised Dafny reference; no Vest, controls or model execution."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import socket

ROOT = Path(__file__).resolve().parent
PROJECTS = ('dafny-vmc',)
STAGES = {'dafny-vmc': dict(cpus=1, memory_gb=2, minutes=30)}


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def check_pins(base, pins):
    for name, value in pins.items():
        p = PurePosixPath(name)
        require(not p.is_absolute() and '..' not in p.parts and '\\' not in name,
                'Unsafe pinned path: ' + name)
        target = base / name
        current = target
        while current != base:
            require(not current.is_symlink(), 'Symlink in pinned path: ' + name)
            current = current.parent
        require(not base.is_symlink(), 'Symlink at pin root')
        require(sha(target) == value, 'Pinned bytes changed: ' + name)


def project_sources(project, root=ROOT):
    require(project in PROJECTS, 'Unknown project')
    return next(p for p in read(root / 'qualification/source-manifest.json')
                if p['id'] == project)['files']


def base_profile(project, root=ROOT):
    require(project in PROJECTS, 'Unknown project')
    return read(root / 'qualification/coverage-001/profile.json')


def reference(project, root=ROOT, case_id=None):
    plan = read(root / 'plan.json')
    require(project in PROJECTS, 'Unknown project')
    expected = plan['references'][project]
    require(case_id in (None, expected), 'Controls are frozen but not executable in phase one')
    matches = [e for e in plan['catalog'][project] if e['id'] == expected]
    require(len(matches) == 1 and matches[0]['phase_one_eligible'] is True,
            'Reference scope differs')
    return matches[0]


def validate_inputs(root=ROOT):
    plan = read(root / 'plan.json')
    require(plan['model_calls'] == 0 and plan['native_invocations_authorized_in_this_runtime'] == 1,
            'Invocation scope differs')
    require(plan['controls_execution_enabled'] is False and
            plan['remaining_controls_gate']['dispatch_available'] is False and
            plan['remaining_controls_gate']['count'] == 11 and plan['model_policy_frozen'] is False and
            plan['old_model_body_policy_compatible'] is False,
            'Control or model scope was enabled')
    require(plan['references'] == {'dafny-vmc': 'pair-reference'} and
            set(plan['catalog']) == {'dafny-vmc'} and set(plan['resources']) == {'dafny-vmc'},
            'Reference selection differs')
    require(plan['excluded_projects'] == ['vest'], 'Excluded project changed')
    require({p.name for p in (root / 'inputs').iterdir()} == {'dafny-vmc'},
            'Unexpected project input')
    require([p['id'] for p in read(root / 'qualification/source-manifest.json')] == ['dafny-vmc'],
            'Unexpected source project')
    require(set(read(root / 'tool-image-pins.json')) == {'container-003'}, 'Unexpected tool image')
    for project, count in [('dafny-vmc', 1)]:
        cases = plan['catalog'][project]
        require(len(cases) == count and len({e['id'] for e in cases}) == count,
                'Control catalog differs')
        require(sum(e['phase_one_eligible'] for e in cases) == 1, 'More than one executable reference')
        require({p.name for p in (root / 'inputs' / project / 'overlays').iterdir()} == {'pair-reference'},
                'Unexpected reference/control input')
        for entry in cases:
            folder = root / 'inputs' / project / 'overlays' / entry['id']
            check_pins(folder, entry['overlay_sha256'])
            actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
            require(actual == set(entry['overlay_sha256']), 'Unexpected overlay input')
        require(base_profile(project, root)['source_sha256'] == project_sources(project, root),
                'Baseline source identity differs')
        resource = plan['resources'][project]
        require(resource['cpus'] == 1 and resource['job_minutes'] == STAGES[project]['minutes'],
                'Resource scope differs')
    require(plan['resources']['dafny-vmc']['resource_limit'] == 100000 and
            plan['resources']['dafny-vmc']['native_wall_seconds'] == 300, 'Dafny budget differs')
    require(plan['resources']['dafny-vmc']['memory_gb'] == 2, 'Memory scope differs')
    return plan


def validate_package(root=ROOT):
    runtime = read(root / 'runtime-freeze.json')
    require(runtime['model_calls'] == 0 and runtime['native_invocations'] == 1 and
            runtime['controls_released'] is False, 'Runtime scope differs')
    check_pins(root, runtime['files'])
    return validate_inputs(root)


def compute_environment(project):
    require(project in PROJECTS, 'Unknown project')
    require(os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower(),
            'Compute allocation required')
    require(int(os.environ.get('SLURM_CPUS_PER_TASK', '0')) == 1, 'One CPU allocation required')
    require(os.environ.get('SLURM_JOB_PARTITION') in ('test', 'shared'), 'Unexpected partition')
    return dict(project=project, job_id=os.environ['SLURM_JOB_ID'], host=socket.gethostname(),
                partition=os.environ['SLURM_JOB_PARTITION'], cpus=1, execution_root=str(ROOT))
