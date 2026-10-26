from pathlib import Path
import json,re,hashlib,shutil
r=Path('experiments/inductive-sharing-001');v=r/'verification-001';rows=json.loads((v/'results.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in (r/'fixtures').rglob('*.dfy'):assert p.read_bytes()==(v/p.relative_to(r)).read_bytes()
for row in rows:
 for n,h in row['source_hashes'].items():assert sha(v/'fixtures'/row['variant']/n)==h
(r/'review-001.json').write_text(json.dumps(dict(job_id=55304418,checks=16,matched=10,unexpected_reference_failures=6,all_source_hashes_match=True,valid_for_model_pilot=False,model_calls=0,interpretation='All reference checks fail postcondition proof; negative outcomes cannot yet validate the fixture. Preserve this run.'),indent=2)+'\n')
p=r/'README.md';s=p.read_text().replace('Job **55304418** submitted on shared/sapphire without requeue; verification pending.','Job **55304418 failed**: all six reference checks fail postcondition proof, while ten negatives have expected exit status. This fixture is **not ready for a model pilot**. Raw evidence and original source are preserved in verification-001; review-001.json records the failure. A deliberate revision with explicit base/unfolding facts is being verified separately.');p.write_text(s)
out=r/'revision-002';out.mkdir(exist_ok=False);shutil.copytree(r/'fixtures',out/'fixtures')
for folder in (out/'fixtures').iterdir():
 variant=folder.name.split('_',1)[1];p=folder/'Facts.dfy';text=p.read_text()
 for name in re.findall(r'lemma \{:induction false\} (Append[AB])',text):
  call=f'{name}(s[1..], t);'
  if variant=='wrong_recursive_argument':call=f'{name}(s[1..], []);'
  if variant=='nondecreasing_call':call=f'{name}(s, t);'
  if variant=='no_recursive_step':call=''
  body='''    if |s| == 0 {
      assert s == [];
      assert s + t == t;
    } else {
      assert |s + t| > 0;
      assert (s + t)[0] == s[0];
      assert (s + t)[1..] == s[1..] + t;
      CALL
      assert Total(s + t) == s[0] + Total(s[1..] + t);
      assert Total(s) == s[0] + Total(s[1..]);
    }
'''.replace('CALL',call)
  if variant=='empty' or (variant=='only_A_repaired' and name=='AppendB') or (variant=='only_B_repaired' and name=='AppendA'):body=''
  pattern=r'(  lemma \{:induction false\} '+name+r'.*?\n  \{\n).*?(  \}\n)'
  text,count=re.subn(pattern,lambda m:m[1]+body+m[2],text,flags=re.S);assert count==1
 p.write_text(text)
for name in ['checks.json','task.json','run_verification.py']:shutil.copy2(r/name,out/name)
# Explicitly check clients and protected signatures remained byte-identical.
for folder in (out/'fixtures').iterdir():
 old=r/'fixtures'/folder.name
 for name in ['ClientA.dfy','ClientB.dfy','All.dfy']:assert (folder/name).read_bytes()==(old/name).read_bytes()
 for source in ['Facts.dfy']:
  new=(folder/source).read_text();original=(old/source).read_text();assert new.split('  lemma')[0]==original.split('  lemma')[0]
  assert re.findall(r'  lemma.*?\n  \{',new,re.S)==re.findall(r'  lemma.*?\n  \{',original,re.S)
(out/'revision.json').write_text(json.dumps(dict(reason='Explicit base case and one-step unfolding equalities added to failed reference proof',prior_job=55304418,prior_evidence_preserved=True,protected_signatures_and_clients_unchanged=True,model_calls=0),indent=2)+'\n')
s=(r/'verify.sbatch').read_text().replace('outputs/inductive-sharing-001/run_verification.py','outputs/inductive-sharing-001/revision-002/run_verification.py').replace('outputs/inductive-sharing-001/verification-001','outputs/inductive-sharing-001/revision-002/verification-001').replace('verify-%j','revision-verify-%j')
(r/'revision-verify.sbatch').write_text(s)
