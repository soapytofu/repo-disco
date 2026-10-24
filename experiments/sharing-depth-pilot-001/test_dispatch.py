import json,tempfile,unittest
from pathlib import Path
from dispatch import run_batch
class DispatchTests(unittest.TestCase):
    def test_exact_budget_order_and_durable_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'run';seen=[]
            def transport(messages):
                ledger=json.loads((out/'ledger.json').read_text())
                self.assertEqual(ledger['calls_dispatched'],len(seen)+1)
                self.assertEqual(ledger['current']['status'],'DISPATCHED')
                self.assertEqual(messages,json.loads((Path(__file__).parent / ledger['current']['prompt_file']).read_text()));seen.append(ledger['current']['condition']);return dict(text='{}',usage={})
            state=run_batch(out,transport,lambda *a:dict(outcome='EDIT_REJECTED'))
            self.assertEqual(len(seen),8);self.assertEqual(seen,['shared','separate','separate','shared','shared','separate','separate','shared'])
            with self.assertRaises(FileExistsError):run_batch(out,transport)
            self.assertEqual(state['calls_dispatched'],8)
    def test_api_error_never_retries(self):
        with tempfile.TemporaryDirectory() as d:
            count=[]
            def fail(*a):count.append(1);raise TimeoutError('not logged')
            state=run_batch(Path(d)/'run',fail)
            self.assertEqual(len(count),1);self.assertEqual(state['calls_dispatched'],1)
            self.assertEqual(state['completed'][0]['outcome'],'API_ERROR')
    def test_verifier_timeout_stops_batch(self):
        with tempfile.TemporaryDirectory() as d:
            state=run_batch(Path(d)/'run',lambda *a:dict(text='{}'),lambda *a:dict(outcome='TIMEOUT'))
            self.assertEqual(state['calls_dispatched'],1)
if __name__=='__main__':unittest.main()
