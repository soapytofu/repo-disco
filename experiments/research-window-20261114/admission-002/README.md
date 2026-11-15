# Second admission: repository repair selection

This operator helper admits 32 prospectively frozen requests to the **existing**
research process, job `60698074`. It creates no Slurm job, provider client,
credential handoff, budget owner, or alternate ledger. The first batch has 32
completed reservations; the window cap remains 128. Successful completion of
this batch would leave 64 calls available, without allocating them here.

The input proposal was published in `9e3d3c780c563c5f3961c80c1c05eb18bf24be80`.
Its SHA-256 is
`9a3ac2546edc6c79307826766af3517bdc8d9a8fe629a2ba0239660f4ead778a`.
The helper pins the original scope, execution freeze, fixed `repair-v1` handler,
first admission, published first global ledger and first completion receipt.
The immutable bundle contains 1,207 files: 110 frozen files including the freeze,
1,095 repository dependencies, a copied runtime freeze and a batch binding.
The 32 slot identifiers differ from all first-batch identifiers, as required by
the existing global gate. No prior freeze or executable is modified.

## Operator sequence

Run from this directory. **`prepare` has already been run locally.** Do not repeat
it or delete its output. The parent coordinator reviews and publishes this code
and the exact prepared descriptor before any remote mutation.

1. `python3 -B next_admission.py stage` writes only the exact new data bundle.
2. `python3 -B next_admission.py check` performs a fresh remote read-only audit.
3. `python3 -B next_admission.py admit` repeats the complete audit, takes a durable
   exclusive attempt lock, syncs the inputs and descriptor, rechecks state and
   deadline, then atomically publishes `admissions/000002.json` without replacing
   an existing file. The original owner alone notices and executes that descriptor.
4. After an exception, disconnection or unconfirmed result, use only
   `python3 -B next_admission.py inspect`. Do not repeat stage/admit, remove locks,
   create a new runner, or infer failure from a missing local receipt.

Every SSH subprocess has a 120-second hard timeout, and the read-only scheduler
probe has a 10-second timeout. The descriptor and archive travel via stdin rather
than shell arguments. The helper never reads credentials or probes the provider.

Staging cannot publish an admission. Both mutating commands have permanent local
and remote attempt markers. Admission requires the one original job to be running
in the canonical directory, matching retained owner records, no active or terminal
batch, exactly 32 declared/completed reservations, the exact predecessor chain,
no second queue/admission/submission/output, and complete old/new file inventories.
The first run directory is `session-001/runs/0001-repair-diversity-pilot-002`.

Publication uses an exclusive hard link from a synced temporary file on the same
filesystem, then syncs the admissions directory. The temporary name is retained
outside the admissions directory. If durability confirmation fails after the link,
publication is ambiguous; it is never retried. This relies on the filesystem's
normal exclusive-link/fsync semantics, not a claim of a distributed transaction.
The live gate continues to check its own budget, ownership and deadline before
every request, including after durable reservation.

## Offline validation

`offline-tests.log` records 13 passing tests. They prepare the actual immutable
bundle in a temporary directory, validate/decode all 32 planned slots through the
unchanged handler, and audit copies of the actual published first ledger,
completion receipt and complete evidence using the coordinator's real run-path
convention. The remote absolute path check and scheduler are injected only in that
local replay. No network, provider or Dafny process is invoked.

Synthetic cases cover stage/admit separation, duplicate attempts, active/terminal
or ambiguous ledger state, mismatched owner, inventory/deadline drift, source changes
during sync, pre- and post-publication fsync failures, no-clobber publication races,
and ambiguous SSH outcomes. They do not certify the current remote state; the
operator commands recheck it immediately before admission.

During review, the parent caught an initial unprefixed run-directory assumption;
the actual predecessor replay now explicitly exercises the `0001-` convention.
Large descriptor inventories were also moved to stdin to avoid shell argument
limits. All final checks include these corrections.
