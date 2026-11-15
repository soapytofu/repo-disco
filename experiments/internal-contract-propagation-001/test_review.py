"""Synthetic reviewer tests; no verifier/network/model process is used."""
import base64
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import review as r


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')


def source(case):return {p.name:p.read_bytes() for p in (r.ROOT/case['path']).glob('*.dfy')}


def csv_text(declarations,failed=(),extra_wf=False):
    out=io.StringIO(newline='');writer=csv.writer(out);writer.writerow(r.HEADER)
    for symbol,kind in sorted(declarations.items()):
        unit='correctness' if kind=='method' else 'well-formedness'
        writer.writerow([symbol+' ('+unit+')','Failed' if symbol in failed else 'Passed','00:00:00.001','42','0'])
        if extra_wf and symbol=='Client.Target':
            writer.writerow([symbol+' (well-formedness)','Passed','00:00:00.002','17','0'])
    return out.getvalue()


def make_archive(out):
    pins={**r.load(r.ROOT/'runtime-manifest.json'),**r.load(r.ROOT/'fixture-manifest.json')}
    for name in set(pins)|{'runtime-manifest.json'}:
        dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(r.ROOT/name,dest)
    spec=importlib.util.spec_from_file_location('synthetic_pinned_verifier',r.ROOT/'verify.py')
    v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    env=dict(model_calls=0,job_id='123456',host='synthetic-compute',partition='test',
             runtime_manifest_sha256=r.RUNTIME_SHA,fixture_manifest_sha256=r.FIXTURE_SHA)
    for program,version in [('dafny',v.DAFNY_VERSION),('z3',v.Z3_VERSION)]:
        env[program]=dict(stdout=version+'\n',stderr='',exit_code=0)
        for stream in ('stdout','stderr'):(out/(program+'-version.'+stream)).write_text(env[program][stream])
    save(out/'environment.json',env)
    tasks={t['task_id']:t for t in r.load(r.ROOT/'tasks.json')};rows=[]
    for case in r.load(r.ROOT/'cases.json'):
        files=source(case)
        declarations=r.source_scope(files,tasks[case['task_id']],case,
            {p.name:p.read_bytes() for p in (r.ROOT/'fixtures'/case['task_id']/'reference').glob('*.dfy')})
        text=csv_text(declarations,case['expected_failed_targets'],case['internal_api_version']=='new')
        if case['expected']=='success':stdout='Dafny program verifier finished with 5 verified, 0 errors\n'
        else:
            message={'precondition':'a precondition for this call could not be proved',
                     'postcondition':'a postcondition could not be proved',
                     'assertion':'assertion might not hold'}[case['expected_diagnostic']]
            filename=case['expected_failed_targets'][0].split('.')[0]+'.dfy'
            stdout=filename+'(1,1): Error: '+message+'\nDafny program verifier finished with 4 verified, 1 error\n'
        rawstdout=stdout.encode();rawstderr=b'';rawcsv=text.encode()
        ev=dict(command=v.COMMAND,exit_code=case['expected_exit'],stdout=stdout,stderr='',
            stdout_base64=base64.b64encode(rawstdout).decode(),stderr_base64='',
            stdout_sha256=r.sha(rawstdout),stderr_sha256=r.sha(rawstderr),
            csv={'synthetic.csv':text},csv_base64={'synthetic.csv':base64.b64encode(rawcsv).decode()},
            csv_sha256={'synthetic.csv':r.sha(rawcsv)},source_sha256=case['source_sha256'],
            attempts=1,model_calls=0,timed_out=False,execution_error=None,case_id=case['case_id'],
            expected=case['expected'],expected_diagnostic=case['expected_diagnostic'])
        ev.update(actual=v.classify(ev),matched=v.matches(case,ev),diagnostics=v.diagnostic_details(ev))
        path=out/(case['case_id']+'.json');save(path,ev)
        raw=out/'raw'/case['case_id'];(raw/'csv').mkdir(parents=True)
        (raw/'stdout.txt').write_bytes(rawstdout);(raw/'stderr.txt').write_bytes(rawstderr)
        (raw/'csv/synthetic.csv').write_bytes(rawcsv)
        rows.append(dict(case_id=case['case_id'],expected=case['expected'],actual=ev['actual'],matched=ev['matched'],
                         expected_diagnostic=case['expected_diagnostic'],diagnostic_categories=ev['diagnostics']['diagnostic_categories'],
                         evidence_sha256=r.sha(path.read_bytes())))
    save(out/'summary.json',dict(planned=18,completed=18,all_expected=True,model_calls=0,checks=rows))
    save(out/'evidence-manifest.json',r.inventory(out))


