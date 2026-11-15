"""Compute-only, single-attempt verification of hash-pinned existing fixtures."""
from pathlib import Path, PurePosixPath
import base64
import csv
import hashlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
DAFNY_VERSION = '4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
Z3_VERSION = 'Z3 version 4.12.1 - 64 bit'
COMMAND = ['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy']
SUMMARY_RE = re.compile(r'^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$', re.M)
RESOLUTION_RE = re.compile(r'does not exist|unresolved identifier|has not been declared|could not be resolved|could not resolve|no member|not a member|unknown member', re.I)
FRONTEND_RE = re.compile(r'\bparse errors? detected|\bresolution/type errors? detected|\bresolution errors? detected|\bsyntax error|this symbol not expected|\btype mismatch|\bincorrect type', re.I)
DIAGNOSTICS = {
    'precondition': re.compile(r'\bprecondition\b.*(?:could not be proved|might not hold|not satisfied)', re.I),
    'postcondition': re.compile(r'\bpostcondition\b.*(?:could not be proved|might not hold)|possible violation of postcondition|postcondition of forall statement', re.I),
    'assertion': re.compile(r'\bassertion\b.*(?:might not hold|could not be proved|not satisfied)', re.I),
    'termination': re.compile(r'decreases (?:expression|clause) might not decrease|failure to decrease|(?:could not|cannot) prove termination', re.I),
    'missing export member': RESOLUTION_RE,
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def safe_path(root, name):
    rel = PurePosixPath(name)
    assert rel.parts and not rel.is_absolute() and '..' not in rel.parts, name
    path = root / str(rel)
    assert not path.is_symlink() and path.resolve().is_relative_to(root.resolve()), name
    return path


def validate_pins(root=ROOT):
    """Check both flat manifests and the original construction inventory."""
    root = Path(root)
    runtime, fixtures = load(root/'runtime-manifest.json'), load(root/'fixture-manifest.json')
    assert runtime and fixtures
    allpins = {}
    for manifest in (runtime, fixtures):
        for name, digest in manifest.items():
            assert isinstance(name,str) and isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest)
            assert name not in allpins or allpins[name] == digest
            assert sha(safe_path(root,name).read_bytes()) == digest, name
            allpins[name] = digest
    assert 'fixture-manifest.json' in runtime
    assert 'tasks.json' in fixtures and 'cases.json' in fixtures
    assert {'build.py','verify.py','test_structure.py','test_design.py','verify.sbatch'} <= set(runtime)
    original = load(root/'adapter-preservation-001.json')['files']
    for name,digest in original.items():
        assert sha(safe_path(root,name).read_bytes()) == digest, 'Original changed: '+name
    cases = load(root/'cases.json')
    assert len({c['case_id'] for c in cases}) == len(cases)
    for case in cases:
        folder = safe_path(root,case['path'])
        sources = {p.name:sha(p.read_bytes()) for p in sorted(folder.glob('*.dfy'))}
        assert sources == case['source_sha256'], case['case_id']
        for name,digest in sources.items():
            assert fixtures[case['path']+'/'+name] == digest
        assert case['expected_diagnostic'] in ('none', *DIAGNOSTICS)
    return allpins


def diagnostic_details(record):
    text = record['stdout']+'\n'+record['stderr']
    error_lines = re.findall(r'^.*\bError:\s*(.*)$',text,re.M)
    errors = '\n'.join(error_lines)
    warnings = len(re.findall(r'^.*\bWarning\s*:',text,re.I|re.M))
    numeric_warning = re.search(r'\b([1-9]\d*) warnings?\b',text,re.I)
    if numeric_warning:
        warnings = max(warnings,int(numeric_warning.group(1)))
    return {'summaries': [(int(a),int(b)) for a,b in SUMMARY_RE.findall(text)],
            'warnings': warnings, 'error_lines': error_lines,
            'diagnostic_categories': [name for name,pattern in DIAGNOSTICS.items() if pattern.search(errors)],
            'frontend': bool(FRONTEND_RE.search(text)),
            'resolution': bool(RESOLUTION_RE.search(errors)),
            'termination': bool(DIAGNOSTICS['termination'].search(errors))}


