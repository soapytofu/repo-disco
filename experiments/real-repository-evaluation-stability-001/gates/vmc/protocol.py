"""Closed qualification profiles for exact host-authored controls, not a model edit API.

Raw records are trusted host observations. Source, command, toolchain and named
proof inventories are bound before accepting an observation; no code executes here.
"""
import csv,hashlib,io,json,re,math
from pathlib import Path,PurePosixPath

def sha(data):return hashlib.sha256(data).hexdigest()
def require(condition,message):
    if not condition:raise ValueError(message)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def safe_name(name):return isinstance(name,str) and name and not PurePosixPath(name).is_absolute() and all(x not in ('','..','.') for x in name.split('/')) and '\\' not in name

def expected_files(base,patches):
    require(all(safe_name(n) for n in base) and all(safe_name(n) for n in patches),'Unsafe source path')
    return {**base,**patches}

def check_sources(observed,expected):
    require(observed==expected,'Source additions, removals or bytes differ from approved candidate')

def check_record(record,profile,run_id,raw):
    require(record.get('run_id')==run_id,'Stale run')
    require(record.get('profile_sha256')==sha(canonical(profile)),'Profile differs')
    check_sources(record.get('source_sha256'),profile['source_sha256'])
    require(record.get('source_after_sha256')==profile['source_sha256'],'Source changed during execution')
    require(record.get('logical_command')==profile['logical_command'],'Command/scope differs')
    require(record.get('toolchain')==profile['toolchain'],'Toolchain differs')
    require(record.get('raw_sha256')=={n:sha(b) for n,b in sorted(raw.items())},'Raw evidence missing or changed')
    require(record.get('model_calls')==0 and record.get('attempts')==1,'Unexpected call provenance')
    require(type(record.get('exit_code')) is int and type(record.get('elapsed_seconds')) in (int,float),'Missing process result')
    require(math.isfinite(record['elapsed_seconds']) and record['elapsed_seconds']>=0,'Invalid runtime')

def dafny_observation(exit_code,stdout,stderr,csv_files,required_units=None):
    text=stdout.decode(errors='replace')+'\n'+stderr.decode(errors='replace')
    summary=[tuple(map(int,p)) for p in re.findall(r'^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$',text,re.M)]
    warnings=re.findall(r'^(.+\(\d+,\d+\): Warning:.*)$',text,re.M)
    units={};headers=[]
    for name,raw in sorted(csv_files.items()):
        reader=csv.DictReader(io.StringIO(raw.decode('utf-8'),newline=''),strict=True)
        require(reader.fieldnames==['TestResult.DisplayName','TestResult.Outcome','TestResult.Duration','TestResult.ResourceCount'],'Unknown Dafny 4.4 CSV schema')
        headers.append(reader.fieldnames)
        for row in reader:
            require(set(row)==set(reader.fieldnames) and all(isinstance(v,str) for v in row.values()),'Malformed CSV row')
            require(re.fullmatch(r'(?:\d+\.)?\d{2}:[0-5]\d:[0-5]\d(?:\.\d+)?',row['TestResult.Duration']) and row['TestResult.ResourceCount'].isdigit(),'Invalid unit resource metrics')
            n=row['TestResult.DisplayName'];outcome=row['TestResult.Outcome']
            require(n and n not in units,'Duplicate/empty named obligation')
            require(outcome in ('Passed','Failed','Skipped','NotExecuted','Inconclusive','Timeout'),'Unknown obligation outcome')
            units[n]=outcome
    text_failure=bool(re.search(r'Prover error:|SKIPPED due|Unhandled exception|Broken pipe|GLIBC.*not found',text,re.I))
    if exit_code in (124,137):category='TIMEOUT_OR_KILLED'
    elif text_failure:category='ENVIRONMENT_OR_SOLVER_ERROR'
    elif re.search(r'\bparse errors? detected\b',text):category='PARSE_FAILURE'
    elif re.search(r'resolution/type errors? detected',text):category='RESOLUTION_OR_TYPE_FAILURE'
    elif re.search(r'\b[1-9]\d* time outs?\b|out of resource|out of memory',text,re.I):category='VERIFIER_RESOURCE_FAILURE'
    elif len(summary)==1 and summary[0][1]>0 and exit_code!=0:category='PROOF_FAILURE'
    elif len(summary)==1 and summary[0][0]>0 and summary[0][1]==0 and exit_code in (0,2) and not re.search(r'\bError:',text):
        category='PROVED_WITH_WARNINGS' if warnings else 'PROVED'
    else:category='UNCLASSIFIED'
    complete=bool(units) and all(v in ('Passed','Failed') for v in units.values())
    if required_units is not None:complete=complete and set(units)==set(required_units)
    counts_match=len(summary)==1 and summary[0][0]==sum(v=='Passed' for v in units.values())
    proof_pass=category in ('PROVED','PROVED_WITH_WARNINGS') and complete and counts_match and all(v=='Passed' for v in units.values())
    return dict(category=category,summary=summary,units=units,csv_headers=headers,warnings=warnings,coverage_complete=complete,
                count_agreement=counts_match,proof_pass=proof_pass,strict_zero_warning_pass=proof_pass and not warnings and exit_code==0)
