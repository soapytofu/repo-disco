"""Offline submission, archive and accounting boundaries; no live transport."""
import contextlib
import hashlib
import io
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import ops
import build_runtime as builder
import preflight


def sdk_record():
    return dict(required=True, installed=True, client_created=False,
                config=dict(connect_timeout=15,read_timeout=180,retries=dict(mode='standard',total_max_attempts=1)))


def sdk_auth_record():
    return dict(status='PASS', required=True, returncode=0, scenarios=3,
                record=dict(status='PASS', real_credentials_read=False, model_calls=0,
                            native_calls=0, provider_requests=0, socket_connection_attempts=0))


class TransportAndSubmissionTests(unittest.TestCase):
    def test_transport_uses_only_socket_and_hard_timeout(self):
        observed = []
        def fake_run(argv, **kwargs):
            observed.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, stdout=b'fake', stderr=b'')
        with patch.object(ops.subprocess, 'run', fake_run), patch.object(ops, 'sha', return_value='a' * 64):
            self.assertEqual(ops.remote('print("fake")', seconds=17, socket=Path('/tmp/test-only.sock')), b'fake')
        argv, kwargs = observed[0]
        self.assertEqual(len(observed), 1)
        self.assertIn('/tmp/test-only.sock', argv)
        self.assertIn('BatchMode=yes', argv)
        self.assertIn('ProxyCommand=false', argv)
        self.assertEqual(kwargs['timeout'], 17)
        self.assertIn('real-repository-growth-001/execution-002', argv[-1])
        self.assertEqual(shlex.split(argv[-1])[:3],
                         ['/n/home13/sophiezeng/.conda/envs/repodisco/bin/python', '-B', '-c'])
        self.assertNotIn('python3 -c', argv[-1])

    def test_absent_or_stale_authorization_stops_before_transport_or_intent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(ops, 'ROOT', root), patch.object(ops, 'validate_package'), \
                 patch.object(ops, 'validate_authorization', side_effect=ValueError('expired authorization')), \
                 patch.object(ops, 'remote', side_effect=AssertionError('transport reached')):
                with self.assertRaisesRegex(ValueError, 'expired'):
                    ops.submit(root / 'authorization.json')
            self.assertFalse((root / 'submissions').exists())

    def test_prior_intent_output_claim_or_ledger_cannot_restart(self):
        for marker in ('model-001', 'startup-failure.json', 'execution.claim.json',
                       'submissions/model.intent.json', 'requests-ledger.json'):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); path = root / marker
                path.parent.mkdir(parents=True, exist_ok=True); path.write_text('prior state')
                with self.assertRaises(ValueError):
                    ops.fresh_execution(root)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'execution.claim.json').symlink_to(root/'missing-target')
            with self.assertRaises(ValueError): ops.fresh_execution(root)

    def test_private_handoff_is_metadata_only_and_rejects_unsafe_modes_or_links(self):
        with tempfile.TemporaryDirectory() as temp:
            key = Path(temp) / 'synthetic-private'; key.write_bytes(b'FAKE-NOT-A-CREDENTIAL')
            key.chmod(0o600)
            with patch.object(Path, 'open', side_effect=AssertionError('content read')):
                result = ops.private_handoff_metadata(key)
            self.assertFalse(result['content_read'])
            key.chmod(0o644)
            with self.assertRaises(ValueError): ops.private_handoff_metadata(key)
            key.chmod(0o600); link = Path(temp) / 'link'; link.symlink_to(key)
            with self.assertRaises(ValueError): ops.private_handoff_metadata(link)

    def test_partition_must_be_shared_nonpreemptible_up_and_four_hours(self):
        good = 'PartitionName=shared MaxTime=04:00:00 State=UP PreemptMode=OFF'
        self.assertEqual(ops.partition_seconds(good), 14400)
        self.assertIsNone(ops.partition_seconds(good.replace('04:00:00', 'UNLIMITED')))
        for bad in (good.replace('04:00:00', '03:59:59'), good.replace('OFF', 'CANCEL'),
                    good.replace('UP', 'DOWN'), good.replace('shared', 'test'),
                    good.replace('04:00:00', 'UNKNOWN')):
            with self.subTest(value=bad), self.assertRaises(ValueError): ops.partition_seconds(bad)

    def test_matching_queue_refuses_changed_job_name_or_directory(self):
        for row in ('12|/runtime|other-name|RUNNING', '12|/other|' + ops.JOB_NAME + '|PENDING'):
            with self.assertRaises(ValueError): ops.no_matching_queue(row, Path('/runtime'))
        ops.no_matching_queue('12|/unrelated|unrelated|RUNNING', Path('/runtime'))
        with self.assertRaises(ValueError): ops.no_matching_queue('bad listing', Path('/runtime'))

    def test_ambiguous_submit_keeps_intent_and_no_second_transport(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); authorization = root / 'explicit.json'; authorization.write_text('{}')
            with patch.object(ops, 'ROOT', root), patch.object(ops, 'validate_package'), \
                 patch.object(ops, 'validate_authorization'), patch.object(ops, 'sha', return_value='a' * 64), \
                 patch.object(ops, 'remote', side_effect=subprocess.TimeoutExpired('synthetic', 1)) as transport:
                with self.assertRaises(subprocess.TimeoutExpired): ops.submit(authorization)
                with self.assertRaisesRegex(ValueError, 'Existing submission'): ops.submit(authorization)
            self.assertEqual(transport.call_count, 1)
            self.assertTrue((root / 'submissions/model.intent.json').exists())
            self.assertTrue((root / 'submissions/model.transport-failure.json').exists())

    def test_failed_sbatch_receipt_is_preserved_and_cannot_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); authorization = root / 'explicit.json'; authorization.write_text('{}')
            receipt = dict(returncode=1, stdout='', stderr='synthetic scheduler rejection')
            with patch.object(ops, 'ROOT', root), patch.object(ops, 'validate_package'), \
                 patch.object(ops, 'validate_authorization'), patch.object(ops, 'sha', return_value='a' * 64), \
                 patch.object(ops, 'remote', return_value=json.dumps(receipt).encode()) as transport, \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, 'failed or ambiguous'): ops.submit(authorization)
                with self.assertRaisesRegex(ValueError, 'Existing submission'): ops.submit(authorization)
            self.assertEqual(transport.call_count, 1)
            self.assertEqual(json.loads((root / 'submissions/model.json').read_bytes()), receipt)

