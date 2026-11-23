"""Read-only independent review of the final concrete preparation artifacts.

Only this review directory receives output. No project module is imported and
no subprocess, verifier, model, credentials, network, or allocation is used.
"""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REPO = ROOT.parents[1]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_bytes())


def pins(mapping):
    for name, expected in mapping.items():
        path = ROOT / name
        assert not path.is_symlink() and path.is_file(), name
        assert digest(path.read_bytes()) == expected, name
    return len(mapping)


runtime = read('execution-001/runtime-freeze.json')
assert digest((ROOT/'execution-001/runtime-freeze.json').read_bytes()) == '13f21cc5b329db74761c1b833cc2b7722a8c784c0fea5933fa64c075978ef693'
runtime_count = pins(runtime['files'])
scope = read(runtime['scope'])
manifest = read('pilot/frozen-001/manifest.json')
prompt_files = pins(manifest['files'])
source_inputs = pins(manifest['source_inputs'])
renderer = read('pilot/frozen-001/renderer-inputs.json')
renderer_count = pins(renderer['files'])
assert renderer['renderer_sha256'] == digest((ROOT/'pilot/render.py').read_bytes())
preparation = read('pilot/preparation-inputs.json')
assert preparation['control_gate']['sha256'] == '34977084989b4d14dfa01cdf19bc8e9ab0a2b8479ec3aa00a72933a4e9ee934b'
gate = read(preparation['control_gate']['path'])
assert digest((ROOT/preparation['control_gate']['path']).read_bytes()) == preparation['control_gate']['sha256']
assert gate['status'] == 'PASS' and gate['all_expected_match'] is True
gate_count = pins(gate['input_files'])
assert scope['max_calls'] == 8 and scope['independent_trials'] is True
assert scope['adaptive_expansion'] is False and scope['execution_enabled'] is False
assert scope['authorization_issued'] is False
order = ['stdlib-filter', 'aws-batch', 'stdlib-splice', 'aws-tagged']
assert [s['project'] for s in scope['slots']] == order + order[::-1]
assert len({s['chain_id'] for s in scope['slots']}) == 8
assert all(s['stage'] == 1 for s in scope['slots'])
assert [s['replicate'] for s in scope['slots']] == [1]*4+[2]*4
assert scope['settings'] == preparation['settings'] == {
    'model_id':'global.anthropic.claude-opus-4-5-20251101-v1:0',
    'region':'us-east-1', 'inference_config':{'temperature':1,'maxTokens':4096}}

# Read the two literal prompt paragraphs without importing executable modules.
constants = {}
for node in ast.parse((ROOT/'pilot/prepare.py').read_bytes()).body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id in {'SYSTEM', 'INSTRUCTIONS'}:
            constants[node.targets[0].id] = ast.literal_eval(node.value)
assert set(constants) == {'SYSTEM', 'INSTRUCTIONS'}
tasks = {}
unique_base = set()
base_occurrences = 0
for task in order:
    spec = preparation['tasks'][task]
    stage = scope['projects'][task]['stages']['1']
    edit, native = read(stage['edit_profile']), read(stage['native_profile'])
    assert edit['stage'] == native['stage'] == 1 and edit['parent_requirement'] is None
    assert edit['verification_inputs'] == native['verification_inputs']
    assert set(stage['base_sources']) | {edit['addition']['path']} == set(edit['verification_inputs'])
    assert edit['registrations'] == {}
    new = edit['addition']
    start = new['template_utf8'].index(new['begin_marker'])+len(new['begin_marker'])
    stop = new['template_utf8'].index(new['end_marker'])
    assert not new['template_utf8'][start:stop].strip()
    text = constants['INSTRUCTIONS']+'\n\nTask: '+spec['description']+'\nEditable kind: '+new['kind']+'\n'
    text += 'Pinned verification argv (reference to tool syntax and complete source scope):\n'+json.dumps(native['command'])+'\n'
    text += '\nFixed source files, exact UTF-8 bytes between file delimiters:\n'
    source_hashes = {}
    for name in edit['verification_inputs']:
        if name not in stage['base_sources']:
            continue
        pin = stage['base_sources'][name]
        raw = (ROOT/pin['path']).read_bytes()
        assert digest(raw) == pin['sha256'] == edit['base_source_sha256'][name]
        assert gate['tasks'][task]['input_files'][pin['path']] == pin['sha256']
        text += '\n--- FILE '+name+' ---\n'+raw.decode('utf-8')+'\n--- END FILE ---\n'
        source_hashes[name] = digest(raw)
        unique_base.add(pin['path'])
        base_occurrences += 1
    text += '\n--- NEW FILE '+new['path']+' ---\n'+new['template_utf8']+'\n--- END NEW FILE ---\n'
    actual = read(stage['exact_payload_path'])
    expected = {'modelId':scope['settings']['model_id'], 'system':[{'text':constants['SYSTEM']}],
        'messages':[{'role':'user','content':[{'text':text}]}], 'inferenceConfig':scope['settings']['inference_config']}
    assert actual == expected, task
    assert native['inherited_warnings'] == []
    assert all(item['counted_as_pass'] is False for item in native['unlogged_definitions'])
    tasks[task] = {'payload_sha256':digest((ROOT/stage['exact_payload_path']).read_bytes()),
        'payload_bytes':len((ROOT/stage['exact_payload_path']).read_bytes()),
        'exact_base_files':source_hashes, 'target_path':new['path'],
        'template_sha256':digest(new['template_utf8'].encode()), 'empty_target_body':True,
        'required_native_units':len(native['required_units']),
        'unlogged_definitions':native.get('unlogged_definitions',[]),
        'adapter_wall_seconds':stage['native_adapter']['wall_seconds']}

