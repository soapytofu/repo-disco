"""Only fake processes and saved evidence; no native verifier on local/login."""
import copy,json,os,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import common as c
import review
import verify_candidates as v
from capture import digest

class ComputeTests(unittest.TestCase):
    def test_exact_matrix_and_full_scope(self):
        tasks,entries=c.validate_package()
        self.assertEqual([(e['source'],e['resource_limit']) for e in entries],c.ORDER)
        for entry in entries:
            command,logical,limit,required,base=v.make_command('dafny-vmc','slot-%02d'%entry['slot'],c.ROOT/'unused')
            self.assertEqual(logical[logical.index('--resource-limit')+1],str(entry['resource_limit']))
            self.assertEqual(len(required),267);self.assertEqual(len(base['explicit_sources']),28)
            self.assertEqual([x for x in logical if x.endswith('.dfy')],sorted(base['explicit_sources']))
            self.assertEqual(limit,300);self.assertNotIn('--filter-symbol',logical)
    def test_fixed_sources_preserve_both_contract_boundaries(self):
        task=c.read(c.ROOT/'plan.json')['task']
        for source in ['upstream','saved-candidate']:
            raw=(c.ROOT/'sources'/(source+'.txt')).read_bytes()
            self.assertEqual(digest(raw[:task['body_start']]),task['protected_prefix_sha256'])
            self.assertEqual(digest(raw[-task['suffix_bytes']:]),task['protected_suffix_sha256'])
    def test_serial_resources_and_compute_only(self):
        script=(c.ROOT/'verify-dafny-vmc.sbatch').read_text()
        for line in ['#SBATCH --cpus-per-task=1','#SBATCH --ntasks=1','#SBATCH --no-requeue','#SBATCH --mem=2G']:
            self.assertIn(line+'\n',script)
        with patch.dict(os.environ,{},clear=True),self.assertRaises(ValueError):
            c.compute_environment('dafny-vmc')
    def test_package_change_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'runtime-freeze.json').write_text(json.dumps(dict(model_calls=0,native_invocations=4,files={'x':'wrong'})))
            (root/'x').write_text('changed')
            with self.assertRaisesRegex(ValueError,'Pinned bytes'):c.validate_package(root)
    def test_four_fake_native_observations_review_and_no_restart(self):
        tasks,entries=c.validate_package();task=tasks['vmc-swap']
        saved=c.ROOT/'test-evidence/dafny-vmc';raw={n:(saved/n).read_bytes() for n in c.read(saved/'bound-record.json')['raw_sha256']}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);q=root/'fake-upstream'
            for name in ['qualification','sources']:shutil.copytree(c.ROOT/name,root/name)
            for name in ['runtime-freeze.json','plan.json']:shutil.copyfile(c.ROOT/name,root/name)
            upstream=q/'upstream/dafny-vmc'/task['file'];upstream.parent.mkdir(parents=True)
            upstream.write_bytes((root/'sources/upstream.txt').read_bytes())
            (root/'qualification/source-manifest.json').write_text(json.dumps([dict(id='dafny-vmc',files={task['file']:c.sha(upstream)})]))
            out=root/'verification-dafny-vmc-001';out.mkdir()
            env=dict(job_id='FAKE-NO-COMPUTE',cpus=1,model_calls=0,execution_root=str(root),
                     plan_sha256=c.sha(root/'plan.json'),runtime_sha256=c.sha(root/'runtime-freeze.json'))
            (root/'submissions').mkdir();v.write(root/'submissions/dafny-vmc.json',dict(job_id=env['job_id']))
            v.write(out/'environment.json',env);calls=[]
            def fake(label,command,cwd,output,environment,limit):
                calls.append(label);d=output/label;d.mkdir();work=root/'work/dafny-vmc'/label
                for n,b in raw.items():
                    dest=work/n[4:] if n.startswith('csv/') else d/n
                    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
                record=dict(command=command,cwd=str(cwd),exit_code=0,elapsed_seconds=1,model_calls=0,attempts=1,
                            artifacts={n:c.sha(d/n) for n in ['stdout.txt','stderr.txt','resources.txt']})
                v.write(d/'record.json',record);return record
            with patch.object(v,'remote_qualification',return_value=q):
                rows=[v.verify_one(e,task,'dafny-vmc',out,env['job_id'],root=root,native_capture=fake) for e in entries]
                v.write(out/'complete.json',dict(project='dafny-vmc',model_calls=0,results=rows,expected_candidates=4))
                with patch.object(c,'validate_package',return_value=(tasks,entries)):
                    self.assertEqual(review.review_verification('dafny-vmc',root)['qualified_passes'],4)
                    p=out/'slot-03/bound-record.json';b=c.read(p);b['run_id']='stale';p.write_text(json.dumps(b))
                    with self.assertRaisesRegex(ValueError,'Stale run'):review.review_verification('dafny-vmc',root)
                with self.assertRaises(FileExistsError):
                    v.verify_one(entries[0],task,'dafny-vmc',out,env['job_id'],root=root,native_capture=fake)
            self.assertEqual(calls,['slot-01','slot-02','slot-03','slot-04'])
    def test_changed_candidate_rejected_before_dispatch(self):
        tasks,entries=c.validate_package()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'sources').mkdir();(root/'sources/upstream.txt').write_text('changed')
            calls=[]
            with self.assertRaisesRegex(ValueError,'candidate changed'):
                v.verify_one(entries[0],tasks['vmc-swap'],'dafny-vmc',root/'out','fake',root=root,native_capture=lambda *x:calls.append(x))
            self.assertEqual(calls,[])

if __name__=='__main__':unittest.main(verbosity=2)
