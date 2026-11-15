"""Fake-only session tests. No credentials, SDK, network, Slurm or Dafny."""
import copy
import json
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'runtime'))
import stat
import window_budget as w
import coordinator as c

FAKE_PRIVATE_VALUE = 'FAKE_PRIVATE_VALUE_MUST_NOT_BE_ARCHIVED'
RETAINED = []


def scope(cap=4, deadline=100):
    return dict(window_id='repodisco-session-fake', authorized=True, no_retries=True,
                max_calls=cap, deadline_epoch=deadline, authorization_basis='FAKE TEST ONLY')


def validator(descriptor, directory):
    freeze = json.loads((directory / descriptor['freeze_path']).read_text())
    return freeze['reviewed'] is True and freeze['batch_id'] == descriptor['batch_id']


def executor(descriptor, context):
    evidence = {}
    for trial in context.trial_ids:
        result = context.invoke(trial)
        path = context.output_directory / (trial + '.json')
        path.write_bytes(w.canonical(dict(request_id=result['request_id'], outcome='evaluated')) + b'\n')
        evidence[path.name] = w.digest(path.read_bytes())
    return dict(completed_trials=list(context.trial_ids), evidence_sha256=evidence)


def broken_executor(descriptor, context):
    context.invoke(context.trial_ids[0])
    raise RuntimeError(FAKE_PRIVATE_VALUE)


def incomplete_executor(descriptor, context):
    context.invoke(context.trial_ids[0])
    return dict(completed_trials=list(context.trial_ids), evidence_sha256={})


def caught_error_executor(descriptor, context):
    for trial in context.trial_ids:
        try:
            context.invoke(trial)
        except Exception:
            pass
    return dict(completed_trials=list(context.trial_ids), evidence_sha256={})


def wrong_order_executor(descriptor, context):
    context.invoke(context.trial_ids[-1])
    return dict(completed_trials=list(context.trial_ids), evidence_sha256={})


def retaining_executor(descriptor, context):
    RETAINED.append(context)
    return executor(descriptor, context)


def mutation_executor(descriptor, context):
    context.invoke(context.trial_ids[0])
    path = context.input_directory / descriptor['slots'][1]['request_path']
    path.write_bytes(path.read_bytes() + b' ')
    context.invoke(context.trial_ids[1])
    return dict(completed_trials=list(context.trial_ids), evidence_sha256={})


VALIDATOR_CALLS = 0

def adding_validator(descriptor, directory):
    global VALIDATOR_CALLS
    VALIDATOR_CALLS += 1
    if VALIDATOR_CALLS == 3:
        (directory / 'UNPINNED_CACHE.txt').write_text('accidental validator cache')
    return validator(descriptor, directory)


def nested_executor(descriptor, context):
    evidence = {}
    folder = context.output_directory / 'nested' / 'deeper'
    folder.mkdir(parents=True)
    for trial in context.trial_ids:
        result = context.invoke(trial)
        path = folder / (trial + '.json')
        path.write_bytes(w.canonical(dict(request_id=result['request_id'], outcome='evaluated')) + b'\n')
        evidence[path.relative_to(context.output_directory).as_posix()] = w.digest(path.read_bytes())
    return dict(completed_trials=list(context.trial_ids), evidence_sha256=evidence)


