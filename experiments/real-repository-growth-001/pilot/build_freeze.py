"""Build/review an unapproved proposal; never construct fictitious live parents."""
from pathlib import Path
import json
import math
import sys
import render as r

ROOT=Path(__file__).resolve().parent

def planned_sizes(root=ROOT):
    grammar=r.read(root/'grammar-spec.json');views=r.read(root/'template-views.json')['stages'];rows=[]
    for entry in r.order():
        text=r.template_text(entry['stage_id'],root)
        if entry['stage']==1:
            exact=r.render_stage1(entry['slot_id'],root)['payload']
            rows.append(dict(slot_id=entry['slot_id'],stage=1,payload_bytes=len(r.encode(exact)),
                             model_input_characters=len(r.SYSTEM)+len(text),measurement='exact_frozen_stage_one_payload'))
        else:
            parent=views[views[entry['stage_id']]['parent']];raw=(root/parent['asset']).read_bytes()
            begin=raw.index(parent['begin'].encode())+len(parent['begin'].encode());end=raw.index(parent['end'].encode())
            removed=len(''.join(parent['removed_prefix_lines']).encode())
            bound=len(raw)-(end-begin)-removed+grammar['max_body_bytes']+1
            language='dafny' if entry['project']=='dafny-vmc' else 'rust'
            wrapper='READ-ONLY PREVIOUS ADDITION '+parent['path']+'\n```'+language+'\n'+'\n```'
            upper_text=text.replace(r.PARENT_TOKEN,wrapper+' '*bound)
            # A planning bound only. JSON escaping can expand each parent source
            # byte by at most six characters; no fake parent payload is emitted.
            base_payload=r.payload(text.replace(r.PARENT_TOKEN,wrapper),root)
            rows.append(dict(slot_id=entry['slot_id'],stage=2,payload_bytes=None,
                payload_bytes_upper_bound=len(r.encode(base_payload))+6*bound,
                model_input_characters=None,model_input_characters_upper_bound=len(r.SYSTEM)+len(upper_text),
                accepted_parent_view_bytes_upper_bound=bound,measurement='future_parent_bounded_rule_only_no_payload'))
    first=sum(row['model_input_characters'] for row in rows if row['stage']==1)
    maximum=first+sum(row['model_input_characters_upper_bound'] for row in rows if row['stage']==2)
    return dict(slots=rows,exact_stage_one_payload_bytes=sum(row['payload_bytes'] for row in rows if row['stage']==1),
                exact_stage_one_model_input_characters=first,
                all_eight_input_characters_upper_bound=maximum,
                all_eight_payload_bytes_upper_bound=sum(row.get('payload_bytes_upper_bound') or row['payload_bytes'] for row in rows),
                all_eight_character_based_input_token_heuristic=[math.ceil(maximum/5),math.ceil(maximum/3)],
                note='Characters divided by 5 to 3 are a planning heuristic, not tokenization or a provider measurement. Stage-two exact sizes do not exist before real parent acceptance.')

def scope(root=ROOT):
    return dict(schema='repodisco-real-repository-growth-pilot-v1',status='FROZEN_PROPOSAL_NOT_AUTHORIZED',
        model_calls_made=0,execution_authorized=False,proposed_max_new_requests=8,
        budget_is_ceiling_not_target=True,accepted_model_parent_receipts_created=0,
        exact_stage_two_payloads_created=0,
        repositories=2,lineages_per_repository=2,stages_per_lineage=2,
        exact_stage_one_slots=4,conditional_stage_two_slots=4,max_requests_per_stage=1,
        maximum_output_tokens=8*4096,output_tokens_per_request=4096,
        automatic_retries=False,reassign_unused=False,feedback_repair_loop=False,
        initial_failure_feedback=False,context_per_slot='fresh; stage two receives only the accepted prior source plus fixed context, not conversational history',
        parent_failure_policy='Block that exact child slot; retain rejected response/native evidence; continue only other scheduled independent lineages.',
        provider_or_transport_error='terminal_stop_no_automatic_recovery; ambiguous request has no proof score',
        native_integrity_or_ambiguous_execution='terminal_stop_preserve_all_evidence',
        ordinary_native_proof_or_guard_failure='failed_current_stage; child blocked without reassignment',
        old_budgets='All prior closed or exhausted scopes remain separate; no recovery or slot reuse.',
        primary_outcome='Both additions accepted sequentially under complete source-bound native scope per lineage.',
        secondary_outcomes=['Stage-one acceptance / dispatched stage-one responses',
            'Stage-two acceptance / dispatched stage-two responses, conditional on accepted parent',
            'Whole-lineage completion / four prespecified lineage starts; blocked child is not a model response',
            'Envelope/grammar/native failure categories; inherited versus additional warnings',
            'Input/output tokens returned by a future provider, verification wall time, resource use and timeouts',
            'Syntactic calls to the prior API, reported separately from completion and never as necessary proof dependence'],
        model_result_denominator='Every dispatched returned response, including guard rejection; missing/ambiguous responses and undispatched blocked slots reported separately.',
        interpretation='Descriptive feasibility of contract-guided sequential repository growth on two selected upstream projects.',
        structural_claims=False,language_comparison=False,held_out_claim=False,
        protected_edit='Only the current stage body changes; original repository, public and internal interfaces/contracts/types, registered modules and accepted parent remain fixed.',
        task_kind={'dafny-vmc':'stable sequence operations added to the Fisher-Yates model API',
                   'vest':'specification/proof library extensions; not executable parser generation; batch count is out of band'},
        new_growth_reference_alternative_negative_solutions_in_prompts=False,
        host_fixed_target_templates_in_prompts=True,
        upstream_implementations_in_context='Exact selected existing upstream API files are legitimate context; new-growth reference/alternative/negative files are excluded.',
        remaining_execution_gates=['Root review of prompt views, source selection and deterministic renderers',
            'Reviewed protocol-003 actual-parent integration and control gate bound into this freeze',
            'Separate explicit approval for at most eight new calls',
            'Reviewed bounded execution handler with immutable request ledger, no retries and conditional child skipping',
            'Private credential handoff only after separately approved execution'],
        limitations=['Two development task chains and two repetitions per project are not independent families.',
            'Prompts use curated context rather than complete import closure; native verification retains the full declared scope.',
            'Inherited trust and unlogged specification definitions remain explicit and are not counted as logged passes.',
            'Direct child implementations remain admissible; observed reuse does not prove necessary dependence.',
            'This is host-selected contract-guided extension, not unrestricted requirement or abstraction discovery.'])

