import copy,unittest
import warning_policy as p

class WarningTests(unittest.TestCase):
    def setUp(self):
        self.command=['cargo','verus','verify','--target-dir','/run/targets/case-07']
        self.warning='warning: failed to garbage collect incremental compilation session directory `/run/targets/case-07/debug/incremental/vest_dev-abc123/s-abc123-def456-working`: Directory not empty (os error 39)'
        self.base={'upstream_warnings':['warning: exact upstream diagnostic']}
    def observe(self,warnings,proof=True,coverage=True):
        return dict(warnings=warnings,proof_pass=proof,coverage_complete=coverage,
                    qualified_scope_pass=proof and warnings==self.base['upstream_warnings'])
    def run_report(self,warnings,**kw):
        return p.report('vest',self.observe(warnings,**kw),dict(command=self.command),self.base)
    def test_exact_upstream_remains_eligible(self):
        r=self.run_report(list(self.base['upstream_warnings']))
        self.assertTrue(r['eligible_under_policy_v2']);self.assertTrue(r['legacy_qualified_scope_pass'])
    def test_known_cleanup_kept_separate(self):
        warnings=self.base['upstream_warnings']+[self.warning];o=self.observe(warnings);before=copy.deepcopy(o)
        r=p.report('vest',o,dict(command=self.command),self.base)
        self.assertTrue(r['proof_complete']);self.assertTrue(r['eligible_under_policy_v2'])
        self.assertFalse(r['legacy_qualified_scope_pass']);self.assertEqual(r['operational_warnings'],[self.warning])
        self.assertEqual(o,before);self.assertEqual(r['all_observed_warnings'],warnings)
    def test_unknown_warning_still_blocks(self):
        for warning in ['warning: trigger selection changed','warning: verification skipped',
                        self.warning.replace('39','13'),self.warning+'\nextra diagnostic']:
            with self.subTest(warning=warning):
                r=self.run_report(self.base['upstream_warnings']+[warning])
                self.assertFalse(r['eligible_under_policy_v2']);self.assertTrue(r['requires_warning_review'])
    def test_missing_upstream_warning_blocks(self):
        r=self.run_report([self.warning]);self.assertFalse(r['eligible_under_policy_v2'])
        self.assertEqual(r['missing_upstream_warnings'],self.base['upstream_warnings'])
    def test_exact_target_binding(self):
        for replacement in ['/other/targets/case-07','/run/targets/case-08','/run/targets/case-07/../case-08']:
            with self.subTest(path=replacement):
                self.assertFalse(p.operational_cleanup(self.warning.replace('/run/targets/case-07',replacement),self.command))
    def test_only_observed_crate_and_session_shape(self):
        for wrong in [self.warning.replace('vest_dev','vstd'),self.warning.replace('-working',''),self.warning.replace('debug/incremental','release/incremental')]:
            self.assertFalse(p.operational_cleanup(wrong,self.command))
    def test_ambiguous_command_never_whitelisted(self):
        for command in [[],self.command+['--target-dir','/other'],self.command[:-1]]:
            self.assertFalse(p.operational_cleanup(self.warning,command))
    def test_failure_or_missing_coverage_never_eligible(self):
        for proof,coverage in [(False,True),(False,False),(True,False)]:
            r=self.run_report(self.base['upstream_warnings']+[self.warning],proof=proof,coverage=coverage)
            self.assertFalse(r['eligible_under_policy_v2'])
    def test_duplicate_warnings_preserved(self):
        r=self.run_report(self.base['upstream_warnings']+[self.warning,self.warning])
        self.assertEqual(r['operational_warnings'],[self.warning,self.warning])
    def test_not_applied_to_dafny(self):
        r=p.report('dafny-vmc',self.observe(self.base['upstream_warnings']+[self.warning]),dict(command=self.command),self.base)
        self.assertFalse(r['eligible_under_policy_v2']);self.assertEqual(r['operational_warnings'],[])
    def test_legacy_acceptance_cannot_be_overwritten(self):
        o=self.observe(self.base['upstream_warnings']+[self.warning]);o['qualified_scope_pass']=True
        with self.assertRaises(ValueError):p.report('vest',o,dict(command=self.command),self.base)

if __name__=='__main__':unittest.main(verbosity=2)
