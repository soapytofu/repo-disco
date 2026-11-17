"""Frozen-region lexical policy for four real-source repair sites.

This is not a Dafny/Verus typechecker or an arbitrary patch API. Balanced source
and a closed callable vocabulary prevent escaping the registered body or adding
trusted mechanisms. Native verification decides syntax, typing and mathematics.
"""
import hashlib,json,re
from pathlib import Path
from extract_response import extract_json,unique,reject_constant
ROOT=Path(__file__).resolve().parent
VERSION='real-repository-four-regions-v1'
MAX_BODY_BYTES=16384
MAX_TOKENS=4096
FORBIDDEN=set('assume admit axiom extern external external_body unsafe unreachable panic todo unimplemented arbitrary transmute include include_str include_bytes macro_rules fn impl trait mod use pub const static async await dyn union mut return yield break continue loop while for try catch ghost lemma method function predicate class datatype newtype import export ensures requires reads modifies decreases diverges assume_specification assume_false verify resource_limit timeLimit rlimit'.split())
TOKEN=re.compile(r'\s+|[A-Za-z_][A-Za-z_0-9]*|0[xX][0-9A-Fa-f]+|[0-9]+(?:u8|u16|u32|u64|int|nat)?|<==>|==>|&&&|\|\|\||::|:=|\.\.|==|!=|<=|>=|&&|\|\||->|[{}()\[\].,;:+*/%<>=!|&-]')
RULES={
 'vmc-swap':dict(calls=['multiset','PermutationsPreserveCardinality','MultisetAndSequenceCardinality'],protected=['s','i','j'],reveals=[],expression_required=True),
 'vmc-small-shuffle':dict(calls=['Model.Shuffle','Model.ShuffleCurried','Monad.Return','Monad.Result'],protected=['a','oldASeq','oldS','s','Model','Monad'],reveals=['aInvariant','sInvariant','aLength'],expression_required=False),
 'vest-roundtrip':dict(calls=['Seq::empty','self.theorem_serialize_dps_parse_roundtrip','self.lemma_serialize_equiv_on_empty','self.lemma_serialize_len','self.spec_serialize','self.spec_parse','self.spec_serialize_dps','self.byte_len','self.consistent','self.unambiguous','self.sp_roundtrip_inv','self.serialize_inv','self.equiv_inv','Some'],protected=['self','v','Seq'],reveals=[],expression_required=False),
 'vest-pair':dict(calls=['self.0.spec_serialize_dps','self.1.spec_serialize_dps','self.0.theorem_serialize_dps_parse_roundtrip','self.1.theorem_serialize_dps_parse_roundtrip','self.0.lemma_serialize_dps_prepend','self.1.lemma_serialize_dps_prepend','self.0.lemma_serialize_dps_len','self.1.lemma_serialize_dps_len','self.0.spec_parse','self.1.spec_parse','self.spec_parse','self.spec_serialize_dps','self.unambiguous','self.0.unambiguous','self.1.unambiguous','self.0.consistent','self.1.consistent','self.consistent','self.0.byte_len','self.1.byte_len','self.byte_len','Some'],protected=['self','v','obuf'],reveals=[],expression_required=False),
}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def task(tid):
 ts=json.loads((ROOT/'tasks.json').read_bytes());found=[t for t in ts if t['id']==tid]
 if len(found)!=1 or tid not in RULES:raise ValueError('Unknown task')
 return found[0]
def tokens(body):
 if not isinstance(body,str) or not body.isascii() or len(body.encode())>MAX_BODY_BYTES:raise ValueError('Body encoding/size')
 if any(x in body for x in ['//','/*','*/','"',"'",'#','\\','@','$','`']):raise ValueError('Comments, strings, attributes or escaped source forbidden')
 out=[];pos=0;stack=[]
 while pos<len(body):
  m=TOKEN.match(body,pos)
  if not m:raise ValueError('Unsupported source token at '+str(pos))
  x=m[0];pos=m.end()
  if x.isspace():continue
  if x in FORBIDDEN:raise ValueError('Forbidden source mechanism: '+x)
  if x in '{([':
   stack.append(x)
   if len(stack)>32:raise ValueError('Excessive nesting')
  elif x in '})]':
   if not stack or stack.pop()!={'}':'{',')':'(',']':'['}[x]:raise ValueError('Unbalanced body delimiters')
  out.append(x)
  if len(out)>MAX_TOKENS:raise ValueError('Too many tokens')
 if stack:raise ValueError('Unbalanced body delimiters')
 return out
