"""Offline integration tests: fake process only; never launch Dafny here."""
import asyncio
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from language import VerificationOutcome, Program, Language
from language.dafny import DafnyBackend
from language.dafny.repository import verify_repository, snapshot_agenda_repository


class RepositoryTests(unittest.TestCase):
    def test_agenda_snapshot_nested_staging_and_evidence(self):
        source = {'entry.dfy': b'include "lib/Facts.dfy"\n', 'lib/Facts.dfy': b'module Facts {}\r\n'}
        class Agenda:
            async def get_object(self, path):
                return SimpleNamespace(content=source[path.removeprefix('objects/')])
        files = asyncio.run(snapshot_agenda_repository(Agenda(),
            {k: 'objects/' + k for k in source}, 'entry.dfy'))
        def run(command, cwd, **kwargs):
            self.assertIn('--verify-included-files', command)
            self.assertEqual(command[-1], 'entry.dfy')
            for name, content in source.items():
                self.assertEqual((Path(cwd)/name).read_bytes(), content)
            return SimpleNamespace(returncode=0, stdout='ok', stderr='')
        with patch('language.dafny.repository.subprocess.run', side_effect=run) as process:
            result = verify_repository(files, 'entry.dfy')
        self.assertEqual(process.call_count, 1)
        self.assertEqual(result.verification.outcome, VerificationOutcome.SUCCESS)
        self.assertEqual(result.evidence['source_sha256'], {k: sha256(v).hexdigest() for k,v in source.items()})

    def test_exit_categories_and_no_retry(self):
        for code, category in [(4,'proof_failure'),(2,'frontend_error'),(124,'timeout'),(137,'killed'),(1,'execution_error')]:
            with self.subTest(code=code), patch('language.dafny.repository.subprocess.run', return_value=SimpleNamespace(returncode=code, stdout='0 errors', stderr='detail')) as process:
                result = verify_repository({'a.dfy': b''}, 'a.dfy')
                self.assertEqual(result.evidence['category'], category)
                self.assertNotEqual(result.verification.outcome, VerificationOutcome.SUCCESS)
                self.assertEqual(process.call_count, 1)

    def test_invalid_paths_and_missing_entry_never_execute(self):
        for name in ['../a.dfy','/a.dfy','a//b.dfy','./a.dfy','-a.dfy','a\\b.dfy','a.txt']:
            with self.subTest(name=name), patch('language.dafny.repository.subprocess.run') as process:
                with self.assertRaises(ValueError): verify_repository({name:b''},name)
                process.assert_not_called()
        with self.assertRaises(ValueError): verify_repository({'a.dfy': b''}, 'missing.dfy')
        with self.assertRaises(ValueError): verify_repository({'a.dfy': b'', 'a.dfy/b.dfy': b''}, 'a.dfy')

    def test_missing_or_aliased_agenda_source(self):
        class Missing:
            async def get_object(self, path): return None
        for paths in [{'a.dfy':'absent'}, {'a.dfy':'same','b.dfy':'same'}]:
            with self.assertRaises(ValueError): asyncio.run(snapshot_agenda_repository(Missing(),paths,'a.dfy'))

    def test_launch_error_is_evidence_not_success(self):
        with patch('language.dafny.repository.subprocess.run', side_effect=FileNotFoundError('missing timeout')):
            result = verify_repository({'a.dfy':b''},'a.dfy')
        self.assertEqual(result.evidence['category'],'launch_error')
        self.assertIn('missing timeout',result.verification.stderr)

    def test_legacy_single_program_path_unchanged(self):
        with patch('language.dafny.execute', return_value={'status':0,'out':'0 errors','log':''}) as execute:
            result = DafnyBackend().verify(Program('method A() {}',Language.DAFNY))
        execute.assert_called_once_with('dafny verify','dfy','method A() {}',timeout=10)
        self.assertEqual(result.outcome,VerificationOutcome.SUCCESS)

if __name__ == '__main__': unittest.main()
