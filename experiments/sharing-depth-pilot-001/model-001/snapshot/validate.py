"""Offline integrity and design validation; no API or verification subprocesses."""
import hashlib,importlib.util,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def validate(root=ROOT):
    root=Path(root);load=lambda name:json.loads((root/name).read_text())
    bundle=load('frozen-bundle.json')
    for name,digest in bundle['sha256'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:raise ValueError('Frozen hash mismatch: '+name)
    plan=load('plan.json');protocol=load('protocol.json')
    assert len(plan)==8 and [p['sequence'] for p in plan]==list(range(1,9))
    cells=[(p['tier'],p['condition']) for p in plan]
    assert cells[4:]==list(reversed(cells[:4])) and len(set(cells[:4]))==4
    assert set(Counter(cells).values())=={2}
    assert protocol['authorized_calls']==0 and protocol['model_calls_made']==0
    systems=[]
    for p in plan:
        data=(root/p['prompt_file']).read_bytes();assert hashlib.sha256(data).hexdigest()==p['prompt_sha256']
        messages=json.loads(data);assert [m['role'] for m in messages]==['system','user'];systems.append(messages[0]['content'])
        source='Complete repository source:\n\n'+''.join('FILE '+n+'\n'+(root/p['fixture']/n).read_text()+'\n' for n in ['All.dfy','ClientA.dfy','ClientB.dfy','Facts.dfy'])
        assert messages[1]['content']==source
    assert len(set(systems))==1
    assert hashlib.sha256((root/'parser.py').read_bytes()).hexdigest()==protocol['parser']['sha256']
    return dict(trials=8,cells=4,repetitions_per_cell=2,prompt_hashes_valid=True,source_payloads_exact=True,reversed_blocks_valid=True,authorized_calls=0)
if __name__=='__main__':print(json.dumps(validate(),indent=2))
