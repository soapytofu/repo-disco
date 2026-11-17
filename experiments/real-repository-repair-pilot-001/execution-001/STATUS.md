# Execution status

The approved collection was submitted once as **61582770** on November 17, 2026
at 18:31:06 UTC. The live partition check confirmed `test`, `PreemptMode=OFF`.
It uses one CPU, 2 GB and a 60-minute limit, with no requeue. The first status
observation showed RUNNING; no completion or proof score is inferred.

The separate fresh authorization allows at most sixteen requests from the exact
frozen order, with no retries or reassignment. The older terminal sessions remain
closed. Runtime preparation is published in `61b5ed2`; 17 offline tests passed
locally and on Cannon. Full collection evidence will be reviewed before either
1-CPU Dafny or 4-CPU Vest verification job is submitted.
