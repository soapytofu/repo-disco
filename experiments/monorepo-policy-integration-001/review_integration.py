"""Offline witness replay and four-family compatibility catalog; no new runs."""
import collections
import hashlib
import json
from pathlib import Path

import body_guard as guard

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
EXP = ROOT.parent
BALANCED = EXP / 'monorepo-balanced-calibration-pilot-001'
WITNESS = EXP / 'monorepo-calibration-v2-001/remaining-families-001/revision-003'
REASONING = EXP / 'monorepo-reasoning-calibration-pilot-001'
MONOTONE = EXP / 'conditional-monotonicity-001'


def load(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def files(path): return {p.name:p.read_text() for p in path.glob('*.dfy')}
def hashes(source): return {name:guard.digest(text) for name,text in source.items()}
def rel(path): return str(path.relative_to(REPO))
def need(condition, message):
    if not condition: raise ValueError(message)


def replay(target, seeds, task):
    bodies = {}
    for name in task['editable_files']:
        prefix,suffix = guard.split_seed(seeds[name])
        need(target[name].startswith(prefix) and target[name].endswith(suffix),'Protected boundary changed')
        bodies[name] = target[name][len(prefix):-len(suffix)]
    candidate, decision = guard.parse_response(json.dumps(bodies),seeds,task)
    need(candidate==target,'Candidate bytes differ')
    return decision


def review():
    need(sha(BALANCED/'frozen-001/freeze.json')=='df6771bf7ac6e81d2201811a84888ca01156eb6974bee4af85d6e2eb67e49c6f','Frozen balanced plan drift')
    for name, expected in load(BALANCED/'frozen-001/freeze.json')['files'].items():
        need(sha(BALANCED/'frozen-001'/name)==expected,'Frozen balanced file drift')
    need(sha(BALANCED/'model-001-sha256.json')=='fff9c09fee371bd55a19ee7c9a39f71a11e5b09ed9f1db2da88ebd0c0417ebec','Archive manifest drift')
    original_archive={str(p.relative_to(BALANCED/'model-001')):sha(p) for p in (BALANCED/'model-001').rglob('*') if p.is_file()}
    need(original_archive==load(BALANCED/'model-001-sha256.json'),'Original model archive drift')
    need(sha(BALANCED/'frozen-001/preflight-gate.json')=='d4167698fdf3389c57ee82b67aa7945f1644b623cefee1b54871f153e1b8aef0','Preflight gate drift')
    need(sha(BALANCED/'results-review.json')=='5bcc94603309aef0e5e221fff9ba897d29928664cbbb254e945ca46f85a618a3','Original result review drift')
    need(load(BALANCED/'results-review.json')['verified']==29,'Original balanced score changed')
    need(load(REASONING/'results-review.json')['verified']==18,'Original reasoning score changed')

    tasks={task['task_id']:task for task in load(BALANCED/'frozen-001/tasks.json') if task['task_id'].startswith('witness-')}
    controls=[]
    for gate in load(BALANCED/'frozen-001/preflight-gate.json'):
        if gate['task_id'] not in tasks:continue
        need(sha(REPO/gate['review_path'])==gate['review_sha256'],'Reviewed fixture evidence drift')
        task=tasks[gate['task_id']];seeds=files(BALANCED/'frozen-001/tasks'/task['task_id'])
        need(hashes(seeds)==task['source_sha256'],'Seed drift')
        for item in gate['evidence']:
            variant=item['variant'];record=REPO/item['log_path'];evidence=load(record)
            need(sha(record)==item['log_sha256'],'Raw verifier record drift')
            target=files(WITNESS/'fixtures'/task['task_id']/variant)
            need(hashes(target)==item['source_sha256']==evidence['source_sha256'],'Verified source differs')
            rejection=None
            try:replay(target,seeds,task)
            except ValueError as error:rejection=str(error)
            expected_rejection=variant in ('hidden_shortcut','weakened_helper_contract')
            need((rejection is not None)==expected_rejection,'Unexpected parser result: '+variant)
            expected_exit={'success':0,'proof_failure':4,'resolution_failure':2}[item['expected']]
            need(evidence['exit_code']==expected_exit,'Unexpected semantic evidence')
            controls.append(dict(task_id=task['task_id'],variant=variant,admitted=rejection is None,
                                 rejection=rejection,source_sha256=hashes(target),evidence_path=item['log_path'],
                                 evidence_sha256=sha(record),prior_exit_code=evidence['exit_code'],
                                 prior_expected_category=item['expected']))
    responses=[]
    for trial in load(BALANCED/'frozen-001/trials.json'):
        if trial['task_id'] not in tasks:continue
        task=tasks[trial['task_id']];folder=BALANCED/'model-001'/trial['trial_id']
        candidate,decision=guard.parse_response(load(folder/'response.json')['text'],files(BALANCED/'frozen-001/tasks'/task['task_id']),task)
        evidence=load(folder/'verification.json')
        need(candidate==files(folder/'candidate'),'Old response candidate changed')
        need(hashes(candidate)==evidence['source_sha256'],'Old response semantic source changed')
        responses.append(dict(trial_id=trial['trial_id'],task_id=trial['task_id'],admitted=True,
                              original_outcome=load(folder/'result.json')['outcome'],prior_exit_code=evidence['exit_code'],
                              candidate_sha256=hashes(candidate),response_sha256=sha(folder/'response.json'),
                              evidence_path=rel(folder/'verification.json'),evidence_sha256=sha(folder/'verification.json')))
    need(len(controls)==30 and sum(x['admitted'] for x in controls)==24,'Incomplete controls')
    need(len(responses)==8,'Incomplete saved-response replay')

    catalog=[]
    groups=[(load(REASONING/'frozen-001/tasks.json'),REASONING/'frozen-001/tasks'),
            (load(MONOTONE/'tasks.json'),MONOTONE/'fixtures'),(list(tasks.values()),BALANCED/'frozen-001/tasks')]
    for group, parent in groups:
        for task in group:
            seed_path=parent/task['task_id']
            if parent==MONOTONE/'fixtures':seed_path=seed_path/'empty'
            need(hashes(files(seed_path))==task['source_sha256'],'Catalog seed drift')
            rules=guard.policy(task)
            catalog.append(dict(task_id=task['task_id'],semantic_instance=task['semantic_instance'],
                                family='relational' if task['task_id'].startswith('witness-') else task['family'],
                                original_family_label=task['family'],depth_label=task['depth'],sharing=task['sharing'],
                                seed_path=rel(seed_path),seed_sha256=task['source_sha256'],
                                editable_files=task['editable_files'],variables=rules['variables'],
                                lemma_calls=rules['calls'],pure_functions=rules['pure'],split='development',
                                task_metadata_path=rel(parent.parent/'tasks.json') if parent.name=='tasks' else rel(MONOTONE/'tasks.json')))
    need(len(catalog)==32 and len({row['task_id'] for row in catalog})==32,'Catalog identity conflict')
    report=dict(policy_version=guard.VERSION,policy_sha256=sha(ROOT/'body_guard.py'),
                new_model_calls=0,new_verifier_invocations=0,witness_control_replays=30,
                admitted_witness_control_bodies=24,protected_or_hidden_rejections=6,
                saved_witness_responses=8,original_balanced_score='29/32 unchanged',
                original_reasoning_score='18/24 unchanged',witness_controls=controls,saved_responses=responses,
                original_archive_files=len(original_archive),
                interpretation='Compatibility only; prior evidence reused, no scores pooled or changed.')
    catalog_report=dict(status='COMPATIBILITY_LIBRARY_NOT_A_PILOT',new_model_calls=0,
                        policy_version=guard.VERSION,workspace_count=len(catalog),
                        semantic_instances=len({row['semantic_instance'] for row in catalog}),
                        family_workspace_counts=dict(collections.Counter(row['family'] for row in catalog)),
                        tasks=catalog,model_prompts_frozen=False,trial_order_frozen=False,execution_authorized=False)
    (ROOT/'integration-review.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'task-catalog.json').write_text(json.dumps(catalog_report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key not in ('witness_controls','saved_responses')},indent=2))
    print(json.dumps({key:value for key,value in catalog_report.items() if key!='tasks'},indent=2))


if __name__=='__main__':review()