copies = read('execution-001/copy-provenance.json')['copies']
for item in copies:
    assert item['changed'] is False
    assert digest((REPO/item['source']).read_bytes()) == item['sha256']
    assert (ROOT/'execution-001'/item['file']).read_bytes() == (REPO/item['source']).read_bytes()
for name in ('guard.py','review_native.py'):
    assert (ROOT/'common'/name).read_bytes() == (REPO/'experiments/dafny-real-library-growth-001/common'/name).read_bytes()
receipt = read('execution-001/reviews/offline-003/receipt.json')
assert receipt['exit_code'] == 0 and receipt['model_calls'] == receipt['native_calls'] == 0
for name, expected in receipt['source_sha256'].items():
    assert digest((ROOT/'execution-001'/name).read_bytes()) == expected
for stream in ('stdout','stderr'):
    assert digest((ROOT/'execution-001/reviews/offline-003'/f'{stream}.txt').read_bytes()) == receipt[stream+'_sha256']
assert 'Ran 98 tests' in (ROOT/'execution-001/reviews/offline-003/stderr.txt').read_text()
assert 'test_review_collection' in receipt['argv']
binding = read('execution-001/execution-binding.json')
budget = read('execution-001/budget-snapshot.json')
assert binding == scope['execution_binding']
assert digest((ROOT/binding['budget_snapshot_input']).read_bytes()) == binding['budget_snapshot_sha256']
assert sum(a['maximum_new_requests'] for a in budget['allocations']) == 36
assert budget['maximum_total_new_requests'] == 100 and budget['unallocated_request_ceiling'] == 64
assert budget['allocations'][-1]['maximum_new_requests'] == 8
assert budget['allocations'][-1]['requests_reserved'] == budget['allocations'][-1]['returned_responses'] == 0

inspected = dict(runtime['files'])
for name in ('execution-001/runtime-freeze.json','pilot/frozen-001/manifest.json',
             'execution-001/adaptation-origins.json','execution-001/reviews/offline-003/receipt.json',
             'execution-001/reviews/offline-003/stdout.txt','execution-001/reviews/offline-003/stderr.txt'):
    inspected[name] = digest((ROOT/name).read_bytes())
result = {'status':'PASS_STATIC_REVIEW', 'runtime_sha256':digest((ROOT/'execution-001/runtime-freeze.json').read_bytes()),
    'blocking_findings':[], 'runtime_files':runtime_count, 'prompt_freeze_files':prompt_files,
    'prompt_source_inputs':source_inputs, 'renderer_input_files':renderer_count,
    'control_gate_input_files_checked':gate_count, 'tasks':tasks,
    'base_file_occurrences':base_occurrences,'distinct_base_paths':len(unique_base),
    'unchanged_transport_copies':len(copies), 'unchanged_common_modules':2,
    'existing_tests_reviewed_not_rerun':98,'new_tests_run':0,
    'native_calls':0,'model_calls':0,'network_calls':0,
    'inspection_source_sha256':digest(Path(__file__).read_bytes()),'inspected_sha256':dict(sorted(inspected.items()))}
(HERE/'static-inspection.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({key:result[key] for key in ('status','runtime_sha256','runtime_files','prompt_freeze_files',
    'prompt_source_inputs','renderer_input_files','control_gate_input_files_checked','base_file_occurrences',
    'distinct_base_paths','existing_tests_reviewed_not_rerun','blocking_findings')},indent=2))
