"""Validate explicit import maps and measure structural depth (not proof depth).

Usage: python scripts/repository_map_metrics.py MAP.json --root Client
No Dafny execution, network requests, or model calls.
"""
import argparse
import json
from pathlib import Path


def measure(mapping, root):
    if not isinstance(mapping, dict):
        raise ValueError('Map must be an object')
    modules = mapping.get('modules')
    imports = mapping.get('imports')
    if (not isinstance(modules, list) or not modules
            or any(not isinstance(m, str) or not m for m in modules)
            or len(set(modules)) != len(modules)):
        raise ValueError('modules must be unique nonempty strings')
    if not isinstance(imports, dict) or set(imports) != set(modules):
        raise ValueError('imports must have exactly one entry per module')
    if root not in modules:
        raise ValueError('Unknown root module')
    graph = {}
    aliases = 0
    for module, bindings in imports.items():
        if not isinstance(bindings, dict):
            raise ValueError('Import bindings must be objects')
        for alias, target in bindings.items():
            if not isinstance(alias, str) or not alias:
                raise ValueError('Import aliases must be nonempty strings')
            if not isinstance(target, str) or target not in modules:
                raise ValueError('Unknown import target')
        graph[module] = set(bindings.values())
        aliases += len(bindings)
    visiting, depths = set(), {}

    def depth(module):
        if module in visiting:
            raise ValueError('Import graph contains a cycle')
        if module not in depths:
            visiting.add(module)
            depths[module] = max((1 + depth(n) for n in graph[module]), default=0)
            visiting.remove(module)
        return depths[module]

    # Reject cycles even in components unreachable from the chosen client.
    for module in modules:
        depth(module)
    reachable, pending = set(), [root]
    while pending:
        module = pending.pop()
        if module not in reachable:
            reachable.add(module)
            pending.extend(graph[module])
    return {
        'schema_version': 1,
        'edge_semantics': 'importer_to_imported',
        'root': root,
        'module_count': len(modules),
        'alias_binding_count': aliases,
        'distinct_import_edge_count': sum(map(len, graph.values())),
        'root_import_depth': depths[root],
        'reachable_modules': sorted(reachable),
        'unreachable_modules': sorted(set(modules) - reachable),
        'module_import_depths': dict(sorted(depths.items())),
        'proof_depth': None,
        'proof_depth_note': 'Not inferable from import structure alone',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    try:
        result = measure(json.loads(args.map.read_text()), args.root)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
