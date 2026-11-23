"""Offline exact prompt construction after the reviewed native-control gate."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'execution-001'))
from runtime import TASK_ORDER, canonical, read_json, require, save, save_bytes, sha, validate_scope
from allocation import validate_frozen_budget

SYSTEM='You are extending a Dafny library component under fixed contracts. Return exactly one JSON object with exactly one key, "body", whose string value contains only the replacement body. Do not include a new signature, surrounding method/function braces, imports, declarations, or changes to other files.'
INSTRUCTIONS='''Implement the marked body so that the entire supplied verification scope passes the pinned Dafny verifier. All source files other than that body are fixed. Preserve the public contracts, specification helpers, return types, imports and termination clauses exactly. You may call the supplied APIs and use ordinary Dafny statements/expressions, loops, invariants, assertions, calc blocks and reveal where the language permits. No new declarations, assume/admit/axiom/expect, attributes or decreases * are allowed. A direct implementation is permitted; API-call presence is measured separately from verification. You receive one attempt, no later verifier feedback and no repair opportunity. Return the complete body, including every proof assertion needed. Escape newlines and quotes correctly in JSON. The editable body is a method statement sequence or a function expression as indicated below; omit the host-owned outer braces and marker comments.'''


def pinned(root,entry):
    path=root/entry['path']
    require(path.is_file() and not path.is_symlink() and sha(path.read_bytes())==entry['sha256'],'Preparation pin differs: '+entry['path'])
    return path.read_bytes()


def prepare(inputs_path, output):
    inputs=read_json(inputs_path)
    require(inputs.get('schema')=='dafny-varied-pilot-preparation-v1','Wrong preparation schema')
    require(set(inputs['tasks'])==set(TASK_ORDER),'Exactly four tasks required')
    gate=json.loads(pinned(ROOT,inputs['control_gate']))
    require(gate.get('all_expected_match') is True and gate.get('model_calls')==0
            and gate.get('status')=='PASS','Actual native-control gate required')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    relative=output.relative_to(ROOT).as_posix()
    settings=inputs['settings']
    scope=dict(schema='dafny-library-independent-extension-scope-v1',
        batch_id='dafny-real-library-growth-002-execution-001',max_calls=8,
        independent_trials=True,adaptive_expansion=False,settings=settings,
        execution_enabled=False,authorization_issued=False,
        projects={},slots=[],renderer='pilot/render.py',runtime_inputs=[],
        execution_binding=read_json(ROOT/'execution-001/execution-binding.json'),
        preparation_input_sha256=sha(Path(inputs_path).read_bytes()),
        interpretation='Four independent additions to fixed selected component snapshots; two fresh responses per task, not two-stage current-run growth.')
    runtime_inputs={inputs_path.relative_to(ROOT).as_posix(),inputs['control_gate']['path'],
        'execution-001/ops.py','execution-001/test_ops.py','execution-001/model.sbatch',
        'execution-001/execution-binding.json','execution-001/budget-snapshot.json',
        'pilot/test_render.py','pilot/prepare.py','pilot/render.py'}
    for task in TASK_ORDER:
        spec=inputs['tasks'][task]
        task_gate=gate.get('tasks',{}).get(task)
        require(isinstance(task_gate,dict) and task_gate.get('qualified_success') is True
                and task_gate.get('all_controls_match') is True, 'Matching task-level qualification gate required')
        required_pins={spec['edit_profile']['path']:spec['edit_profile']['sha256'],
                       spec['native_profile']['path']:spec['native_profile']['sha256']}
        required_pins.update({pin['path']:pin['sha256'] for pin in spec['base_sources'].values()})
        require(all(task_gate.get('input_files',{}).get(name)==digest for name,digest in required_pins.items()),
                'Task/native/edit/base inputs are not bound to the reviewed gate')
        edit=json.loads(pinned(ROOT,spec['edit_profile']))
        native=json.loads(pinned(ROOT,spec['native_profile']))
        require(edit['project']==task and edit['stage']==1 and edit['parent_requirement'] is None,
                'Independent protected-body profile required')
        require(native['project']==task and native['stage']==1 and native['inventory_status']=='qualified',
                'Task must have actual qualified native profile')
        require(native['verification_inputs']==edit['verification_inputs'],'Native/edit input order differs')
        sources={name:pinned(ROOT,pin) for name,pin in spec['base_sources'].items()}
        require({name:sha(raw) for name,raw in sources.items()}==edit['base_source_sha256'],'Exact fixed base differs')
        text=INSTRUCTIONS+'\n\nTask: '+spec['description']+'\nEditable kind: '+edit['addition']['kind']+'\n'
        text+='Pinned verification argv (reference to tool syntax and complete source scope):\n'+json.dumps(native['command'])+'\n'
        text+='\nFixed source files, exact UTF-8 bytes between file delimiters:\n'
        for name in edit['verification_inputs']:
            if name in sources:text+='\n--- FILE '+name+' ---\n'+sources[name].decode('utf-8')+'\n--- END FILE ---\n'
        text+='\n--- NEW FILE '+edit['addition']['path']+' ---\n'+edit['addition']['template_utf8']+'\n--- END NEW FILE ---\n'
        payload=dict(modelId=settings['model_id'],system=[{'text':SYSTEM}],
            messages=[{'role':'user','content':[{'text':text}]}],inferenceConfig=settings['inference_config'])
        payload_path=relative+'/payloads/'+task+'.json'
        save(ROOT/payload_path,payload)
        stage=dict(stage_id=edit['stage_id'],edit_profile=spec['edit_profile']['path'],native_profile=spec['native_profile']['path'],
            base_sources=spec['base_sources'],native_adapter=spec['native_adapter'],exact_payload_path=payload_path,
            target_file=edit['addition']['path'])
        scope['projects'][task]=dict(component=spec['component'],stages={'1':stage})
        runtime_inputs.update([spec['edit_profile']['path'],spec['native_profile']['path'],payload_path])
        runtime_inputs.update(x['path'] for x in spec['base_sources'].values())
    for index,task in enumerate(list(TASK_ORDER)+list(reversed(TASK_ORDER))):
        replicate=1 if index<4 else 2
        scope['slots'].append(dict(id='slot-%02d'%(index+1),project=task,stage=1,replicate=replicate,cohort='pilot',
                                  chain_id=task+'-attempt-'+str(replicate)))
    scope['runtime_inputs']=sorted(runtime_inputs|{relative+'/renderer-inputs.json'})
    validate_scope(scope);validate_frozen_budget(ROOT,scope)
    scope_path=relative+'/scope.json';save(ROOT/scope_path,scope)
    binding_names=(runtime_inputs-{'pilot/render.py'})|{scope_path}
    binding=dict(schema='dafny-library-independent-renderer-inputs-v1',authorization_issued=False,
        scope_path=scope_path,renderer_sha256=sha((ROOT/'pilot/render.py').read_bytes()),
        files={name:sha((ROOT/name).read_bytes()) for name in sorted(binding_names)})
    save(output/'renderer-inputs.json',binding)
    manifest=dict(schema='dafny-varied-prompt-freeze-v1',max_calls=8,independent_trials=True,no_retries=True,
        files={path.relative_to(ROOT).as_posix():sha(path.read_bytes()) for path in sorted(output.rglob('*')) if path.is_file()},
        source_inputs={name:sha((ROOT/name).read_bytes()) for name in sorted(runtime_inputs) if name!=relative+'/renderer-inputs.json'},
        authorization_issued=False)
    save(output/'manifest.json',manifest)
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=prepare(args.inputs.resolve(),args.output.resolve())
    print(json.dumps({'files':len(result['files']),'max_calls':8,'model_calls':0}))
