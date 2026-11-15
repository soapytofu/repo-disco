"""Offline study audit layered on the exact previous protected-source reviewer.

Usage: python -B review_verification.py witness|maps
Writes fresh reviews/<group>/review-001 outputs only. Never executes a verifier.
"""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import importlib.util
import io
import json
import re
import sys

ROOT=Path(__file__).resolve().parent
SCOPE_SHA256='179cec720d26dd3635240965d0fcba1abbe96fe50814f4675385fa7f77030044'
UPSTREAM_SHA256='f4de7b39772026d86ce92cb825afa45b07a021519d963b234baf1f6e0d8daf2d'
TARGETS=('HelperA.Prove','HelperB.Prove','ClientA.Target','ClientB.Target')


def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj


def scope():
    raw=(ROOT/'review-scope.json').read_bytes();assert sha(raw)==SCOPE_SHA256
    result=json.loads(raw);assert result['original_reviewer_sha256']==UPSTREAM_SHA256
    return result


class ReportPaths:
    def __init__(self,group,destination):self.group,self.destination=Path(group),Path(destination)
    def __truediv__(self,name):
        if str(name) in ('results-review.json','verification-001-sha256.json'):
            return self.destination/name
        return self.group/name


def dependency_closed(local,graph):
    """Three-valued closure under the declared graph; not a necessity proof."""
    assert set(local)==set(graph)==set(TARGETS)
    assert all(value is None or type(value) is bool for value in local.values())
    result,visiting={},set()
    def visit(name):
        assert name in graph,'Unknown dependency'
        if name in result:return result[name]
        assert name not in visiting,'Cyclic declared dependency graph'
        visiting.add(name)
        values=[local[name]]+[visit(parent) for parent in graph[name]]
        result[name]=False if False in values else None if None in values else True
        visiting.remove(name);return result[name]
    for name in graph:visit(name)
    return {name:result[name] for name in graph}


def csv_units(evidence):
    units={}
    for text in evidence['csv'].values():
        for row in csv.DictReader(io.StringIO(text)):
            name,value=row['TestResult.DisplayName'],row['TestResult.Outcome']
            assert name not in units,'Duplicate named verifier unit'
            assert value in ('Passed','Failed'),'Unrecognized verifier unit outcome'
            units[name]=value
    return units


def local_targets(units):
    result={}
    for target in TARGETS:
        outcomes=[value for name,value in units.items() if re.sub(r' \([^)]*\)$','',name)==target]
        result[target]=all(value=='Passed' for value in outcomes) if outcomes else None
    return result


def expected_targets(group,case,review_scope):
    if group=='witness':
        result={name:case.get(name) for name in ('expected_failed_targets','expected_local_targets','expected_dependency_closed_targets')}
    else:result=review_scope['maps_expected_target_statuses'][case['case_id']]
    expected=result['expected_local_targets']
    if expected is not None:
        assert set(expected)==set(TARGETS) and all(type(value) is bool for value in expected.values())
        assert sorted(result['expected_failed_targets'])==sorted(name for name,value in expected.items() if not value)
        assert result['expected_dependency_closed_targets']==dependency_closed(expected,review_scope['declared_target_dependencies'])
    else:
        assert case['expected']=='resolution_failure'
        assert result['expected_failed_targets'] is None and result['expected_dependency_closed_targets'] is None
    return result


def evidence_aliases(path,cases,rows):
    if not path.exists():return []
    bycase={case['case_id']:case for case in cases};byrow={row['case_id']:row for row in rows};result=[]
    for alias in load(path):
        assert alias['logical_case_id'] not in bycase
        canonical=bycase[alias['evidence_alias_of']];row=byrow[alias['evidence_alias_of']]
        assert alias['source_sha256']==canonical['source_sha256']
        assert alias['source_path']==canonical['path'] and alias['expected']==canonical['expected']
        assert not alias['new_verifier_call'] and not alias['independent_observation']
        result.append({**alias,'canonical_evidence_sha256':row['evidence_sha256'],
                       'strict_actual':row['strict_actual'],'local_targets':row['local_targets'],
                       'dependency_closed_targets':row['dependency_closed_targets'],
                       'canonical_control_matched':row['matched']})
    assert len({alias['logical_case_id'] for alias in result})==len(result)
    return result


