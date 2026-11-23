"""Deterministic offline construction of two independent AWS growth tasks."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
OLD = REPO / 'experiments/dafny-real-library-growth-001'
SLOTS = OLD / 'execution-001/retrieved-001/model-001/slots'
BEGIN = b'    // BEGIN REPLACEMENT\n'
END = b'    // END REPLACEMENT\n'
BASE_ORDER = ['StandardLibrary/src/UInt.dfy', 'libraries/src/BoundedInts.dfy',
              'libraries/src/Wrappers.dfy', 'StandardLibrary/src/RepoDiscoU16Frame.dfy',
              'StandardLibrary/src/RepoDiscoFramePair.dfy']
SEED_HASHES = {
    'StandardLibrary/src/RepoDiscoFramePair.dfy': '71cc49e947f10f0717c8cdb2969ef6e27b0e88a948176ab082e6cc97a4ffddda',
    'StandardLibrary/src/RepoDiscoU16Frame.dfy': '7a2efb8f00acb9ab3dc7239ff6f363c50a0a275daef243a937003810532b2939',
    'StandardLibrary/src/UInt.dfy': '78a8087ad152365e2947402286d62554860dd33b7ab2a1117e925e618232f304',
    'libraries/src/BoundedInts.dfy': 'be64dfad94ddd7f6c4150322b4ad96f08ba1453eec0d167a2721a85ccbd2d810',
    'libraries/src/Wrappers.dfy': '62c82fa69e1d6b0fde3622c07a891704dda51662668e77183f17c3e2916380e2',
}
TASKS = {
    'aws-batch': {'stem': 'counted', 'path': 'StandardLibrary/src/RepoDiscoFrameBatch.dfy',
        'target': 'RepoDiscoFrameBatch.ReadCountedFrames',
        'fixed_declarations': ['RepoDiscoFrameBatch.HasCountedFrames',
                               'RepoDiscoFrameBatch.BoundedPayloads', 'RepoDiscoFrameBatch.EncodeFrames'],
        'helper_path': BASE_ORDER[3], 'helper_target': 'RepoDiscoU16Frame.ReadU16Frame',
        'bad': ['always-failure', 'missing-tail', 'reversed-payloads', 'wrong-suffix'],
        'helper_control': 'unproved-frame'},
    'aws-tagged': {'stem': 'tagged', 'path': 'StandardLibrary/src/RepoDiscoTaggedFramePair.dfy',
        'target': 'RepoDiscoTaggedFramePair.ReadTaggedBoundedPair',
        'fixed_declarations': ['RepoDiscoTaggedFramePair.IsTaggedBounded'],
        'helper_path': BASE_ORDER[4], 'helper_target': 'RepoDiscoFramePair.ReadFramePair',
        'bad': ['always-failure', 'skips-tag', 'skips-budget', 'keeps-tag'],
        'helper_control': 'unproved-pair'},
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def encode(obj):
    return (json.dumps(obj, sort_keys=True, indent=2) + '\n').encode()


def read(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return path.read_bytes()


def parts(raw):
    assert raw.count(BEGIN) == raw.count(END) == 1
    before, rest = raw.split(BEGIN)
    body, after = rest.split(END)
    return before + BEGIN, body, END + after


def render(template, body):
    before, empty, after = parts(template)
    assert not empty.strip() and body.endswith(b'\n')
    assert BEGIN not in body and END not in body
    return before + body + after


def replace_once(raw, old, new):
    assert raw.count(old) == 1, old
    return raw.replace(old, new, 1)


def closure(roots, sources):
    pending, found = list(roots), set()
    while pending:
        name = pending.pop()
        if name in found:
            continue
        assert name in sources, name
        found.add(name)
        for include in re.findall(r'^\s*include\s+"([^"\r\n]+)"', sources[name].decode(), re.M):
            pieces = list(PurePosixPath(name).parent.parts)
            for piece in PurePosixPath(include).parts:
                if piece == '..':
                    assert pieces
                    pieces.pop()
                elif piece != '.':
                    pieces.append(piece)
            pending.append('/'.join(pieces))
    return found


def material():
    files, origins = {}, {}

    def copy(source, destination):
        raw = read(source)
        files[destination] = raw
        origins[destination] = {'origin': source.relative_to(REPO).as_posix(),
                                'sha256': sha(raw), 'bytes': len(raw), 'byte_identical': True}
        return raw

    seed = {name: copy(SLOTS / 'slot-04/candidate' / name, 'seed/workspace/' + name)
            for name in BASE_ORDER}
    assert {name: sha(raw) for name, raw in seed.items()} == SEED_HASHES
    assert closure(BASE_ORDER, seed) == set(BASE_ORDER)
    source_revision = sha(canonical(SEED_HASHES))
    assert source_revision == 'c7d77ff6a33a4756ef7a2baf5247f74aae3787638c87a4e1c9f3c0bd29b9f874'
    for slot in ('slot-02', 'slot-04'):
        for name in ('outcome.json', 'native-review.json', 'edit-review.json',
                     'response-binding.json', 'native-profile.json', 'native/record.json', 'native/event.json'):
            copy(SLOTS / slot / name, 'seed/evidence/' + slot + '/' + name)
        for path in sorted((SLOTS / slot / 'native/raw').rglob('*')):
            if path.is_file():
                copy(path, 'seed/evidence/' + slot + '/' + path.relative_to(SLOTS / slot).as_posix())
    receipt = json.loads(copy(SLOTS / 'slot-02/parent-receipt.json',
                             'seed/evidence/slot-02/parent-receipt.json'))
    accepted = json.loads(files['seed/evidence/slot-04/outcome.json'])
    review = json.loads(files['seed/evidence/slot-04/native-review.json'])
    record = json.loads(files['seed/evidence/slot-04/native/record.json'])
    edit = json.loads(files['seed/evidence/slot-04/edit-review.json'])
    assert accepted['accepted'] and accepted['outcome'] == 'ACCEPTED' and not accepted['synthetic']
    assert accepted['chain_id'] == 'aws-lineage-01' and accepted['parent_slot_id'] == 'slot-02'
    assert accepted['native_record_sha256'] == sha(canonical(record)) == review['record_sha256']
    assert review['qualified_success'] and review['proof_coverage_complete'] and review['strict_zero_warning_success']
    assert review['passed_units'] == 77 and review['failed_units'] == 0 and review['warnings'] == 0
    assert review['origin'] == record['origin'] == 'model_candidate'
    assert review['source_revision_sha256'] == source_revision == edit['source_revision_sha256']
    assert record['source_before_sha256'] == record['source_after_sha256'] == SEED_HASHES
    assert record['toolchain'] == record['toolchain_after'] and record['attempts'] == 1
    assert not record['timeout'] and record['exit_code'] == 0
    for name, digest in record['raw_sha256'].items():
        assert sha(files['seed/evidence/slot-04/native/raw/' + name]) == digest
    assert receipt['accepted'] and not receipt['synthetic'] and receipt['origin'] == 'model_candidate'
    assert receipt['chain_id'] == accepted['chain_id']
    assert edit['parent']['receipt_sha256'] == sha(canonical(receipt))
    for name in BASE_ORDER[:-1]:
        assert read(SLOTS / 'slot-02/candidate' / name) == seed[name]
    for name in BASE_ORDER:
        assert read(SLOTS / 'slot-04/native/workspace' / name) == seed[name]
    original_case = json.loads(copy(OLD / 'aws/cases-001/aws-baseline-001/case.json',
                                   'seed/evidence/upstream-source-case.json'))
    upstream = {item['path']: item for item in original_case['source_files']}
    for name in BASE_ORDER[:3]:
        raw = seed[name]
        assert sha(raw) == upstream[name]['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == upstream[name]['git_blob_sha']
    config = json.loads(copy(OLD / 'qualification-005/configs/aws.json', 'seed/evidence/native-config.json'))
    assert config['source_pin'] == 'dab800a2a610253659d113ee6e4bf8a70b86d13a'
    command_prefix = [config['dafny'], 'verify'] + config['options']
    assert record['argv'] == command_prefix + BASE_ORDER
    for name in ('guard.py', 'review_native.py'):
        copy(OLD / 'common' / name, 'compatibility/' + name)

    bodies = {stem + '-reference': read(ROOT / 'bodies' / (stem + '-reference.txt'))
              for stem in ('counted', 'tagged')}
    counted = bodies['counted-reference']
    bodies['counted-always-failure'] = b'    Failure("No decoded frames")\n'
    bodies['counted-missing-tail'] = b'''    if count == 0 then Success(Batch([], input))
    else
      var first := F.ReadU16Frame(input);
      if first.Failure? then Failure(first.error)
      else Success(Batch([first.value.payload], first.value.rest))
'''
    bodies['counted-reversed-payloads'] = replace_once(counted,
        b'var payloads := [frame.payload] + tail.payloads;',
        b'var payloads := tail.payloads + [frame.payload];')
    bodies['counted-wrong-suffix'] = replace_once(counted,
        b'Success(Batch(payloads, tail.rest))', b'Success(Batch(payloads, []))')
    tagged = bodies['tagged-reference']
    bodies['tagged-always-failure'] = b'    Failure("No tagged pair")\n'
    bodies['tagged-skips-tag'] = replace_once(tagged,
        b'      else if pair.left[0] != tag then\n        Failure("Unexpected tag")\n', b'')
    bodies['tagged-skips-budget'] = replace_once(tagged,
        b'if |payload| + |pair.right| > budget then', b'if false then')
    bodies['tagged-keeps-tag'] = replace_once(tagged,
        b'var payload := pair.left[1..];', b'var payload := pair.left;')
    for name, body in bodies.items():
        files['bodies/' + name + '.txt'] = body

    cases, profiles, specifications = [], {}, []
    for task_id, task in TASKS.items():
        template = read(ROOT / 'templates' / PurePosixPath(task['path']).name)
        files['templates/' + PurePosixPath(task['path']).name] = template
        before, body, after = parts(template)
        assert body == b''
        profile = {'schema': 'dafny-library-edit-profile-v1', 'project': task_id, 'stage': 1,
            'stage_id': task_id, 'base_source_sha256': SEED_HASHES,
            'addition': {'path': task['path'], 'kind': 'function', 'template_utf8': template.decode(),
                         'begin_marker': BEGIN.decode(), 'end_marker': END.decode()},
            'registrations': {}, 'parent_requirement': None,
            'verification_inputs': BASE_ORDER + [task['path']], 'forbidden_identifiers': []}
        profiles[task_id] = profile
        files['profiles/' + task_id + '.json'] = encode(profile)
        stem = task['stem']
        specifications += [(stem + '-reference', task_id, 'reference', stem + '-reference')]
        specifications += [(stem + '-' + suffix, task_id, 'proof', stem + '-' + suffix)
                           for suffix in task['bad']]
        specifications += [(stem + '-' + task['helper_control'], task_id, 'unproved-helper', stem + '-reference'),
                           (stem + '-omitted', task_id, 'omitted', stem + '-always-failure')]
    references = {'counted-reference', 'tagged-reference'}
    specifications.sort(key=lambda x: (x[0] not in references, list(TASKS).index(x[1]), x[0]))
    for ident, task_id, kind, body_id in specifications:
        task = TASKS[task_id]
        template = files['templates/' + PurePosixPath(task['path']).name]
        sources = dict(seed)
        sources[task['path']] = render(template, bodies[body_id])
        mutated = []
        if kind == 'unproved-helper':
            before, _, after = parts(sources[task['helper_path']])
            sources[task['helper_path']] = before + b'    Failure("Deliberately unproved immutable helper")\n' + after
            mutated = [task['helper_path']]
        scope = BASE_ORDER + [task['path']]
        omitted = [task['path']] if kind == 'omitted' else []
        roots = [name for name in scope if name not in omitted]
        assert closure(roots, sources) == set(sources) - set(omitted)
        category = 'PROOF_PASS' if kind == 'reference' else 'COVERAGE_OMISSION' if kind == 'omitted' else 'PROOF_FAILURE'
        failed = [] if kind in ('reference', 'omitted') else [task['helper_target'] if kind == 'unproved-helper' else task['target']]
        inspected = ([task['target']] + [t for t in ('RepoDiscoU16Frame.ReadU16Frame', 'RepoDiscoFramePair.ReadFramePair')
                     if t != task['helper_target']]) if kind == 'unproved-helper' else []
        workspace = 'cases/' + ident + '/workspace'
        for name, raw in sources.items():
            files[workspace + '/' + name] = raw
        cases.append({'id': ident, 'project': task_id, 'stage': 1, 'stage_id': task_id,
            'workspace_dir': workspace, 'source_sha256': {n: sha(b) for n, b in sorted(sources.items())},
            'command_files': roots, 'declared_scope_files': scope, 'argv': command_prefix + roots,
            'expected_category': category,
            'expected_native_category': 'PROOF_PASS' if kind == 'omitted' else category,
            'expected_failed_targets': failed, 'expected_passed_targets': [] if kind == 'unproved-helper'
                else ['RepoDiscoU16Frame.ReadU16Frame', 'RepoDiscoFramePair.ReadFramePair']
                    + ([task['target']] if kind == 'reference' else []),
            'required_targets': ['RepoDiscoU16Frame.ReadU16Frame', 'RepoDiscoFramePair.ReadFramePair', task['target']],
            'new_fixed_declarations': task['fixed_declarations'],
            'omitted_targets': [task['target']] if omitted else [], 'omit_from_command': omitted,
            'omitted_source_all_units': omitted, 'inspect_targets': inspected,
            'child_outcome_predetermined': False if kind == 'unproved-helper' else None,
            'deliberately_mutated_seed_files': mutated,
            'edit_guard_expected': 'REJECT_IMMUTABLE_BASE' if mutated else 'ADMIT_BODY',
            'body_id': body_id, 'gated_until_positive_review': kind != 'reference',
            'native_status': 'UNKNOWN', 'actual_native_unit_labels': None,
            'analyst_authored': True, 'model_acceptance': False, 'native_dispatch_authorized': False,
            'classification_requires_named_units_and_exact_inventory': True})
    files['cases.json'] = encode(cases)
    files['seed/source-manifest.json'] = encode({'schema': 'repodisco-accepted-aws-seed-v1',
        'selection': 'Earliest complete accepted AWS lineage in the frozen prior execution, selected by slot order.',
        'source_pin': config['source_pin'], 'chain_id': 'aws-lineage-01', 'parent_slot': 'slot-02', 'accepted_slot': 'slot-04',
        'source_sha256': SEED_HASHES, 'source_revision_sha256': source_revision,
        'accepted_request_id': accepted['request_id'], 'accepted_response_sha256': accepted['response_sha256'],
        'accepted_native_run_id': accepted['native_run_id'], 'accepted_native_record_sha256': accepted['native_record_sha256'],
        'inherited_native_units': [unit['name'] for unit in review['units']],
        'inherited_passed_units': 77, 'inherited_warnings': 0,
        'new_native_observations': 0, 'copy_origins': origins,
        'scope_caveat': 'The five-file qualified UInt component plus two accepted additions, not the full AWS/MPL repository.'})
    files['native-policy.json'] = encode({'schema': 'repodisco-growth-native-policy-v1',
        'command_prefix': command_prefix, 'expected_version': config['expected_version'],
        'source_pin': config['source_pin'], 'toolchain_root': config['toolchain_root'],
        'solver': config['solver'], 'expected_tool_fingerprint': config['expected_tool_fingerprint'],
        'wall_seconds': 900, 'verification_time_limit_seconds': 300, 'resource_limit': 500000000,
        'cpus': 1, 'memory_gib': 4, 'new_native_calls': 0, 'no_automatic_retry': True})
    files['manifest.json'] = encode({'schema': 'repodisco-aws-independent-growth-manifest-v1',
        'files': {name: sha(raw) for name, raw in sorted(files.items())}, 'native_status': 'UNKNOWN',
        'reference_cases': ['counted-reference', 'tagged-reference'],
        'gated_controls': [c['id'] for c in cases if c['gated_until_positive_review']],
        'model_calls': 0, 'native_calls': 0})
    return files


def build():
    files = material()
    for name, raw in files.items():
        path = ROOT / name
        if path.exists():
            assert read(path) == raw, name
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(raw)
    return {'cases': 14, 'references': 2, 'gated_controls': 12,
            'source_files': sum(name.startswith('cases/') and name.endswith('.dfy') for name in files),
            'manifest_sha256': sha(files['manifest.json']), 'native_calls': 0, 'model_calls': 0}


if __name__ == '__main__':
    print(json.dumps(build(), indent=2, sort_keys=True))
