"""Weaken one helper guarantee at a time; preserve every client proof byte."""
from pathlib import Path
import json,re,shutil
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'sharing-branching-001/fixtures'
checks=[];changes=[]
for condition in ['shared','separate']:
 for helper in [None,'Case0A','Case1A','Case0B','Case1B']:
  name=condition+'_'+(helper or 'reference');folder=ROOT/'fixtures'/name;shutil.copytree(SOURCE/f'{condition}_reference',folder)
  if helper:
   path=folder/'Facts.dfy';text=path.read_text();pattern=r'(lemma '+helper+r'\(x: int\)\n    requires [^\n]+\n    ensures )[^\n]+'
   replacement,count=re.subn(pattern,r'\g<1>true',text);assert count==1;path.write_text(replacement)
   changes.append(dict(variant=name,helper='Facts.'+helper,mutation='replace only selected ensures clause with true',fixed_clients=['ClientA.Prove','ClientB.Prove']))
  for entry in (['All.dfy','ClientA.dfy','ClientB.dfy'] if helper is None else ['ClientA.dfy','ClientB.dfy']):
   used_suffix='B' if condition=='separate' and entry=='ClientB.dfy' else 'A'
   expected=4 if helper is not None and helper.endswith(used_suffix) else 0
   checks.append(dict(variant=name,entry=entry,expected_exit=expected))
(ROOT/'checks.json').write_text(json.dumps(checks,indent=2)+'\n');(ROOT/'task.json').write_text(json.dumps(dict(model_calls=0,changes=changes,scope='Fixed reference proof sensitivity, not minimum proof requirements or model effects'),indent=2)+'\n')
print(len(checks),'checks')
