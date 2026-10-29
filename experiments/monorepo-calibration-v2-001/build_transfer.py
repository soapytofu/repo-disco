"""New development instance: alias-aware balance transfer with conservation.
Construction only; no models or verifier. Prior frozen tasks remain untouched.
"""
import hashlib, importlib.util, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent/'monorepo-calibration-001/remaining-families-001/build.py'
spec = importlib.util.spec_from_file_location('old_builder', OLD)
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)

def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def save(p, value): p.write_text(json.dumps(value, indent=2)+'\n')

def family():
 kernel='''module Kernel {
  export Public reveals Move provides Valid, Transfer, Debited, Credited
  export Internal reveals Move, Valid, Transfer, Debited, Credited
  function Move(m: map<int,int>, k: int, j: int, v: int): map<int,int>
    requires k in m && j in m
  { if k == j then m else m[k := m[k] - v][j := m[j] + v] }
  opaque predicate Valid(m: map<int,int>) { forall q :: q in m ==> m[q] >= 0 }
  opaque predicate Transfer(m: map<int,int>, n: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m
  {
    n.Keys == m.Keys && k in n && j in n &&
    n[k] + n[j] == m[k] + m[j] &&
    (if k == j then n == m else n[k] == m[k] - v && n[j] == m[j] + v) &&
    (forall q :: q in m && q != k && q != j ==> q in n && n[q] == m[q])
  }
  opaque predicate Debited(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m
  { k != j && 0 <= v <= m[k] && Valid(m) && Valid(m[k := m[k] - v]) }
  opaque predicate Credited(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m
  { Valid(Move(m,k,j,v)) && Transfer(m,Move(m,k,j,v),k,j,v) }
}
'''
 stages=['''include "Kernel.dfy"
module Stage1 {
  export Public provides K, Debit
  import K = Kernel`Internal
  lemma Debit(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m && k != j
    requires K.Valid(m) && 0 <= v <= m[k]
    ensures K.Debited(m,k,j,v)
  { reveal K.Valid(); reveal K.Debited(); }
}
''','''include "Kernel.dfy"
module Stage2 {
  export Public provides K, Credit
  import K = Kernel`Internal
  lemma Credit(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m
    requires K.Debited(m,k,j,v)
    ensures K.Credited(m,k,j,v)
  { reveal K.Debited(); reveal K.Valid(); reveal K.Credited(); reveal K.Transfer(); }
}
''','''include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Alias, Direct
  export Deep provides K, Alias, Finish
  import K = Kernel`Internal
  lemma Alias(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m && k == j && K.Valid(m)
    ensures K.Valid(K.Move(m,k,j,v)) && K.Transfer(m,K.Move(m,k,j,v),k,j,v)
  { reveal K.Transfer(); }
  lemma Direct(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m && k != j
    requires K.Valid(m) && 0 <= v <= m[k]
    ensures K.Valid(K.Move(m,k,j,v)) && K.Transfer(m,K.Move(m,k,j,v),k,j,v)
  { reveal K.Valid(); reveal K.Transfer(); }
  lemma Finish(m: map<int,int>, k: int, j: int, v: int)
    requires k in m && j in m && K.Credited(m,k,j,v)
    ensures K.Valid(K.Move(m,k,j,v)) && K.Transfer(m,K.Move(m,k,j,v),k,j,v)
  { reveal K.Credited(); }
}
''']
 contract='K.Valid(K.Move(m,k,j,v)) && K.Transfer(m,K.Move(m,k,j,v),k,j,v)'
 decl='  lemma {:induction false} Prove(m: map<int,int>, k: int, j: int, v: int)\n    requires k in m && j in m\n    requires K.Valid(m) && 0 <= v <= m[k]\n    ensures '+contract+'\n'
 def proof(depth):
  nonalias='      End.Direct(m,k,j,v);\n' if depth=='shallow' else '      S1.Debit(m,k,j,v);\n      S2.Credit(m,k,j,v);\n      End.Finish(m,k,j,v);\n'
  return '    if k == j {\n      End.Alias(m,k,j,v);\n    } else {\n'+nonalias+'    }\n'
 clients=[('m: map<int,int>, k: int, j: int, v: int','    requires k in m && j in m && K.Valid(m) && 0 <= v <= m[k]\n',contract,'m,k,j,v'),('m: map<int,int>, k: int, j: int, v: int','    requires k in m && j in m && K.Valid(m) && 0 <= v <= m[j]\n','K.Valid(K.Move(m,j,k,v)) && K.Transfer(m,K.Move(m,j,k,v),j,k,v)','m,j,k,v')]
 return dict(kernel=kernel,stages=stages,spec=decl,proof=proof,clients=clients,args='m,k,j,v',mutations={
  'wrong_alias_branch':lambda b,d:b.replace('k == j','k != j'),
  'missing_alias':lambda b,d:b.replace('      End.Alias(m,k,j,v);\n',''),
  'wrong_amount':lambda b,d:b.replace('m,k,j,v','m,k,j,v + 1'),
  'wrong_direction':lambda b,d:b.replace('m,k,j,v','m,j,k,v'),
  'missing_credit':lambda b,d:b.replace('      S2.Credit(m,k,j,v);\n','') if d=='deep' else b.replace('      End.Direct(m,k,j,v);\n','')})

def main():
 (ROOT/'fixtures').mkdir(exist_ok=False); tasks=[]; checks=[]; f=family()
 for depth in ['shallow','deep']:
  for sharing in ['shared','separate']:
   tid=f'transfer-{depth}-{sharing}'
   variants=['reference','empty',*f['mutations'],'weakened_helper_contract']
   if sharing=='separate':variants+=['only_a','only_b']
   if depth=='deep':variants+=['hidden_shortcut']
   for variant in variants:
    files=builder.snapshot(f,depth,sharing,variant); p=ROOT/'fixtures'/tid/variant;p.mkdir(parents=True)
    for n,s in files.items():(p/n).write_text(s)
    checks.append(dict(task_id=tid,variant=variant,path=str(p.relative_to(ROOT)),expected='success' if variant=='reference' else 'resolution_failure' if variant=='hidden_shortcut' else 'proof_failure',source_sha256={n:sha(s) for n,s in files.items()}))
   files=builder.snapshot(f,depth,sharing,'empty')
   tasks.append(dict(task_id=tid,family='map_transfer',semantic_instance='alias-aware-conservation-001',lineage='development finite-map frames; adds alias cases, source balance bound, exact balances, conservation and reverse-direction client',split='development',depth=depth,sharing=sharing,entry='All.dfy',editable_files=['HelperA.dfy'] if sharing=='shared' else ['HelperA.dfy','HelperB.dfy'],variables=['m','k','j','v'],calls={'End.Alias':4,**({'End.Direct':4} if depth=='shallow' else {'S1.Debit':4,'S2.Credit':4,'End.Finish':4})},source_sha256={n:sha(s) for n,s in files.items()},reference_depth={'alias':1,'distinct_keys':1 if depth=='shallow' else 3},reference_depth_not_minimal=True))
 save(ROOT/'tasks.json',tasks);save(ROOT/'checks.json',checks)
 print(len(tasks),'matched snapshots;',len(checks),'verifier checks planned; zero model calls')
if __name__=='__main__':main()
