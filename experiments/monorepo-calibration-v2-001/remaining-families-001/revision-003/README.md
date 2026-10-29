# Relational revision 003: proof-only existential predicate

The only source change from revision 002 is `opaque predicate Overlap` →
`opaque ghost predicate Overlap`. This predicate is used only in lemma contracts;
its definition, parameter types, public name, helper/client contracts and proof
bodies remain unchanged. The failed first and second runs are preserved.

Revision 002's frontend diagnostic required a compilable bounded range for the
non-ghost existential. [Dafny's documentation](https://dafny.org/dafny/HowToFAQ/Errors)
explains the distinction between compiled and ghost functions/predicates. Marking
this mathematical specification as ghost addresses that restriction without
weakening the existential or introducing assumptions.

Three offline tests pass. Job 56197984 completed once on non-preemptible test in
1m52s: **30/30 expected outcomes** (4 references, 24 proof failures, 2 explicit
hidden-name failures). All source/code hashes and diagnostic locations were
reviewed. Full raw sources/logs and results-review.json are archived. This is
verifier-only fixture development, not a model run.
