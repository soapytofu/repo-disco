from pathlib import Path
import json,shutil
r=Path('experiments/sharing-composition-002'); old=Path('experiments/sharing-reasoning-001')
facts='''module Facts {
  export ViewA provides Value, Step, Pair, Large, LiftA, JoinA, Finish
  export ViewB provides Value, Step, Pair, Large, LiftB, JoinB, Finish
  opaque function Value(x: nat): nat { x }
  opaque function Step(x: nat): nat { x + 1 }
  opaque function Pair(x: nat, y: nat): nat { x + y }
  opaque predicate Large(x: nat, k: nat) { Value(x) > k }
'''
for suffix in 'AB':
 facts+=f'''  lemma Lift{suffix}(x: nat)
    ensures Value(Step(x)) == Value(x) + 1
  {{ reveal Value(), Step(); }}
  lemma Join{suffix}(x: nat, y: nat)
    requires Value(x) > 0 && Value(y) > 0
    ensures Value(Pair(x, y)) == Value(x) + Value(y)
  {{ reveal Value(), Pair(); }}
'''
facts+='''  lemma Finish(x: nat, k: nat)
    requires Value(x) > k
    ensures Large(x, k)
  { reveal Large(); }
}
'''
checks=[];design=[]
for tier in ['diamond','nested']:
 for condition in ['shared','separate']:
  sources={}; bodies={}
  for client in 'AB':
   suffix='B' if client=='B' and condition=='separate' else 'A'
   a,b,c=('s','t','u') if client=='A' else ('t','u','s')
   calls=[f'F.Lift{suffix}({a});',f'F.Lift{suffix}({b});']
   term=f'F.Pair(F.Step({a}), F.Step({b}))'
   calls+=[f'F.Join{suffix}(F.Step({a}), F.Step({b}));']
   if tier=='nested':
    calls+=[f'F.Lift{suffix}({c});',f'F.Join{suffix}({term}, F.Step({c}));']
    term=f'F.Pair({term}, F.Step({c}))'
   threshold=2 if tier=='diamond' else 3
   calls+=[f'F.Finish({term}, k + {threshold});']
   prefix=f'''include "Facts.dfy"
module Client{client} {{
  import F = Facts`View{suffix}
  lemma Prove(s: nat, t: nat, u: nat, k: nat)
    requires F.Value({a}) > k
    ensures F.Large({term}, k + {threshold})
  {{
'''
   sources[client]=prefix;bodies[client]=calls
  variants={'reference':bodies,'empty':{c:[] for c in 'AB'}}
  for i in range(len(bodies['A'])):
   variants[f'omit_{i+1}']={c:[v for j,v in enumerate(bodies[c]) if i!=j] for c in 'AB'}
  variants['join_early']={c:[bodies[c][2]]+bodies[c][:2]+bodies[c][3:] for c in 'AB'}
  variants['wrong_lift']={c:[bodies[c][0].replace('(s)','(u)') if c=='A' else bodies[c][0].replace('(t)','(s)')]+bodies[c][1:] for c in 'AB'}
  for variant,bs in variants.items():
   name=f'{tier}_{condition}_{variant}';p=r/'fixtures'/name;p.mkdir(parents=True,exist_ok=True)
   (p/'Facts.dfy').write_text(facts);(p/'All.dfy').write_text('include "ClientA.dfy"\ninclude "ClientB.dfy"\n')
   for c in 'AB':(p/f'Client{c}.dfy').write_text(sources[c]+''.join('    '+v+'\n' for v in bs[c])+'  }\n}\n')
   # Joint reference plus each client; negative controls per client establish both need each step.
   for entry in (['All.dfy','ClientA.dfy','ClientB.dfy'] if variant=='reference' else ['ClientA.dfy','ClientB.dfy']):
    checks.append(dict(variant=name,entry=entry,expected_exit=0 if variant=='reference' else 4))
  design.append(dict(tier=tier,condition=condition,calls_per_client=len(bodies['A']),model_calls=0))
(r/'checks.json').write_text(json.dumps(checks,indent=2)+'\n');(r/'task.json').write_text(json.dumps(design,indent=2)+'\n')
shutil.copy2(old/'run_verification.py',r/'run_verification.py')
print(len(checks),'checks built')