def competing_owner(root, result):
    try:
        w.WindowBudget.open_existing(root, scope(), clock=lambda: 0)
    except Exception as error:
        result.put(type(error).__name__)
    else:
        result.put('UNEXPECTED_OWNER')


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.artifacts = self.root / 'artifacts'
        self.artifacts.mkdir()
        self.now = [0]
        self.sent = []
        self.gate = None
        RETAINED.clear()
        global VALIDATOR_CALLS
        VALIDATOR_CALLS = 0

    def transport(self, payload):
        # This sentinel models a private value retained only in a client closure.
        private = FAKE_PRIVATE_VALUE
        assert private
        self.sent.append(copy.deepcopy(payload))
        return dict(request_id=f'fake-{len(self.sent)}', retry_attempts=0, text='FAKE PUBLIC RESPONSE')

    def session(self, cap=4, callback=executor, transport=None, sleep=None, validation=validator):
        self.gate = w.WindowBudget.create(self.root / 'budget', scope(cap), clock=lambda: self.now[0])
        self.handler = c.ReviewedHandler(validation, callback, {'test_session.py':w.digest(Path(__file__).read_bytes())})
        return c.ResearchSession.create(self.root / 'session', budget=self.gate,
            transport=transport or self.transport, handlers={'fake':self.handler}, artifact_root=self.artifacts,
            code_root=HERE, clock=lambda:self.now[0], sleep=sleep or (lambda seconds:self.now.__setitem__(0,self.now[0]+seconds)))

    def descriptor(self, session, name='a', count=2, reviewed=True):
        directory = self.artifacts / name
        directory.mkdir()
        (directory / 'freeze.json').write_bytes(w.canonical(dict(batch_id=name, reviewed=reviewed)))
        (directory / 'runtime.json').write_bytes(w.canonical(dict(batch_id=name, fake_runtime=True)))
        slots = []
        for index in range(count):
            path = directory / f'request-{index}.json'
            path.write_bytes(w.canonical(dict(modelId='FAKE', trial_id=f'{name}-{index}')))
            slots.append(dict(trial_id=f'{name}-{index}', request_path=path.name, request_sha256=w.digest(path.read_bytes())))
        pins = {p.name:w.digest(p.read_bytes()) for p in directory.iterdir()}
        return dict(schema=c.SCHEMA, sequence=session.next_sequence,
            previous_descriptor_sha256=session.previous_descriptor_sha256, batch_id=name,
            handler_id='fake', handler_binding_sha256=w.digest(w.canonical(self.handler.code_sha256)),
            artifact_directory=name, freeze_path='freeze.json',freeze_sha256=pins['freeze.json'],
            runtime_path='runtime.json',runtime_sha256=pins['runtime.json'],input_sha256=pins,
            slots=slots,max_calls=count,sdk_total_max_attempts=1)

    def status(self):
        return json.loads((self.root/'session/status.json').read_text())

    def _one_then_next(self):
        session=self.session(callback=nested_executor)
        session.publish(self.descriptor(session,count=1))
        session.publish(self.descriptor(session,'b',count=1))
        return session

    def _assert_terminal_sync_failure(self,session):
        self.assertEqual(len(self.sent),1)
        self.assertEqual(self.status()['phase'],'error')
        self.assertEqual(self.status()['completed_batch_ids'],[])
        self.assertIsNotNone(self.gate.snapshot()['terminal_reason'])
        self.assertFalse((session.root/'runs/0001-a/completion.json').exists())
        with self.assertRaises(c.SessionClosed):session.step()

    def test_validator_added_file_on_third_validation_blocks_first_dispatch(self):
        session=self.session(validation=adding_validator)
        session.publish(self.descriptor(session,count=1))
        with self.assertRaises(ValueError):session.step()
        self.assertEqual(VALIDATOR_CALLS,3)
        self.assertFalse(self.sent);self.assertFalse(self.gate.snapshot()['reservations'])
        self.assertEqual(self.status()['phase'],'error')
        self.assertIsNotNone(self.gate.snapshot()['terminal_reason'])

    def test_nested_evidence_and_directories_fsynced_before_each_receipt(self):
        session=self._one_then_next();synced=[];receipts=[]
        original_sync=c.os.fsync;original_write=w.exclusive_bytes
        def sync(fd):
            info=os.fstat(fd);synced.append((info.st_dev,info.st_ino))
            return original_sync(fd)
        def write(path,raw):
            if path.name=='completion.json':
                paths=[path.parent.parent,path.parent,*path.parent.rglob('*')]
                for item in paths:
                    info=item.stat();self.assertIn((info.st_dev,info.st_ino),synced,str(item))
                receipts.append(path)
            return original_write(path,raw)
        session.seal()
        with patch.object(c.os,'fsync',side_effect=sync),patch.object(w,'exclusive_bytes',side_effect=write):
            self.assertEqual(session.run(),'closed')
        self.assertEqual(len(receipts),2);self.assertEqual(len(self.sent),2)
        self.assertEqual(self.status()['completed_batch_ids'],['a','b'])

    def test_evidence_file_fsync_error_is_terminal_before_receipt_or_next_batch(self):
        session=self._one_then_next();original=c.os.fsync;fired=[]
        target=session.root/'runs/0001-a/nested/deeper/a-0.json'
        def sync(fd):
            info=os.fstat(fd)
            if target.exists() and (info.st_dev,info.st_ino)==c._identity(target) and not fired:
                fired.append(True);raise OSError(FAKE_PRIVATE_VALUE)
            return original(fd)
        with patch.object(c.os,'fsync',side_effect=sync),self.assertRaises(OSError):session.step()
        self.assertTrue(fired);self._assert_terminal_sync_failure(session)

    def test_evidence_directory_fsync_error_is_terminal_before_receipt_or_next_batch(self):
        session=self._one_then_next();original=c.os.fsync;fired=[]
        target=session.root/'runs/0001-a/nested/deeper'
        def sync(fd):
            info=os.fstat(fd)
            if target.exists() and (info.st_dev,info.st_ino)==c._identity(target) and not fired:
                fired.append(True);raise OSError(FAKE_PRIVATE_VALUE)
            return original(fd)
        with patch.object(c.os,'fsync',side_effect=sync),self.assertRaises(OSError):session.step()
        self.assertTrue(fired);self._assert_terminal_sync_failure(session)

    def test_evidence_bytes_drifting_during_sync_are_terminal(self):
        session=self._one_then_next();original=c.os.fsync;fired=[]
        target=session.root/'runs/0001-a/nested/deeper/a-0.json'
        def sync(fd):
            info=os.fstat(fd)
            if target.exists() and (info.st_dev,info.st_ino)==c._identity(target) and not fired:
                fired.append(True);target.write_bytes(b'changed during sync')
            return original(fd)
        with patch.object(c.os,'fsync',side_effect=sync),self.assertRaises(ValueError):session.step()
        self.assertTrue(fired);self._assert_terminal_sync_failure(session)

    def test_added_evidence_during_directory_sync_is_terminal(self):
        session=self._one_then_next();original=c.os.fsync;fired=[]
        target=session.root/'runs/0001-a/nested/deeper'
        def sync(fd):
            info=os.fstat(fd)
            if target.exists() and (info.st_dev,info.st_ino)==c._identity(target) and not fired:
                fired.append(True);(target/'unaccounted.txt').write_bytes(b'unpinned')
            return original(fd)
        with patch.object(c.os,'fsync',side_effect=sync),self.assertRaises(ValueError):session.step()
        self.assertTrue(fired);self._assert_terminal_sync_failure(session)

    def test_same_byte_file_replacement_during_sync_is_terminal(self):
        session=self._one_then_next();original=c.os.fsync;fired=[]
        target=session.root/'runs/0001-a/nested/deeper/a-0.json'
        def sync(fd):
            info=os.fstat(fd)
            if target.exists() and (info.st_dev,info.st_ino)==c._identity(target) and not fired:
                fired.append(True);raw=target.read_bytes();target.unlink();target.write_bytes(raw)
            return original(fd)
        with patch.object(c.os,'fsync',side_effect=sync),self.assertRaises(ValueError):session.step()
        self.assertTrue(fired);self._assert_terminal_sync_failure(session)

    def test_two_batches_complete_under_one_aggregate_ledger(self):
        session=self.session();first=self.descriptor(session);h=session.publish(first)
        second=self.descriptor(session,'b');self.assertEqual(second['previous_descriptor_sha256'],h);session.publish(second)
        self.assertFalse(self.gate.snapshot()['batches'])
        session.seal();self.assertEqual(session.run(),'closed')
        self.assertEqual(len(self.sent),4)
        self.assertEqual([r['trial_id'] for r in self.gate.snapshot()['reservations']],['a-0','a-1','b-0','b-1'])
        self.assertEqual(self.status()['completed_batch_ids'],['a','b'])
        self.assertEqual(self.status()['reason'],'sealed_queue_complete')
        self.assertTrue((self.root/'budget/research-session.lock').exists())
        self.assertIsNotNone(self.gate.snapshot()['terminal_reason'])
        phases=[json.loads(p.read_text())['phase'] for p in sorted((session.root/'events').iterdir())]
        for phase in ('idle','running','completed','closed'):self.assertIn(phase,phases)

    def test_aggregate_overallocation_closes_without_registration_or_dispatch(self):
        session=self.session(cap=3);session.publish(self.descriptor(session))
        with self.assertRaises(ValueError):session.publish(self.descriptor(session,'b'))
        self.assertEqual(self.status()['phase'],'error');self.assertFalse(self.sent)
        self.assertFalse(self.gate.snapshot()['batches']);self.assertIsNotNone(self.gate.snapshot()['terminal_reason'])

    def test_validator_must_pass_before_budget_registration(self):
        session=self.session()
        with self.assertRaises(ValueError):session.publish(self.descriptor(session,reviewed=False))
        self.assertFalse(self.gate.snapshot()['batches']);self.assertFalse(self.sent)

    def test_idle_loop_stops_at_deadline(self):
        session=self.session();self.assertEqual(session.run(poll_interval=30),'closed')
        self.assertEqual(self.now[0],100);self.assertFalse(self.sent)
        self.assertEqual(self.status()['reason'],'deadline')

    def test_deadline_between_requests_blocks_next_slot(self):
        def slow(payload):
            result=self.transport(payload);self.now[0]=100;return result
        session=self.session(transport=slow);session.publish(self.descriptor(session))
        self.assertEqual(session.step(),'closed');self.assertEqual(len(self.sent),1)
        self.assertEqual(self.status()['reason'],'deadline');self.assertEqual(self.status()['completed_batch_ids'],[])

    def test_inflight_last_response_can_be_logged_after_deadline_without_next_batch(self):
        def slow(payload):
            result=self.transport(payload);self.now[0]=100;return result
        session=self.session(transport=slow);session.publish(self.descriptor(session,count=1))
        self.assertEqual(session.step(),'closed');self.assertEqual(len(self.sent),1)
        self.assertEqual(self.status()['completed_batch_ids'],['a'])
        self.assertTrue((session.root/'runs/0001-a/completion.json').is_file())

    def test_deadline_during_window_reservation_never_dispatches(self):
        session=self.session();session.publish(self.descriptor(session));original=w.durable_json
        def persist(path,value):
            original(path,value)
            if path.name=='ledger.json' and value.get('reservations'):
                if value['reservations'][-1]['status']=='RESERVED':self.now[0]=100
        with patch.object(w,'durable_json',side_effect=persist),self.assertRaises(w.GateClosed):session.step()
        self.assertFalse(self.sent);self.assertEqual(len(self.gate.snapshot()['reservations']),1)
        self.assertEqual(self.status()['phase'],'error')

    def test_duplicate_and_out_of_order_descriptors_are_terminal(self):
        session=self.session();a=self.descriptor(session);session.publish(a)
        with self.assertRaises(ValueError):session.publish(a)
        self.assertFalse(self.sent);self.assertEqual(self.status()['phase'],'error')

    def test_out_of_order_first_descriptor_never_registers(self):
        session=self.session();d=self.descriptor(session);d['sequence']=2
        with self.assertRaises(ValueError):session.publish(d)
        self.assertFalse(self.sent);self.assertFalse(self.gate.snapshot()['batches'])

    def test_deadline_during_idle_supplier_closes_before_publishing(self):
        session=self.session();d=self.descriptor(session)
        def late(sequence,previous):self.now[0]=100;return d
        self.assertEqual(session.run(supply=late),'closed')
        self.assertFalse(self.sent);self.assertFalse(self.gate.snapshot()['batches'])
        self.assertEqual(self.status()['reason'],'deadline')

    def test_wrong_predecessor_is_terminal(self):
        session=self.session();d=self.descriptor(session);d['previous_descriptor_sha256']='1'*64
        with self.assertRaises(ValueError):session.publish(d)
        self.assertFalse(self.sent)

    def test_queue_tampering_prevents_execution(self):
        session=self.session();session.publish(self.descriptor(session));p=next((session.root/'queue').iterdir())
        p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(ValueError):session.step()
        self.assertFalse(self.sent);self.assertFalse(self.gate.snapshot()['batches'])

    def test_unpublished_queue_file_is_not_a_command(self):
        session=self.session();(session.root/'queue/0001-unreviewed.json').write_text('{}')
        with self.assertRaises(ValueError):session.step()
        self.assertFalse(self.sent)

    def test_frozen_input_hash_and_inventory_changes_are_terminal(self):
        session=self.session();d=self.descriptor(session);session.publish(d)
        (self.artifacts/'a/request-0.json').write_text('{"different":true}')
        with self.assertRaises(ValueError):session.step()
        self.assertFalse(self.sent);self.assertFalse(self.gate.snapshot()['batches'])

    def test_code_binding_is_checked_again_before_execution(self):
        session=self.session();session.publish(self.descriptor(session));original=c._hash_file
        def changed(path):return '0'*64 if Path(path).resolve()==Path(__file__).resolve() else original(path)
        with patch.object(c,'_hash_file',side_effect=changed),self.assertRaises(ValueError):session.step()
        self.assertFalse(self.sent)

    def test_mutation_between_requests_prevents_second_dispatch(self):
        session=self.session(callback=mutation_executor);session.publish(self.descriptor(session))
        with self.assertRaises(ValueError):session.step()
        self.assertEqual(len(self.sent),1);self.assertEqual(self.status()['phase'],'error')

    def test_wrong_request_order_cannot_spend_a_slot(self):
        session=self.session(callback=wrong_order_executor);session.publish(self.descriptor(session))
        with self.assertRaises(ValueError):session.step()
        self.assertFalse(self.sent);self.assertFalse(self.gate.snapshot()['reservations'])

    def test_executor_error_stops_global_budget_and_redacts_exception(self):
        session=self.session(callback=broken_executor);session.publish(self.descriptor(session));session.publish(self.descriptor(session,'b'))
        with self.assertRaises(RuntimeError):session.step()
        self.assertEqual(len(self.sent),1);self.assertEqual(self.status()['phase'],'error')
        self.assertIsNotNone(self.gate.snapshot()['terminal_reason'])
        with self.assertRaises(c.SessionClosed):session.step()
        for path in self.root.rglob('*'):
            if path.is_file():self.assertNotIn(FAKE_PRIVATE_VALUE.encode(),path.read_bytes())

    def test_caught_ambiguous_transport_error_cannot_continue(self):
        def timed_out(payload):self.sent.append(payload);raise TimeoutError(FAKE_PRIVATE_VALUE)
        session=self.session(callback=caught_error_executor,transport=timed_out);session.publish(self.descriptor(session))
        with self.assertRaises(c.SessionError):session.step()
        self.assertEqual(len(self.sent),1);self.assertEqual(self.status()['phase'],'error')
        self.assertEqual(self.gate.snapshot()['reservations'][0]['status'],'AMBIGUOUS_OR_UNSAVED')
        self.assertIsNotNone(self.gate.snapshot()['terminal_reason'])

    def test_incomplete_success_receipt_is_not_a_completed_batch(self):
        session=self.session(callback=incomplete_executor);session.publish(self.descriptor(session))
        with self.assertRaises(ValueError):session.step()
        self.assertEqual(len(self.sent),1);self.assertEqual(self.status()['completed_batch_ids'],[])
        self.assertIsNotNone(self.gate.snapshot()['terminal_reason'])

    def test_retained_batch_capability_never_reruns_completed_trial(self):
        session=self.session(callback=retaining_executor);session.publish(self.descriptor(session,count=1));self.assertEqual(session.step(),'completed')
        with self.assertRaises(c.SessionClosed):RETAINED[0].invoke('a-0')
        self.assertEqual(len(self.sent),1);self.assertIsNotNone(self.gate.snapshot()['terminal_reason'])

    def test_stop_marker_blocks_remaining_requests_cleanly(self):
        def stop_after_first(payload):
            result=self.transport(payload);w.exclusive_bytes(self.root/'session/STOP',b'');return result
        session=self.session(transport=stop_after_first);session.publish(self.descriptor(session));session.publish(self.descriptor(session,'b'))
        self.assertEqual(session.run(),'closed');self.assertEqual(len(self.sent),1)
        self.assertEqual(self.status()['reason'],'stop_requested');self.assertEqual(self.status()['completed_batch_ids'],[])

    def test_stop_arriving_during_reservation_prevents_transport(self):
        session=self.session();session.publish(self.descriptor(session));original=w.durable_json
        def persist(path,value):
            original(path,value)
            if path.name=='ledger.json' and value.get('reservations'):
                if value['reservations'][-1]['status']=='DISPATCHING' and not (session.root/'STOP').exists():
                    w.exclusive_bytes(session.root/'STOP',b'')
        with patch.object(w,'durable_json',side_effect=persist):self.assertEqual(session.step(),'closed')
        self.assertFalse(self.sent);self.assertEqual(len(self.gate.snapshot()['reservations']),1)
        self.assertEqual(self.status()['reason'],'stop_requested')
        self.assertIsNotNone(self.gate.snapshot()['terminal_reason'])

    def test_reentrant_transport_attempt_is_terminal_even_if_caught(self):
        def nested(payload):
            try:RETAINED[0].invoke('a-1')
            except c.SessionClosed:pass
            return self.transport(payload)
        session=self.session(callback=retaining_executor,transport=nested);session.publish(self.descriptor(session))
        with self.assertRaises(c.SessionClosed):session.step()
        self.assertEqual(len(self.sent),1);self.assertIsNotNone(self.gate.snapshot()['terminal_reason'])
        self.assertEqual(self.status()['phase'],'error')

    def test_publish_after_seal_is_terminal_and_cannot_spend(self):
        session=self.session();session.seal()
        with self.assertRaises(ValueError):session.publish(self.descriptor(session))
        self.assertFalse(self.sent);self.assertIsNotNone(self.gate.snapshot()['terminal_reason'])

    def test_session_directory_and_canonical_owner_cannot_restart(self):
        session=self.session()
        kwargs=dict(budget=self.gate,transport=self.transport,handlers={'fake':self.handler},artifact_root=self.artifacts,code_root=HERE,clock=lambda:0)
        with self.assertRaises(FileExistsError):c.ResearchSession.create(session.root,**kwargs)
        with self.assertRaises(c.SessionBusy):c.ResearchSession.create(self.root/'second-session',**kwargs)
        self.assertFalse(self.sent)

    def test_competing_process_cannot_take_canonical_owner(self):
        session=self.session();ctx=multiprocessing.get_context('spawn');result=ctx.Queue()
        child=ctx.Process(target=competing_owner,args=(str(self.gate.root),result));child.start();child.join(15)
        if child.is_alive():child.terminate();child.join();self.fail('Ownership test timed out')
        self.assertEqual(child.exitcode,0);self.assertEqual(result.get(timeout=2),'OwnerBusy');self.assertFalse(self.sent)

    @unittest.skipUnless(hasattr(os,'fork'),'POSIX required')
    def test_fork_inherited_session_cannot_dispatch(self):
        session=self.session();session.publish(self.descriptor(session));read,write=os.pipe();pid=os.fork()
        if pid==0:
            os.close(read)
            try:session.step()
            except BaseException as error:os.write(write,type(error).__name__.encode())
            else:os.write(write,b'UNEXPECTED')
            os.close(write);os._exit(0)
        os.close(write);answer=os.read(read,100);os.close(read);os.waitpid(pid,0)
        self.assertEqual(answer,b'SessionBusy');self.assertFalse(self.sent);self.assertFalse(self.gate.snapshot()['reservations'])

    def test_status_persistence_failure_stops_without_next_batch(self):
        session=self.session();session.publish(self.descriptor(session,count=1));session.publish(self.descriptor(session,'b',count=1))
        original=w.durable_json;failed=[False]
        def persist(path,value):
            if path.name=='status.json' and value.get('phase')=='completed' and not failed[0]:
                failed[0]=True;raise OSError(FAKE_PRIVATE_VALUE)
            original(path,value)
        with patch.object(w,'durable_json',side_effect=persist),self.assertRaises(OSError):session.step()
        self.assertEqual(len(self.sent),1);self.assertIsNotNone(self.gate.snapshot()['terminal_reason'])

    def test_fixed_supplier_can_add_an_independent_batch_only_after_completion(self):
        session=self.session();seen=[]
        def supplier(sequence,previous):
            seen.append((sequence,list(session.completed)))
            if sequence<=2:return self.descriptor(session,chr(96+sequence),count=1)
            session.seal();return None
        self.assertEqual(session.run(poll_interval=1,supply=supplier),'closed')
        self.assertEqual(seen,[(1,[]),(2,['a']),(3,['a','b'])]);self.assertEqual(len(self.sent),2)

    def test_tampered_durable_budget_cannot_be_ignored(self):
        session=self.session();session.publish(self.descriptor(session));p=self.gate.root/'ledger.json';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(ValueError):session.step()
        self.assertFalse(self.sent)


if __name__=='__main__':unittest.main(verbosity=2)
