"""Offline fake-transport tests, including real competing OS processes."""
import copy
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import window_budget as w


def scope(cap=4, deadline=100):
    return dict(window_id='repodisco-research-20261114', authorized=True,
                no_retries=True, max_calls=cap, deadline_epoch=deadline,
                authorization_basis='FAKE TEST ONLY')


def batch(name, count=2):
    raw=[json.dumps(dict(modelId='FAKE',messages=[dict(text=f'{name}-{i}')]),indent=2).encode() for i in range(count)]
    manifest=dict(batch_id=name,freeze_sha256=w.digest(('freeze-'+name).encode()),
                  runtime_sha256=w.digest(b'FAKE RUNTIME'),max_calls=count,sdk_total_max_attempts=1,
                  slots=[dict(trial_id=f'{name}-{i}',request_sha256=w.digest(p)) for i,p in enumerate(raw)])
    return manifest,raw


def competing_owner(path, result):
    try:
        w.WindowBudget.open_existing(path,scope(),clock=lambda:0)
    except Exception as error:
        result.put(type(error).__name__)
    else:
        result.put('UNEXPECTED_OWNER')


class WindowBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)/'window';self.sent=[]

    def gate(self, authorization=None, clock=lambda:0):
        return w.WindowBudget.create(self.directory,authorization or scope(),clock=clock)

    def transport(self,payload):
        self.sent.append(copy.deepcopy(payload))
        return dict(request_id=f'fake-{len(self.sent)}',retry_attempts=0,text='FAKE')

    def register(self,gate,name='batch-a',count=2):
        manifest,raw=batch(name,count);bound=gate.register_batch(manifest)
        return manifest,raw,bound

    def call(self,gate,info,index=0,transport=None):
        manifest,raw,bound=info
        return gate.invoke(batch_id=manifest['batch_id'],trial_id=manifest['slots'][index]['trial_id'],
                           manifest_sha256=bound,request_bytes=raw[index],transport=transport or self.transport)

    def ledger(self):
        return json.loads((self.directory/'ledger.json').read_bytes())

    def test_two_batches_share_total_cap_and_fixed_order(self):
        gate=self.gate();a=self.register(gate);b=self.register(gate,'batch-b')
        with self.assertRaises(ValueError):self.call(gate,b)
        for info in (a,b):
            for i in range(2):self.call(gate,info,i)
        self.assertEqual(len(self.sent),4)
        self.assertEqual([r['sequence'] for r in self.ledger()['reservations']],[1,2,3,4])
        self.assertEqual([r['status'] for r in self.ledger()['reservations']],['COMPLETED']*4)
        with self.assertRaises(w.GateClosed):self.call(gate,b,1)
        with self.assertRaises(w.GateClosed):self.register(gate,'overflow',1)
        gate.close()
        with w.WindowBudget.open_existing(self.directory,scope(),clock=lambda:0) as next_owner:
            with self.assertRaises(w.GateClosed):self.call(next_owner,a)
        self.assertEqual(len(self.sent),4)

    def test_clean_handoff_preserves_remaining_frozen_slots(self):
        gate=self.gate();a=self.register(gate);self.call(gate,a);gate.close()
        next_owner=w.WindowBudget.open_existing(self.directory,scope(),clock=lambda:0)
        with self.assertRaises(ValueError):next_owner.register_batch(a[0])
        with self.assertRaises(ValueError):self.call(next_owner,a,0)
        b=self.register(next_owner,'batch-b')
        with self.assertRaises(ValueError):self.call(next_owner,b,0)
        self.call(next_owner,a,1)
        self.call(next_owner,b,0)
        self.assertEqual(len(self.sent),3)
        self.assertEqual(next_owner.snapshot()['batches'][0]['manifest'],a[0])
        next_owner.close()

    def test_competing_process_cannot_acquire_existing_owner(self):
        gate=self.gate()
        ctx=multiprocessing.get_context('spawn');result=ctx.Queue()
        child=ctx.Process(target=competing_owner,args=(str(self.directory),result))
        child.start();child.join(15)
        if child.is_alive():child.terminate();child.join();self.fail('Lock test process timed out')
        self.assertEqual(child.exitcode,0);self.assertEqual(result.get(timeout=2),'OwnerBusy')
        gate.close()

    @unittest.skipUnless(hasattr(os,'fork'),'POSIX fork unavailable')
    def test_inherited_gate_cannot_dispatch_from_fork(self):
        gate=self.gate();info=self.register(gate);read,write=os.pipe();pid=os.fork()
        if pid==0:
            os.close(read)
            try:self.call(gate,info)
            except Exception as error:os.write(write,type(error).__name__.encode())
            else:os.write(write,b'UNEXPECTED_DISPATCH')
            os.close(write);os._exit(0)
        os.close(write);data=os.read(read,100);os.close(read);os.waitpid(pid,0)
        self.assertEqual(data,b'OwnerBusy');self.assertFalse(self.ledger()['reservations'])
        gate.close()

    def test_timeout_is_charged_and_caught_worker_cannot_retry(self):
        gate=self.gate();info=self.register(gate)
        def failed(payload):self.sent.append(payload);raise TimeoutError('FAKE')
        with self.assertRaises(TimeoutError):self.call(gate,info,transport=failed)
        self.assertEqual(len(self.sent),1)
        self.assertEqual(self.ledger()['reservations'][0]['status'],'AMBIGUOUS_OR_UNSAVED')
        for i in (0,1):
            with self.assertRaises(w.GateClosed):self.call(gate,info,i)
        with self.assertRaises(w.OwnerBusy):w.WindowBudget.open_existing(self.directory,scope(),clock=lambda:0)
        with self.assertRaises(w.GateClosed):gate.close()
        self.assertTrue((self.directory/'owner.lock').exists())

    def test_crash_left_dispatch_marker_blocks_even_if_lock_manually_missing(self):
        gate=self.gate();info=self.register(gate)
        def failed(payload):raise TimeoutError('FAKE')
        with self.assertRaises(TimeoutError):self.call(gate,info,transport=failed)
        # Simulates an external lock deletion; library has no such API.
        (self.directory/'owner.lock/owner.json').unlink();(self.directory/'owner.lock').rmdir()
        with self.assertRaises(w.GateClosed):w.WindowBudget.open_existing(self.directory,scope(),clock=lambda:0)
        self.assertTrue((self.directory/'owner.lock').exists())

    def test_deadline_before_and_after_durable_work(self):
        for place in ('initial','reservation','dispatch_intent'):
            with self.subTest(place=place),tempfile.TemporaryDirectory() as temp:
                now=[0];gate=w.WindowBudget.create(Path(temp)/'gate',scope(),clock=lambda:now[0]);info=self.register(gate)
                original=w.durable_json
                def persist(path,value):
                    original(path,value)
                    if value.get('reservations'):
                        state=value['reservations'][-1]['status']
                        if (place=='reservation' and state=='RESERVED') or (place=='dispatch_intent' and state=='DISPATCHING'):now[0]=100
                if place=='initial':now[0]=100
                with patch.object(w,'durable_json',side_effect=persist),self.assertRaises(w.GateClosed):self.call(gate,info)
                self.assertFalse(self.sent)
                if place!='initial':
                    self.assertEqual(len(gate.snapshot()['reservations']),1)
                    self.assertEqual(gate.snapshot()['reservations'][0]['status'],'EXPIRED_NO_DISPATCH')

    def test_return_after_deadline_does_not_allow_next_dispatch(self):
        now=[0];gate=self.gate(clock=lambda:now[0]);info=self.register(gate)
        def slow(payload):now[0]=101;return self.transport(payload)
        self.call(gate,info,transport=slow)
        self.assertEqual(len(self.sent),1)
        with self.assertRaises(w.GateClosed):self.call(gate,info,1)
        self.assertEqual(self.ledger()['reservations'][0]['status'],'COMPLETED')

    def test_reentrant_transport_cannot_make_second_dispatch(self):
        gate=self.gate();info=self.register(gate)
        def nested(payload):
            with self.assertRaises(w.OwnerBusy):self.call(gate,info,1)
            return self.transport(payload)
        self.call(gate,info,transport=nested);self.assertEqual(len(self.sent),1);gate.close()

    def test_reservation_disk_failure_prevents_transport(self):
        gate=self.gate();info=self.register(gate)
        with patch.object(w,'durable_json',side_effect=OSError('FAKE DISK')),self.assertRaises(OSError):self.call(gate,info)
        self.assertFalse(self.sent)
        with self.assertRaises(w.GateClosed):self.call(gate,info)
        self.assertTrue((self.directory/'owner.lock').exists())

    def test_response_disk_failure_retains_charge_and_closes(self):
        gate=self.gate();info=self.register(gate);original=w.exclusive_bytes
        def write(path,raw):
            if path.name.startswith('response-'):raise OSError('FAKE RESPONSE DISK')
            original(path,raw)
        with patch.object(w,'exclusive_bytes',side_effect=write),self.assertRaises(OSError):self.call(gate,info)
        self.assertEqual(len(self.sent),1)
        self.assertEqual(self.ledger()['reservations'][0]['status'],'AMBIGUOUS_OR_UNSAVED')
        with self.assertRaises(w.GateClosed):self.call(gate,info,1)

    def test_completed_record_failure_is_ambiguous_not_resent(self):
        gate=self.gate();info=self.register(gate);original=w.durable_json;failed=[False]
        def persist(path,value):
            if value.get('reservations') and value['reservations'][-1]['status']=='COMPLETED' and not failed[0]:
                failed[0]=True;raise OSError('FAKE COMMIT DISK')
            original(path,value)
        with patch.object(w,'durable_json',side_effect=persist),self.assertRaises(OSError):self.call(gate,info)
        self.assertEqual(len(self.sent),1)
        self.assertTrue((self.directory/'requests/response-001.json').exists())
        self.assertEqual(self.ledger()['reservations'][0]['status'],'AMBIGUOUS_OR_UNSAVED')

    def test_duplicate_id_or_sdk_retry_closes_and_retains_response(self):
        for response in (dict(request_id='fake-1',retry_attempts=0),dict(request_id='new',retry_attempts=1),dict(text='missing')):
            with self.subTest(response=response),tempfile.TemporaryDirectory() as temp:
                gate=w.WindowBudget.create(Path(temp)/'gate',scope(),clock=lambda:0);info=self.register(gate)
                self.sent=[];self.call(gate,info)
                with self.assertRaises(w.GateClosed):self.call(gate,info,1,transport=lambda payload:response)
                self.assertEqual(len(gate.snapshot()['reservations']),2)
                self.assertEqual(gate.snapshot()['reservations'][-1]['status'],'RESPONSE_METADATA_REJECTED')
                self.assertTrue((gate.root/'requests/response-002.json').exists())

    def test_exact_payload_hash_and_freeze_order_binding(self):
        gate=self.gate();info=self.register(gate);manifest,raw,bound=info
        altered=json.dumps(json.loads(raw[0])).encode()
        self.assertNotEqual(altered,raw[0])
        for changes in [dict(request_bytes=altered),dict(manifest_sha256='0'*64),dict(trial_id=manifest['slots'][1]['trial_id'])]:
            args=dict(batch_id=manifest['batch_id'],trial_id=manifest['slots'][0]['trial_id'],manifest_sha256=bound,request_bytes=raw[0],transport=self.transport);args.update(changes)
            with self.assertRaises(ValueError):gate.invoke(**args)
        self.assertFalse(self.sent);self.assertFalse(self.ledger()['reservations'])
        self.call(gate,info);self.assertEqual((self.directory/'requests/request-001.json').read_bytes(),raw[0]);gate.close()

    def test_hard_limit_deadline_scope_and_manifest_changes_rejected(self):
        for changed in [dict(max_calls=129),dict(deadline_epoch=w.LATEST_DEADLINE+1),dict(authorized=False),dict(no_retries=False),dict(max_calls=True)]:
            with tempfile.TemporaryDirectory() as temp,self.assertRaises(ValueError):w.WindowBudget.create(Path(temp)/'gate',dict(scope(),**changed),clock=lambda:0)
        gate=self.gate();a=self.register(gate)
        for changed in [dict(max_calls=3),dict(sdk_total_max_attempts=2),dict(runtime_sha256='unbound')]:
            manifest=dict(batch('other')[0],**changed)
            with self.assertRaises(ValueError):gate.register_batch(manifest)
        duplicate=batch('other')[0];duplicate['slots'][0]['trial_id']=a[0]['slots'][0]['trial_id']
        with self.assertRaises(ValueError):gate.register_batch(duplicate)
        gate.close()
        with self.assertRaises(w.GateClosed):w.WindowBudget.open_existing(self.directory,dict(scope(),max_calls=5),clock=lambda:0)

    def test_saved_response_tampering_blocks_clean_reopen(self):
        gate=self.gate();info=self.register(gate);self.call(gate,info);gate.close()
        path=self.directory/'requests/response-001.json';path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(w.GateClosed):w.WindowBudget.open_existing(self.directory,scope(),clock=lambda:0)

    def test_unaccounted_file_blocks_clean_reopen(self):
        gate=self.gate();self.register(gate);gate.close()
        (self.directory/'requests/response-099.json').write_text('{}')
        with self.assertRaises(w.GateClosed):w.WindowBudget.open_existing(self.directory,scope(),clock=lambda:0)

    def test_input_mutation_and_snapshot_cannot_change_authority(self):
        authorization=scope();gate=self.gate(authorization);info=self.register(gate);authorization['max_calls']=999
        external=gate.snapshot();external['scope']['max_calls']=999
        manifest,raw,bound=info;manifest['freeze_sha256']='0'*64
        def mutating(payload):
            payload['modelId']='CHANGED';return self.transport(payload)
        self.call(gate,info,transport=mutating)
        self.assertEqual(gate.snapshot()['scope']['max_calls'],4)
        self.assertEqual((self.directory/'requests/request-001.json').read_bytes(),raw[0]);gate.close()

    def test_duplicate_json_request_keys_never_dispatch(self):
        gate=self.gate();manifest,raw=batch('duplicate-json',1)
        raw[0]=b'{"modelId":"FAKE-A","modelId":"FAKE-B"}'
        manifest['slots'][0]['request_sha256']=w.digest(raw[0])
        bound=gate.register_batch(manifest)
        with self.assertRaises(ValueError):self.call(gate,(manifest,raw,bound))
        self.assertFalse(self.sent);self.assertFalse(self.ledger()['reservations']);gate.close()

    def test_finish_is_terminal_and_cannot_be_reopened(self):
        gate=self.gate();self.register(gate);gate.finish()
        self.assertEqual(self.ledger()['terminal_reason'],'finished')
        with self.assertRaises(w.OwnerBusy):w.WindowBudget.open_existing(self.directory,scope(),clock=lambda:0)

if __name__=='__main__':unittest.main()
