"""Source-bound named control expectations, separate from workspace success."""
import json
import common as c
from gates.vmc import protocol as dg
from gates.vest import protocol_v2 as vg
import warning_policy

def missing(expected,actual):
    return {k:dict(expected=v,observed=actual.get(k,0)) for k,v in expected.items() if actual.get(k,0)!=v}

def vest_outcomes(raw):
    result={}
    for report in vg.json_reports(raw['stdout.txt'])+vg.json_reports(raw['stderr.txt']):
        local=[]
        for module in report.get('times-ms',{}).get('smt',{}).get('smt-run-module-times',[]):
            for unit in module.get('function-breakdown',[]):
                local.append((module['module'],unit))
        owners={unit['function'].split('::')[0] for _,unit in local}&{'vstd','vest_lib','vest_dev'}
        c.require(len(owners)<=1,'Mixed report crate ownership')
        owner=next(iter(owners)) if owners else 'unidentified'
        for module,unit in local:
            # External-spec friendly labels retain the owning native report crate.
            key=json.dumps([owner,module,unit['function'],unit['mode:']],separators=(',',':'))
            result.setdefault(key,[]).append('Passed' if unit['success'] else 'Failed')
    return result

def observe(project,case_id,native,raw,root=c.ROOT):
    entry=c.case(project,case_id,root);base=c.base_profile(project,root)
    if project=='dafny-vmc':
        native_observation=dg.dafny_observation(native['exit_code'],raw['stdout.txt'],raw['stderr.txt'],
                            {n:b for n,b in raw.items() if n.startswith('csv/')})
        inventory={n:1 for n in native_observation['units']}
        outcomes={n:[v] for n,v in native_observation['units'].items()}
        original={n:1 for n in base['required_units']};metadata=True
    else:
        native_observation=vg.verus_observation(native['exit_code'],raw['stdout.txt'],raw['stderr.txt'])
        inventory=native_observation['inventory'];outcomes=vest_outcomes(raw);original=base['required']['inventory']
        metadata=(set(native_observation['crates'])==set(base['required']['crates']) and
                  native_observation['entire_crate'] and all(x['version']==base['required']['version'] and x['num_threads']==1
                                                           for x in native_observation['crates'].values()))
    required={**original,**entry['required_new_inventory']}
    expected_observed={**original,**entry['expected_observed_new_inventory']}
    observed_scope_complete=bool(native_observation['coverage_complete'] and metadata and inventory==expected_observed)
    workspace_coverage=bool(native_observation['coverage_complete'] and metadata and inventory==required)
    old_inventory_exact=not missing(original,inventory)
    old_failures={k:outcomes[k] for k in original if k in outcomes and any(x!='Passed' for x in outcomes[k])}
    old_all_pass=old_inventory_exact and not old_failures and all(outcomes.get(k)==['Passed']*v for k,v in original.items())
    named={k:outcomes.get(k,[]) for k in entry['required_new_inventory']}
    named_match=all(named[k]==([] if expectation=='Missing' else [expectation]*entry['required_new_inventory'][k])
                    for k,expectation in entry['expected_new_outcomes'].items())
    whole_proof=bool(native_observation['proof_pass'] and workspace_coverage)
    warnings_exact=sorted(native_observation['warnings'])==sorted(base['upstream_warnings'])
    warning_input={**native_observation,'proof_pass':whole_proof,'coverage_complete':workspace_coverage,
                   'qualified_scope_pass':whole_proof and warnings_exact}
    warnings=warning_policy.report(project,warning_input,native,base)
    warning_eligible=not warnings['unclassified_warnings'] and not warnings['missing_upstream_warnings']
    kind=entry['expected_kind'];category=native_observation['category']
    interrupted=native['exit_code']<0 or native['exit_code'] in (124,137,143) or native.get('timeout') is True
    ambiguous=category in c.read(root/'plan.json')['ambiguous_native_categories_halt']
    stopped=interrupted or ambiguous
    if kind=='named_proof_failure':
        expected_native=(category=='PROOF_FAILURE' and native['exit_code']!=0 and bool(entry['expected_failed_new_units']))
    else:expected_native=native_observation['proof_pass'] and category in ('PROVED','PROVED_WITH_WARNINGS')
    matched=bool(expected_native and observed_scope_complete and old_all_pass and named_match and warning_eligible and not stopped)
    if kind=='coverage_omission':
        matched=matched and not workspace_coverage and bool(entry['expected_missing_new_units'])
    unlogged=[]
    if project=='vest':
        for item in c.read(root/'plan.json')['unlogged_vest_frame_definitions']:
            record=dict(item);record['source_sha256']=entry['overlay_sha256'][item['file']]
            key=json.dumps(record['unit'],separators=(',',':'))
            if key in inventory:record['observation']='UNEXPECTED_LOGGED_FIXED_SPEC_DEFINITION'
            elif entry['id']=='frame-omitted':record['observation']='UNREGISTERED_FIXED_SPEC_SOURCE'
            unlogged.append(record)
    return dict(project=project,case=case_id,category=category,native_observation=native_observation,
        actual_inventory=inventory,native_metadata_matches=bool(metadata),observed_scope_complete=observed_scope_complete,
        required_workspace_coverage=workspace_coverage,missing_or_count_changed_required=missing(required,inventory),
        unexpected_units={k:v for k,v in inventory.items() if k not in required},original_inventory_exact=old_inventory_exact,
        original_failed_units=old_failures,original_all_pass=old_all_pass,named_new_outcomes=named,
        expected_kind=kind,expected_named_outcomes=entry['expected_new_outcomes'],named_expectations_match=named_match,
        expectation_match=matched,whole_workspace_proof_pass=whole_proof,warning_review=warnings,
        warning_policy_eligible=bool(warning_eligible),fixed_unlogged_definitions=unlogged,
        unproved_parent_observation=(dict(parent=entry['parent_target'],parent_outcome=named.get(entry['parent_target'],[]),
                                         child=entry['child_target'],child_outcome=named.get(entry['child_target'],[]))
                                    if entry['unproved_parent_control'] else None),
        stop_after_case=stopped,
        execution_termination=('UNRESOLVED_SIGNAL_OR_TIMEOUT' if interrupted else
                               'AMBIGUOUS_OR_MISSING_NATIVE_EVIDENCE' if ambiguous else 'RETURNED_WITHOUT_TERMINATION_FLAG'),
        model_calls=0,live_repository_promoted=False,model_scope_authorized=False)
