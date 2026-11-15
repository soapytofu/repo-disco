"""Versioned correction for one exact unlogged Endpoint definition.

All original source/raw evidence checks and strict named-unit parsing are reused.
Only the hash-bound Endpoint declaration may lack a CSV unit; it is reported as
unlogged, never represented by a synthetic or assumed Passed provider record.
"""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OLD_REVIEW_SHA='b27e58637eecadca8a999b3d3d584cd8bd0bb587cc26891270de26391e88e750'
SCOPE_SHA='d63f06034e08ba7769906121fc0e3a1a4bea7d3880b4a20c97de0d4331681a37'


def require(value,message):
    if not value:raise ValueError(message)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load_scope(path=None):
    path=Path(path or ROOT/'review-v2-scope.json')
    require(sha(path)==SCOPE_SHA,'Versioned logger scope changed')
    return json.loads(path.read_bytes())


def original_reviewer():
    path=ROOT/'review.py';require(sha(path)==OLD_REVIEW_SHA,'Original reviewer changed')
    spec=importlib.util.spec_from_file_location('internal_contract_review_v1_preserved',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def preservation(scope):
    for name,h in scope['predecessor_files'].items():
        require(sha(ROOT/name)==h,'Preserved predecessor changed: '+name)


class Adapter:
    def __init__(self):
        self.scope=load_scope();self.old=original_reviewer();self.pending=None
        self.old_source_scope=self.old.source_scope;self.old_named_units=self.old.named_units
        require(self.scope['runtime_manifest_sha256']==self.old.RUNTIME_SHA and
                self.scope['fixture_manifest_sha256']==self.old.FIXTURE_SHA,'Runtime provenance differs')
        self.old.source_scope=self.source_scope
        self.old.named_units=self.named_units

    def source_scope(self,files,task,case,reference):
        declarations=self.old_source_scope(files,task,case,reference)
        require(task['task_id']==case['task_id'],'Task/source identity differs')
        optional=[]
        for item in self.scope['unlogged_definitions']:
            if item['task_id']!=case['task_id']:continue
            require(item['source_file'] in files and hashlib.sha256(files[item['source_file']]).hexdigest()==item['source_sha256'],
                    'Unlogged definition source hash differs')
            require(declarations.get(item['symbol'])==item['declaration_kind']=='function','Unlogged symbol/kind differs')
            optional.append(item)
        if case['task_id']=='extracted_entry_return_migration':
            require(set(self.scope['mandatory_map_providers'])<=set(declarations),'Map provider source scope changed')
        require(set(self.scope['mandatory_methods'])==self.old.TARGETS,'Mandatory methods differ')
        self.pending=dict(task_id=case['task_id'],declarations=dict(declarations),optional=optional)
        return declarations

    def named_units(self,csv_files,declarations):
        require(self.pending is not None and self.pending['declarations']==declarations,'Missing exact source context')
        observed=set()
        # Discovery grants no validity. The original parser still checks every
        # header, field, name, outcome, duplicate, assertion batch and target.
        for text in csv_files.values():
            for row in csv.DictReader(io.StringIO(text,newline=''),strict=True):
                name=row.get(self.old.HEADER[0])
                match=self.old.NAME.fullmatch(name) if isinstance(name,str) else None
                if match:observed.add(match[1])
        absent=[item for item in self.pending['optional'] if item['symbol'] not in observed]
        required={name:kind for name,kind in declarations.items() if name not in {item['symbol'] for item in absent}}
        result=self.old_named_units(csv_files,required)
        result['unlogged_definitions']=[dict(symbol=item['symbol'],source_file=item['source_file'],
            source_sha256=item['source_sha256'],classification=item['classification']) for item in absent]
        result['logged_provider_units']=[name for name in result['units'] if self.old.NAME.fullmatch(name)[1] not in self.old.TARGETS]
        result['source_context_task_id']=self.pending['task_id']
        return result

    def audit(self,root,out):
        result,pins=self.old.audit(root,out)
        # The old audit uses providers_verified internally. In the public v2
        # report it is explicitly limited to the actually observed provider units.
        for row in result['checks']:
            named=row['named_evidence']
            if named is not None and 'providers_verified' in named:
                named['logged_provider_units_verified']=named.pop('providers_verified')
                named['provider_observation_complete']=not named['unlogged_definitions']
        result['schema']='repodisco-internal-contract-named-review-v2'
        result['review_v1_sha256']=OLD_REVIEW_SHA
        result['logger_scope_sha256']=SCOPE_SHA
        result['prior_review_result_sha256']=self.scope['predecessor_files']['reviews/review-001/results-review.json']
        result['reviewer_assumption_correction']='V1 required every function declaration to emit a named unit. The exact Endpoint definition has no CSV entry; it is now explicitly unlogged, not a verified provider unit.'
        result['unlogged_definition_observations']=sum(len(row['named_evidence']['unlogged_definitions'])
            for row in result['checks'] if row['named_evidence'] is not None)
        result['logged_provider_unit_observations']=sum(len(row['named_evidence']['logged_provider_units'])
            for row in result['checks'] if row['named_evidence'] is not None)
        result['whole_workspace_outcomes_unchanged']=True
        return result,pins


def review(out=None,destination=None):
    out=Path(out or ROOT/'verification-001').resolve()
    destination=Path(destination or ROOT/'reviews/review-002').resolve()
    require(not destination.exists() and not destination.is_relative_to(out),'New v2 review outside evidence required')
    adapter=Adapter();preservation(adapter.scope)
    result,pins=adapter.audit(ROOT,out)
    # V2 is a re-interpretation of the exact same complete archive.
    old_inventory=adapter.old.load(ROOT/'reviews/review-001/evidence-sha256.json')
    require(pins==old_inventory,'Evidence changed since v1 review')
    preservation(adapter.scope)
    destination.mkdir(parents=True,exist_ok=False)
    for name,value in [('results-review.json',result),('evidence-sha256.json',pins)]:
        with (destination/name).open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,default=ROOT/'verification-001')
    parser.add_argument('--output',type=Path,default=ROOT/'reviews/review-002')
    args=parser.parse_args();result=review(args.evidence,args.output)
    print(json.dumps({k:v for k,v in result.items() if k not in ('checks','reference_units')},indent=2))
    raise SystemExit(0 if result['all_expected'] else 1)
