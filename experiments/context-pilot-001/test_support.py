import unittest
from pilot_support import PREFIX,SUFFIX,validate,prompt,API_CONTEXT

class PolicyTests(unittest.TestCase):
    def test_reference_allowed(self):validate(PREFIX+'    F.EstablishLowerBound(x);\n'+SUFFIX)
    def test_unknown_api_allowed_for_verifier(self):validate(PREFIX+'    F.GuessedName(x);\n'+SUFFIX)
    def test_empty_proof_allowed_for_verifier(self):validate(PREFIX+SUFFIX)
    def test_contract_protected(self):
        with self.assertRaises(ValueError):validate((PREFIX+SUFFIX).replace('>= 0','>= -1'))
    def test_assumption_rejected(self):
        with self.assertRaises(ValueError):validate(PREFIX+'    assume false;\n'+SUFFIX)
    def test_new_declaration_rejected(self):
        with self.assertRaises(ValueError):validate(PREFIX+' } lemma Extra() {\n'+SUFFIX)
    def test_only_difference_is_api_appendix(self):
        low=prompt('local_only',PREFIX+SUFFIX,'failure');high=prompt('api_context',PREFIX+SUFFIX,'failure')
        self.assertEqual(low[0],high[0]);self.assertEqual(high[1]['content'],low[1]['content']+'\n\n'+API_CONTEXT)
        self.assertNotIn('EstablishLowerBound',str(low));self.assertIn('EstablishLowerBound',str(high))
if __name__=='__main__':unittest.main()
