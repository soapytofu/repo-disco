"""Saved native logs and fake processes only; no verifier or API invocation."""
import copy,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import common as c
import review
import verify_candidates as v

class ExecutionTests(unittest.TestCase):
    def test_commands_and_resources(self):
        for stage in c.STAGES:
            command,logical,_,required,base=v.make_command(stage,'slot-test',c.ROOT/'work'/stage/'slot-test')
            script=(c.ROOT/('verify-'+stage+'.sbatch')).read_text()
            self.assertIn('#SBATCH --cpus-per-task='+str(c.STAGES[stage]['cpus'])+'\n',script)
            self.assertIn('#SBATCH --ntasks=1\n',script);self.assertIn('#SBATCH --no-requeue\n',script)
            if stage=='dafny-vmc':
                self.assertEqual(len(required),267);self.assertEqual(len(base['explicit_sources']),28)
                self.assertEqual([x for x in logical if x.endswith('.dfy')],sorted(base['explicit_sources']))
            else:
                self.assertIn('CARGO_BUILD_JOBS=4',command)
                self.assertEqual(logical[-2:],['--num-threads','3']);self.assertNotIn('--focus',logical)
    def saved(self,project):
        d=c.ROOT/'test-evidence'/project;bound=c.read(d/'bound-record.json')
        return d,c.read(d/'record.json'),{n:(d/n).read_bytes() for n in bound['raw_sha256']}
    def test_frozen_native_scores_and_warning_policy(self):
        for project in c.STAGES:
            d,native,raw=self.saved(project)
            base=c.read(c.ROOT/'qualification'/('coverage-001/profile.json' if project=='dafny-vmc' else 'vest-coverage-001/profile.json'))
            observation=c.verification_observation(project,native,raw,base)
            self.assertEqual(observation,c.read(d/'observation.json'));self.assertTrue(observation['qualified_scope_pass'])
            altered=copy.deepcopy(base);altered['upstream_warnings']=[]
            self.assertFalse(c.verification_observation(project,native,raw,altered)['qualified_scope_pass'])
    def test_missing_coverage_does_not_pass(self):
        for project in c.STAGES:
            _,native,raw=self.saved(project)
            base=c.read(c.ROOT/'qualification'/('coverage-001/profile.json' if project=='dafny-vmc' else 'vest-coverage-001/profile.json'))
            if project=='dafny-vmc':
                raw={n:b for n,b in raw.items() if not n.startswith('csv/')}
            else:raw={**raw,'stdout.txt':b'','stderr.txt':b''}
            self.assertFalse(c.verification_observation(project,native,raw,base)['qualified_scope_pass'])
    def test_fake_worker_review_and_stale_rejection(self):
        tasks,groups=c.validate_package();entry=groups[0];task=tasks[entry['task']]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);q=root/'fake-upstream'
            for name in ['qualification','candidates']:shutil.copytree(c.ROOT/name,root/name)
            for name in ['runtime-freeze.json','plan.json']:shutil.copyfile(c.ROOT/name,root/name)
            upstream=q/'upstream/dafny-vmc'/task['file'];upstream.parent.mkdir(parents=True)
            upstream.write_bytes((c.ROOT/'fixtures'/task['id']/'source.txt').read_bytes())
            (root/'qualification/source-manifest.json').write_text(json.dumps([dict(id='dafny-vmc',files={task['file']:c.sha(upstream)})]))
            out=root/'verification-dafny-vmc-001';out.mkdir()
            env=dict(job_id='FAKE-NO-COMPUTE',cpus=1,model_calls=0,execution_root=str(root),
                     plan_sha256=c.sha(root/'plan.json'),runtime_sha256=c.sha(root/'runtime-freeze.json'))
            (root/'submissions').mkdir();v.write(root/'submissions/dafny-vmc.json',dict(job_id=env['job_id']))
            v.write(out/'environment.json',env)
            saved,_,raw=self.saved('dafny-vmc');calls=[]
            def fake(label,command,cwd,output,environment,limit):
                calls.append(label);d=output/label;d.mkdir();work=root/'work/dafny-vmc'/label
                for n,b in raw.items():
                    dest=work/n[4:] if n.startswith('csv/') else d/n
                    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
                record=dict(command=command,cwd=str(cwd),exit_code=0,elapsed_seconds=1,model_calls=0,attempts=1,
                            artifacts={n:c.sha(d/n) for n in ['stdout.txt','stderr.txt','resources.txt']})
                v.write(d/'record.json',record);return record
            with patch.object(v,'remote_qualification',return_value=q):
                row=v.verify_one(entry,task,'dafny-vmc',out,env['job_id'],root=root,native_capture=fake)
                v.write(out/'complete.json',dict(project='dafny-vmc',model_calls=0,results=[row],expected_candidates=1))
                with patch.object(c,'validate_package',return_value=(tasks,[entry])):
                    self.assertEqual(review.review_verification('dafny-vmc',root)['qualified_passes'],1)
                    p=out/'slot-01/bound-record.json';b=c.read(p);b['run_id']='stale'
                    p.write_text(json.dumps(b))
                    with self.assertRaisesRegex(ValueError,'Stale run'):review.review_verification('dafny-vmc',root)
                with self.assertRaises(FileExistsError):v.verify_one(entry,task,'dafny-vmc',out,env['job_id'],root=root,native_capture=fake)
            self.assertEqual(calls,['slot-01'])

if __name__=='__main__':unittest.main(verbosity=2)
