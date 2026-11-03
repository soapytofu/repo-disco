# Saved-response diagnostic — zero model calls

**Complete:** three of five unchanged rejected bodies verify; one fails assertions
and one exits nonzero on trigger warnings. The separately authored one-statement
repair also verifies. [Results and full evidence](RESULTS.md). Original pilot
score remains 18/24.

This separately labeled verifier-only diagnostic uses the remaining authorized
two-hour analysis window after the [24-call pilot](../monorepo-reasoning-calibration-pilot-001/RESULTS.md).
The original **18/24** score, five guard rejections and one proof failure remain
unchanged. No new model requests, retry or revised general parser is involved.

Five candidates insert the exact JSON body strings from rejected trials 02, 08,
18, 21 and 24 into their original trusted empty seeds. Only these manually reviewed
and hash-pinned bodies bypass the body-language restriction for diagnosis; this
is not an automatic admission policy. Whole-repository verification still includes
all providers/clients and preserves all contracts, imports and other source.
Their semantic outcomes are unknown before this diagnostic.

A sixth candidate adds exactly `O2.PutAt(m,j,y,q);` at the start of the existing
`q == j` branch in trial 03, testing the suspected missing inner-update fact.
The original assertion failure is already archived and is not rerun. This added
statement is a human/agent-authored repair hypothesis, not a new model output or
retroactive success. No other proof statement or protected byte changes.

[Case identities and hashes](cases.json), [scope](scope.json), source fixtures,
runner and no-requeue Slurm script are preserved. Three offline design tests check
exact original response hashes, five unchanged body reconstructions, the single
insertion, protected sources and unchanged original guard decisions. The compute
job will perform six checks once on a live-confirmed nonpreemptible partition,
recording every stdout/stderr and exit category. No verification runs locally or
on login nodes. Job **57167108** completed once on live-confirmed nonpreemptible `test` in 25 seconds; [submission evidence](submission-responses.json).
