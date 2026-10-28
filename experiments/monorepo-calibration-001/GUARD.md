# Calibration output policy (calibration-body-v1)

The model returns one JSON object mapping exactly the editable helper filenames
to complete file strings. A single fenced/prose-wrapped JSON object is accepted;
duplicate keys, multiple objects, malformed brace wrappers, wrong filename sets
and non-string sources are rejected. Extraction decodes JSON only: it never
repairs escaped newlines, source, proofs or contracts.

Every byte outside each trusted seed's unique empty Prove body is protected.
Candidate bodies use a bounded parser for if/else, assert, task-allowlisted lemma
calls, permitted parameter/pure-expression names, integer arithmetic/comparisons,
Boolean connectives, sequence indexing/slicing and map updates. No comments,
assume, reveal, declarations, loops, attributes, arbitrary qualified names or
cross-helper delegation are accepted. Only sequence tasks allow self-recursion;
the fixed induction-disabled attribute and decreases clause remain protected.

Limits: response 256 KiB, each body 64 KiB, 8192 tokens, 256 statements, expression
depth 32, statement depth 24. The guard checks syntax and immutable bytes, not
semantic correctness. The entire guarded workspace must verify with strict exit
zero. It is not a general Dafny parser or a sandbox for untrusted original inputs.

The call allowlists deliberately enforce each export view and prohibit delegation
to another editable helper. This is a disclosed treatment restriction, including
for separate mode. Both separate bodies may still contain copied proof text.
Eight offline tests cover all 16 reference replays, rejected bypasses/spec edits,
ordinary wrong proofs, payload ambiguity, file boundaries and limits. Replaying a
reference is not yet evidence that the twelve newly built references verify;
that gate is tracked in remaining-families-001. Earlier frozen parsers and results
are unchanged.