def accounting(*rows):
    header='|'.join(ops.ACCOUNTING_FIELDS)
    return header+'\n'+''.join(job+'|'+state+'|00:00:01|1|0:0|1|00:00:01|1|1K|fake-node\n'
                              for job,state in rows)


class TerminalAccountingTests(unittest.TestCase):
    def test_each_explicit_terminal_parent_state_is_admitted(self):
        for state in ops.TERMINAL_STATES:
            with self.subTest(state=state):
                result=ops.terminal_accounting(accounting(('12345',state)), '12345')
                self.assertTrue(result['all_relevant_rows_terminal'])
                self.assertEqual(result['rows'][0]['normalized_state'],state)

    def test_normal_display_suffixes_are_normalized(self):
        result=ops.terminal_accounting(accounting(('12345','CANCELLED by 4567'),
                    ('12345.batch','CANCELLED+'),('12345.extern','COMPLETED+'),
                    ('12345.0','CANCELLED by 4567+')), '12345')
        self.assertEqual([r['normalized_state'] for r in result['rows']],
                         ['CANCELLED','CANCELLED','COMPLETED','CANCELLED'])

    def test_missing_and_duplicate_exact_parent_fail_closed(self):
        for rows in [(('123450','COMPLETED'),), (('12345.batch','COMPLETED'),),
                     (('12345','COMPLETED'),('12345','COMPLETED'))]:
            with self.subTest(rows=rows), self.assertRaisesRegex(ValueError,'parent'):
                ops.terminal_accounting(accounting(*rows),'12345')

    def test_similar_prefixes_cannot_replace_parent_or_become_its_steps(self):
        raw=accounting(('12345','COMPLETED'),('12345.batch','COMPLETED'),
                       ('123450','RUNNING'),('123450.batch','SUSPENDED'),
                       ('912345','UNKNOWN'),('12345_0','PENDING'))
        result=ops.terminal_accounting(raw,'12345')
        self.assertEqual([r['job_id'] for r in result['rows']],['12345','12345.batch'])
        self.assertEqual(result['ignored_job_ids'],['123450','123450.batch','912345','12345_0'])

    def test_live_unknown_and_requeue_parent_states_fail_closed(self):
        for state in ('SUSPENDED','STOPPED','RUNNING','PENDING','COMPLETING','CONFIGURING',
                      'REQUEUED','REQUEUE_HOLD','SIGNALING','STAGE_OUT','SPECIAL_EXIT','FUTURE_STATE'):
            with self.subTest(state=state), self.assertRaisesRegex(ValueError,'Nonterminal or unknown'):
                ops.terminal_accounting(accounting(('12345',state)),'12345')

    def test_live_or_unknown_step_blocks_terminal_parent(self):
        for ident in ('12345.batch','12345.extern','12345.0'):
            for state in ('RUNNING','SUSPENDED','STOPPED','UNKNOWN'):
                with self.subTest(ident=ident,state=state), self.assertRaisesRegex(ValueError,'Nonterminal or unknown'):
                    ops.terminal_accounting(accounting(('12345','COMPLETED'),(ident,state)),'12345')

    def test_duplicate_step_and_malformed_relevant_step_fail_closed(self):
        for rows in [(('12345','COMPLETED'),('12345.batch','COMPLETED'),('12345.batch','COMPLETED')),
                     (('12345','COMPLETED'),('12345.','COMPLETED')),
                     (('12345','COMPLETED'),('12345..batch','COMPLETED'))]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                ops.terminal_accounting(accounting(*rows),'12345')

    def test_unknown_suffix_or_truncated_base_is_never_guessed(self):
        for state in ('OUT_OF_ME+','COMPLETED unexpected','COMPLETED by 7','CANCELLED by user',
                      'CANCELLED+++','COMPLETED+RUNNING',''):
            with self.subTest(state=state), self.assertRaises(ValueError):
                ops.terminal_accounting(accounting(('12345',state)),'12345')

    def test_missing_header_malformed_rows_and_bad_parent_identifiers_rejected(self):
        for text in ('', 'JobID|State\n12345|COMPLETED\n',
                     accounting(('12345','COMPLETED'))+'12345.batch|COMPLETED\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                ops.terminal_accounting(text,'12345')
        for job in ('12345.batch','12345_0','012345','',12345):
            with self.subTest(job=job), self.assertRaises(ValueError):
                ops.terminal_accounting(accounting(('12345','COMPLETED')),job)


class ActualRemoteProgramTests(unittest.TestCase):
    def setup_roots(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        base = Path(temp.name); local = base / 'local'; remote = base / 'remote'
        for root in (local, remote):
            root.mkdir(); (root / 'submissions').mkdir()
            code = root / 'repo' / ops.REL; code.mkdir(parents=True)
            freeze = json.dumps(dict(schema='repodisco-growth-execution-runtime-v1', repo_files={})).encode()
            for destination in (root / 'runtime-freeze.json', code / 'runtime-freeze.json'):
                destination.write_bytes(freeze)
            for destination in (root / 'run.sbatch', code / 'run.sbatch'):
                destination.write_bytes(b'#!/bin/bash\n# synthetic fixture\n')
        return local, remote

    def execute_remote(self, code, root, data=None, query=None, run=None):
        output = io.BytesIO()
        class Output:
            buffer = output
            def write(self, value): output.write(value.encode())
            def flush(self): pass
        code = code.replace('EXPECTED_RUNTIME', repr(ops.sha(root / 'runtime-freeze.json')))
        stdin = SimpleNamespace(buffer=io.BytesIO(data or b''))
        with patch.object(subprocess, 'check_output', query or (lambda *a, **k: '')), \
             patch.object(sys, 'stdout', Output()), patch.object(sys, 'stdin', stdin), \
             patch.object(sys, 'path', list(sys.path)):
            if run is not None:
                with patch.object(subprocess, 'run', run):
                    exec(compile(code, '<synthetic-remote>', 'exec'), {'root': root, 'Path': Path})
            else:
                exec(compile(code, '<synthetic-remote>', 'exec'), {'root': root, 'Path': Path})
        return output.getvalue()

    def test_remote_submit_checks_live_partition_and_writes_one_receipt(self):
        local, remote = self.setup_roots(); calls = []
        (remote / 'remote-preflight-001.json').write_text(json.dumps(dict(returncode=0, runtime_sha256=ops.sha(remote/'runtime-freeze.json'), sdk=sdk_record(), sdk_auth_regression=sdk_auth_record())))
        auth = dict(authorized_runtime_root=str(remote), output_relative_path='model-001')
        import runtime
        def query(argv, **kwargs):
            self.assertEqual(kwargs['timeout'], 15)
            if argv[0] == 'squeue': return ''
            self.assertEqual(argv, ['scontrol','show','partition','shared'])
            return 'PartitionName=shared MaxTime=1-00:00:00 State=UP PreemptMode=OFF'
        def submit(argv, **kwargs):
            calls.append(argv); self.assertEqual(kwargs['timeout'], 25)
            return subprocess.CompletedProcess(argv, 0, stdout='12345;cluster\n', stderr='')
        with patch.object(runtime, 'validate_package'), patch.object(runtime, 'validate_authorization', return_value=auth), \
             patch.object(ops, 'private_handoff_metadata', return_value=dict(content_read=False)):
            raw = self.execute_remote(ops.SUBMIT, remote, json.dumps(auth).encode(), query=query, run=submit)
            with self.assertRaisesRegex(ValueError, 'Existing submission'):
                self.execute_remote(ops.SUBMIT, remote, json.dumps(auth).encode(), query=query, run=submit)
        self.assertEqual(calls, [['sbatch','--parsable','--partition=shared','run.sbatch']])
        self.assertEqual(json.loads(raw)['job_id'], '12345')
        self.assertEqual((remote/'authorization.json').read_bytes(), json.dumps(auth).encode())
        self.assertTrue((remote/'submissions/model.lock').exists())

    def test_remote_wrong_root_authorization_rejected_before_handoff_or_sbatch(self):
        local, remote = self.setup_roots()
        (remote / 'remote-preflight-001.json').write_text(json.dumps(dict(returncode=0, runtime_sha256=ops.sha(remote/'runtime-freeze.json'), sdk=sdk_record(), sdk_auth_regression=sdk_auth_record())))
        import runtime
        with patch.object(runtime, 'validate_package'), \
             patch.object(runtime, 'validate_authorization', return_value=dict(authorized_runtime_root='/wrong', output_relative_path='model-001')), \
             patch.object(ops, 'private_handoff_metadata', side_effect=AssertionError('handoff reached')) as key:
            with self.assertRaises(AssertionError):
                self.execute_remote(ops.SUBMIT, remote, b'{}')
        self.assertEqual(key.call_count, 0)
        self.assertFalse((remote/'submissions/model.lock').exists())

    def test_remote_submit_requires_successful_sdk_regression_before_handoff(self):
        local, remote = self.setup_roots()
        import runtime
        variants = [None]
        for field, value in [('status', 'FAIL'), ('required', False), ('scenarios', 0), ('returncode', 1)]:
            item = sdk_auth_record(); item[field] = value; variants.append(item)
        item = sdk_auth_record(); item['record']['provider_requests'] = 1; variants.append(item)
        for regression in variants:
            record = dict(returncode=0, runtime_sha256=ops.sha(remote/'runtime-freeze.json'), sdk=sdk_record())
            if regression is not None:
                record['sdk_auth_regression'] = regression
            (remote / 'remote-preflight-001.json').write_text(json.dumps(record))
            with self.subTest(regression=regression), patch.object(runtime, 'validate_package'), \
                    patch.object(ops, 'private_handoff_metadata', side_effect=AssertionError('handoff reached')) as key:
                with self.assertRaises((AssertionError, KeyError)):
                    self.execute_remote(ops.SUBMIT, remote, b'{}')
            self.assertEqual(key.call_count, 0)
            self.assertFalse((remote/'authorization.json').exists())
            self.assertFalse((remote/'submissions/model.lock').exists())

    def fake_fetch(self, raw):
        local, remote = self.setup_roots()
        (local/'submissions/model.json').write_text(json.dumps(dict(job_id='12345')))
        for name in ('submissions/model.lock','submissions/model.json','authorization.json','remote-preflight-001.json'):
            (remote/name).write_text('{}')
        (remote/'model-001').mkdir()
        (remote/'model-001/evidence.txt').write_text('synthetic saved evidence')
        (remote/'model-001/archive-manifest.json').write_text('{}')
        target = remote/'model-001/slot-01/native/fresh-target'; target.mkdir(parents=True)
        (target/'generated-cache').write_text('not evidence')
        captured = []
        def query(argv, **kwargs):
            self.assertEqual(argv[:3], ['sacct','-j','12345'])
            self.assertIn('State%80', argv[3]); self.assertEqual(kwargs['timeout'], 15)
            return raw
        def transport(code, data=None, seconds=45, socket=None):
            result = self.execute_remote(code, remote, data, query=query)
            captured.append(result); return result
        def run(free=1024*1024*1024):
            with patch.object(ops, 'ROOT', local), patch.object(ops, 'remote', transport), \
                 patch.object(ops.shutil, 'disk_usage', return_value=SimpleNamespace(free=free)), \
                 contextlib.redirect_stdout(io.StringIO()): ops.fetch()
        return run, local, remote, captured

    def test_terminal_fetch_preserves_logs_and_excludes_only_fixed_scratch(self):
        raw = accounting(('12345','COMPLETED'),('12345.batch','COMPLETED'))
        run, local, remote, captured = self.fake_fetch(raw); run()
        self.assertEqual(len(captured), 2)
        retrieved = local/'retrieved-001'
        self.assertEqual((retrieved/'accounting.txt').read_text(), raw)
        self.assertTrue((retrieved/'model-001/evidence.txt').exists())
        self.assertTrue((retrieved/'model-001/archive-manifest.json').exists())
        self.assertFalse((retrieved/'model-001/slot-01/native/fresh-target').exists())
        self.assertTrue((remote/'model-001/slot-01/native/fresh-target/generated-cache').exists())
        self.assertEqual(json.loads(captured[0])['excluded_scratch_directories'], ['model-001/slot-01/native/fresh-target'])
        with self.assertRaisesRegex(ValueError, 'Already fetched'): run()

    def test_live_step_prevents_accounting_and_archive_mutation(self):
        run, local, remote, captured = self.fake_fetch(accounting(('12345','COMPLETED'),('12345.batch','SUSPENDED')))
        with self.assertRaisesRegex(ValueError, 'Nonterminal or unknown'): run()
        self.assertEqual(captured, [])
        self.assertFalse((remote/'accounting.txt').exists())
        self.assertFalse((local/'retrieved-001').exists())

    def test_insufficient_space_only_performs_read_only_estimate(self):
        run, local, remote, captured = self.fake_fetch(accounting(('12345','COMPLETED')))
        with self.assertRaisesRegex(ValueError, 'Insufficient local disk'): run(64*1024*1024)
        self.assertEqual(len(captured), 1)
        self.assertFalse((remote/'accounting.txt').exists())
        self.assertFalse((local/'retrieved-001').exists())

    def test_unrecognized_cache_path_is_evidence_and_symlinks_are_rejected(self):
        run, local, remote, captured = self.fake_fetch(accounting(('12345','COMPLETED')))
        other = remote/'model-001/slot-09/native/fresh-target'; other.mkdir(parents=True)
        (other/'important.txt').write_text('not an allowed exclusion')
        broken = remote/'model-001/source-link'; broken.symlink_to(other/'important.txt')
        with self.assertRaisesRegex(ValueError, 'Symlink|Nonregular'): run()
        broken.unlink(); run()
        self.assertTrue((local/'retrieved-001/model-001/slot-09/native/fresh-target/important.txt').exists())


class PackageBoundaryTests(unittest.TestCase):
    def test_sdk_import_preflight_constructs_only_config_not_client(self):
        calls=[]
        def config(**kwargs):
            calls.append(kwargs);return SimpleNamespace(**kwargs)
        fake=SimpleNamespace(__version__='SYNTHETIC-VERSION',client=lambda *a,**k: (_ for _ in ()).throw(AssertionError('client reached')))
        with patch.dict(sys.modules,{'boto3':fake,'botocore':fake,'botocore.config':SimpleNamespace(Config=config)}):
            result=preflight.sdk_preflight(required=True)
        self.assertEqual(len(calls),1)
        self.assertEqual(result['config'],sdk_record()['config'])
        self.assertEqual(result['boto3_version'],'SYNTHETIC-VERSION')
        self.assertFalse(result['client_created'])
        self.assertEqual(result['model_calls'],0)

    def test_absent_sdk_is_optional_locally_and_required_for_remote(self):
        with patch.dict(sys.modules,{'boto3':None}):
            self.assertFalse(preflight.sdk_preflight()['installed'])
            with self.assertRaisesRegex(ValueError,'imports unavailable'):preflight.sdk_preflight(required=True)

    def test_freeze_is_explicit_exclusive_and_contains_no_authorization(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp); root = repo/builder.REL; root.mkdir(parents=True)
            fake = dict(repo_files={'synthetic.py':'a'*64},package_bytes=10,model_calls_authorized=0)
            with patch.object(builder,'collect',return_value=fake):
                result = builder.freeze(repo)
                with self.assertRaisesRegex(ValueError,'Freeze already exists'): builder.freeze(repo)
            self.assertFalse(result['execution_authorized'])
            self.assertFalse((root/'authorization.json').exists())

    def test_stage_archive_preserves_relative_paths_and_never_includes_authorization(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp); root = repo/ops.REL; root.mkdir(parents=True)
            (root/'run.sbatch').write_text('# synthetic\n')
            (repo/'input.txt').write_text('exact input\n')
            (root/'authorization.json').write_text('not selected by package')
            pins={name:ops.sha(repo/name) for name in ('input.txt',ops.REL+'/run.sbatch')}
            (root/'runtime-freeze.json').write_text(json.dumps(dict(repo_files=pins)))
            captured=[]
            def remote(code,data=None,**kwargs):
                with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
                    names=tar.getnames();captured.append(names)
                    self.assertEqual(set(names),{'repo/input.txt','repo/'+ops.REL+'/run.sbatch',
                        'runtime-freeze.json','repo/'+ops.REL+'/runtime-freeze.json','run.sbatch'})
                    self.assertFalse(any('authorization' in name for name in names))
                    self.assertEqual(tar.extractfile('repo/input.txt').read(),b'exact input\n')
                return b'{"synthetic":true}'
            with patch.object(ops,'ROOT',root),patch.object(ops,'REPO',repo),patch.object(ops,'validate_package'), \
                 patch.object(ops,'remote',remote),contextlib.redirect_stdout(io.StringIO()):
                ops.stage()
                with self.assertRaisesRegex(ValueError,'Existing staging'): ops.stage()
            self.assertEqual(len(captured),1)

    def test_unsafe_or_symlinked_package_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            repo=Path(temp);(repo/'actual').write_text('fake');(repo/'link').symlink_to(repo/'actual')
            for name in ('../outside','/absolute','a/../actual','link','missing'):
                with self.subTest(name=name),self.assertRaises(ValueError):builder.safe_file(repo,name)


if __name__ == '__main__':
    unittest.main()

