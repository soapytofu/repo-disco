"""Materialize parsed alternative proofs for compute-only semantic validation."""
from pathlib import Path
import json,shutil,hashlib
from branch_guard import parse_response
ROOT=Path(__file__).resolve().parent
out=ROOT/'guard-preflight';out.mkdir(exist_ok=False);checks=[]
for condition in ['shared','separate']:
 originals={n:(ROOT/'fixtures'/f'{condition}_empty'/n).read_text() for n in ['ClientA.dfy','ClientB.dfy']}
 for form in ['negative_first','reversed_comparison']:
  files={}
  for client in 'AB':
   suffix='B' if condition=='separate' and client=='B' else 'A';expr='x' if client=='A' else '(x - y)';prefix=originals[f'Client{client}.dfy'][:-len('  }\n}\n')]
   cond=f'{expr} < 0' if form=='negative_first' else f'0 <= {expr}'
   first,second=('1','0') if form=='negative_first' else ('0','1')
   files[f'Client{client}.dfy']=prefix+f'    if {cond} {{\n      F.Case{first}{suffix}({expr});\n    }} else {{\n      F.Case{second}{suffix}({expr});\n    }}\n  }}\n}}\n'
  raw='Alternative proof:\n```json\n'+json.dumps(files)+'\n```'
  parsed,meta=parse_response(raw,originals);assert parsed==files
  name=f'{condition}_{form}';folder=out/'fixtures'/name;folder.mkdir(parents=True)
  for file in ['Facts.dfy','All.dfy']:shutil.copy2(ROOT/'fixtures'/f'{condition}_empty'/file,folder/file)
  for file,content in parsed.items():(folder/file).write_text(content)
  (folder/'raw-response.txt').write_text(raw);(folder/'guard-metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
  for entry in ['All.dfy','ClientA.dfy','ClientB.dfy']:checks.append(dict(variant=name,entry=entry,expected_exit=0))
(out/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
(out/'task.json').write_text(json.dumps(dict(purpose='Verify parsed alternative branch forms',model_calls=0,guard_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['branch_guard.py','json_payload.py']}),indent=2)+'\n')
shutil.copy2(ROOT/'run_verification.py',out/'run_verification.py')
