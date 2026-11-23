"""Pinned package and explicit fresh authorization checks; no remote actions."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
REL = 'experiments/real-repository-growth-001/execution-004'
PILOT = 'experiments/real-repository-growth-001/pilot'
PROTOCOL = 'experiments/real-repository-growth-001/protocol-003'
PILOT_SHA = '9f2e4c9602b4ce98740f2a3fa1dcf7bbef07d2b0693db8d92d9cc55546820f0c'
PROTOCOL_SHA = '9cf8cc81bd55f83a591c04c2877ab9a0ece3927fcddc31f6f3d42d7953d42057'
LIMIT = 8
EXECUTION_ID = 'real-repository-growth-001-execution-004'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode()


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()


def unique(pairs):
    value = {}
    for k, v in pairs:
        require(k not in value, 'Duplicate JSON field')
        value[k] = v
    return value


def read(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def pinned_path(repo, name):
    require(isinstance(name, str) and name and not name.startswith('/') and
            all(p not in ('', '.', '..') for p in name.split('/')) and '\\' not in name,
            'Invalid repo-relative pin')
    repo = Path(repo).resolve()
    path = repo / name
    require(not any(p.is_symlink() for p in (path, *path.parents) if p != repo.parent) and
            path.resolve().is_relative_to(repo) and path.is_file(), 'Missing or symlinked pinned input')
    return path


def load_context(repo):
    repo = Path(repo).resolve()
    path = repo / PILOT / 'render.py'
    name = 'repodisco_growth_prompt_renderer'
    if name in sys.modules:
        renderer = sys.modules[name]
        require(Path(renderer.__file__).resolve() == path, 'Mixed prompt-runtime imports')
    else:
        spec = importlib.util.spec_from_file_location(name, path)
        renderer = importlib.util.module_from_spec(spec)
        sys.modules[name] = renderer
        spec.loader.exec_module(renderer)
    return renderer, renderer.protocol_api(repo / PILOT)


def validate_package(repo):
    repo = Path(repo).resolve()
    freeze_path = repo / REL / 'runtime-freeze.json'
    freeze = read(freeze_path)
    require(freeze.get('schema') == 'repodisco-growth-execution-runtime-v1', 'Unknown runtime freeze')
    require(freeze.get('pilot_freeze_sha256') == PILOT_SHA and
            freeze.get('protocol_freeze_sha256') == PROTOCOL_SHA, 'Wrong proposal or protocol')
    files = freeze.get('repo_files')
    require(isinstance(files, dict) and len(files) > 3572, 'Complete runtime input closure required')
    for name, digest in files.items():
        require(sha(pinned_path(repo, name).read_bytes()) == digest, 'Runtime input drift: ' + name)
    require(sha((repo / PILOT / 'frozen-001/manifest.json').read_bytes()) == PILOT_SHA,
            'Frozen proposal drift')
    require(sha((repo / PROTOCOL / 'runtime-freeze.json').read_bytes()) == PROTOCOL_SHA,
            'Frozen protocol drift')
    for name, digest in read(repo / PILOT / 'frozen-001/manifest.json').items():
        require(sha(pinned_path(repo / PILOT / 'frozen-001', name).read_bytes()) == digest,
                'Frozen payload drift')
    renderer, api = load_context(repo)
    order = read(repo / PILOT / 'frozen-001/order.json')
    require(order == renderer.order() and len(order) == LIMIT, 'Fixed order differs')
    return dict(runtime_sha256=sha(freeze_path.read_bytes()), proposal_sha256=PILOT_SHA,
                protocol_sha256=PROTOCOL_SHA, policy_sha256=api.b.policy_digest(),
                order=order, settings=read(repo / PILOT / 'frozen-001/settings.json'))


def validate_authorization(path, repo, now=None):
    now = time.time() if now is None else now
    package = validate_package(repo)
    auth = read(path)
    expected = dict(schema='repodisco-growth-execution-authorization-v1', execution_authorized=True,
                    approved_by='Sophie Zeng', max_new_requests=LIMIT, no_retries=True,
                    no_reassignment=True, pilot_freeze_sha256=PILOT_SHA,
                    runtime_freeze_sha256=package['runtime_sha256'], execution_id=EXECUTION_ID,
                    output_relative_path='model-001')
    require(all(type(auth.get(k)) is type(v) and auth[k] == v for k, v in expected.items()),
            'Explicit authorization does not match this fresh scope')
    require(isinstance(auth.get('human_basis'), str) and auth['human_basis'].strip(),
            'Human approval basis required')
    root = auth.get('authorized_runtime_root')
    require(isinstance(root, str) and root.startswith('/') and '\x00' not in root and
            str(Path(root)) == root and all(x not in ('.', '..') for x in root.split('/')),
            'One exact absolute runtime directory required')
    start, end = auth.get('issued_at_epoch'), auth.get('expires_at_epoch')
    require(all(type(x) in (float, int) and math.isfinite(x) for x in (start, end, now)),
            'Finite authorization times required')
    require(start <= now < end and 0 < end - start <= 86400, 'Authorization absent, future or expired')
    return auth


def archive_files(out):
    """Full evidence inventory, excluding only exact generated Cargo target trees."""
    out = Path(out)
    excluded = {f'slot-{n:02d}/native/fresh-target' for n in range(1, LIMIT + 1)}
    found = []
    for folder, dirs, files in __import__('os').walk(out, followlinks=False):
        folder = Path(folder)
        dirs[:] = [d for d in dirs if (folder / d).relative_to(out).as_posix() not in excluded]
        require(not any((folder / d).is_symlink() for d in dirs), 'Symlinked evidence directory')
        for name in files:
            path = folder / name
            require(not path.is_symlink() and path.is_file(), 'Nonregular evidence file')
            if path.name != 'archive-manifest.json' or path.parent != out:
                found.append(path)
    return sorted(found)


def check_response(response, seen):
    require(isinstance(response, dict), 'Missing model response')
    rid = response.get('request_id')
    require(isinstance(rid, str) and 0 < len(rid) <= 256 and rid not in seen, 'Missing or duplicate request ID')
    require(type(response.get('retry_attempts')) is int and response['retry_attempts'] == 0,
            'Nonzero or unknown SDK retry count')
    usage = response.get('usage')
    require(isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0
            for k in ('inputTokens', 'outputTokens', 'totalTokens')), 'Missing token accounting')
    require(usage['outputTokens'] <= 4096 and usage['totalTokens'] == usage['inputTokens'] + usage['outputTokens'],
            'Contradictory token accounting')
    raw = response.get('raw_response')
    require(isinstance(raw, dict) and raw.get('usage') == usage and raw.get('stopReason') == response.get('stop_reason'),
            'Saved raw response metadata differs')
    metadata = raw.get('ResponseMetadata', {})
    require(metadata.get('RequestId') == rid and metadata.get('RetryAttempts') == 0 and
            metadata.get('HTTPStatusCode') == 200, 'Unsuccessful or inconsistent provider response')
    content = raw.get('output', {}).get('message', {}).get('content')
    require(isinstance(content, list) and content == response.get('content') and content and
            all(isinstance(x, dict) and set(x) == {'text'} and isinstance(x['text'], str) for x in content),
            'Unexpected provider output blocks')
    require(response.get('text') == ''.join(x['text'] for x in content), 'Saved response text differs')
    require(response.get('stop_reason') in ('end_turn', 'max_tokens'), 'Unexpected model stop reason')
    seen.add(rid)
