"""Build the prospective per-file registry from exact, trusted task templates.

This is construction/review tooling, not a live policy extension mechanism. It
writes only this protocol directory and does not freeze or verify any fixture.
"""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
POLICY_ID = 'repository-repair-selection-bodies-v1-development'
ABI = 'repair-diversity-bodies-v1-development'
EDITABLE = ['HelperA.dfy', 'HelperB.dfy']
EDGE_SET = [['HelperB.Prove', 'HelperA.Prove'], ['ClientA.Target', 'HelperB.Prove'], ['ClientB.Target', 'HelperB.Prove']]


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def read_sources(folder):
    return {path.name: path.read_text() for path in sorted(folder.glob('*.dfy'))}


def parameters(text):
    # Trusted fixture signatures use these four concrete types only.
    result = []
    rest = text.strip()
    while rest:
        match = re.match(r'([a-z][a-zA-Z0-9_]*)\s*:\s*(map\s*<\s*int\s*,\s*int\s*>|set\s*<\s*int\s*>|int|bool)(?:\s*,\s*|\s*$)', rest)
        if not match:
            raise ValueError('Unsupported trusted parameter declaration')
        result.append((match[1], re.sub(r'\s+', '', match[2])))
        rest = rest[match.end():]
    return result


def declarations(source):
    result = {}
    pattern = r'\b(lemma|function|predicate)\s+(?:\{:[^}]+\}\s*)?([A-Za-z][A-Za-z0-9_]*)\(([^)]*)\)'
    for match in re.finditer(pattern, source):
        kind, name, args = match.groups()
        if name in result:
            raise ValueError('Ambiguous trusted declaration')
        params = parameters(args)
        item = dict(kind=kind, parameters=params)
        if kind == 'predicate':
            item['result'] = 'bool'
        elif kind == 'function':
            returned = re.match(r'\s*:\s*(map\s*<\s*int\s*,\s*int\s*>|set\s*<\s*int\s*>|int|bool)', source[match.end():])
            if not returned:
                raise ValueError('Unsupported trusted function return type')
            item['result'] = re.sub(r'\s+', '', returned[1])
        result[name] = item
    return result


def imports(source):
    pairs = re.findall(r'^\s*import\s+([A-Za-z][A-Za-z0-9_]*)\s*=\s*([A-Za-z][A-Za-z0-9_]*(?:`[A-Za-z][A-Za-z0-9_]*)?)\s*$', source, flags=re.M)
    if len(pairs) != len({alias for alias, _ in pairs}):
        raise ValueError('Duplicate trusted import alias')
    return dict(pairs)


def review_sources(files, task):
    """Check declaration signatures and the fixed, direct import graph."""
    if task['editable_files'] != EDITABLE or task['entry'] != 'All.dfy':
        raise ValueError('Unsupported editable set')
    if task.get('dependency_edges', EDGE_SET) != EDGE_SET:
        raise ValueError('Unsupported helper dependency graph')
    for filename in EDITABLE:
        source = files[filename]
        module_name = filename.removesuffix('.dfy')
        if len(re.findall(r'\bmodule\s+' + module_name + r'\s*\{', source)) != 1:
            raise ValueError('Expected helper module missing')
        declared = declarations(source)
        if set(declared) != {'Prove'} or declared['Prove']['kind'] != 'lemma':
            raise ValueError('One protected Prove lemma required per helper')
        rules = task['file_rules'][filename]
        if declared['Prove']['parameters'] != [(name, rules['parameter_types'][name]) for name in rules['variables']]:
            raise ValueError('Parameter rules differ from the immutable source')
        aliases = imports(source)
        if filename == 'HelperA.dfy' and any(target.split('`')[0].startswith('Helper') for target in aliases.values()):
            raise ValueError('HelperA imports another helper')
        if filename == 'HelperB.dfy' and aliases.get('H') != 'HelperA':
            raise ValueError('HelperB must import H = HelperA')
        if any(target.split('`')[0] == 'HelperB' for target in aliases.values()):
            raise ValueError('No helper may import HelperB')
        if any(target.rpartition('`')[2] in {'Internal', 'Hidden'} for target in aliases.values()):
            raise ValueError('Helper imports a hidden provider view')
        for category, signatures in (('calls', rules['call_types']), ('pure', rules['pure_types'])):
            for symbol, signature in signatures.items():
                alias, name = symbol.split('.')
                target = aliases.get(alias)
                if target is None:
                    raise ValueError('Allowed callable has no immutable import')
                module, _, view = target.partition('`')
                provider = files[module + '.dfy']
                declared_provider = declarations(provider).get(name)
                if declared_provider is None:
                    raise ValueError('Allowed callable has no declaration')
                if view:
                    export = re.search(r'^\s*export\s+' + re.escape(view) + r'\s+([^\n]+)', provider, flags=re.M)
                    if export is None or name not in re.findall(r'[A-Za-z][A-Za-z0-9_]*', export[1]):
                        raise ValueError('Allowed callable is hidden in the imported view')
                expected = signature if category == 'calls' else signature['arguments']
                if [typ for _, typ in declared_provider['parameters']] != expected:
                    raise ValueError('Callable rules differ from declared parameter types')
                if category == 'calls' and declared_provider['kind'] != 'lemma':
                    raise ValueError('Statement must call a lemma')
                if category == 'pure' and (declared_provider['kind'] not in {'function', 'predicate'} or declared_provider['result'] != signature['result']):
                    raise ValueError('Pure signature differs from declaration')
    for client in ('ClientA.dfy', 'ClientB.dfy'):
        aliases = imports(files[client])
        if aliases.get('H') != 'HelperB' or any(target.split('`')[0] == 'HelperA' for target in aliases.values()):
            raise ValueError('Immutable clients must import HelperB only')
    return True


