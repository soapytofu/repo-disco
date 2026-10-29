"""Format audited descriptive results; no model or verifier calls."""
import collections,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
 s=json.loads((ROOT/'results-review.json').read_text())
 if s['integrity_issues']:raise ValueError('Resolve audit issues first')
 lines=['# Calibration results (development data)', '',f"{s['reserved']}/32 requests reserved; {s['completed_responses']} saved completed responses; {s['unique_request_ids']} unique request IDs. Strict whole-workspace successes: **{s['verified']}/32 planned trials**. No SDK retries: {s['no_sdk_retries']}.",'','Every trial uses its original frozen prompt/order/settings and a fresh seed. No repairs, retries, feedback, replacement samples or main-corpus requests.','', '| Family | Shallow/shared | Shallow/separate | Deep/shared | Deep/separate | Total |','| --- | ---: | ---: | ---: | ---: | ---: |']
 families=sorted({x['family'] for x in s['cells']})
 for family in families:
  cells=[next(x for x in s['cells'] if x['family']==family and x['cell']==c) for c in ['shallow_shared','shallow_separate','deep_shared','deep_separate']]
  lines.append('| '+family+' | '+' | '.join(str(x['verified'])+'/2' for x in cells)+' | '+str(sum(x['verified'] for x in cells))+'/8 |')
 lines+=['','## Failure categories','']
 for outcome,count in sorted(s['request_outcomes'].items()):lines.append(f'- {outcome}: {count}')
 if s.get('output_rejection_reasons'):
  lines+=['','Guard rejection reasons (raw responses retained; no post-hoc repair):','']
  for reason,count in sorted(s['output_rejection_reasons'].items()):lines.append(f'- `{reason}`: {count}')
 lines+=['','## Usage and interpretation','', 'Saved token usage: `'+json.dumps(s['token_usage'],sort_keys=True)+'`. No dollar estimate is inferred from token totals.','',s['limitations'],'', 'Parser/guard failures are part of end-to-end completion, but must be distinguished from proof failure. A verifier pass establishes the protected contract, not task difficulty. Review both 8/8 family ceilings and 0/8 floors before scaling. The main 192-call corpus is still gated and has no new authorization.','', 'All exact messages, provider responses, request IDs, extraction decisions, candidate source, guarded parent/accepted hashes and raw verifier stdout/stderr are archived under model-001. results-review.json and model-001-sha256.json bind the review to saved bytes.','']
 (ROOT/'RESULTS.md').write_text('\n'.join(lines))
if __name__=='__main__':main()