def classify(record):
    info = diagnostic_details(record)
    exit_code = record['exit_code']
    if record.get('execution_error'):
        return 'execution_error'
    if exit_code in (124,137) or record.get('timed_out'):
        return 'timeout'
    if info['resolution']:
        return 'resolution_failure' if exit_code==2 else 'unexpected_resolution_exit'
    if info['frontend']:
        return 'frontend_failure'
    summaries = info['summaries']
    if exit_code==0 and len(summaries)==1 and summaries[0][0]>0 and summaries[0][1]==0 and not info['error_lines']:
        return 'success' if info['warnings']==0 else 'warning_only'
    if exit_code==4 and len(summaries)==1 and summaries[0][1]>0 and info['error_lines']:
        if info['warnings']:
            return 'proof_failure_with_warnings'
        if info['termination']:
            return 'termination_failure'
        return 'proof_failure'
    if info['warnings']:
        return 'warning_or_other'
    return 'other'


def matches(case, record):
    actual = classify(record)
    diagnostic = case['expected_diagnostic']
    info = diagnostic_details(record)
    diagnostic_ok = diagnostic=='none' or diagnostic in info['diagnostic_categories']
    required=set(case['required_diagnostics']) <= set(info['diagnostic_categories'])
    named=named_details(case,record)
    return actual==case['expected'] and record['exit_code']==case['expected_exit'] and diagnostic_ok and required and named['matched']


def named_details(case,record):
    """Require actual method failures and provider observations, not closure labels."""
    result={'matched':False,'units':{},'local_targets':{},'target_diagnostics':{},
            'unlogged_definitions':[],'error':None}
    try:
        assert record['csv'], 'No CSV evidence'
        units={}
        for name,text in record['csv'].items():
            raw=base64.b64decode(record['csv_base64'][name],validate=True)
            assert sha(raw)==record['csv_sha256'][name], 'CSV hash mismatch'
            assert raw.decode('utf-8')==text, 'CSV text mismatch'
            reader=csv.DictReader(io.StringIO(text))
            assert reader.fieldnames and len(set(reader.fieldnames))==len(reader.fieldnames), 'Duplicate CSV headers'
            assert {'TestResult.DisplayName','TestResult.Outcome'} <= set(reader.fieldnames), 'CSV columns missing'
            for row in reader:
                assert None not in row and all(value is not None for value in row.values()), 'Malformed CSV row'
                label,outcome=row['TestResult.DisplayName'],row['TestResult.Outcome']
                assert label not in units, 'Duplicate CSV unit: '+label
                assert outcome in ('Passed','Failed'), 'Unfinished CSV unit: '+label
                units[label]=outcome
        result['units']=units
        target_names=set(case['expected_local_targets'])
        for target in target_names:
            label=target+' (correctness)'
            assert label in units, 'Missing method correctness unit: '+target
            observed={n:v for n,v in units.items() if n.startswith(target+' (')}
            assert observed and all(n in (label,target+' (well-formedness)') for n in observed), 'Unknown method unit kind'
            result['local_targets'][target]=all(value=='Passed' for value in observed.values())
            if case['expected_local_targets'][target] is False:
                assert units[label]=='Failed', 'Required correctness failure absent: '+target
        assert result['local_targets']==case['expected_local_targets'], 'Named target outcome mismatch'
        required_providers=set(case['expected_logged_provider_units'])
        assert required_providers <= set(units), 'Mandatory provider unit missing'
        optional_symbols={item['symbol'] for item in case['unlogged_definitions']}
        for label,outcome in units.items():
            symbol=label.rsplit(' (',1)[0]
            if symbol in target_names:continue
            assert label in required_providers or symbol in optional_symbols, 'Unexpected provider unit: '+label
            assert outcome=='Passed', 'Provider verification failed: '+label
        for item in case['unlogged_definitions']:
            assert record['source_sha256'][item['source_file']]==item['source_sha256'], 'Unlogged source mismatch'
            if not any(name.startswith(item['symbol']+' (') for name in units):
                result['unlogged_definitions'].append(item)
        by_file={'Helper.Transfer':[],'Client.Target':[]}
        for line in (record['stdout']+'\n'+record['stderr']).splitlines():
            match=re.match(r'^(?:.*[/\\])?(Helper|Client)\.dfy\(\d+,\d+\): Error:\s*(.*)$',line)
            if match:by_file[match.group(1)+('.Transfer' if match.group(1)=='Helper' else '.Target')].append(match.group(2))
        for target,required in case['expected_target_diagnostics'].items():
            messages='\n'.join(by_file[target])
            categories=[kind for kind,pattern in DIAGNOSTICS.items() if pattern.search(messages)]
            result['target_diagnostics'][target]=categories
            assert set(required) <= set(categories), 'Required target diagnostic absent: '+target
        result['matched']=True
    except (AssertionError,KeyError,ValueError,TypeError,csv.Error,UnicodeError) as error:
        result['error']=str(error) or type(error).__name__
    return result


