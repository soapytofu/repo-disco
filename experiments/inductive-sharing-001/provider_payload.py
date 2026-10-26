"""Exact JSON payload extraction copied from tolerant-v1; original unchanged.
No API calls. Wrappers are never executed. No escape or proof repair.
"""
import json,re
CLIENTS=('Facts.dfy',)
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
        raise ValueError('Expected exactly one Facts.dfy string')
    return files,dict(json_start=start,json_end=end,prefix_chars=start,suffix_chars=len(raw)-end,extraction='exact substring; JSON decode only')
