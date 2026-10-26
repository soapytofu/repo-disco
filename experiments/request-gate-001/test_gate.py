import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from offline_gate import OfflineGate,GateClosed

class GateTests(unittest.TestCase):
    def test_nested_worker_repairs_share_one_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'run';seen=[]
            def transport(prompt):
                ledger=json.loads((path/'ledger.json').read_text())
                self.assertEqual(ledger['reservations'][-1]['status'],'RESERVED')
                self.assertEqual(ledger['reservations'][-1]['prompt'],prompt)
                seen.append(prompt);return {'text':'fake'}
            gate=OfflineGate(path,3,100,transport,clock=lambda:0)
            for task in range(3):
                for repair in range(4):
                    try:gate.invoke({'task':task,'repair':repair},task_id=str(task),attempt_id=str(repair))
                    except GateClosed:pass
            self.assertEqual(len(seen),3)
            self.assertTrue(gate.closed)
            self.assertEqual(len(gate.state['reservations']),3)

    def test_caught_transport_error_never_reopens(self):
        with tempfile.TemporaryDirectory() as temp:
            calls=[]
            def fail(prompt):calls.append(1);raise TimeoutError('private detail')
            gate=OfflineGate(Path(temp)/'run',8,100,fail,clock=lambda:0)
            with self.assertRaises(TimeoutError):gate.invoke([],task_id='a',attempt_id='1')
            for _ in range(5):
                with self.assertRaises(GateClosed):gate.invoke([],task_id='a',attempt_id='2')
            self.assertEqual(calls,[1])
            self.assertNotIn('private detail',(gate.directory/'ledger.json').read_text())

    def test_deadline_checked_each_call_and_after_reservation(self):
        for ticks,expected in [([0,0,101],1),([0,101],0)]:
            with self.subTest(ticks=ticks),tempfile.TemporaryDirectory() as temp:
                clock=iter(ticks);calls=[]
                gate=OfflineGate(Path(temp)/'run',8,100,lambda p:calls.append(p) or {},clock=lambda:next(clock))
                if expected:gate.invoke([],task_id='a',attempt_id='1')
                with self.assertRaises(GateClosed):gate.invoke([],task_id='a',attempt_id='2')
                self.assertEqual(len(calls),expected)

    def test_transport_cannot_rewrite_recorded_prompt(self):
        with tempfile.TemporaryDirectory() as temp:
            def mutate(prompt):prompt['x']=99;return {}
            gate=OfflineGate(Path(temp)/'run',1,100,mutate,clock=lambda:0)
            prompt={'x':1};gate.invoke(prompt,task_id='a',attempt_id='1')
            self.assertEqual(prompt,{'x':1})
            self.assertEqual(gate.state['reservations'][0]['prompt'],{'x':1})

    def test_existing_ledger_cannot_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'run';OfflineGate(path,1,100,lambda p:{})
            with self.assertRaises(FileExistsError):OfflineGate(path,1,100,lambda p:{})

    def test_failed_reservation_persistence_never_dispatches(self):
        with tempfile.TemporaryDirectory() as temp:
            calls=[];gate=OfflineGate(Path(temp)/'run',2,100,lambda p:calls.append(p),clock=lambda:0)
            with patch('offline_gate.durable_json',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):gate.invoke([],task_id='a',attempt_id='1')
            with self.assertRaises(GateClosed):gate.invoke([],task_id='a',attempt_id='2')
            self.assertEqual(calls,[])

    def test_response_serialization_failure_consumes_reservation(self):
        with tempfile.TemporaryDirectory() as temp:
            gate=OfflineGate(Path(temp)/'run',2,100,lambda p:object(),clock=lambda:0)
            with self.assertRaises(TypeError):gate.invoke([],task_id='a',attempt_id='1')
            with self.assertRaises(GateClosed):gate.invoke([],task_id='a',attempt_id='2')
            self.assertEqual(len(gate.state['reservations']),1)

    def test_reentrant_transport_cannot_dispatch_twice(self):
        with tempfile.TemporaryDirectory() as temp:
            calls=[]
            def transport(prompt):
                calls.append(1)
                with self.assertRaises(GateClosed):gate.invoke([],task_id='nested',attempt_id='1')
                return {}
            gate=OfflineGate(Path(temp)/'run',2,100,transport,clock=lambda:0)
            gate.invoke([],task_id='a',attempt_id='1');self.assertEqual(calls,[1])

if __name__=='__main__':unittest.main()
