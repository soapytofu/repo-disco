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


def measure_multiclient(rows, repositories, ablations=None):
    """Aggregate audited observations; identities are scoped by repository.

    Evidence strings identify upstream reviewed records; this function does not
    execute proofs or independently attest those records. Ablations, when given,
    must cover every registered helper/target pair, including unaffected targets.
    """
    seen=set();observed=defaultdict(set);successful_targets=set();trial_targets=defaultdict(set);trials=[]
    for row in rows:
        required={'repository','trial','target','outcome','called_symbols','evidence'}
        if not required <= row.keys() or not row['evidence']:raise ValueError('Missing observation evidence')
        repo,target=row['repository'],row['target'];key=(repo,row['trial'],target)
        if repo not in repositories or target not in repositories[repo]['targets']:raise ValueError('Unknown repository/target')
        if key in seen:raise ValueError('Duplicate trial target')
        seen.add(key);trial_targets[(repo,row['trial'])].add(target)
        bindings=repositories[repo]['targets'][target];resolved=[]
        if not isinstance(row['called_symbols'],list):raise ValueError('Calls must be a list')
        for call in row['called_symbols']:
            parts=call.split('.')
            if len(parts)!=2 or parts[0] not in bindings:raise ValueError('Unknown alias')
            symbol=bindings[parts[0]]+'.'+parts[1]
            if symbol not in repositories[repo]['symbols']:raise ValueError('Unknown helper definition')
            resolved.append(symbol)
        if row['outcome']=='SUCCESS':
            successful_targets.add((repo,target))
            for symbol in resolved:observed[(repo,symbol)].add(target)
        trials.append(dict(repository=repo,trial=row['trial'],target=target,outcome=row['outcome'],resolved_calls=resolved,evidence=row['evidence']))
    if {repo for repo,trial in trial_targets}!=set(repositories):raise ValueError('Missing repository observations')
    for (repo,trial),targets in trial_targets.items():
        if targets!=set(repositories[repo]['targets']):raise ValueError('Incomplete client trial')
    dependence=[]
    if ablations is not None:
        matrix={}
        for row in ablations:
            required={'repository','symbol','target','baseline_exit','ablated_exit','evidence'}
            if not required<=row.keys() or not row['evidence']:raise ValueError('Missing ablation evidence')
            repo,symbol,target=row['repository'],row['symbol'],row['target'];key=(repo,symbol,target)
            if repo not in repositories or target not in repositories[repo]['targets'] or symbol not in repositories[repo]['symbols']:raise ValueError('Unknown ablation identity')
            if key in matrix:raise ValueError('Duplicate/conflicting ablation')
            if row['baseline_exit']!=0 or row['ablated_exit'] not in (0,4):raise ValueError('Invalid baseline or non-proof failure')
            matrix[key]=row
        expected={(repo,symbol,target) for repo,spec in repositories.items() for symbol in spec['symbols'] for target in spec['targets']}
        if set(matrix)!=expected:raise ValueError('Incomplete ablation matrix')
        for repo,spec in sorted(repositories.items()):
            for symbol in sorted(spec['symbols']):
                selected=[matrix[(repo,symbol,t)] for t in sorted(spec['targets'])]
                affected=[r['target'] for r in selected if r['ablated_exit']==4]
                dependence.append(dict(repository=repo,symbol=symbol,affected_targets=affected,affected_count=len(affected),evidence=[r['evidence'] for r in selected]))
    usage=[dict(repository=repo,symbol=symbol,distinct_targets=sorted(targets),target_count=len(targets)) for (repo,symbol),targets in sorted(observed.items())]
    return dict(schema_version=2,distinct_successful_targets=len(successful_targets),observed_usage=usage,trial_calls=trials,ablation_dependence=dependence if ablations is not None else None,proof_prerequisite_depth=None,scope_note='Observed calls and fixed-proof contract sensitivity are separate. Repeats are not new targets; equal names across repositories are not shared definitions. No proof minimality or model effect is inferred.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', type=Path)
    parser.add_argument('--multiclient', action='store_true', help='Read an audited multi-client evidence JSON bundle')
    args = parser.parse_args()
    if args.multiclient:
        data=json.loads(args.experiment.read_text())
        print(json.dumps(measure_multiclient(data['observations'],data['repositories'],data.get('ablations')),indent=2,sort_keys=True))
        return
    run = args.experiment / 'pilot-001'
    ledger = json.loads((run / 'ledger.json').read_text())
    maps = {p.parent.name: json.loads(p.read_text()) for p in (run / 'inputs').glob('*/dependency-map.json')}
    print(json.dumps(measure(ledger['completed'], maps), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