def as_bytes(value):
    if value is None:
        return b''
    return value if isinstance(value,bytes) else value.encode('utf-8')


def verify(files):
    """One process per case; fake-process tests exercise exact staged byte copies."""
    assert 'All.dfy' in files and all(isinstance(raw,bytes) for raw in files.values())
    assert all(Path(name).name==name and name.endswith('.dfy') for name in files)
    start = time.monotonic()
    state = {'timed_out':False, 'execution_error':None}
    with tempfile.TemporaryDirectory(prefix='repodisco-repair-adapter-') as temp:
        folder = Path(temp)
        for name,raw in files.items():
            (folder/name).write_bytes(raw)
        assert {p.name:p.read_bytes() for p in folder.glob('*.dfy')} == files
        try:
            process = subprocess.run(COMMAND,cwd=folder,capture_output=True,timeout=75)
            code,stdout,stderr = process.returncode,as_bytes(process.stdout),as_bytes(process.stderr)
        except subprocess.TimeoutExpired as error:
            code,stdout,stderr = None,as_bytes(error.stdout),as_bytes(error.stderr)
            state['timed_out'] = True
        except OSError as error:
            code,stdout,stderr = None,b'',str(error).encode()
            state['execution_error'] = type(error).__name__
        raw_csv = {str(p.relative_to(folder)):p.read_bytes() for p in sorted(folder.rglob('*.csv'))}
    return {'command':COMMAND, 'exit_code':code,
            'stdout':stdout.decode('utf-8',errors='replace'), 'stderr':stderr.decode('utf-8',errors='replace'),
            'stdout_base64':base64.b64encode(stdout).decode(), 'stderr_base64':base64.b64encode(stderr).decode(),
            'stdout_sha256':sha(stdout), 'stderr_sha256':sha(stderr),
            'csv':{n:b.decode('utf-8',errors='replace') for n,b in raw_csv.items()},
            'csv_base64':{n:base64.b64encode(b).decode() for n,b in raw_csv.items()},
            'csv_sha256':{n:sha(b) for n,b in raw_csv.items()},
            'source_sha256':{n:sha(b) for n,b in sorted(files.items())},
            'elapsed_seconds':time.monotonic()-start, 'attempts':1, 'model_calls':0, **state}