def build(families=('witness', 'maps')):
    # Import only after independent fixture declaration checks are available.
    import body_guard as guard
    tasks, inputs = {}, {}
    for family in families:
        base = PARENT / family
        for rel in ('tasks.json', 'cases.json'):
            inputs[f'{family}/{rel}'] = sha((base / rel).read_bytes())
        for rel in ('file_rules.json', 'control-aliases.json'):
            if (base / rel).exists():
                inputs[f'{family}/{rel}'] = sha((base / rel).read_bytes())
        for task in json.loads((base / 'tasks.json').read_text()):
            task_id = task['task_id']
            if task_id in tasks:
                raise ValueError('Duplicate task ID')
            template_path = task.get('template_path', 'templates/' + task_id)
            files = read_sources(base / template_path)
            if guard.hashes(files) != task['source_sha256']:
                raise ValueError('Task template hashes differ from exact sources')
            review_sources(files, task)
            boundaries = {}
            for filename in EDITABLE:
                guard.validate_rules(task['file_rules'][filename], filename)
                prefix, suffix = guard.split_seed(files[filename])
                boundary = dict(start_utf8_byte=len(prefix.encode()), end_utf8_byte=len(prefix.encode()),
                    prefix_sha256=sha(prefix), suffix_sha256=sha(suffix), protected_sha256=sha(prefix + '<EDITABLE_BODY>\n' + suffix))
                source_bound = task['body_boundaries'][filename]
                if (source_bound['start'], source_bound['end'], source_bound['protected_sha256']) != (boundary['start_utf8_byte'], boundary['end_utf8_byte'], boundary['protected_sha256']):
                    raise ValueError('Task boundary differs from the empty template')
                boundaries[filename] = boundary
            entry = {key: task[key] for key in ('task_id', 'semantic_instance', 'sharing', 'depth', 'entry', 'editable_files', 'source_sha256', 'file_rules')}
            entry.update(fixture_family=family, template_path=template_path, body_boundaries=boundaries)
            tasks[task_id] = entry
        for top in ('templates', 'fixtures'):
            for path in sorted((base / top).rglob('*.dfy')):
                inputs[str(path.relative_to(PARENT))] = sha(path.read_bytes())
    data = dict(schema='repository-repair-selection-per-file-registry-v1', policy_id=POLICY_ID,
        adapter_abi=ABI, development_only=True, semantically_verified=False, tasks=tasks)
    raw = (json.dumps(data, indent=2) + '\n').encode()
    (ROOT / 'registry.json').write_bytes(raw)
    (ROOT / 'source-inputs.json').write_text(json.dumps(inputs, indent=2, sort_keys=True) + '\n')
    path = ROOT / 'body_guard.py'
    source = path.read_text()
    changed, count = re.subn(r"(?m)^REGISTRY_SHA256 = '[^']*'$", "REGISTRY_SHA256 = '" + sha(raw) + "'", source)
    if count != 1:
        raise ValueError('Cannot update draft registry digest')
    path.write_text(changed)
    return dict(tasks=len(tasks), pinned_fixture_inputs=len(inputs), registry_sha256=sha(raw),
        model_calls=0, verifier_invocations=0, frozen=False)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--families', nargs='+', choices=['witness', 'maps'], default=['witness', 'maps'])
    args = parser.parse_args()
    print(json.dumps(build(tuple(args.families)), indent=2))
