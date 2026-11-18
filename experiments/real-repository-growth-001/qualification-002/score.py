"""Namespace-revised Dafny inventory review using the unchanged native parser.

No control release or model-policy compatibility is inferred from a result.
"""
import json

import common as c
from gates.vmc import protocol as dg
import warning_policy


def observe(project, native, raw, root=c.ROOT):
    entry = c.reference(project, root)
    base = c.base_profile(project, root)
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
                  fixed_unlogged_spec_definitions=[], native_metadata_matches=True)
    covered = parsed['coverage_complete'] and actual == original | required_new
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
    observation['old_model_body_policy_compatible'] = False
    observation['live_repository_promoted'] = False
    return observation
