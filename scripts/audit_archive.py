"""Read-only verification of a relative-path -> SHA-256 experiment manifest.

Checks integrity, not scientific validity or authenticity. Does not regenerate hashes.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def audit(manifest):
    manifest = Path(manifest).resolve()
    root = manifest.parent
    entries = json.loads(manifest.read_text())
    if not isinstance(entries, dict) or not entries:
        raise ValueError('Expected a nonempty path-to-hash object')
    issues = []
    checked = 0
    for name, expected in sorted(entries.items()):
        path = PurePosixPath(name)
        if (not name or path.is_absolute() or '..' in path.parts
                or '\\' in name or str(path) != name or name == '.'):
            issues.append({'path': name, 'error': 'invalid_relative_path'})
            continue
        if not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected):
            issues.append({'path': name, 'error': 'invalid_sha256'})
            continue
        target = root / name
        if any(part.is_symlink() for part in [target, *target.parents] if part != root and root in part.parents):
            issues.append({'path': name, 'error': 'symlink_not_allowed'})
            continue
        if not target.is_file():
            issues.append({'path': name, 'error': 'missing_file'})
            continue
        checked += 1
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            issues.append({'path': name, 'error': 'hash_mismatch'})
    # Coverage is reported separately: scratch files do not invalidate listed hashes.
    unlisted = sorted(str(p.relative_to(root)) for p in root.rglob('*')
                      if p.is_file() and p != manifest and '__pycache__' not in p.parts
                      and str(p.relative_to(root)) not in entries)
    return {'listed_files': len(entries), 'checked_files': checked,
            'integrity_passed': not issues, 'issues': issues,
            'unlisted_files': unlisted, 'complete_coverage': not unlisted}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    try:
        result = audit(args.manifest)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['integrity_passed'] and (not args.require_complete or result['complete_coverage']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
