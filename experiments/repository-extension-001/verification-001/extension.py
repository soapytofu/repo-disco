"""Contract-guided new-client extension. No provider or live model integration."""
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'guards'))
from branch_guard import validate_body

def hashes(files):return {k:hashlib.sha256(v).hexdigest() for k,v in sorted(files.items())}
def sources(path):return {p.name:p.read_bytes() for p in path.glob('*.dfy')}
def unique_object(pairs):
 out={}
 for k,v in pairs:
  if k in out:raise ValueError('Duplicate JSON field')
  out[k]=v
 return out

def sequence_body(body):
 """Only F.AppendA calls on nonempty + expressions of s,t,u; no proof bypass."""
 if len(body)>8192:raise ValueError('Body too long')
 calls=[]
 expr=r'[stu](?:\s*\+\s*[stu])*'
 pattern=re.compile(r'\s*F\.AppendA\(\s*('+expr+r')\s*,\s*('+expr+r')\s*\)\s*;')
 pos=0
 while body[pos:].strip():
  m=pattern.match(body,pos)
  if not m:raise ValueError('Only bounded sequence concatenation calls allowed')
  calls.append(m.groups());pos=m.end()
  if len(calls)>16:raise ValueError('Too many calls')
 return calls

def prepare(seed,task,raw):
 """Return a separate complete snapshot. Seed bytes remain unchanged.

 New ClientC.dfy is model-authored within a fixed interface. All.dfy receives one
 deterministic host-owned include. No existing file is model-editable.
 """
 if hashes(seed)!=task['seed_sha256']:raise ValueError('Seed hash mismatch')
 if 'ClientC.dfy' in seed:raise ValueError('New-file collision')
 if not isinstance(raw,str) or len(raw)>32768:raise ValueError('Response size/type')
 payload=json.loads(raw,object_pairs_hook=unique_object)
 if not isinstance(payload,dict) or set(payload)!={'ClientC.dfy'} or not isinstance(payload['ClientC.dfy'],str):raise ValueError('Expected single new client')
 candidate=payload['ClientC.dfy'];prefix=task['prefix'];suffix=task['suffix']
 if not candidate.startswith(prefix) or not candidate.endswith(suffix):raise ValueError('Protected interface changed')
 body=candidate[len(prefix):-len(suffix)]
 (validate_body if task['family']=='branch' else sequence_body)(body)
 result={**seed,'ClientC.dfy':candidate.encode(),'All.dfy':seed['All.dfy']+b'include "ClientC.dfy"\n'}
 return result
