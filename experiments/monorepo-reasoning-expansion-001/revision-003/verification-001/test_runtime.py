"""Exercise the isolated package and staging with a fake process, no Dafny/API."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
from language.dafny.repository import verify_repository
import preflight


class RuntimeTests(unittest.TestCase):
    def test_imports_resolve_inside_staged_snapshot(self):
        import execute
        import language.dafny.prompt
        self.assertEqual(Path(execute.__file__).resolve(),ROOT/'code/execute.py')
        self.assertEqual(Path(language.dafny.prompt.__file__).resolve(),ROOT/'code/language/dafny/prompt.py')

    def test_staging_uses_exact_bytes_and_single_fake_process(self):
        source=ROOT/'fixtures/nested_clamp-shallow-shared/reference'
        files={p.name:p.read_bytes() for p in source.glob('*.dfy')}
        calls=[]
        def fake_run(command,**kwargs):
            calls.append(command)
            actual={p.name:p.read_bytes() for p in Path(kwargs['cwd']).glob('*.dfy')}
            self.assertEqual(actual,files)
            self.assertIn('--verify-included-files',command)
            return SimpleNamespace(returncode=0,stdout='Fake process: no Dafny executed',stderr='')
        with patch('subprocess.run',side_effect=fake_run):
            record=verify_repository(files,'All.dfy',timeout=60).evidence
        self.assertEqual(len(calls),1)
        self.assertEqual(record['source_sha256'],{n:preflight.sha(b) for n,b in files.items()})
        self.assertEqual(record['exit_code'],0)


if __name__=='__main__':unittest.main(verbosity=2)
