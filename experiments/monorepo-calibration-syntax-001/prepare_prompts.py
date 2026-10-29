"""Offline, prompt-only revision. No transport, credential, or verifier calls."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / 'monorepo-calibration-v2-001' / 'frozen-001'
PARENT_SHA = 'c37781be6014e0b5ba53ae99b28a90bf7a5bf05be2cd15650098dadc3ac0a590'
VERSION = 'statement-syntax-v1'
EXAMPLE_BODY = ('if true {\n  assert true;\n} else {\n  assert true;\n}\n'
                'assert (if true then 1 else 0) == 1;')
SYNTAX = '''Dafny STATEMENT syntax (required inside a lemma body):
- A conditional statement is `if CONDITION { STATEMENTS } else { STATEMENTS }`. Keep these inner block braces. Do NOT put `then` after a statement condition. An `else if CONDITION { ... }` chain is also permitted.
- Every lemma-call statement and every assert statement ends with `;`. A branch block does not need a trailing semicolon. Lemma calls are statements, not values in an expression.
- `if CONDITION then EXPR else EXPR` is ONLY a pure value expression, for example inside an assertion or as an argument to a listed call. It cannot contain statement calls or statement sequences. Parenthesize it when embedded in a larger expression.
- Return the contents of the Prove body: omit ONLY the outer lemma body braces. Preserve braces around every nested statement branch. Do not return a signature, contract, import, module, or whole file.
- JSON values are strings: escape internal newlines as JSON \\n (decoded once to real newlines). Do not double-escape them into literal backslash-n text. Use exactly the requested filenames, with no extra keys or prose.

Allowed statements: braced if/else, assert, and the listed statement calls. Allowed expressions: parameters, integer/Boolean literals, + and -, comparisons, &&, ||, ==> and !; parentheses, length |s|, empty sequence [], indexing/slicing, map updates m[k := v], listed pure calls, and pure conditional expressions as described above. No comments, declarations, assignments, loops, quantifiers, multiplication, assume, reveal, attributes, assert-by blocks or unlisted calls. Assertions and all calls must verify. Copying equivalent proof text between bodies is allowed; delegation to another helper is not.'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def check_bundle(root):
    manifest = load(root / 'freeze.json')
    names = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} - {'freeze.json'}
    if names != set(manifest['files']):
        raise ValueError('Frozen file-set drift')
    for name, expected in manifest['files'].items():
        if sha(root / name) != expected:
            raise ValueError('Frozen byte drift: ' + name)


def revised_prompt(original, task):
    before, sep, rest = original.partition('Allowed syntax:')
    if not sep:
        raise ValueError('Missing parent syntax paragraph')
    _, sep, after = rest.partition('\n\nAllowed parameters:')
    if not sep:
        raise ValueError('Missing parent parameter paragraph')
    example = json.dumps({name: EXAMPLE_BODY for name in task['editable_files']})
    explanation = ('Syntax-only JSON example (not a solution; these assertions do not prove the task contracts). '
                   'The example uses no task helper or proof strategy:\n' + example)
    return before + SYNTAX + '\n\n' + explanation + '\n\nAllowed parameters:' + after


def prepare(out):
    if sha(PARENT / 'freeze.json') != PARENT_SHA:
        raise ValueError('Unexpected parent proposal')
    check_bundle(PARENT)
    out.mkdir(exist_ok=False)
    # Explicit selection excludes previous preparation code and all reference solutions.
    for name in ['guard', 'tasks']:
        shutil.copytree(PARENT / name, out / name)
    for name in ['preflight-gate.json', 'order-design.json']:
        shutil.copy2(PARENT / name, out / name)
    system = ((PARENT / 'system.txt').read_text().rstrip() +
              '\nUse braced if/else STATEMENTS and semicolon-terminated lemma calls/assertions. '
              'The if/then/else form is for pure value expressions only, never for lemma-call branches.\n')
    (out / 'system.txt').write_text(system)
    tasks = load(PARENT / 'tasks.json')
    changes = []
    for task in tasks:
        folder = out / 'tasks' / task['task_id']
        original = (folder / 'prompt.txt').read_text()
        revised = revised_prompt(original, task)
        (folder / 'prompt.txt').write_text(revised)
        changes.append(dict(task_id=task['task_id'], old_sha256=digest(original),
                            new_sha256=digest(revised), added_utf8_bytes=len(revised.encode())-len(original.encode())))
        task.update(prompt_sha256=digest(revised), prompt_utf8_bytes=len(revised.encode()))
        save(folder / 'task.json', task)
    save(out / 'tasks.json', tasks)
    lookup = {t['task_id']: t for t in tasks}
    trials = load(PARENT / 'trials.json')
    for trial in trials:
        trial['prompt_sha256'] = lookup[trial['task_id']]['prompt_sha256']
        trial['system_sha256'] = digest(system)
    save(out / 'trials.json', trials)
    settings = load(PARENT / 'settings.json')
    settings['prompt_revision'] = VERSION
    save(out / 'settings.json', settings)
    save(out / 'provenance.json', dict(parent_freeze_sha256=PARENT_SHA,
         prompt_revision=VERSION, model_calls=0, new_dafny_runs=0, parser_changed=False,
         changes=changes, instruction='No execution authorization; 32 trial slots retained only for a possible later proposal.'))
    (out / 'README.md').write_text('''# Syntax-only revised prompt bundle: no model authorization

Sixteen task prompts and the existing 32-slot counterbalanced order. Only syntax
instructions/examples and corresponding hashes change. Sources, contracts, maps,
body-json-v2.1 parser, model settings and previous preflight evidence are unchanged.
No reference proofs are in prompts. Examples show only neutral syntax, not solutions.
No model execution or Dafny run is performed or authorized by this preparation.
The historical 1/32 pilot score is unchanged; a model benefit is not yet measured.
''')
    save(out / 'freeze.json', dict(status='FROZEN_PROPOSAL_NO_MODEL_AUTHORIZATION',
         model_calls=0, trial_count=32, files={str(p.relative_to(out)):sha(p)
         for p in sorted(out.rglob('*')) if p.is_file()}))
    return out


if __name__ == '__main__':
    print(prepare(ROOT / 'frozen-001'))
