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

def json_reports(raw):
    """Read complete top-level JSON objects from mixed native output; never nested matches."""
    text=raw.decode('utf-8');decoder=json.JSONDecoder();reports=[];index=0
    while index<len(text):
        match=re.search(r'^\{',text[index:],re.M)
        if match is None:break
        pos=index+match.start()
        try:value,end=decoder.raw_decode(text,pos)
        except ValueError:index=pos+1;continue
        index=end
        if isinstance(value,dict) and 'verification-results' in value:reports.append(value)
    return reports

def verus_observation(exit_code,stdout,stderr,required_functions=None):
    reports=json_reports(stdout)+json_reports(stderr)
    units={};entire=True;errors=0;verified=0;valid=bool(reports)
    for report in reports:
        result=report['verification-results']
        require(isinstance(result,dict),'Invalid Verus summary')
        entire=entire and result.get('is-verifying-entire-crate') is True
        errors+=result.get('errors',0);verified+=result.get('verified',0)
        valid=valid and result.get('encountered-vir-error') is False
        require(type(result.get('errors',0)) is int and type(result.get('verified',0)) is int,'Invalid Verus counts')
        modules=report.get('times-ms',{}).get('smt',{}).get('smt-run-module-times',[])
        # Exact key nesting is bound by a separately reviewed actual native baseline.
        for module in modules:
            for unit in module.get('function-breakdown',[]):
                name=unit.get('function');require(name and name not in units,'Missing/duplicate Verus function')
                require(type(unit.get('success')) is bool,'Missing function outcome')
                units[name]=unit['success']
    text=stdout.decode(errors='replace')+'\n'+stderr.decode(errors='replace')
    if exit_code in (124,137):category='TIMEOUT_OR_KILLED'
    elif not reports and re.search(r'linker .* not found|GLIBC.*not found|failed to get .*dependency|failed to download',text,re.I):category='ENVIRONMENT_OR_BUILD_ERROR'
    elif not reports and re.search(r'error\[E[0-9]+\]',text):category='RUST_FRONTEND_FAILURE'
    elif not reports:category='NO_VERIFICATION_REPORT'
    elif not valid:category='FRONTEND_OR_EXECUTION_ERROR'
    elif errors:category='PROOF_FAILURE'
    elif exit_code==0 and entire and all(x['verification-results'].get('success') is True for x in reports):category='PROVED'
    else:category='INCOMPLETE_OR_UNCLASSIFIED'
    covered=bool(units) and (required_functions is None or set(units)==set(required_functions))
    warnings=re.findall(r'^warning(?:\[[^\]]+\])?:.*$',text,re.M)
    if category=='PROVED' and warnings:category='PROVED_WITH_WARNINGS'
    return dict(category=category,reports=len(reports),units=units,entire_crate=entire,errors=errors,verified=verified,warnings=warnings,
                coverage_complete=covered,proof_pass=category in ('PROVED','PROVED_WITH_WARNINGS') and covered and all(units.values()),
                strict_zero_warning_pass=category=='PROVED' and covered and all(units.values()) and not warnings)
