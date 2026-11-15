"""Construct only this new policy's registry from immutable, local seed metadata."""
from pathlib import Path
import argparse
import importlib.util
import json

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT.parent / 'fixtures-and-controls'
spec = importlib.util.spec_from_file_location('method_registry_guard', ROOT / 'body_guard.py')
guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)


def build():
    raw = (INPUTS / 'tasks.json').read_bytes()
    tasks = json.loads(raw, object_pairs_hook=guard.unique)
    entries = {}
    for task in tasks:
        tid = task['task_id']
        if tid in entries:
            raise ValueError('Duplicate task identifier')
        sources = {p.name: p.read_bytes() for p in (INPUTS / task['template_path']).glob('*.dfy')}
        if set(sources) != set(guard.FILES) or {n: guard.sha(b) for n, b in sorted(sources.items())} != task['source_sha256']:
            raise ValueError('Template snapshot changed')
        boundaries = {}
        for name in guard.EDITABLE_FILES:
            guard.validate_rules(task['file_rules'][name], name)
            span = task['body_boundaries'][name]
            raw_source = sources[name]; start, end = span['start'], span['end']
            prefix, body, suffix = raw_source[:start], raw_source[start:end], raw_source[end:]
            if not prefix.endswith(b'  {\n') or suffix != b'  }\n}\n':
                raise ValueError('Unexpected fixed method span')
            if guard.sha(prefix + b'<BODY>\n' + suffix) != span['protected_sha256']:
                raise ValueError('Protected span hash differs')
            # Balanced source and exact closing suffix make the host span explicit.
            level = 0
            for char in body:
                level += (char == ord('{')) - (char == ord('}'))
                if level < 0:
                    raise ValueError('Body escapes its method span')
            if level:
                raise ValueError('Unbalanced source body')
            boundaries[name] = {**span, 'prefix_sha256': guard.sha(prefix),
                                'body_sha256': guard.sha(body), 'suffix_sha256': guard.sha(suffix)}
        entries[tid] = {'binding': {key: task[key] for key in guard.BINDING_KEYS},
                        'boundaries': boundaries}
    return {'schema': 'repodisco-method-body-registry-v1', 'policy_id': guard.POLICY_ID,
            'source_tasks_sha256': guard.sha(raw), 'tasks': entries}


def serialized():
    return (json.dumps(build(), indent=2) + '\n').encode()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true', help='Create once; never overwrite different registry bytes')
    args = parser.parse_args(); raw = serialized(); target = ROOT / 'registry.json'
    if args.write and not target.exists():
        with target.open('xb') as stream:
            stream.write(raw)
    if target.read_bytes() != raw:
        raise SystemExit('Existing registry differs; a deliberate new policy revision is required')
    print(json.dumps({'registry_sha256': guard.sha(raw), 'tasks': len(build()['tasks']), 'exact': True}))