def material(root=ROOT):
    r.assets(root);api=r.protocol_api(root)
    binding=r.read(root/'protocol-binding.json')
    gate=r.read(root/'control-gate-binding.json');gate_path=(root/gate['path']).resolve()
    r.require(r.sha(gate_path.read_bytes())==gate['sha256'],'Source-bound control gate changed')
    result={'settings.json':(root/'assets/proposed-settings.json').read_bytes(),
            'scope.json':r.encode(scope(root)),'order.json':r.encode(r.order()),
            'planned-sizes.json':r.encode(planned_sizes(root)),'protocol-binding.json':r.encode(binding),
            'context-selection.json':(root/'context-selection.json').read_bytes(),
            'template-views.json':(root/'template-views.json').read_bytes(),
            'grammar-spec.json':(root/'grammar-spec.json').read_bytes(),
            'system.txt':r.SYSTEM.encode()}
    deferred=[]
    for stage_id in r.TASKS:result['templates/'+stage_id+'.txt']=r.template_text(stage_id,root).encode()
    for entry in r.order():
        if entry['stage']==1:
            rendered=r.render_stage1(entry['slot_id'],root)
            result['stage1/'+entry['slot_id']+'.payload.json']=r.encode(rendered['payload'])
            result['stage1/'+entry['slot_id']+'.rendering.json']=r.encode(rendered['rendering'])
        else:deferred.append(dict(**entry,payload=None,status='DEFERRED_REQUIRES_ACTUAL_ACCEPTED_PARENT',
            renderer='render.render_stage2',renderer_sha256=r.sha((root/'render.py').read_bytes()),
            parent_requirement='Same-lineage actual model-origin stage-one accepted revision and native evidence validated by protocol-003.',
            reference_substitution=False,synthetic_parent_eligible=False))
    result['deferred-stage2.json']=r.encode(deferred)
    # Native/parent policy remains separately frozen and reviewed. Exact current
    # task templates and bounded call vocabulary must agree before this freeze.
    grammar=r.read(root/'grammar-spec.json');views=r.read(root/'template-views.json')['stages']
    for sid,item in views.items():
        stage,_,_=api.b.stage_spec(sid)
        r.require(stage['path']==item['path'] and stage['template_sha256']==item['source_sha256'],'Protocol task/template differs')
        r.require({k:sorted(v) for k,v in api.b.RULES[sid].items()}==grammar['rules'][sid],'Protocol grammar differs')
    # Explicit preparation inputs: future results or new notes cannot silently
    # enter this historical prompt freeze on a later deterministic replay.
    names=set(r.read(root/'copy-provenance.json'))|{
        'render.py','build_freeze.py','test_pilot.py','README.md','copy-provenance.json',
        'context-selection.json','template-views.json','grammar-spec.json','toolchain-versions.json',
        'control-gate-binding.json','protocol-binding.json'}
    inputs={name:r.sha((root/name).read_bytes()) for name in sorted(names)}
    result['preparation-inputs.json']=r.encode(inputs)
    return result

def build(root=ROOT):
    content=material(root);folder=root/'frozen-001';folder.mkdir(exist_ok=False)
    for name,raw in sorted(content.items()):
        path=folder/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
    manifest={name:r.sha(raw) for name,raw in sorted(content.items())}
    with (folder/'manifest.json').open('xb') as stream:stream.write(r.encode(manifest))
    return dict(status='FROZEN_PROPOSAL_NOT_AUTHORIZED',model_calls=0,proposed_max_calls=8,
                exact_stage_one_payloads=4,stage_two_payloads=0,stage_specific_templates=4,
                freeze_sha256=r.sha((folder/'manifest.json').read_bytes()),artifacts=len(manifest))

def review_freeze(root=ROOT):
    expected=material(root);folder=root/'frozen-001';manifest=r.read(folder/'manifest.json')
    r.require(manifest=={name:r.sha(raw) for name,raw in sorted(expected.items())},'Frozen prompt manifest differs')
    r.require({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}==set(manifest)|{'manifest.json'},'Unexpected frozen artifact')
    for name,raw in expected.items():r.require((folder/name).read_bytes()==raw,'Frozen artifact differs: '+name)
    return dict(status='DETERMINISTIC_FREEZE_REVIEW_PASSED',artifacts=len(manifest),model_calls=0,
                live_stage_two_payloads=0,freeze_sha256=r.sha((folder/'manifest.json').read_bytes()))

if __name__=='__main__':
    r.require(len(sys.argv)==2 and sys.argv[1] in ('build','review'),'Choose offline build or review')
    print(json.dumps(build() if sys.argv[1]=='build' else review_freeze(),indent=2))
