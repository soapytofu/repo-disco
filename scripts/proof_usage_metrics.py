"""Resolve recorded call aliases and measure reuse across distinct client targets.

Recorded call order is not a proof-prerequisite graph. Repeated model trials do
not count as additional target proofs. Input task IDs must identify one target
lemma each (as in composition-pilot-001).
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path


def measure(rows, task_maps):
    lemma_targets = defaultdict(set)
    target_providers = defaultdict(set)
    trials = []
    seen = set()
    for row in rows:
        sequence = row['sequence']
        if sequence in seen:
            raise ValueError('Duplicate trial sequence')
        seen.add(sequence)
        task = row['task']
        if task not in task_maps:
            raise ValueError('Unknown task')
        if row['outcome'] != 'SUCCESS':
            continue
        bindings = task_maps[task]['imports']['Client']
        resolved = []
        for call in row.get('called_symbols', []):
            parts = call.split('.')
            if len(parts) != 2 or parts[0] not in bindings or not parts[1]:
                raise ValueError('Unresolvable recorded call: ' + call)
            symbol = bindings[parts[0]] + '.' + parts[1]
            resolved.append(symbol)
            # Symbols are scoped to repository task: same spelling in another
            # repository is NOT enough evidence of a shared definition.
            lemma_targets[(task, symbol)].add(task + ':Client')
            target_providers[task + ':Client'].add(bindings[parts[0]])
        trials.append({'sequence': sequence, 'task': task,
                       'condition': row['condition'], 'resolved_calls': resolved,
                       'distinct_provider_count': len({c.rsplit('.', 1)[0] for c in resolved})})
    lemmas = [{'repository_task': task, 'symbol': symbol, 'distinct_client_targets': sorted(targets),
               'client_target_count': len(targets)}
              for (task, symbol), targets in sorted(lemma_targets.items())]
    return {'schema_version': 1, 'successful_trials': len(trials),
            'distinct_client_targets': len(target_providers),
            'trial_calls': trials, 'lemma_usage': lemmas,
            'target_provider_coverage': {t: sorted(v) for t, v in sorted(target_providers.items())},
            'lemmas_shared_by_multiple_targets': sum(v['client_target_count'] >= 2 for v in lemmas),
            'scope_note': 'One client target per repository task; repeats are not new targets. This corpus cannot test shared-proof reuse across multiple clients.',
            'proof_prerequisite_depth': None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', type=Path)
    args = parser.parse_args()
    run = args.experiment / 'pilot-001'
    ledger = json.loads((run / 'ledger.json').read_text())
    maps = {p.parent.name: json.loads(p.read_text()) for p in (run / 'inputs').glob('*/dependency-map.json')}
    print(json.dumps(measure(ledger['completed'], maps), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
