"""Materialize proposed Vest growth controls; never runs Rust, Verus or a model."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
UPSTREAM = REPO / 'experiments/real-repository-qualification-001/upstream/vest'
REGISTER = 'vest_dev/src/formats/mod.rs'
FRAME = 'vest_dev/src/formats/growth_frame.rs'
BATCH = 'vest_dev/src/formats/growth_batch.rs'
FRAME_TARGET = ['vest_dev', 'formats::growth_frame',
                'vest_dev::formats::growth_frame::frame_roundtrip', 'proof']
BATCH_TARGET = ['vest_dev', 'formats::growth_batch',
                'vest_dev::formats::growth_batch::batch_roundtrip', 'proof']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def changed_body(source, name, body):
    begin = f'    // BEGIN EDITABLE {name}\n'.encode()
    end = f'    // END EDITABLE {name}\n'.encode()
    assert source.count(begin) == source.count(end) == 1
    before, rest = source.split(begin)
    _, after = rest.split(end)
    return before + begin + body + end + after


def build():
    source_manifest = json.loads((REPO / 'experiments/real-repository-qualification-001/source-manifest.json').read_bytes())
    vest = next(x for x in source_manifest if x['id'] == 'vest')
    assert vest['commit'] == '333d61c1f0a2a5accc6962ee9a4ae05619fd0dcc'
    parent = (UPSTREAM / REGISTER).read_bytes()
    assert digest(parent) == vest['files'][REGISTER]
    frame = (ROOT / 'reference/growth_frame.rs').read_bytes()
    batch = (ROOT / 'reference/growth_batch.rs').read_bytes()
    assert not (UPSTREAM / FRAME).exists() and not (UPSTREAM / BATCH).exists()

    def body(name):
        return (ROOT / 'bodies' / (name + '.txt')).read_bytes()

    frames = {'reference': frame, 'empty': changed_body(frame, 'frame_roundtrip', b'')}
    batches = {'reference': batch, 'empty': changed_body(batch, 'batch_roundtrip', b'')}
    for name in ('alternative', 'wrong-header', 'wrong-consumption'):
        frames[name] = changed_body(frame, 'frame_roundtrip', body('frame-' + name))
    for name in ('alternative', 'wrong-count', 'missing-induction'):
        batches[name] = changed_body(batch, 'batch_roundtrip', body('batch-' + name))

    # Expected proof outcomes are prospective, not native verification claims.
    cases = []
    for name, source in frames.items():
        cases.append(dict(id='frame-' + name, stage=1, frame=name, batch=None,
                          register_frame=True, register_batch=False,
                          expected='proof_pass' if name in ('reference', 'alternative') else 'proof_failure',
                          required_new_targets=[FRAME_TARGET]))
    for name, source in batches.items():
        cases.append(dict(id='batch-' + name, stage=2, frame='reference', batch=name,
                          register_frame=True, register_batch=True,
                          expected='proof_pass' if name in ('reference', 'alternative') else 'proof_failure',
                          required_new_targets=[FRAME_TARGET, BATCH_TARGET]))
    cases.append(dict(id='batch-unproved-frame', stage=2, frame='wrong-header', batch='reference',
                      register_frame=True, register_batch=True, expected='proof_failure',
                      required_new_targets=[FRAME_TARGET, BATCH_TARGET],
                      intended_target_pattern={'frame_roundtrip':'Failed', 'batch_roundtrip':'Passed'},
                      purpose='Reject a passing batch that assumes an unproved frame contract.'))
    cases.append(dict(id='frame-omitted', stage=1, frame='reference', batch=None,
                      register_frame=False, register_batch=False, expected='coverage_rejection',
                      required_new_targets=[FRAME_TARGET],
                      purpose='A staged but unregistered new frame module must not count as verified.'))
    cases.append(dict(id='batch-omitted', stage=2, frame='reference', batch='reference',
                      register_frame=True, register_batch=False, expected='coverage_rejection',
                      required_new_targets=[FRAME_TARGET, BATCH_TARGET],
                      purpose='A staged but unregistered descendant must not count as verified growth.'))

    inventory = {}
    for case in cases:
        files = {FRAME: frames[case['frame']]}
        if case['batch'] is not None:
            files[BATCH] = batches[case['batch']]
        registration = parent
        if case['register_frame']:
            registration += b'\npub mod growth_frame;\n'
        if case['register_batch']:
            registration += b'pub mod growth_batch;\n'
        files[REGISTER] = registration
        case['overlay_sha256'] = {name: digest(data) for name, data in files.items()}
        for name, data in files.items():
            target = ROOT / 'cases' / case['id'] / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            inventory[str(target.relative_to(ROOT))] = digest(data)
    report = dict(status='OFFLINE_CONSTRUCTION_ONLY_NATIVE_VALIDATION_PENDING',
                  upstream_commit=vest['commit'], upstream_registration_sha256=vest['files'][REGISTER],
                  model_calls=0, native_verifier_calls=0, cases=cases, files=inventory,
                  expected_target_labels_require_native_inventory_confirmation=True,
                  complete_old_proof_inventory_must_be_retained=True)
    (ROOT / 'cases.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'cases':len(cases), 'source_files':len(inventory),
                      'native_verifier_calls':0, 'status':report['status']},indent=2))


if __name__ == '__main__':
    build()