def validate_body(body,tid):
 r=RULES[tid];ts=tokens(body)
 if tid.startswith('vest') and ('|' in ts or any(x=='||' and (i==0 or ts[i-1] in ('=','(', '{',',',';')) for i,x in enumerate(ts))):raise ValueError('No new closures/quantifier binders in these repair regions')
 if r['expression_required'] and not ts:raise ValueError('Function result expression required')
 if any(ts[i:i+2]==['=','>'] for i in range(len(ts)-1)):raise ValueError('No new closure/lambda definitions')
 locals_=set();bound=set(r['protected']);calls=[]
 # New value locals and tuple-pattern binders may be named freely, but cannot
 # shadow input receivers, module/type aliases or the permitted call vocabulary.
 reserved=bound|{re.split(r'\.|::',c)[0] for c in r['calls']}
 for i,x in enumerate(ts):
  if x in ('let','var'):
   j=i+1
   if j<len(ts) and ts[j]=='Some':j+=1
   while j<len(ts) and ts[j] not in (':=', '=',':',';'):
    name=ts[j]
    if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',name) and name!='Some':
     if name in reserved:raise ValueError('Protected name shadowing')
     locals_.add(name)
    j+=1
 for i,x in enumerate(ts):
  if x=='reveal':
   if i+2>=len(ts) or ts[i+1] not in r['reveals'] or ts[i+2]!=';':raise ValueError('Only listed named Dafny assumptions may be revealed')
  if x=='!' and i and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',ts[i-1]):raise ValueError('No macro invocation')
  if x=='(' and i:
   j=i-1
   if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',ts[j]):
    start=j
    while start>=2 and ts[start-1] in ('.','::') and re.fullmatch(r'[A-Za-z_0-9]+',ts[start-2]):start-=2
    callee=''.join(ts[start:i])
    if callee in ('assert','if','multiset'):
     if callee=='multiset' and tid!='vmc-swap':raise ValueError('Unexpected builtin')
    elif callee in r['calls']:calls.append(callee)
    elif callee.endswith('.len') and callee[:-4] in locals_|bound:pass
    else:raise ValueError('Call outside closed vocabulary: '+callee)
   elif ts[j]==')' and tid!='vmc-small-shuffle':raise ValueError('Indirect call forbidden')
  if x in ('=',':=') and i:
   # Assignments to existing inputs/receiver fields are outside these proof/
   # expression repair sites. Local initializations and equality tests remain.
   j=i-1
   if ts[j] in bound:raise ValueError('Protected input assignment')
 return dict(tokens=len(ts),locals=sorted(locals_),calls=calls,semantics_checked=False)
def reconstruct(tid,body):
 t=task(tid);src=(ROOT/'fixtures'/tid/'source.txt').read_bytes();b=t['boundary']
 if sha(src)!=t['source_sha256']:raise ValueError('Seed bytes changed')
 prefix,old,suffix=src[:b['start']],src[b['start']:b['end']],src[b['end']:]
 if (sha(prefix),sha(old),sha(suffix))!=(b['prefix_sha256'],b['seed_body_sha256'],b['suffix_sha256']):raise ValueError('Body boundary drift')
 decision=validate_body(body,tid);candidate=prefix+body.encode()+suffix
 return candidate,dict(policy=VERSION,task=tid,file=t['file'],seed_sha256=sha(src),candidate_sha256=sha(candidate),prefix_sha256=sha(prefix),suffix_sha256=sha(suffix),body_sha256=sha(body.encode()),**decision)
def parse_response(raw,tid):
 payload,envelope=extract_json(raw)
 obj=json.loads(payload,object_pairs_hook=unique,parse_constant=reject_constant)
 if not isinstance(obj,dict) or set(obj)!={'replacement'} or not isinstance(obj['replacement'],str):raise ValueError('Exactly one replacement string required')
 candidate,receipt=reconstruct(tid,obj['replacement']);receipt['envelope']=envelope
 return candidate,receipt
