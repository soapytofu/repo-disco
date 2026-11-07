"""Extract the single schema-matching JSON span from each rejected saved response."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
PILOT = ROOT.parent
sys.path.insert(0, str(PILOT))
import run_pilot as pilot


def prepare():
    plan, tasks, trials = pilot.validate_bundle(PILOT)
    guard = pilot.guard_module(PILOT)
    decoder = json.JSONDecoder(object_pairs_hook=guard.unique)
    pilot.require(pilot.inventory(PILOT / 'model-001') == pilot.load(PILOT / 'model-001-sha256.json'),
                  'Original evidence changed')
    cases = []
    for trial in trials:
        original = PILOT / 'model-001' / trial['trial_id']
        if pilot.load(original / 'result.json')['outcome'] != 'OUTPUT_REJECTED':
            continue
        task = next(t for t in tasks if t['task_id'] == trial['task_id'])
        raw = pilot.load(original / 'response.json')['text']
        spans = []
        # Decode full objects at each opening brace. Require one exact filename/string
        # object, irrespective of its location in prose or a markdown fence.
        for start, character in enumerate(raw):
            if character != '{':
                continue
            try:
                obj, length = decoder.raw_decode(raw[start:])
            except (ValueError, RecursionError):
                continue
            if isinstance(obj, dict) and set(obj) == set(task['editable_files']) and all(isinstance(b, str) for b in obj.values()):
                spans.append((start, start+length))
        pilot.require(len(spans) == 1, 'Ambiguous or absent JSON object: ' + trial['trial_id'])
        start, end = spans[0]
        extracted = raw[start:end]
        seed = pilot.sources(PILOT, task)
        candidate, decision = guard.parse_response(extracted, {n: b.decode() for n, b in seed.items()}, task)
        folder = ROOT / 'fixtures' / trial['trial_id']
        folder.mkdir(parents=True, exist_ok=False)
        for name, text in candidate.items():
            (folder / name).write_text(text)
        raw_path = ROOT / 'extracted' / (trial['trial_id'] + '.json')
        raw_path.parent.mkdir(exist_ok=True)
        raw_path.write_text(extracted)
        case = dict(case_id=trial['trial_id'], original_trial=trial['trial_id'], task_id=task['task_id'],
                    path=str(folder.relative_to(ROOT)), candidate_sha256=decision['candidate_sha256'],
                    original_response_sha256=pilot.sha(original / 'response.json'),
                    original_result_sha256=pilot.sha(original / 'result.json'),
                    original_outcome='OUTPUT_REJECTED', body_edits=False,
                    extraction=dict(start_char=start, end_char=end, schema_matching_objects=1,
                                    json_sha256=hashlib.sha256(extracted.encode()).hexdigest()),
                    expected='Observed diagnostic only; original strict result is retained')
        cases.append(case)
    pilot.require(len(cases) == 7, 'Expected seven rejected responses')
    (ROOT / 'cases.json').write_text(json.dumps(cases, indent=2)+'\n')
    shutil.copytree(PILOT / 'inputs' / pilot.TASK_PATH / 'code', ROOT / 'code')
    print('Seven unique JSON spans admitted with unchanged proof bodies and protected sources.')


if __name__ == '__main__':
    prepare()
