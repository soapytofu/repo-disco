"""Self-contained preparation and isolated-runtime tests; no Dafny/model calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import verify


def load(path): return json.loads(path.read_text())
def digest(text): return hashlib.sha256(text.encode()).hexdigest()


class WarningAliasDesignTests(unittest.TestCase):
    def test_exact_alias_substitution_only(self):
        original = load(ROOT / 'original-body.json')['HelperA.dfy']
        changed = load(ROOT / 'analyst-body.json')['HelperA.dfy']
        mutation = load(ROOT / 'mutation.json')
        self.assertEqual(digest(original), mutation['original_body_sha256'])
        self.assertEqual(digest(changed), mutation['changed_body_sha256'])
        prefix, tail = original.split('    forall q |', 1)
        tail = '    forall q |' + tail
        for edit in mutation['replacements']:
            self.assertEqual(tail.count(edit['old']), edit['occurrences'])
            tail = tail.replace(edit['old'], edit['new'])
        self.assertEqual(prefix + tail, changed)
        self.assertEqual(mutation['added_lemma_calls'], 0)
        self.assertTrue(mutation['analyst_authored'])

    def test_guard_replay_and_all_protected_bytes(self):
        sources = verify.guarded_sources()
        task = load(ROOT / 'task.json')
        self.assertEqual(task['editable_files'], ['HelperA.dfy'])
        self.assertEqual(len(sources), 9)
        for name in set(sources) - set(task['editable_files']):
            self.assertEqual(sources[name], (ROOT / 'seed' / name).read_bytes())
        from body_guard import split_seed
        prefix, suffix = split_seed((ROOT / 'seed/HelperA.dfy').read_text())
        body = load(ROOT / 'analyst-body.json')['HelperA.dfy']
        self.assertEqual(sources['HelperA.dfy'].decode(), prefix + body + suffix)

    def test_isolated_package_import_and_fake_process_stages_exact_bytes(self):
        # A child process sees only this pinned runtime, not the repository checkout.
        script = '''import sys, json, subprocess
from pathlib import Path
from unittest.mock import patch
root=Path(sys.argv[1]);sys.path.insert(0,str(root));import verify
sources=verify.guarded_sources()
from language.dafny.repository import verify_repository
def fake(command, **kwargs):
 assert command == ['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy']
 actual={p.name:p.read_bytes() for p in Path(kwargs['cwd']).glob('*.dfy')}
 assert actual == sources
 return subprocess.CompletedProcess(command,0,'fake process only','')
with patch('subprocess.run',side_effect=fake) as run:
 result=verify_repository(sources,'All.dfy',60)
 assert run.call_count == 1 and result.evidence['exit_code'] == 0
print('isolated import and fake-process staging passed; zero real verification/model calls')
'''
        run = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(ROOT)],
                             capture_output=True, text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_main_rejects_missing_compute_allocation(self):
        with patch.dict('os.environ', {}, clear=True), patch.object(sys, 'argv', ['verify.py', 'verification-001']):
            with self.assertRaisesRegex(SystemExit, 'Compute allocation required'):
                verify.main()


if __name__ == '__main__': unittest.main(verbosity=2)
