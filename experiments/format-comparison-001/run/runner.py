"""Bounded, paired repair trials with an interactive pause every five calls.

Run from the repository root. Credentials are kept in this process only.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import time

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from botocore.config import Config
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage
from code_output_parser import CodeOutputParser
from language import Language, Program
from patch import apply_text_diff, TEXT_BEFORE_EXAMPLE, TEXT_DIFF_EXAMPLE, TEXT_AFTER_EXAMPLE

# Reuse the reviewed credential loader from the recorded full-program pilot.
helpers = runpy.run_path(str(ROOT / 'experiments/repair-003/runner.py'), run_name='credential_helpers')
consume_key = helpers['consume_key']
write_json = helpers['write_json']


def screen_preservation(before, after):
    def obligations(text):
        return Counter(re.sub(r'\s+', '', line) for line in text.splitlines()
                       if re.match(r'\s*(requires|ensures|assert)\b', line))
    def declarations(text):
        return set(re.findall(r'\b(function|method|lemma)\s+(\w+)', text))
    old, new = obligations(before), obligations(after)
    return {
        'missing_literal_obligations': list((old - new).elements()),
        'missing_declarations': sorted(declarations(before) - declarations(after)),
        'possible_proof_bypass': bool(re.search(r'\bassume\b|\baxiom\b|verify\s+false|\{:\s*extern', after)),
        'requires_count_increased': len(re.findall(r'\brequires\b', after)) > len(re.findall(r'\brequires\b', before)),
        'manual_review': 'required; this lexical screen is not semantic validation',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite', type=Path, required=True)
    parser.add_argument('--max-calls', type=int, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if args.max_calls not in (20, 50):
        raise SystemExit('Use an explicitly approved cap of 20 or 50 calls.')
    suite = args.suite.resolve()
    baseline = json.loads((suite / 'baseline-validation.json').read_text())
    assert len(baseline) == 5
    assert all(r['reference']['status'] == 0 and r['reference']['outcome'] == 'SUCCESS' for r in baseline)
    assert all(r['broken']['status'] not in (0, 124, 137) for r in baseline)
    cases = sorted(row['case'] for row in baseline)
    plan = []
    for repeat in range(args.max_calls // 10):
        for case_index, case in enumerate(cases):
            modes = ['diff', 'full_program'] if (repeat + case_index) % 2 == 0 else ['full_program', 'diff']
            for mode in modes:
                plan.append({'case': case, 'repeat': repeat + 1, 'mode': mode})
    if args.prepare_only:
        print(json.dumps(plan, indent=2))
        return

    run = suite / datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%S-%fZ')
    run.mkdir(exist_ok=False)
    shutil.copy2(__file__, run / 'runner.py')
    write_json(run / 'plan.json', plan)
    write_json(run / 'protocol.json', {
        'model': 'us.anthropic.claude-sonnet-4-6', 'region': 'us-east-1',
        'max_calls': args.max_calls, 'max_output_tokens_per_call': 4096,
        'sdk_total_max_attempts': 1, 'verifier_timeout_seconds': 60,
        'temperature': 'provider_default', 'pause_every_calls': 5,
        'model_request_retries': 0, 'verifier_retries': 0,
        'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'python': sys.version,
        'packages': {p: version(p) for p in ['langchain-aws', 'langchain-core', 'boto3', 'botocore', 'z3-solver']},
        'case_input_hashes': {case: hashlib.sha256((suite / 'cases' / case / 'broken.dfy').read_bytes()).hexdigest() for case in cases},
    })
    shared = ('You are an expert Dafny developer. Repair the supplied program using the verifier feedback. '
              'Preserve all existing declarations, preconditions, postconditions, and assertions. '
              'Do not strengthen preconditions, weaken specifications, remove checks, introduce assumptions, '
              'or disable verification. Make only the changes needed to repair the program. ')
    format_instructions = {
        'full_program': 'Return only the COMPLETE corrected Dafny source, optionally inside one dafny code fence. Do not return a diff.',
        'diff': ('Return only a line-based diff. Anchors must be @@ exact existing line @@, including BOTH opening and closing markers. '
                 'Anchors move the cursor after a matching line; consecutive anchors must match consecutive source lines. '
                 '= line keeps a matching line forward; - line deletes a matching line forward; + line inserts at the cursor. '
                 'Malformed or unmatched directives reject the entire patch. Use enough context to identify the intended location. '
                 f'Example before:\n{TEXT_BEFORE_EXAMPLE}\nExample diff:\n{TEXT_DIFF_EXAMPLE}\nExample after:\n{TEXT_AFTER_EXAMPLE}'),
    }
    results = []
    calls = 0
    consume_key(Path.home() / '.repodisco-bedrock-handoff')
    print(f'RUN_DIRECTORY={run}', flush=True)
    try:
        model = ChatBedrockConverse(model='us.anthropic.claude-sonnet-4-6', region_name='us-east-1', max_tokens=4096,
                                   config=Config(connect_timeout=15, read_timeout=90, retries={'total_max_attempts': 1}))
        for sequence, item in enumerate(plan, 1):
            if (suite / 'STOP').exists():
                break
            folder = run / f"{sequence:03d}-{item['case']}-{item['mode']}-r{item['repeat']}"
            folder.mkdir()
            before = (suite / 'cases' / item['case'] / 'broken.dfy').read_text()
            feedback = (suite / 'cases' / item['case'] / 'broken-stdout.txt').read_text()
            system = shared + format_instructions[item['mode']]
            user = f'Program:\n{before}\n\nVerifier feedback:\n{feedback}'
            write_json(folder / 'prompt.json', [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}])
            record = dict(item, sequence=sequence, outcome='DISPATCHED', usage=None)
            calls += 1
            assert calls <= args.max_calls
            write_json(run / 'ledger.json', {'calls_dispatched': calls, 'max_calls': args.max_calls, 'completed': results, 'current': record})
            try:
                response = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
                record['usage'] = response.usage_metadata
                write_json(folder / 'response.json', {'content': response.content, 'usage_metadata': response.usage_metadata,
                                                     'stop_reason': response.response_metadata.get('stopReason')})
            except Exception as error:
                record['outcome'] = 'API_ERROR'
                record['error_type'] = type(error).__name__
                write_json(folder / 'result.json', record)
                results.append(record)
                break  # investigate infrastructure failures; never retry automatically
            text = CodeOutputParser().invoke(response)
            (folder / 'parsed-response.txt').write_text(text)
            try:
                candidate = apply_text_diff(before, text) if item['mode'] == 'diff' else text
                if not candidate.strip():
                    raise ValueError('Empty candidate')
            except ValueError as error:
                record.update(outcome='PATCH_ERROR', error=str(error), program_changed=False)
            else:
                (folder / 'output-program.dfy').write_text(candidate)
                record['program_changed'] = candidate != before
                record['preservation_screen'] = screen_preservation(before, candidate)
                start = time.monotonic()
                ver = Language.DAFNY.get_backend().verify(Program(candidate, Language.DAFNY), timeout=60)
                record.update(outcome='TIMEOUT' if ver.status in (124, 137) else ver.outcome.name,
                              verifier_exit_status=ver.status, verifier_seconds=round(time.monotonic() - start, 3))
                (folder / 'verifier-stdout.txt').write_text(ver.stdout)
                (folder / 'verifier-stderr.txt').write_text(ver.stderr)
            write_json(folder / 'result.json', record)
            results.append(record)
            write_json(run / 'ledger.json', {'calls_dispatched': calls, 'max_calls': args.max_calls, 'completed': results, 'current': None})
            print(f"TRIAL {sequence}/{args.max_calls} {item['case']} {item['mode']} {record['outcome']}", flush=True)
            if calls % 5 == 0 and calls < args.max_calls:
                if input('BATCH_READY: type continue or stop: ').strip() != 'continue':
                    break
    finally:
        os.environ.pop('AWS_BEARER_TOKEN_BEDROCK', None)
        write_json(run / 'ledger.json', {'calls_dispatched': calls, 'max_calls': args.max_calls, 'completed': results,
                                        'current': record if calls > len(results) else None,
                                        'finished_at_utc': datetime.now(timezone.utc).isoformat()})
    print(f'FINISHED calls={calls}; credential cleared from runner environment.', flush=True)


if __name__ == '__main__':
    main()
