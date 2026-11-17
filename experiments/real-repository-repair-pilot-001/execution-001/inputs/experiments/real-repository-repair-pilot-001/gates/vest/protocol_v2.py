"""Versioned native Verus report reader; preserve repeated friendly labels.

A timed label is not a unique proof obligation. Exact (crate,module,label,mode)
multiplicities are checked; all occurrences must pass. Native summary counts
remain separate. This is a qualification scorer for frozen host controls.
"""
import collections,json,re
from .protocol import sha,require,canonical,safe_name,expected_files,check_sources,check_record

def json_reports(raw):
    text=raw.decode('utf-8');decoder=json.JSONDecoder();reports=[];index=0
    while index<len(text):
        match=re.search(r'^\{',text[index:],re.M)
        if match is None:break
        pos=index+match.start()
        try:value,end=decoder.raw_decode(text,pos)
        except ValueError as e:raise ValueError('Truncated/malformed native JSON object') from e
        index=end
        if isinstance(value,dict) and 'verification-results' in value:reports.append(value)
    return reports

def warnings(text):
    # Keep complete diagnostic blocks, including source locations/help. Cargo's
    # generated-N-warnings line is a summary, not an additional diagnostic.
    blocks=[];cargo=[];lines=text.splitlines();i=0
    while i<len(lines):
        if re.match(r'^warning(?:\[[^\]]+\])?:',lines[i]):
            if re.match(r'^warning: `[^`]+` .*generated [0-9]+ warnings?$',lines[i]):
                cargo.append(lines[i]);i+=1;continue
            start=i;i+=1
            while i<len(lines) and lines[i].strip():i+=1
            blocks.append('\n'.join(lines[start:i]))
        else:i+=1
    return blocks,cargo

def verus_observation(exit_code,stdout,stderr,required=None):
    reports=json_reports(stdout)+json_reports(stderr);units={};inventory={};summaries={}
    errors=verified=0;entire=True;valid=bool(reports);consistent=True
    for report in reports:
        result=report['verification-results'];require(isinstance(result,dict),'Invalid Verus summary')
        require(type(result.get('encountered-vir-error')) is bool and type(result.get('encountered-error')) is bool,'Missing error flags')
        valid=valid and not result['encountered-vir-error']
        er=result.get('errors',0);ve=result.get('verified',0)
        require(type(er) is int and type(ve) is int and er>=0 and ve>=0,'Invalid Verus counts')
        errors+=er;verified+=ve;entire=entire and result.get('is-verifying-entire-crate') is True
        local=[]
        for module in report.get('times-ms',{}).get('smt',{}).get('smt-run-module-times',[]):
            require(isinstance(module.get('module'),str),'Missing module name')
            for unit in module.get('function-breakdown',[]):
                name=unit.get('function');mode=unit.get('mode:')
                require(isinstance(name,str) and '::' in name and mode in ('exec','proof','spec'),'Missing function identity')
                require(type(unit.get('success')) is bool,'Missing function outcome')
                local.append((name.split('::')[0],module['module'],name,mode,unit['success']))
        crates={x[0] for x in local}&{'vstd','vest_lib','vest_dev'};require(len(crates)<=1,'Mixed project crate labels in one report')
        crate=next(iter(crates)) if crates else 'unidentified'
        require(crate not in summaries,'Duplicate native crate report')
        counts=collections.Counter(json.dumps((crate,*x[1:4]),separators=(',',':')) for x in local)
        inventory.update(counts)
        for _,_,name,_,passed in local:units[name]=units.get(name,True) and passed
        summaries[crate]=dict(result,version=report.get('verus'),num_threads=report.get('times-ms',{}).get('num-threads'),timed_entries=len(local),unique_friendly_labels=len({x[2] for x in local}))
        if result.get('success') is True:
            consistent=consistent and er==0 and not result['encountered-error'] and not result['encountered-vir-error'] and all(x[4] for x in local)
    text=stdout.decode(errors='replace')+'\n'+stderr.decode(errors='replace')
    wrn,cargo=warnings(text)
    if exit_code in (124,137):category='TIMEOUT_OR_KILLED'
    elif not reports and re.search(r'linker .* not found|GLIBC.*not found|failed to get .*dependency|failed to download',text,re.I):category='ENVIRONMENT_OR_BUILD_ERROR'
    elif re.search(r'error\[E[0-9]+\]',text):category='RUST_FRONTEND_FAILURE'
    elif not reports:category='NO_VERIFICATION_REPORT'
    elif not valid or not consistent:category='FRONTEND_OR_EXECUTION_ERROR'
    elif errors:category='PROOF_FAILURE'
    elif exit_code==0 and entire and all(x['verification-results'].get('success') is True for x in reports):category='PROVED_WITH_WARNINGS' if wrn else 'PROVED'
    else:category='INCOMPLETE_OR_UNCLASSIFIED'
    covered=bool(inventory)
    if required is not None:
        covered=covered and inventory==required['inventory'] and set(summaries)==set(required['crates'])
        covered=covered and all(summaries[c]['version']==required['version'] and summaries[c]['num_threads']==required['num_threads'] for c in summaries)
    return dict(category=category,crates=summaries,units=units,inventory=inventory,entire_crate=entire,errors=errors,verified=verified,warnings=wrn,cargo_warning_summaries=cargo,
        coverage_complete=covered,proof_pass=category in ('PROVED','PROVED_WITH_WARNINGS') and covered and all(units.values()),strict_zero_warning_pass=category=='PROVED' and covered and all(units.values()))
