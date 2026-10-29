# Relational revision 002: explicit existential witness

The first run's four relational reference failures and all raw evidence remain
in the parent directory. This deliberate revision changes only Kernel.dfy and
Stage3.dfy: an opaque Witness predicate has exactly the original conjunction
a<=w<=b && c<=w<=d; Overlap remains its existential closure with an explicit
quantifier trigger. Providers assert the supplied witness before the existential.
No client, helper interface, helper proof, import/export view or control category
changes. Witness is not exported through the public kernel view. Three offline
tests pass. Job 56197868 completed in 40s: all 30 checks failed on a frontend error
because the existential could not be compiled as a non-ghost predicate. No
reference or negative outcome validates this revision. Full raw evidence is
preserved. Revision 003 makes Overlap explicitly ghost; zero model calls.

Do not treat matching negative outcomes from the first faulty provider as evidence
that the old relational tasks were valid. Select only this revision after its
references and all targeted negative categories pass review.
