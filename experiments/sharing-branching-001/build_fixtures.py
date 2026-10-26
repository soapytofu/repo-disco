"""Deterministic branch-sensitive task controls; no model calls."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
facts='''module Facts {
  export ViewA provides Wrap, Good, Case0A, Case1A
  export ViewB provides Wrap, Good, Case0B, Case1B
  opaque function Wrap(x: int): int { x }
  opaque predicate Good(x: int) { x >= 0 }
'''
for suffix in 'AB':
 facts+=f'''  lemma Case0{suffix}(x: int)
    requires x >= 0
    ensures Good(Wrap(x))
  {{ reveal Good(), Wrap(); }}
  lemma Case1{suffix}(x: int)
    requires x < 0
    ensures Good(Wrap(-x))
  {{ reveal Good(), Wrap(); }}
'''
facts+='}\n';checks=[]
for condition in ['shared','separate']:
 for variant in ['reference','empty','only_nonnegative','only_negative','swapped_calls','wrong_boundary','wrong_argument','missing_else']:
  folder=ROOT/'fixtures'/f'{condition}_{variant}';folder.mkdir(parents=True,exist_ok=True)
  (folder/'Facts.dfy').write_text(facts);(folder/'All.dfy').write_text('include "ClientA.dfy"\ninclude "ClientB.dfy"\n')
  for client in 'AB':
   suffix='B' if condition=='separate' and client=='B' else 'A';expr='x' if client=='A' else '(x - y)'
   pos=f'F.Case0{suffix}({expr});';neg=f'F.Case1{suffix}({expr});'
   body=f'    if {expr} >= 0 {{\n      {pos}\n    }} else {{\n      {neg}\n    }}\n'
   if variant=='empty':body=''
   elif variant=='only_nonnegative':body='    '+pos+'\n'
   elif variant=='only_negative':body='    '+neg+'\n'
   elif variant=='swapped_calls':body=body.replace(pos,'TEMP').replace(neg,pos).replace('TEMP',neg)
   elif variant=='wrong_boundary':body=body.replace('>= 0','> 0')
   elif variant=='wrong_argument':body=body.replace(pos,f'F.Case0{suffix}({expr} + 1);')
   elif variant=='missing_else':body=f'    if {expr} >= 0 {{\n      {pos}\n    }}\n'
   text=f'''include "Facts.dfy"
module Client{client} {{
  import F = Facts`View{suffix}
  lemma Prove(x: int, y: int)
    ensures F.Good(F.Wrap(if {expr} >= 0 then {expr} else -{expr}))
  {{
'''+body+'  }\n}\n'
   (folder/f'Client{client}.dfy').write_text(text)
  for entry in (['All.dfy','ClientA.dfy','ClientB.dfy'] if variant=='reference' else ['ClientA.dfy','ClientB.dfy']):checks.append(dict(variant=folder.name,entry=entry,expected_exit=0 if variant=='reference' else 4))
(ROOT/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
(ROOT/'task.json').write_text(json.dumps(dict(family='sign-conditional-wrap',conditions=['shared','separate'],edit_scope='client lemma bodies only; branch grammar requires separate guard',model_calls=0,checks=len(checks),source_visibility='full source; opaque definitions hidden from client verifier, not from future model'),indent=2)+'\n')
print(len(checks),'controls built')