class NamedEvidence(unittest.TestCase):
    def setUp(self):self.declarations={'Helper.Transfer':'method','Client.Target':'method','Kernel.Endpoint':'function'}

    def test_named_method_results_and_provider_failures_without_fixed_unit_count(self):
        for extra in (False,True):
            value=r.named_units({'x.csv':csv_text(self.declarations,['Client.Target'],extra)},self.declarations)
            self.assertEqual(value['local_targets'],{'Client.Target':False,'Helper.Transfer':True})
            self.assertTrue(value['providers_verified'])
            self.assertEqual(len(value['units']),3+int(extra))
        value=r.named_units({'x.csv':csv_text(self.declarations,['Kernel.Endpoint'])},self.declarations)
        self.assertFalse(value['providers_verified'])

    def test_missing_duplicate_malformed_unknown_or_incomplete_batches_rejected(self):
        good=csv_text(self.declarations)
        reader=list(csv.reader(io.StringIO(good)))
        bad=[]
        bad.append(good.replace('Client.Target (correctness)','Client.Target (well-formedness)'))
        bad.append(good+'\n'+','.join(reader[1])+'\n')
        bad.append(good.replace('Helper.Transfer (correctness)','Other.Transfer (correctness)'))
        bad.append(good.replace('Passed','Unknown',1))
        bad.append(good.replace('00:00:00.001','NaN',1))
        bad.append(good.replace('TestResult.DisplayName','Name',1))
        bad.append(good.replace('Helper.Transfer (correctness)','Helper.Transfer (correctness) (assertion batch 2)'))
        bad.append('\n'.join(line for line in good.splitlines() if not line.startswith('Kernel.'))+'\n')
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises((ValueError,csv.Error)):r.named_units({'x.csv':value},self.declarations)

    def test_public_prefix_corruption_rejected_even_with_adjusted_source_digest(self):
        case=next(c for c in r.load(r.ROOT/'cases.json') if c['variant']=='paired_repair')
        task=next(t for t in r.load(r.ROOT/'tasks.json') if t['task_id']==case['task_id'])
        files=source(case);reference={p.name:p.read_bytes() for p in (r.ROOT/'fixtures'/case['task_id']/'reference').glob('*.dfy')}
        altered=dict(files);altered['Client.dfy']=altered['Client.dfy'].replace(b'ensures result == K.Endpoint(start,length,cap)',b'ensures true')
        changed=copy.deepcopy(case);changed['source_sha256']={n:r.sha(b) for n,b in altered.items()}
        with self.assertRaisesRegex(ValueError,'Public contract'):r.source_scope(altered,task,changed,reference)
        altered=dict(files);altered['Kernel.dfy']+=b'\n'
        changed['source_sha256']={n:r.sha(b) for n,b in altered.items()}
        with self.assertRaisesRegex(ValueError,'Immutable provider'):r.source_scope(altered,task,changed,reference)


