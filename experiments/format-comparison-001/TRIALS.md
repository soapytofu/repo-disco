# Trial log

One row per dispatched model request. `SUCCESS` means the saved candidate passed Dafny. No request was retried.

| # | Case | Format | Repeat | Outcome | Input / output tokens | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | abs_wrong_branch | diff | 1 | PATCH_ERROR | 478 / 44 | [Result](run/001-abs_wrong_branch-diff-r1/result.json) · [Response](run/001-abs_wrong_branch-diff-r1/response.json) |
| 2 | abs_wrong_branch | full_program | 1 | SUCCESS | 331 / 110 | [Result](run/002-abs_wrong_branch-full_program-r1/result.json) · [Response](run/002-abs_wrong_branch-full_program-r1/response.json) |
| 3 | clamp_missing_upper_bound | full_program | 1 | SUCCESS | 383 / 199 | [Result](run/003-clamp_missing_upper_bound-full_program-r1/result.json) · [Response](run/003-clamp_missing_upper_bound-full_program-r1/response.json) |
| 4 | clamp_missing_upper_bound | diff | 1 | PATCH_ERROR | 530 / 42 | [Result](run/004-clamp_missing_upper_bound-diff-r1/result.json) · [Response](run/004-clamp_missing_upper_bound-diff-r1/response.json) |
| 5 | max_body_placement | diff | 1 | SUCCESS | 668 / 238 | [Result](run/005-max_body_placement-diff-r1/result.json) · [Response](run/005-max_body_placement-diff-r1/response.json) |
| 6 | max_body_placement | full_program | 1 | SUCCESS | 521 / 412 | [Result](run/006-max_body_placement-full_program-r1/result.json) · [Response](run/006-max_body_placement-full_program-r1/response.json) |
| 7 | min_missing_brace | full_program | 1 | SUCCESS | 255 / 126 | [Result](run/007-min_missing_brace-full_program-r1/result.json) · [Response](run/007-min_missing_brace-full_program-r1/response.json) |
| 8 | min_missing_brace | diff | 1 | SUCCESS | 402 / 19 | [Result](run/008-min_missing_brace-diff-r1/result.json) · [Response](run/008-min_missing_brace-diff-r1/response.json) |
| 9 | sum_missing_invariant | diff | 1 | SUCCESS | 468 / 30 | [Result](run/009-sum_missing_invariant-diff-r1/result.json) · [Response](run/009-sum_missing_invariant-diff-r1/response.json) |
| 10 | sum_missing_invariant | full_program | 1 | SUCCESS | 321 / 150 | [Result](run/010-sum_missing_invariant-full_program-r1/result.json) · [Response](run/010-sum_missing_invariant-full_program-r1/response.json) |
| 11 | abs_wrong_branch | full_program | 2 | SUCCESS | 331 / 110 | [Result](run/011-abs_wrong_branch-full_program-r2/result.json) · [Response](run/011-abs_wrong_branch-full_program-r2/response.json) |
| 12 | abs_wrong_branch | diff | 2 | PATCH_ERROR | 478 / 44 | [Result](run/012-abs_wrong_branch-diff-r2/result.json) · [Response](run/012-abs_wrong_branch-diff-r2/response.json) |
| 13 | clamp_missing_upper_bound | diff | 2 | PATCH_ERROR | 530 / 42 | [Result](run/013-clamp_missing_upper_bound-diff-r2/result.json) · [Response](run/013-clamp_missing_upper_bound-diff-r2/response.json) |
| 14 | clamp_missing_upper_bound | full_program | 2 | SUCCESS | 383 / 202 | [Result](run/014-clamp_missing_upper_bound-full_program-r2/result.json) · [Response](run/014-clamp_missing_upper_bound-full_program-r2/response.json) |
| 15 | max_body_placement | full_program | 2 | SUCCESS | 521 / 415 | [Result](run/015-max_body_placement-full_program-r2/result.json) · [Response](run/015-max_body_placement-full_program-r2/response.json) |
| 16 | max_body_placement | diff | 2 | PATCH_ERROR | 668 / 207 | [Result](run/016-max_body_placement-diff-r2/result.json) · [Response](run/016-max_body_placement-diff-r2/response.json) |
| 17 | min_missing_brace | diff | 2 | SUCCESS | 402 / 19 | [Result](run/017-min_missing_brace-diff-r2/result.json) · [Response](run/017-min_missing_brace-diff-r2/response.json) |
| 18 | min_missing_brace | full_program | 2 | SUCCESS | 255 / 126 | [Result](run/018-min_missing_brace-full_program-r2/result.json) · [Response](run/018-min_missing_brace-full_program-r2/response.json) |
| 19 | sum_missing_invariant | full_program | 2 | SUCCESS | 321 / 150 | [Result](run/019-sum_missing_invariant-full_program-r2/result.json) · [Response](run/019-sum_missing_invariant-full_program-r2/response.json) |
| 20 | sum_missing_invariant | diff | 2 | SUCCESS | 468 / 30 | [Result](run/020-sum_missing_invariant-diff-r2/result.json) · [Response](run/020-sum_missing_invariant-diff-r2/response.json) |
| 21 | abs_wrong_branch | diff | 3 | PATCH_ERROR | 478 / 44 | [Result](run/021-abs_wrong_branch-diff-r3/result.json) · [Response](run/021-abs_wrong_branch-diff-r3/response.json) |
| 22 | abs_wrong_branch | full_program | 3 | SUCCESS | 331 / 110 | [Result](run/022-abs_wrong_branch-full_program-r3/result.json) · [Response](run/022-abs_wrong_branch-full_program-r3/response.json) |
| 23 | clamp_missing_upper_bound | full_program | 3 | SUCCESS | 383 / 202 | [Result](run/023-clamp_missing_upper_bound-full_program-r3/result.json) · [Response](run/023-clamp_missing_upper_bound-full_program-r3/response.json) |
| 24 | clamp_missing_upper_bound | diff | 3 | PATCH_ERROR | 530 / 42 | [Result](run/024-clamp_missing_upper_bound-diff-r3/result.json) · [Response](run/024-clamp_missing_upper_bound-diff-r3/response.json) |
| 25 | max_body_placement | diff | 3 | SUCCESS | 668 / 311 | [Result](run/025-max_body_placement-diff-r3/result.json) · [Response](run/025-max_body_placement-diff-r3/response.json) |
| 26 | max_body_placement | full_program | 3 | SUCCESS | 521 / 417 | [Result](run/026-max_body_placement-full_program-r3/result.json) · [Response](run/026-max_body_placement-full_program-r3/response.json) |
| 27 | min_missing_brace | full_program | 3 | SUCCESS | 255 / 126 | [Result](run/027-min_missing_brace-full_program-r3/result.json) · [Response](run/027-min_missing_brace-full_program-r3/response.json) |
| 28 | min_missing_brace | diff | 3 | SUCCESS | 402 / 19 | [Result](run/028-min_missing_brace-diff-r3/result.json) · [Response](run/028-min_missing_brace-diff-r3/response.json) |
| 29 | sum_missing_invariant | diff | 3 | SUCCESS | 468 / 48 | [Result](run/029-sum_missing_invariant-diff-r3/result.json) · [Response](run/029-sum_missing_invariant-diff-r3/response.json) |
| 30 | sum_missing_invariant | full_program | 3 | SUCCESS | 321 / 147 | [Result](run/030-sum_missing_invariant-full_program-r3/result.json) · [Response](run/030-sum_missing_invariant-full_program-r3/response.json) |
| 31 | abs_wrong_branch | full_program | 4 | SUCCESS | 331 / 110 | [Result](run/031-abs_wrong_branch-full_program-r4/result.json) · [Response](run/031-abs_wrong_branch-full_program-r4/response.json) |
| 32 | abs_wrong_branch | diff | 4 | PATCH_ERROR | 478 / 44 | [Result](run/032-abs_wrong_branch-diff-r4/result.json) · [Response](run/032-abs_wrong_branch-diff-r4/response.json) |
| 33 | clamp_missing_upper_bound | diff | 4 | PATCH_ERROR | 530 / 42 | [Result](run/033-clamp_missing_upper_bound-diff-r4/result.json) · [Response](run/033-clamp_missing_upper_bound-diff-r4/response.json) |
| 34 | clamp_missing_upper_bound | full_program | 4 | SUCCESS | 383 / 200 | [Result](run/034-clamp_missing_upper_bound-full_program-r4/result.json) · [Response](run/034-clamp_missing_upper_bound-full_program-r4/response.json) |
| 35 | max_body_placement | full_program | 4 | SUCCESS | 521 / 408 | [Result](run/035-max_body_placement-full_program-r4/result.json) · [Response](run/035-max_body_placement-full_program-r4/response.json) |
| 36 | max_body_placement | diff | 4 | SUCCESS | 668 / 198 | [Result](run/036-max_body_placement-diff-r4/result.json) · [Response](run/036-max_body_placement-diff-r4/response.json) |
| 37 | min_missing_brace | diff | 4 | SUCCESS | 402 / 19 | [Result](run/037-min_missing_brace-diff-r4/result.json) · [Response](run/037-min_missing_brace-diff-r4/response.json) |
| 38 | min_missing_brace | full_program | 4 | SUCCESS | 255 / 126 | [Result](run/038-min_missing_brace-full_program-r4/result.json) · [Response](run/038-min_missing_brace-full_program-r4/response.json) |
| 39 | sum_missing_invariant | full_program | 4 | SUCCESS | 321 / 154 | [Result](run/039-sum_missing_invariant-full_program-r4/result.json) · [Response](run/039-sum_missing_invariant-full_program-r4/response.json) |
| 40 | sum_missing_invariant | diff | 4 | SUCCESS | 468 / 30 | [Result](run/040-sum_missing_invariant-diff-r4/result.json) · [Response](run/040-sum_missing_invariant-diff-r4/response.json) |
| 41 | abs_wrong_branch | diff | 5 | PATCH_ERROR | 478 / 44 | [Result](run/041-abs_wrong_branch-diff-r5/result.json) · [Response](run/041-abs_wrong_branch-diff-r5/response.json) |
| 42 | abs_wrong_branch | full_program | 5 | SUCCESS | 331 / 110 | [Result](run/042-abs_wrong_branch-full_program-r5/result.json) · [Response](run/042-abs_wrong_branch-full_program-r5/response.json) |
| 43 | clamp_missing_upper_bound | full_program | 5 | SUCCESS | 383 / 199 | [Result](run/043-clamp_missing_upper_bound-full_program-r5/result.json) · [Response](run/043-clamp_missing_upper_bound-full_program-r5/response.json) |
| 44 | clamp_missing_upper_bound | diff | 5 | PATCH_ERROR | 530 / 42 | [Result](run/044-clamp_missing_upper_bound-diff-r5/result.json) · [Response](run/044-clamp_missing_upper_bound-diff-r5/response.json) |
| 45 | max_body_placement | diff | 5 | PATCH_ERROR | 668 / 150 | [Result](run/045-max_body_placement-diff-r5/result.json) · [Response](run/045-max_body_placement-diff-r5/response.json) |
| 46 | max_body_placement | full_program | 5 | SUCCESS | 521 / 407 | [Result](run/046-max_body_placement-full_program-r5/result.json) · [Response](run/046-max_body_placement-full_program-r5/response.json) |
| 47 | min_missing_brace | full_program | 5 | SUCCESS | 255 / 126 | [Result](run/047-min_missing_brace-full_program-r5/result.json) · [Response](run/047-min_missing_brace-full_program-r5/response.json) |
| 48 | min_missing_brace | diff | 5 | SUCCESS | 402 / 19 | [Result](run/048-min_missing_brace-diff-r5/result.json) · [Response](run/048-min_missing_brace-diff-r5/response.json) |
| 49 | sum_missing_invariant | diff | 5 | SUCCESS | 468 / 30 | [Result](run/049-sum_missing_invariant-diff-r5/result.json) · [Response](run/049-sum_missing_invariant-diff-r5/response.json) |
| 50 | sum_missing_invariant | full_program | 5 | SUCCESS | 321 / 176 | [Result](run/050-sum_missing_invariant-full_program-r5/result.json) · [Response](run/050-sum_missing_invariant-full_program-r5/response.json) |
