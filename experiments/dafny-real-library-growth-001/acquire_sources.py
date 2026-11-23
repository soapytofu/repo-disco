"""Fetch public pinned source bytes once, with Git object integrity checks.

No repository script, verifier, credential or model is executed. Downloads have
individual bounds and no automatic retry. Existing matching files are audited.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request

ROOT = Path(__file__).resolve().parent


def acquire(manifest, destination, receipt):
    spec = json.loads(manifest.read_bytes())
    assert not receipt.exists()
    commit = spec['commit']
    assert len(commit) == 40 and all(c in '0123456789abcdef' for c in commit)
    destination.mkdir(parents=True, exist_ok=True)
    def one(row):
        name = row['path']; path = PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts
        target = destination / name
        url = f'https://raw.githubusercontent.com/{spec["repository"]}/{commit}/{name}'
        if target.exists():
            raw = target.read_bytes(); mode = 'existing_exact_source'
        else:
            with urllib.request.urlopen(url, timeout=30) as response:
                raw = response.read(row['bytes'] + 1)
            mode = 'downloaded'
        assert len(raw) == row['bytes'], name
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert blob == row['git_blob_sha'], name
        if mode == 'downloaded':
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream: stream.write(raw)
        return dict(path=name, url=url, bytes=len(raw), git_blob_sha=blob,
                    sha256=hashlib.sha256(raw).hexdigest(), mode=mode)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(one, spec['files']))
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open('x') as stream:
        json.dump(dict(repository=spec['repository'], commit=commit,
                       input_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
                       files=results, model_calls=0, native_calls=0), stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(files=len(results), bytes=sum(x['bytes'] for x in results),
                          receipt=str(receipt), integrity='ALL_GIT_BLOBS_MATCH')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    acquire(args.manifest, args.destination, args.receipt)