class CompleteSyntheticArchive(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.out=Path(self.tmp.name)/'verification';self.out.mkdir()
        make_archive(self.out)
        self.source_root=Path(self.tmp.name)/'sources';self.source_root.mkdir()
        pins={**r.load(r.ROOT/'runtime-manifest.json'),**r.load(r.ROOT/'fixture-manifest.json')}
        for name in set(pins)|{'runtime-manifest.json'}:
            dest=self.source_root/name;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(r.ROOT/name,dest)

    def test_all_18_cases_raw_bytes_scope_and_distinct_actual_named_outcomes(self):
        result,pins=r.audit(self.source_root,self.out)
        self.assertTrue(result['all_expected'])
        self.assertEqual(result['reviewed'],18)
        self.assertEqual(result['source_files_checked'],72)
        self.assertEqual(result['public_contract_prefixes_checked'],18)
        self.assertEqual(result['body_boundaries_checked'],36)
        self.assertEqual(result['counts'],{'success':6,'proof_failure':12})
        for row in result['checks']:
            self.assertEqual(row['named_evidence']['local_targets'],row['expected_local_targets'])
        self.assertEqual(len(pins),result['raw_archive_files'])

    def test_raw_stream_corruption_rejected_even_after_inventory_rehash(self):
        case=r.load(r.ROOT/'cases.json')[0]
        path=self.out/'raw'/case['case_id']/'stdout.txt';path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'inventory'):r.audit(self.source_root,self.out)
        inventory=r.inventory(self.out);inventory.pop('evidence-manifest.json')
        save(self.out/'evidence-manifest.json',inventory)
        with self.assertRaisesRegex(ValueError,'stream archive'):r.audit(self.source_root,self.out)

    def test_base64_disagreement_and_unknown_named_scope_are_not_accepted(self):
        case=r.load(r.ROOT/'cases.json')[0];path=self.out/(case['case_id']+'.json');original=r.load(path)
        changed=copy.deepcopy(original);changed['stdout_base64']=base64.b64encode(b'changed').decode();save(path,changed)
        pins=r.inventory(self.out);pins.pop('evidence-manifest.json');save(self.out/'evidence-manifest.json',pins)
        with self.assertRaisesRegex(ValueError,'base64/hash'):r.audit(self.source_root,self.out)
        changed=copy.deepcopy(original)
        csvvalue=changed['csv']['synthetic.csv'].replace('Client.Target (correctness)','Unlisted.Target (correctness)')
        changed['csv']['synthetic.csv']=csvvalue
        changed['csv_base64']['synthetic.csv']=base64.b64encode(csvvalue.encode()).decode()
        changed['csv_sha256']['synthetic.csv']=r.sha(csvvalue.encode());save(path,changed)
        (self.out/'raw'/case['case_id']/'csv/synthetic.csv').write_text(csvvalue,newline='')
        summary=r.load(self.out/'summary.json');summary['checks'][0]['evidence_sha256']=r.sha(path.read_bytes())
        save(self.out/'summary.json',summary)
        pins=r.inventory(self.out);pins.pop('evidence-manifest.json');save(self.out/'evidence-manifest.json',pins)
        result,_=r.audit(self.source_root,self.out)
        self.assertFalse(result['all_expected'])
        self.assertFalse(result['checks'][0]['named_scope_valid'])
        self.assertIn('Unrecognized declaration',result['checks'][0]['named_scope_error'])

    def test_wrong_failed_target_is_not_hidden_by_coarse_success(self):
        case=next(c for c in r.load(r.ROOT/'cases.json') if c['variant']=='helper_only')
        path=self.out/(case['case_id']+'.json');ev=r.load(path)
        csvvalue=ev['csv']['synthetic.csv'].replace('Client.Target (correctness),Failed','Client.Target (correctness),Passed').replace(
            'Helper.Transfer (correctness),Passed','Helper.Transfer (correctness),Failed')
        ev['csv']['synthetic.csv']=csvvalue
        ev['csv_base64']['synthetic.csv']=base64.b64encode(csvvalue.encode()).decode()
        ev['csv_sha256']['synthetic.csv']=r.sha(csvvalue.encode());save(path,ev)
        (self.out/'raw'/case['case_id']/'csv/synthetic.csv').write_text(csvvalue,newline='')
        summary=r.load(self.out/'summary.json')
        next(row for row in summary['checks'] if row['case_id']==case['case_id'])['evidence_sha256']=r.sha(path.read_bytes())
        save(self.out/'summary.json',summary)
        pins=r.inventory(self.out);pins.pop('evidence-manifest.json');save(self.out/'evidence-manifest.json',pins)
        result,_=r.audit(self.source_root,self.out)
        self.assertFalse(result['all_expected'])
        row=next(row for row in result['checks'] if row['case_id']==case['case_id'])
        self.assertTrue(row['coarse_expected_match'])
        self.assertFalse(row['named_expected_match'])


if __name__=='__main__':unittest.main(verbosity=2)
