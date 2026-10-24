"""Post-hoc diagnostic: remove prose around a single complete JSON object only."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'sharing-model-pilot-001'
sys.path.insert(0,str(SOURCE))
from harness import strict_object,parse_response,CLIENTS

def extract(text):
    decoder=json.JSONDecoder(object_pairs_hook=strict_object)
    candidates=[]
    for i,char in enumerate(text):
        if char!='{':continue
        try:value,length=decoder.raw_decode(text[i:])
        except ValueError:continue
        if isinstance(value,dict) and set(value)==set(CLIENTS) and all(isinstance(v,str) for v in value.values()):
            candidates.append((i,i+length,value))
    if len(candidates)!=1:raise ValueError('Expected exactly one complete two-client JSON object')
    start,end,files=candidates[0]
    if text[end:].strip():raise ValueError('Non-whitespace suffix: manual review required')
    return start,end,files

def main():
    out=ROOT/'extracted';out.mkdir(exist_ok=False)
    rows=[]
    ledger=json.loads((SOURCE/'model-001/ledger.json').read_text())
    for trial in ledger['completed']:
        name=f"{trial['sequence']:02d}-{trial['condition']}-r{trial['repeat']}"
        source=SOURCE/'model-001'/name/'response.json'
        response=json.loads(source.read_text());text=response['text']
        start,end,files=extract(text)
        original={n:(SOURCE/'fixtures'/f"{trial['condition']}_missing"/n).read_text() for n in CLIENTS}
        raw=text[start:end]
        accepted=parse_response(raw,original)
        folder=out/name;folder.mkdir();(folder/'response.json').write_text(raw)
        for n,s in accepted.items():(folder/n).write_text(s)
        rows.append(dict(sequence=trial['sequence'],condition=trial['condition'],repeat=trial['repeat'],directory=name,source_response=str(source.relative_to(ROOT.parent.parent)),source_response_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),response_text_sha256=hashlib.sha256(text.encode()).hexdigest(),json_start_character=start,json_end_character=end,removed_prefix_characters=start,removed_suffix_characters=len(text)-end,guard_accepted=True,extraction='Exact JSON substring; standard JSON decoding only; no proof edits',matches_reference_ignoring_whitespace={n:''.join(s.split())==''.join((SOURCE/'fixtures'/f"{trial['condition']}_reference"/n).read_text().split()) for n,s in accepted.items()}))
    (ROOT/'extraction.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('Extracted and guard-checked',len(rows),'responses')
if __name__=='__main__':main()