def review(group,destination=None):
    review_scope=scope();assert group in review_scope['groups']
    root=ROOT/group;destination=Path(destination or ROOT/'reviews'/group/'review-001').resolve()
    assert not destination.exists(),'Never overwrite an earlier review'
    assert not destination.is_relative_to(root.resolve()),'Reports stay outside frozen input group'
    binding=review_scope['groups'][group]
    for filename,key in [('runtime-manifest.json','runtime_manifest_sha256'),('fixture-manifest.json','fixture_manifest_sha256')]:
        assert sha((root/filename).read_bytes())==binding[key],filename
    pins={**load(root/'runtime-manifest.json'),**load(root/'fixture-manifest.json')}
    for name,digest in pins.items():
        path=root/name;assert not path.is_symlink() and path.is_file() and sha(path.read_bytes())==digest,name
    verifier=module('repair_selection_pinned_'+group,root/'verify.py')
    assert verifier.validate_pins(root)==pins
    upstream_path=ROOT/'review-inputs/review_verification.py'
    assert sha(upstream_path.read_bytes())==UPSTREAM_SHA256
    upstream=module('repair_selection_previous_audit',upstream_path)
    out=root/'verification-001';inventory={}
    for path in sorted(out.rglob('*')):
        assert not path.is_symlink(),str(path)
        if path.is_dir():continue
        assert path.is_file(),str(path)
        if path!=out/'evidence-manifest.json':inventory[path.relative_to(out).as_posix()]=sha(path.read_bytes())
    assert inventory==load(out/'evidence-manifest.json'),'Evidence inventory differs'
    for name,digest in {**pins,'runtime-manifest.json':binding['runtime_manifest_sha256']}.items():
        assert sha((out/name).read_bytes())==digest,'Archived input differs: '+name
    env=load(out/'environment.json')
    for key in ('runtime_manifest_sha256','fixture_manifest_sha256'):assert env[key]==binding[key]
    for program,version in [('dafny','4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'),('z3','Z3 version 4.12.1 - 64 bit')]:
        data=env[program];assert data['exit_code']==0 and data['stdout'].strip()==version
        for stream in ('stdout','stderr'):
            assert (out/(program+'-version.'+stream)).read_bytes().decode(errors='replace')==data[stream]
    cases=load(root/'cases.json');tasks={task['task_id']:task for task in load(root/'tasks.json')}
    assert len(cases)==binding['planned_checks']
    graph=review_scope['declared_target_dependencies']
    for task in tasks.values():
        declared=task.get('target_dependencies')
        if declared is None:
            declared={name:[] for name in TARGETS}
            for caller,dependency in task['dependency_edges']:
                assert caller in declared and dependency in declared
                declared[caller].append(dependency)
        assert declared==graph,'Task does not bind the fixed declared graph'
    summary=load(out/'summary.json')
    assert [row['case_id'] for row in summary['checks']]==[case['case_id'] for case in cases]
    strict={};units_by_case={};reference_units={}
    for case,summary_row in zip(cases,summary['checks']):
        path=out/(case['case_id']+'.json');ev=load(path)
        actual,matched=verifier.classify(ev),verifier.matches(case,ev)
        assert ev['case_id']==case['case_id']
        assert ev['actual']==summary_row['actual']==actual
        assert ev['matched']==summary_row['matched']==matched
        assert ev['expected']==summary_row['expected']==case['expected']
        assert ev['expected_diagnostic']==summary_row['expected_diagnostic']==case['expected_diagnostic']
        assert summary_row['evidence_sha256']==sha(path.read_bytes())
        strict[case['case_id']]=dict(strict_actual=actual,strict_expected_match=matched,
            strict_workspace_verified=actual=='success',actual_exit=ev['exit_code'],expected_exit=case['expected_exit'])
        units=csv_units(ev);units_by_case[case['case_id']]=units
        if case['variant']=='reference' and actual=='success':
            reference_units[case['task_id']]=dict(case_id=case['case_id'],source_sha256=case['source_sha256'],
              evidence_sha256=sha(path.read_bytes()),units=sorted(units),
              target_units={name:sorted(unit for unit in units if re.sub(r' \([^)]*\)$','',unit)==name) for name in TARGETS},
              provider_units=sorted(unit for unit in units if re.sub(r' \([^)]*\)$','',unit) not in TARGETS))
    assert summary['all_expected']==all(row['strict_expected_match'] for row in strict.values())
    destination.mkdir(parents=True,exist_ok=False)
    result=upstream.review(ReportPaths(root,destination))
    for row,case in zip(result['checks'],cases):
        assert row['case_id']==case['case_id']
        row.update(strict[case['case_id']])
        units=units_by_case[case['case_id']]
        observed=local_targets(units);closed=dependency_closed(observed,graph)
        expected=expected_targets(group,case,review_scope)
        row.update(local_targets=observed,dependency_closed_targets=closed,
                   actual_failed_targets=sorted(name for name,value in observed.items() if value is False),
                   **expected)
        local_ok=(all(value is None for value in observed.values()) if expected['expected_local_targets'] is None
                  else observed==expected['expected_local_targets'])
        closed_ok=(all(value is None for value in closed.values()) if expected['expected_dependency_closed_targets'] is None
                   else closed==expected['expected_dependency_closed_targets'])
        ref=reference_units.get(case['task_id'])
        scope_match=(sorted(units)==ref['units']) if units and ref is not None else None
        scope_ok=ref is not None and (scope_match is True or
                  not units and row['strict_actual']=='resolution_failure')
        row.update(local_expectations_match=local_ok,dependency_closed_expectations_match=closed_ok,
                   reference_scope_match=scope_match,reference_scope_gate_match=scope_ok,
                   provider_units_passed=(not row['unverified_providers']) if units else None)
        row['matched']=row['matched'] and row['strict_expected_match'] and local_ok and closed_ok and scope_ok
    result.update(all_expected=all(row['matched'] for row in result['checks']),
                  strict_counts=dict(Counter(row['strict_actual'] for row in result['checks'])),
                  primary_strict_workspace_successes=sum(row['strict_workspace_verified'] for row in result['checks']),
                  reference_gate_complete=set(reference_units)==set(tasks),
                  declared_target_dependencies=graph,reference_unit_sets=reference_units,
                  scope_sha256=SCOPE_SHA256,original_reviewer_sha256=UPSTREAM_SHA256,
                  runtime_manifest_sha256=binding['runtime_manifest_sha256'],fixture_manifest_sha256=binding['fixture_manifest_sha256'],
                  archived_input_files_checked=len(pins)+1,raw_inventory_files_checked=len(inventory),
                  claim='Verifier-only fixed-architecture development controls. Local and declared-graph-closed target statuses are secondary; strict whole-workspace verification remains primary. No model, necessary-dependency, sharing-effect, minimality or held-out claim.')
    result['evidence_aliases']=evidence_aliases(root/'control-aliases.json',cases,result['checks'])
    save(destination/'results-review.json',result)
    save(destination/'reference-unit-sets.json',dict(schema='repair-selection-reference-scope-v1',
         group=group,complete=result['reference_gate_complete'],declared_target_dependencies=graph,
         runtime_manifest_sha256=binding['runtime_manifest_sha256'],tasks=reference_units))
    print(json.dumps({key:result[key] for key in ('job_id','reviewed','all_expected','strict_counts',
        'primary_strict_workspace_successes','reference_gate_complete','protected_file_comparisons','protected_body_boundaries')},indent=2))
    return result


if __name__=='__main__':
    assert len(sys.argv)==2 and sys.argv[1] in ('witness','maps')
    result=review(sys.argv[1]);raise SystemExit(0 if result['all_expected'] else 1)
