"""Fake transport boundary checks; never opens SSH or submits Slurm jobs."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import common as c
import ops


def accounting(*rows):
    header='|'.join(ops.ACCOUNTING_FIELDS)
    return header+'\n'+''.join(job+'|'+state+'|00:00:01|1|0:0|1|00:00:01|1|1K|fake-node\n'
                              for job,state in rows)


class TransportBoundaryTests(unittest.TestCase):
    def test_remote_transport_has_socket_and_hard_timeout(self):
        observed = []

        def fake_run(argv, **kwargs):
            observed.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, stdout=b'fake-result', stderr=b'')

        with patch.object(ops.subprocess, 'run', fake_run), patch.object(c, 'sha', return_value='a' * 64):
            self.assertEqual(ops.remote('print("offline fixture")', seconds=17), b'fake-result')
        self.assertEqual(len(observed), 1)
        argv, kwargs = observed[0]
        self.assertEqual(argv[0], 'ssh')
        self.assertIn(str(Path.home() / '.ssh/repodisco-codex-21.sock'), argv)
        self.assertIn('BatchMode=yes', argv)
        self.assertIn('ProxyCommand=false', argv)
        self.assertEqual(kwargs['timeout'], 17)
        self.assertIn('real-repository-growth-001/qualification-002', argv[-1])
        self.assertNotIn('prepare_key', argv[-1])

    def test_unknown_or_control_submission_rejected_before_transport(self):
        with patch.object(ops, 'remote', side_effect=AssertionError('transport reached')):
            for name in ('vest', 'pair-alternative', 'batch-empty', 'all-controls'):
                with self.assertRaisesRegex(ValueError, 'Unknown verifier stage'):
                    ops.submit(name)

    def test_vest_and_controls_have_no_status_or_fetch_route(self):
        self.assertEqual(set(ops.STAGES), {'dafny-vmc'})
        with patch.object(ops, 'remote', side_effect=AssertionError('transport reached')):
            for operation in (ops.status, ops.fetch):
                for name in ('vest', 'pair-alternative', 'batch-reference'):
                    with self.assertRaisesRegex(ValueError, 'Unknown verifier stage'):
                        operation(name)


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

    def _fake_fetch(self,raw):
        """Execute the actual remote fetch program against temporary fake state."""
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        local=Path(temp.name)/'local';remote=Path(temp.name)/'remote'
        for root in (local,remote):
            root.mkdir();(root/'submissions').mkdir()
            (root/'runtime-freeze.json').write_text(json.dumps({'files':{}}))
        (local/'submissions/dafny-vmc.json').write_text(json.dumps({'job_id':'12345'}))
        (remote/'submissions/dafny-vmc.lock').write_text('fake submission lock\n')
        (remote/'verification-dafny-vmc-001').mkdir()
        (remote/'verification-dafny-vmc-001/fake-evidence.txt').write_text('preserved fake evidence\n')
        captured=[]

        def fake_query(argv,**kwargs):
            self.assertEqual(argv[:3],['sacct','-j','12345'])
            self.assertIn('State%80',argv[3])
            self.assertTrue(kwargs['universal_newlines'])
            return raw

        def fake_remote(code,data=None,seconds=45):
            self.assertEqual(seconds,60)
            output=io.BytesIO()
            code=code.replace('EXPECTED_RUNTIME',repr(c.sha(local/'runtime-freeze.json')))
            with patch.object(subprocess,'check_output',fake_query), \
                 patch.object(sys,'stdout',SimpleNamespace(buffer=output)), \
                 patch.object(sys,'path',list(sys.path)):
                exec(compile(code,'<fake-remote-fetch>','exec'),{'root':remote})
            captured.append(output.getvalue())
            return output.getvalue()

        def run():
            with patch.object(c,'ROOT',local),patch.object(ops,'remote',fake_remote), \
                 contextlib.redirect_stdout(io.StringIO()):
                ops.fetch('dafny-vmc')
        return run,local,remote,captured

    def test_fetch_does_not_write_accounting_or_archive_for_live_step(self):
        run,local,remote,captured=self._fake_fetch(accounting(('12345','COMPLETED'),('12345.batch','SUSPENDED')))
        with self.assertRaisesRegex(ValueError,'Nonterminal or unknown'):
            run()
        self.assertEqual(captured,[])
        self.assertFalse((remote/'accounting-dafny-vmc.txt').exists())
        self.assertFalse((remote/'accounting-dafny-vmc-review.json').exists())
        self.assertFalse((local/'transfer-dafny-vmc.json').exists())
        self.assertFalse((local/'verification-dafny-vmc-001').exists())

    def test_fetch_archives_only_after_terminal_parent_and_steps_review(self):
        raw=accounting(('12345','COMPLETED'),('12345.batch','COMPLETED'),('12345.extern','COMPLETED'))
        run,local,remote,captured=self._fake_fetch(raw)
        run()
        self.assertEqual(len(captured),1)
        self.assertEqual((local/'accounting-dafny-vmc.txt').read_text(),raw)
        review=c.read(local/'accounting-dafny-vmc-review.json')
        self.assertEqual(review,ops.terminal_accounting(raw,'12345'))
        self.assertTrue((local/'verification-dafny-vmc-001/fake-evidence.txt').exists())
        self.assertTrue((local/'transfer-dafny-vmc.json').exists())


if __name__ == '__main__':
    unittest.main()
