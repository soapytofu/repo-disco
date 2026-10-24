"""Offline parser v1: one JSON object, exact filenames, guarded proof bodies.
No API calls. Wrappers are never executed. No escape or proof repair.
"""
import json,re
CLIENTS=('ClientA.dfy','ClientB.dfy')
MAX_BYTES=131072

def unique(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise ValueError('Duplicate key')
        out[key]=value
    return out

def extract(raw):
    if not isinstance(raw,str) or len(raw.encode())>MAX_BYTES: raise ValueError('Invalid response size/type')
    decoder=json.JSONDecoder(); found=[]; i=0
    while i<len(raw):
        if raw[i]!='{': i+=1; continue
        try: value,end=decoder.raw_decode(raw[i:])
        except ValueError: i+=1; continue
        found.append((i,i+end));i+=end
    if len(found)!=1: raise ValueError('Expected one unambiguous JSON object')
    start,end=found[0]; payload=raw[start:end]
    files=json.loads(payload,object_pairs_hook=unique)
    if not isinstance(files,dict) or set(files)!=set(CLIENTS) or not all(isinstance(v,str) for v in files.values()):
        raise ValueError('Expected exactly two client strings')
    return files,dict(json_start=start,json_end=end,prefix_chars=start,suffix_chars=len(raw)-end,extraction='exact substring; JSON decode only')

def parse_response(raw,originals):
    files,metadata=extract(raw); accepted={}
    for name in CLIENTS:
        original=originals[name];suffix='  }\n}\n';prefix=original[:-len(suffix)]
        candidate=files[name].strip()+'\n'
        if not original.endswith(suffix) or not candidate.startswith(prefix) or not candidate.endswith(suffix):
            raise ValueError('Protected client bytes changed')
        body=candidate[len(prefix):-len(suffix)];end=0
        for call in re.finditer(r'F\.[A-Za-z_][A-Za-z_0-9]*\s*\(([^;{}]*)\)\s*;',body):
            if body[end:call.start()].strip():raise ValueError('Only lemma calls allowed')
            args=re.sub(r'F\.(?:Step|Pair)\b','',call.group(1))
            if re.search(r'[^A-Za-z_0-9,()\s+\-]',args):raise ValueError('Forbidden argument syntax')
            if set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*',args))-{'s','t','u','k'}:raise ValueError('Unknown identifier')
            depth=0
            for char in args:
                depth+=(char=='(')-(char==')')
                if depth<0:raise ValueError('Unbalanced parentheses')
            if depth:raise ValueError('Unbalanced parentheses')
            end=call.end()
        if body[end:].strip():raise ValueError('Only lemma calls allowed')
        accepted[name]=candidate
    return accepted,metadata
