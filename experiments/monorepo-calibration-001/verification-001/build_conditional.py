"""Build one monorepo calibration family and explicit verifier controls, offline."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def sha(data):return hashlib.sha256(data).hexdigest()
KERNEL='''module Kernel {
  export Public provides Encode, Safe, Ready1, Ready2 reveals Abs
  export Internal reveals Encode, Safe, Ready1, Ready2, Abs
  function Abs(x: int): int { if x >= 0 then x else -x }
  opaque function Encode(x: int, y: int): int { y - x }
  opaque predicate Safe(z: int) { z >= 0 }
  opaque predicate Ready1(x: int, y: int) { x >= 0 }
  opaque predicate Ready2(x: int, y: int) { x >= 0 && y >= x }
}
'''
STAGE1='''include "Kernel.dfy"
module Stage1 {
  export Public provides K, Start
  import K = Kernel`Internal
  lemma Start(x: int, y: int)
    requires x >= 0
    ensures K.Ready1(x, y)
  { reveal K.Ready1(); }
}
'''
STAGE2='''include "Kernel.dfy"
module Stage2 {
  export Public provides K, Advance
  import K = Kernel`Internal
  lemma Advance(x: int, y: int)
    requires K.Ready1(x, y)
    requires y >= x
    ensures K.Ready2(x, y)
  { reveal K.Ready1(); reveal K.Ready2(); }
}
'''
STAGE3='''include "Kernel.dfy"
module Stage3 {
  export Shallow provides K, Direct
  export Deep provides K, Finish
  import K = Kernel`Internal
  lemma Direct(x: int, y: int)
    requires x >= 0 && y >= x
    ensures K.Safe(K.Encode(x, y))
  { reveal K.Ready2(); reveal K.Safe(); reveal K.Encode(); }
  lemma Finish(x: int, y: int)
    requires K.Ready2(x, y)
    ensures K.Safe(K.Encode(x, y))
  { reveal K.Ready2(); reveal K.Safe(); reveal K.Encode(); }
}
'''
CONTRACT='K.Safe(K.Encode(K.Abs(x), if y >= K.Abs(x) then y else K.Abs(x) + K.Abs(x) - y))'

def proof(depth):
 def calls(a,b,indent):
  items=[f'End.Direct({a}, {b});'] if depth=='shallow' else [f'S1.Start({a}, {b});',f'S2.Advance({a}, {b});',f'End.Finish({a}, {b});']
  return ''.join(' '*indent+s+'\n' for s in items)
 return ('    if x >= 0 {\n      if y >= x {\n'+calls('x','y',8)+'      } else {\n'+calls('x','x + x - y',8)+'      }\n    } else {\n      if y >= -x {\n'+calls('-x','y',8)+'      } else {\n'+calls('-x','-x - x - y',8)+'      }\n    }\n')

def helper(label,depth,body,delegate=False):
 includes='include "Kernel.dfy"\n'
 if delegate:
  includes+='include "HelperA.dfy"\n';imports='  import H = HelperA\n'
 else:
  includes+='include "Stage1.dfy"\ninclude "Stage2.dfy"\ninclude "Stage3.dfy"\n'
  imports=('  import S1 = Stage1`Public\n  import S2 = Stage2`Public\n' if depth=='deep' else '')+f'  import End = Stage3`{"Deep" if depth=="deep" else "Shallow"}\n'
 return includes+f'module Helper{label} {{\n  import K = Kernel`Public\n'+imports+'  lemma {:induction false} Prove(x: int, y: int)\n    ensures '+CONTRACT+'\n  {\n'+body+'  }\n}\n'

def client(label):
 args=('a + b','a - b') if label=='A' else ('a - b','a + b')
 return f'''include "Kernel.dfy"
include "Helper{label}.dfy"
module Client{label} {{
  import K = Kernel`Public
  import H = Helper{label}
  lemma Use(a: int, b: int)
    ensures K.Safe(K.Encode(K.Abs({args[0]}), if ({args[1]}) >= K.Abs({args[0]}) then ({args[1]}) else K.Abs({args[0]}) + K.Abs({args[0]}) - ({args[1]})))
  {{ H.Prove({args[0]}, {args[1]}); }}
}}
'''

def snapshot(depth,sharing,variant):
 body=proof(depth)
 a=body;b=body
 if variant=='empty':a=b=''
 if variant=='wrong_argument':a=b=body.replace('x + x - y','y - x - x').replace('-x - x - y','y + x + x')
 if variant=='missing_prerequisite':
  a=b=(''.join(line for line in body.splitlines(True) if 'S2.Advance' not in line) if depth=='deep' else body.replace('if y >= x {','if y >= 0 {'))
 if variant=='only_a':b=''
 if variant=='only_b':a=''
 if variant=='hidden_shortcut':a=b=body.replace('End.Finish','End.Direct')
 files={'Kernel.dfy':KERNEL,'Stage1.dfy':STAGE1,'Stage2.dfy':STAGE2,'Stage3.dfy':STAGE3,'HelperA.dfy':helper('A',depth,a),'HelperB.dfy':helper('B',depth,'    H.Prove(x, y);\n',True) if sharing=='shared' else helper('B',depth,b),'ClientA.dfy':client('A'),'ClientB.dfy':client('B'),'All.dfy':'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}
 if variant=='weakened_helper_contract':files['HelperA.dfy']=files['HelperA.dfy'].replace('ensures '+CONTRACT,'ensures true')
 return files

def main():
 dest=ROOT/'fixtures';dest.mkdir(exist_ok=False);tasks=[];checks=[]
 for depth in ['shallow','deep']:
  for sharing in ['shared','separate']:
   task_id=f'conditional-{depth}-{sharing}'
   variants=['reference','empty','wrong_argument','missing_prerequisite','weakened_helper_contract']
   if sharing=='separate':variants += ['only_a','only_b']
   if depth=='deep':variants += ['hidden_shortcut']
   for variant in variants:
    files=snapshot(depth,sharing,variant);path=dest/task_id/variant;path.mkdir(parents=True)
    for name,text in files.items():(path/name).write_text(text)
    checks.append(dict(task_id=task_id,variant=variant,path=str(path.relative_to(ROOT)),expected='success' if variant=='reference' else 'resolution_failure' if variant=='hidden_shortcut' else 'proof_failure',source_sha256={n:sha(t.encode()) for n,t in files.items()}))
   files=snapshot(depth,sharing,'empty')
   imports={}
   for name,text in files.items():
    if name=='All.dfy':continue
    imports[name[:-4]]={alias:target for alias,target in re.findall(r'import (\w+) = (\w+)',text)}
   tasks.append(dict(task_id=task_id,family='conditional_preconditions',semantic_instance='dependent-reflection-001',split='calibration-development',repository_boundary='single_monorepo_workspace',depth=depth,sharing=sharing,entry='All.dfy',editable_files=['HelperA.dfy'] if sharing=='shared' else ['HelperA.dfy','HelperB.dfy'],editable_scope='Prove lemma bodies only; full guard still pending',client_count=2,reference_contract_application_chain=1 if depth=='shallow' else 3,reference_chain_not_proven_minimal=True,imports={'modules':list(imports),'imports':imports},source_sha256={n:sha(t.encode()) for n,t in files.items()},bytes=sum(len(t.encode()) for t in files.values()),includes={n:re.findall(r'include "([^"]+)"',text) for n,text in files.items()}))
 (ROOT/'tasks.json').write_text(json.dumps(tasks,indent=2)+'\n');(ROOT/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
 print(len(tasks),'calibration variants;',len(checks),'planned verifier controls; zero model calls')
if __name__=='__main__':main()
