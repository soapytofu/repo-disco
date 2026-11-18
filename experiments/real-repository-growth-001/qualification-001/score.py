"""Additive growth-inventory review around the unchanged qualified parsers.

These are provisional reference observations, not an execution-release gate.
Native metadata and inventories are kept intact; missing spec logger entries
are identified and never manufactured as successful proof observations.
"""
import json

import common as c
from gates.vmc import protocol as dg
from gates.vest import protocol_v2 as vg
import warning_policy


def key(value):
    return json.dumps(value, separators=(',', ':'))


def observe(project, native, raw, root=c.ROOT):
    entry = c.reference(project, root)
    base = c.base_profile(project, root)
    plan = c.read(root / 'plan.json')
    if project == 'dafny-vmc':
        parsed = dg.dafny_observation(native['exit_code'], raw['stdout.txt'], raw['stderr.txt'],
                                      {n: b for n, b in raw.items() if n.startswith('csv/')})
        original = set(base['required_units'])
        required_new = set(entry['required_new_names'])
        actual = set(parsed['units'])
        review = dict(old_inventory_complete=original <= actual,
                      missing_original=sorted(original - actual),
                      missing_new=sorted(required_new - actual),
                      unexpected_new=sorted(actual - original - required_new),
                      new_inventory={n: parsed['units'][n] for n in sorted(actual - original)},
                      baseline_unlogged_files=base['unlogged_files'],
                      fixed_unlogged_spec_definitions=[],
                      native_metadata_matches=True)
        covered = parsed['coverage_complete'] and actual == original | required_new
    else:
        parsed = vg.verus_observation(native['exit_code'], raw['stdout.txt'], raw['stderr.txt'])
        expected = base['required']
        actual = parsed['inventory']
        original = expected['inventory']
        missing_original = {k: {'expected': v, 'observed': actual.get(k, 0)}
                            for k, v in original.items() if actual.get(k) != v}
        new = {k: v for k, v in actual.items() if k not in original}
        required_new = {key(x) for x in entry['required_new_targets']}
        missing_new = sorted(k for k in required_new if actual.get(k) != 1)
        permitted = {}
        unlogged = []
        for path, modes in plan['new_vest_definitions'].items():
            module = 'formats::' + path.rsplit('/', 1)[-1][:-3]
            for mode, names in modes.items():
                for name in names:
                    k = key(['vest_dev', module, 'vest_dev::' + module + '::' + name, mode])
                    permitted[k] = dict(file=path, source_sha256=entry['overlay_sha256'][path], mode=mode)
                    if mode == 'spec' and k not in actual:
                        unlogged.append(dict(unit=json.loads(k), file=path,
                                             source_sha256=entry['overlay_sha256'][path],
                                             observation='UNLOGGED_FIXED_SPEC_DEFINITION', counted_as_pass=False))
        unexpected_new = {k: v for k, v in new.items() if k not in permitted or v != 1}
        metadata = (set(parsed['crates']) == set(expected['crates']) and
                    all(info['version'] == expected['version'] and info['num_threads'] == 1
                        for info in parsed['crates'].values()) and parsed['entire_crate'])
        review = dict(old_inventory_complete=not missing_original, missing_original=missing_original,
                      missing_new=missing_new, unexpected_new=unexpected_new, new_inventory=new,
                      new_definition_bindings=permitted, fixed_unlogged_spec_definitions=unlogged,
                      native_metadata_matches=bool(metadata),
                      concurrency_change=dict(baseline_verus_threads=expected['num_threads'],
                                              current_verus_threads=1, current_cargo_workers=1),
                      native_summary_counts_are_not_timed_inventory_counts=True)
        covered = (parsed['coverage_complete'] and metadata and not missing_original and
                   not missing_new and not unexpected_new)
    observation = json.loads(json.dumps(parsed))
    observation['native_parser_coverage_complete'] = parsed['coverage_complete']
    observation['native_parser_proof_pass'] = parsed['proof_pass']
    observation['coverage_complete'] = bool(covered)
    observation['proof_pass'] = bool(parsed['proof_pass'] and covered)
    observation['strict_zero_warning_pass'] = bool(parsed['strict_zero_warning_pass'] and covered)
    observation['warnings_match_upstream'] = sorted(parsed['warnings']) == sorted(base['upstream_warnings'])
    observation['qualified_scope_pass'] = observation['proof_pass'] and observation['warnings_match_upstream']
    observation['growth_inventory_review'] = review
    observation['warning_review'] = warning_policy.report(project, observation, native, base)
    observation['reference_ready_for_human_inventory_review'] = observation['warning_review']['eligible_under_policy_v2']
    observation['reference_gate_status'] = 'REQUIRES_EXPLICIT_SOURCE_BOUND_REVIEW'
    observation['controls_released'] = False
    observation['model_scope_authorized'] = False
    observation['live_repository_promoted'] = False
    return observation