def run(output):
    assert os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname(), 'Compute allocation required'
    assert output=='verification-001', 'Use the one fresh, pinned evidence directory'
    pins = validate_pins()
    out = ROOT/output
    out.mkdir(exist_ok=False)
    for name in sorted(set(pins)|{'runtime-manifest.json'}):
        dest = safe_path(out,name)
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/name,dest)
        assert dest.read_bytes()==(ROOT/name).read_bytes()
    environment = {'host':socket.gethostname(), 'job_id':os.environ['SLURM_JOB_ID'],
        'partition':os.environ.get('SLURM_JOB_PARTITION'), 'model_calls':0,
        'runtime_manifest_sha256':sha((ROOT/'runtime-manifest.json').read_bytes()),
        'fixture_manifest_sha256':sha((ROOT/'fixture-manifest.json').read_bytes()),
        'dafny_path':shutil.which('dafny'), 'z3_path':shutil.which('z3')}
    for program,expected in [('dafny',DAFNY_VERSION),('z3',Z3_VERSION)]:
        result = subprocess.run([program,'--version'],capture_output=True,timeout=15)
        stdout,stderr=as_bytes(result.stdout),as_bytes(result.stderr)
        environment[program]={'stdout':stdout.decode(errors='replace'),'stderr':stderr.decode(errors='replace'),
                              'exit_code':result.returncode,'expected_version':expected}
        (out/(program+'-version.stdout')).write_bytes(stdout)
        (out/(program+'-version.stderr')).write_bytes(stderr)
        save(out/'environment.json',environment)
        assert result.returncode==0 and stdout.decode().strip()==expected, program+' version mismatch'
    cases,rows = load(ROOT/'cases.json'),[]
    save(out/'summary.json',{'completed':0,'planned':len(cases),'all_expected':False,'model_calls':0,'checks':[]})
    for case in cases:
        files={p.name:p.read_bytes() for p in sorted((ROOT/case['path']).glob('*.dfy'))}
        assert {n:sha(b) for n,b in files.items()}==case['source_sha256']
        record=verify(files)
        info=diagnostic_details(record)
        actual=classify(record)
        matched=matches(case,record)
        record.update({'case_id':case['case_id'],'expected':case['expected'],
                       'expected_diagnostic':case['expected_diagnostic'],'actual':actual,'matched':matched,
                       'diagnostics':info,'named_evidence':named_details(case,record),
                       'expected_local_targets':case['expected_local_targets']})
        save(out/(case['case_id']+'.json'),record)
        raw_dir=out/'raw'/case['case_id']
        raw_dir.mkdir(parents=True,exist_ok=False)
        for stream in ('stdout','stderr'):
            raw=base64.b64decode(record[stream+'_base64'])
            assert sha(raw)==record[stream+'_sha256']
            (raw_dir/(stream+'.txt')).write_bytes(raw)
        for name,value in record['csv_base64'].items():
            dest=safe_path(raw_dir/'csv',name)
            dest.parent.mkdir(parents=True,exist_ok=True)
            raw=base64.b64decode(value)
            assert sha(raw)==record['csv_sha256'][name]
            dest.write_bytes(raw)
        rows.append({'case_id':case['case_id'],'expected':case['expected'],'actual':actual,'matched':matched,
                     'expected_diagnostic':case['expected_diagnostic'],'diagnostic_categories':info['diagnostic_categories'],
                     'named_expected_match':record['named_evidence']['matched'],
                     'local_targets':record['named_evidence']['local_targets'],
                     'evidence_sha256':sha((out/(case['case_id']+'.json')).read_bytes())})
        save(out/'summary.json',{'completed':len(rows),'planned':len(cases),'all_expected':len(rows)==len(cases) and all(r['matched'] for r in rows),
                               'model_calls':0,'checks':rows})
        print(case['case_id'],actual,'EXPECTED' if matched else 'UNEXPECTED',flush=True)
        if actual in ('timeout','execution_error'):
            break
    validate_pins()
    inventory={str(p.relative_to(out)):sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()}
    save(out/'evidence-manifest.json',inventory)
    return len(rows)==len(cases) and all(r['matched'] for r in rows)


if __name__=='__main__':
    assert len(sys.argv)==2, 'Specify verification-001'
    raise SystemExit(0 if run(sys.argv[1]) else 1)
