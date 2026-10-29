"""Summarize reviewed saved evidence without any model or verifier calls."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent


def main():
    s=json.loads((ROOT/'results-review.json').read_text())
    if s['integrity_issues']:raise ValueError('Resolve integrity issues before acceptance')
    lines=['# Eight-call syntax smoke results', '',
        f"Requests: {s['reserved']}/8 reserved, {s['completed_responses']} responses, {s['unique_request_ids']} unique request IDs. Zero SDK retries: {s['no_sdk_retries']}.",
        f"Parser/guard admission: **{s['guard_admitted']}/8**. Strict whole-workspace verification: **{s['verified']}/8**.",
        f"Predeclared syntax-readiness gate: **{'PASS' if s['syntax_readiness'] else 'NOT PASSED'}**. No automatic expansion.", '',
        '| Family | Deep/shared | Deep/separate |','| --- | --- | --- |']
    for family in sorted({x['family'] for x in s['cells']}):
        labels=[]
        for cell in ['deep_shared','deep_separate']:
            rows=[r for r in s['trials'] if r['family']==family and r['cell']==cell]
            labels.append(rows[0]['outcome'] if rows else 'NOT RUN')
        lines.append('| '+family+' | '+' | '.join(labels)+' |')
    lines+=['','## Interpretation','',s['limitations'],'',
        'A guard pass establishes syntax and protected assembly, not a proof. '
        'Proof failures, frontend errors, timeouts and infrastructure failures are distinct outcomes. '
        'A syntax-gate pass is only a small development check, not a reliable error-rate estimate. '
        'Any larger run needs review and a new explicit budget. Previous scores remain unchanged.', '',
        'Token usage: `'+json.dumps(s['token_usage'],sort_keys=True)+'`.', '',
        'Full messages, responses, ledger, extraction decisions, admitted source, hashes and raw verifier '
        'logs are in model-001. results-review.json and model-001-sha256.json bind this review to the archive.','']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines))


if __name__=='__main__':main()
