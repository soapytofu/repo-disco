import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('audit_archive', Path(__file__).resolve().parents[1] / 'scripts/audit_archive.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ArchiveAuditTests(unittest.TestCase):
    def test_detects_tampering_missing_and_unlisted_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'good.txt').write_text('original')
            digest = hashlib.sha256(b'original').hexdigest()
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({'good.txt': digest}))
            self.assertTrue(module.audit(manifest)['integrity_passed'])
            (root / 'good.txt').write_text('changed')
            self.assertEqual(module.audit(manifest)['issues'][0]['error'], 'hash_mismatch')
            (root / 'good.txt').unlink()
            (root / 'extra.txt').write_text('scratch')
            result = module.audit(manifest)
            self.assertEqual(result['issues'][0]['error'], 'missing_file')
            self.assertEqual(result['unlisted_files'], ['extra.txt'])

    def test_rejects_traversal_bad_hash_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'target').write_text('x')
            (root / 'link').symlink_to(root / 'target')
            digest = hashlib.sha256(b'x').hexdigest()
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({'../outside': digest, '/absolute': digest,
                                           'link': digest, 'target': 'not-a-hash'}))
            errors = [i['error'] for i in module.audit(manifest)['issues']]
            self.assertEqual(errors.count('invalid_relative_path'), 2)
            self.assertIn('symlink_not_allowed', errors)
            self.assertIn('invalid_sha256', errors)

    def test_empty_or_wrong_shape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'manifest.json'
            for value in ({}, [], 'text'):
                manifest.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    module.audit(manifest)


if __name__ == '__main__':
    unittest.main()
