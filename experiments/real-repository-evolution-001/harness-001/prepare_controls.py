"""Host-only construction of a new, explicit control bundle; no verifier calls."""
from pathlib import Path
import json
import shutil
import dafny_gate as gate

ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parents[1]

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def main():
    destination = ROOT / 'controls'
    destination.mkdir(exist_ok=False)
    parent = EXPERIMENTS / 'internal-contract-propagation-001/fixtures/extracted_entry_return_migration'
    warning = EXPERIMENTS / 'witness-map-diagnostic-001/parents/alias_comprehension/candidate'
    units = {name: file for name, file in [
        ('Kernel.Erase (well-formedness)', 'Kernel.dfy'),
        ('Kernel.Entry (well-formedness)', 'Kernel.dfy'),
        ('Kernel.Exclude (well-formedness)', 'Kernel.dfy'),
        ('Helper.Transfer (correctness)', 'Helper.dfy'),
        ('Client.Target (correctness)', 'Client.dfy')]}
    cases = []
    for identifier, variant, expected in [
        ('correct', 'paired_repair', 'VERIFIED'),
        ('helper_unproved', 'wrong_helper_implementation', 'PROOF_FAILURE'),
        ('client_unproved', 'helper_only', 'PROOF_FAILURE'),
        ('omitted_failure', 'paired_repair', 'PROOF_FAILURE'),
        ('parse_failure', 'paired_repair', 'PARSE_FAILURE'),
        ('resolution_failure', 'paired_repair', 'RESOLUTION_OR_TYPE_FAILURE'),
        ('warning_only', None, 'WARNING_ONLY')]:
        source = warning if variant is None else parent / variant
        files = {p.name: p.read_bytes() for p in sorted(source.glob('*.dfy'))}
        original = gate.hashes(files)
        targets = dict(units)
        mutation = None
        if identifier == 'omitted_failure':
            files['Detached.dfy'] = b'module Detached { method Broken() ensures false { } }\n'
            targets['Detached.Broken (correctness)'] = 'Detached.dfy'
            mutation = 'Added failing Detached.Broken with no include from All or its dependency closure.'
        elif identifier == 'parse_failure':
            files['Client.dfy'] += b'!\n'
            mutation = 'Appended an invalid top-level token to Client.dfy.'
        elif identifier == 'resolution_failure':
            assert files['Client.dfy'].count(b'H.Transfer(m,key)') == 1
            files['Client.dfy'] = files['Client.dfy'].replace(b'H.Transfer(m,key)', b'H.Unknown(m,key)')
            mutation = 'Replaced the single H.Transfer call by undefined H.Unknown.'
        elif identifier == 'warning_only':
            targets = {}
            for module, names in {'Api':['ObservePut','ObserveDrop','Equal'], 'ClientA':['Target'],
                    'ClientB':['Target'], 'HelperA':['Prove'], 'HelperB':['Prove'],
                    'Ops1':['PutKeys','DropKeys'], 'Ops2':['PutAt','DropAt']}.items():
                for name in names: targets[f'{module}.{name} (correctness)'] = module + '.dfy'
            for module, name in [('Kernel','Drop'), ('Api','ObserveDrop'), ('Api','Equal'),
                                 ('Ops2','PutAt'), ('Ops2','DropAt')]:
                targets[f'{module}.{name} (well-formedness)'] = module + '.dfy'
        profile = dict(schema=gate.SCHEMA, language='dafny', dafny_version=gate.DAFNY_VERSION,
                       z3_version=gate.Z3_VERSION, task_id=identifier, source_sha256=gate.hashes(files),
                       entry='All.dfy', verification_inputs=sorted(files), include_edges=gate.include_edges(files),
                       required_units=targets, unitless_files={'All.dfy':'Host-owned include-only file; exact bytes pinned.'},
                       scope_review='Seven declared control scopes in controls.json; not an upstream project qualification.',
                       edit_policy='No edits during this control run. Exact trusted source pins required. Model editing disabled.')
        gate.validate_scope(files, profile)
        target = destination / identifier; target.mkdir()
        for name, raw in files.items(): (target / name).write_bytes(raw)
        write_json(target / 'profile.json', profile)
        cases.append(dict(id=identifier, expected=expected, path=f'controls/{identifier}',
                          parent=str(source.relative_to(EXPERIMENTS.parent)), parent_sha256=original,
                          deliberate_mutation=mutation, required_units=targets))
    write_json(ROOT / 'controls.json', dict(cases=cases, model_calls=0,
        native_verifications=15, purpose='Gate validation on development controls, not real-repository qualification.',
        entry_only_control='omitted_failure is staged twice with explicit all-file inputs plus once with entry-only inputs.'))
    policy = EXPERIMENTS / 'internal-contract-repair-001/protocol'
    copied = ROOT / 'policy'; copied.mkdir()
    for name in ['body_guard.py','registry.json','inherited/typed_guard.py','inherited/syntax_guard.py']:
        dest = copied / name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(policy / name, dest)
    tasks = json.loads((EXPERIMENTS / 'internal-contract-repair-001/fixtures-and-controls/tasks.json').read_bytes())
    task = next(t for t in tasks if t['semantic_instance'] == 'extracted_entry_return_migration')
    write_json(copied / 'task.json', task)
    seed = EXPERIMENTS / 'internal-contract-repair-001/fixtures-and-controls' / task['template_path']
    shutil.copytree(seed, copied / 'seed')
    write_json(ROOT / 'fixture-manifest.json', {p.relative_to(ROOT).as_posix():gate.sha(p.read_bytes())
        for p in sorted(ROOT.rglob('*')) if p.is_file() and
        (p.is_relative_to(destination) or p.is_relative_to(copied) or p.name=='controls.json')})

if __name__ == '__main__': main()
