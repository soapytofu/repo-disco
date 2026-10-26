from pathlib import Path
import json,re,hashlib,shutil
r=Path('experiments/inductive-sharing-001');old=r/'revision-002';v=old/'verification-001';rows=json.loads((v/'results.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in (old/'fixtures').rglob('*.dfy'):assert p.read_bytes()==(v/p.relative_to(old)).read_bytes()
for row in rows:
 for name,digest in row['source_hashes'].items():assert sha(v/'fixtures'/row['variant']/name)==digest
(old/'review.json').write_text(json.dumps(dict(job_id=55305080,checks=16,matched=sum(x['matches_expectation'] for x in rows),valid_for_model_pilot=False,source_hashes_match=True,root_cause='Revision generator used an unanchored closing-brace regex and left extra lemma braces. This is a generator bug, not evidence about proof adequacy.',model_calls=0),indent=2)+'\n')
out=r/'revision-003';out.mkdir(exist_ok=False);shutil.copytree(r/'fixtures',out/'fixtures')
def span(text,name):
 match=re.search(r'  lemma \{:induction false\} '+name+r'.*?\n  \{\n',text,re.S);assert match
 opening=match.end()-2;assert text[opening]=='{';depth=1
 for i in range(opening+1,len(text)):
  depth+=(text[i]=='{')-(text[i]=='}')
  if depth==0:return opening+1,i
 raise ValueError('Unclosed body')
for folder in (out/'fixtures').iterdir():
 variant=folder.name.split('_',1)[1];p=folder/'Facts.dfy';text=p.read_text()
 for name in re.findall(r'lemma \{:induction false\} (Append[AB])',text):
  call=f'{name}(s[1..], t);'
  if variant=='wrong_recursive_argument':call=f'{name}(s[1..], []);'
  if variant=='nondecreasing_call':call=f'{name}(s, t);'
  if variant=='no_recursive_step':call=''
  lines=['    if |s| == 0 {','      assert s == [];','      assert s + t == t;','    } else {','      assert |s + t| > 0;','      assert (s + t)[0] == s[0];','      assert (s + t)[1..] == s[1..] + t;']
  if call:lines.append('      '+call)
  lines+=['      assert Total(s + t) == s[0] + Total(s[1..] + t);','      assert Total(s) == s[0] + Total(s[1..]);','    }']
  if variant=='empty' or (variant=='only_A_repaired' and name=='AppendB') or (variant=='only_B_repaired' and name=='AppendA'):lines=[]
  a,b=span(text,name);text=text[:a]+'\n'+''.join(line+'\n' for line in lines)+'  '+text[b:]
 p.write_text(text)
 # Count braces including balanced induction attributes; no strings/comments in provider.
 depth=0
 for c in text:
  depth+=(c=='{')-(c=='}');assert depth>=0
 assert depth==0
 oldfolder=r/'fixtures'/folder.name
 for n in ['All.dfy','ClientA.dfy','ClientB.dfy']:assert (folder/n).read_bytes()==(oldfolder/n).read_bytes()
 original=(oldfolder/'Facts.dfy').read_text()
 assert text.split('  lemma')[0]==original.split('  lemma')[0]
 assert re.findall(r'  lemma.*?\n  \{',text,re.S)==re.findall(r'  lemma.*?\n  \{',original,re.S)
for name in ['checks.json','task.json','run_verification.py']:shutil.copy2(r/name,out/name)
(out/'revision.json').write_text(json.dumps(dict(reason='Correct revision-002 body replacement using balanced brace spans, preserving intended explicit proof steps',prior_failed_jobs=[55304418,55305080],prior_evidence_preserved=True,balanced_braces_checked=True,protected_signatures_and_clients_unchanged=True,model_calls=0),indent=2)+'\n')
s=(r/'revision-verify.sbatch').read_text().replace('revision-002','revision-003').replace('revision-verify-%j','revision3-verify-%j');(r/'revision3-verify.sbatch').write_text(s)
