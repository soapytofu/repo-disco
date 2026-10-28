import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile,json
import weeks14_continuation as c

class ContinuationTests(unittest.TestCase):
    def test_agent_runs_once_after_twenty_normal_results(self):
        calls=[]
        result=c.stages(lambda:[{'outcome':'PROOF_FAILURE'}]*20,lambda:calls.append('agent') or {})
        self.assertTrue(result['agent_started']);self.assertEqual(calls,['agent'])
    def test_incomplete_or_ambiguous_baseline_never_starts_agent(self):
        for results in [[{'outcome':'VERIFIED'}]*19,[{'outcome':'VERIFIED'}]*19+[{'outcome':'REQUEST_STOP'}],
                        [{'outcome':'VERIFIED'}]*19+[{'outcome':'TIMEOUT'}]]:
            with patch.object(c,'agent_stage') as agent:
                result=c.stages(lambda:results,agent)
                self.assertFalse(result['agent_started']);agent.assert_not_called()
    def test_baseline_exception_cannot_fall_through(self):
        with patch.object(c,'agent_stage') as agent:
            def fail():raise OSError('storage failed')
            with self.assertRaises(OSError):c.stages(fail,agent)
            agent.assert_not_called()
    def test_real_task_guards_loop_with_fake_verifier_and_saved_responses(self):
        # Exercise the live orchestration with original frozen tasks, no provider.
        from types import SimpleNamespace
        from language.dafny.candidate import hashes
        from language import VerificationOutput,VerificationOutcome
        original=c.repair
        def checked_repair(*args,**kwargs):
            def result(files,code):return SimpleNamespace(verification=VerificationOutput(VerificationOutcome.SUCCESS if code==0 else VerificationOutcome.FAIL,code,'diagnostic',''),evidence=dict(exit_code=code,source_sha256=hashes(files)))
            kwargs['base_verifier']=lambda files,entry:result(files,4)
            kwargs['verifier']=lambda candidate:result(candidate.files,0)
            return original(*args,**kwargs)
        real_exp=c.pilot.EXP
        with tempfile.TemporaryDirectory() as temp:
            import shutil
            exp=Path(temp)/'exp';exp.mkdir()
            for name in ['fixtures','frozen-model-001']:shutil.copytree(real_exp/name,exp/name)
            responses=[]
            for family,condition in c.pilot.ORDER:
                positive=c.pilot.files_at(real_exp/'fixtures'/family/(condition+'_reference'))
                editable=['Facts.dfy'] if family=='inductive' else ['ClientA.dfy','ClientB.dfy']
                responses.append({'text':json.dumps({k:positive[k].decode() for k in editable})})
            sequence=iter(responses);calls=[]
            def transport(messages):calls.append(messages);return next(sequence)
            with patch.object(c.pilot,'EXP',exp),patch.object(c.pilot,'validate'),patch.object(c,'repair',side_effect=checked_repair):
                summary=c.agent_stage({'order':c.pilot.ORDER},transport)
            self.assertEqual(summary['reserved_calls'],4);self.assertEqual(len(calls),4)
            self.assertTrue(all(r['attempts'][0]['outcome']=='SUCCESS' for r in summary['results']))

if __name__=='__main__':unittest.main()
