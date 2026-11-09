# Revision 002: explicit map domain certificates

Deliberate design correction after the initial 32/32 core checks. The original
map interfaces both admitted a three-stage reference dependency path. The new
map interface introduces an opaque Domain certificate: Certify(m) -> SwapKeys(m)
-> Certify(once) -> SwapKeys(once)/SwapAt(once) -> Equal. This describes a path
in the chosen reference, not a necessary minimum depth. Arithmetic and
quantifier reasoning still matter; call count alone is not dependency depth.

The other three tasks, all client contracts, the map target contract and the
shallow map API remain unchanged. Map Kernel/observation interfaces changed;
this is a new fixture version, not a repair of the successful original proof.
Two targeted missing-certificate controls are added, both for deep variants.

Current inventory: 126 controls (16 success, 90 ordinary proof failure,
4 termination failure, 16 hidden-export resolution failure). The first new job
runs only the eight changed map reference/empty checks. After their review,
review_reference_gate.py will assemble 32 core outcomes using those eight and
24 byte-identical prior observations. Only then may the 94 distinct targeted
negative controls run. Reuse is not a fresh independent trial.

Nine offline tests passed. Cannon also passed all nine offline tests. Revised verifier job **59352546** is submitted on nonpreemptible test; actual outcomes remain pending.
No model calls, keys, prompt freeze or paid budget. All reserved families remain
untouched. Sources and runtime are pinned in manifest.json. Earlier sources,
results and source audit are preserved in the parent experiment.
