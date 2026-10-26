"""Inductive helper synthesis fixtures; no model calls."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
checks=[]
for condition in ['shared','separate']:
 variants=['reference','empty','no_recursive_step','wrong_recursive_argument','nondecreasing_call']+(['only_A_repaired','only_B_repaired'] if condition=='separate' else [])
 for variant in variants:
  folder=ROOT/'fixtures'/f'{condition}_{variant}';folder.mkdir(parents=True,exist_ok=True)
  helpers=['AppendA'] if condition=='shared' else ['AppendA','AppendB']
  facts='module Facts {\n  export ViewA provides Total, AppendA\n'
  if condition=='separate':facts+='  export ViewB provides Total, AppendB\n'
  facts+='''  function Total(s: seq<int>): int
    decreases |s|
  { if |s| == 0 then 0 else s[0] + Total(s[1..]) }
'''
  for name in helpers:
   call=f'{name}(s[1..], t);'
   if variant=='wrong_recursive_argument':call=f'{name}(s[1..], []);'
   if variant=='nondecreasing_call':call=f'{name}(s, t);'
   body=f'''    if |s| > 0 {{
      {call}
      assert (s + t)[1..] == s[1..] + t;
    }}
'''
   if variant=='no_recursive_step':body='    if |s| > 0 {\n      assert (s + t)[1..] == s[1..] + t;\n    }\n'
   if variant=='empty' or (variant=='only_A_repaired' and name=='AppendB') or (variant=='only_B_repaired' and name=='AppendA'):body=''
   facts+=f'''  lemma {{:induction false}} {name}(s: seq<int>, t: seq<int>)
    ensures Total(s + t) == Total(s) + Total(t)
    decreases |s|
  {{
'''+body+'  }\n'
  facts+='}\n';(folder/'Facts.dfy').write_text(facts)
  (folder/'ClientA.dfy').write_text('''include "Facts.dfy"
module ClientA {
  import F = Facts`ViewA
  lemma SumTwo(s: seq<int>, t: seq<int>)
    ensures F.Total(s + t) == F.Total(s) + F.Total(t)
  { F.AppendA(s, t); }
}
''')
  suffix='A' if condition=='shared' else 'B'
  (folder/'ClientB.dfy').write_text(f'''include "Facts.dfy"
module ClientB {{
  import F = Facts`View{suffix}
  lemma SumThree(s: seq<int>, t: seq<int>, u: seq<int>)
    ensures F.Total((s + t) + u) == F.Total(s) + F.Total(t) + F.Total(u)
  {{
    F.Append{suffix}(s, t);
    F.Append{suffix}(s + t, u);
  }}
}}
''')
  (folder/'All.dfy').write_text('include "ClientA.dfy"\ninclude "ClientB.dfy"\n')
  for entry in (['All.dfy','ClientA.dfy','ClientB.dfy'] if variant=='reference' else ['All.dfy']):checks.append(dict(variant=folder.name,entry=entry,expected_exit=0 if variant=='reference' else 4))
(ROOT/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
(ROOT/'task.json').write_text(json.dumps(dict(family='recursive-sequence-sum-append',model_calls=0,edit_targets={'shared':['Facts.AppendA.body'],'separate':['Facts.AppendA.body','Facts.AppendB.body']},immutable=['clients','exports','Total definition','lemma signatures/contracts/decreases','induction false attributes'],scope='Provider proof synthesis; source size and number of edited helpers differ intentionally'),indent=2)+'\n')
print(len(checks),'checks')
