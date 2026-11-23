# Bounded Dafny-library growth execution

This is a new execution host for the Dafny Standard Library and AWS MPL
extensions. It is preparation code, not a model result or execution permission.
It never imports an old live runner, ledger or authorization. The three provider
modules are exact copies of execution-005; copy-provenance.json records their
origins and hashes. The previously qualified single-JSON extractor is also an
exact copy. All fake outcomes are explicitly synthetic.

The intended ceiling is 12 new requests allocated by the root host within the
user's existing 100-call session ceiling. The runner does not own or reset the
session ledger. Its authorization must name that session and a unique root-owned
allocation. Unused slots are never reassigned. No response is retried, including
provider ambiguity, process restart, parser rejection or proof failure.

## Conditional order

The initial four slots are Standard Library stage one, AWS stage one, then their
respective stage-two children. A failed first stage blocks its child. Expansion
requires the complete saved pilot accounting, no infrastructure failure and at
least one accepted first-stage addition. If both first stages fail, the run
closes after recording the two blocked children.

The next four slots use a fresh lineage per project in the same project order;
the final four use another fresh lineage per project with project order
reversed. There is one response per eligible stage and no verifier feedback
after the response.

## Acceptance and stop rules

Only current method/function body text is model-controlled. A guarded candidate
is reconstructed from the exact frozen source map. A child receives its own
lineage's actual accepted first-stage sources and a host receipt tied to this
run's durable unique request, saved response, reconstructed candidate and fresh
native observation. There is no reference fallback or imported acceptance path.

The fixed production host writes an exclusive fresh workspace, event, command,
native stdout/stderr, resource report, every CSV, before/after source hashes and
toolchain fingerprints. It uses one CPU, no shell, no retries, bounded process
groups and the exact frozen command. Native version/fingerprint preflight
precedes any provider dispatch. A source hash or receipt alone cannot establish
native authenticity; the host owns the actual process.

The common reviewer must report qualified whole-scope success. Exact inherited
warnings may be accepted only if already allowed by the native profile. New
warnings, warning-only exits, frontend failures, incomplete coverage, inventory
mismatch, source/tool drift, outer timeout, ambiguous provider outcome or missing
provenance stop all subsequent dispatch. An ordinary proof failure or a completed
verifier-resource result with complete coverage and resource accounting is a
failed stage; it blocks its child while allowing other declared lineages.

The only dynamic profile fields are source_sha256 in already declared
unlogged_definitions, derived after guard reconstruction. Their exact names,
files and counted_as_pass:false stay frozen. The materialized profile is saved.
Unlogged definitions are never added to passing native counts.

## Root integration boundary

The final root-owned scope must provide:

- Four qualified edit/native profiles and exact base-source pins.
- The final frozen renderer and its complete runtime input inventory.
- Twelve explicit slots and fixed provider settings.
- Per-project native adapter paths for toolchain_root, solver and wall_seconds.
- A fresh authorization binding the exact scope and runtime manifest, max12,
  session ceiling100, unique allocation/session identities and expiry <=24h.

The renderer exports render_stage1(project,chain_id,root=...) and
render_stage2(project,chain_id,parent_sources,parent_evidence,root=...,
allow_synthetic=False). The host checks its complete returned payload, digest,
stage/chain/profile/source identities and parent audit. Its dispatch_eligible
field is false: rendering does not authorize a provider request.

The scope format uses projects.<project>.stages."1"/"2" with edit_profile and
native_profile package-relative paths, base_sources mapping logical Dafny paths
to {path,sha256}, and native_adapter. runtime_inputs explicitly lists every
additional renderer template, evidence and module dependency. build_runtime.py
requires all direct inputs and copies only manifest-pinned files into a new
isolated package.

No runtime freeze or authorization is issued merely by these fake tests.
Qualification corrections must be settled and independently reviewed first.

## Offline tests

Run from this directory:

    python3 -m unittest -v test_runner test_native_host test_build_runtime

All provider transports are fakes. Process tests invoke only Python subprocesses,
including child cleanup/timeout checks; they do not call Dafny, a model, the
network or credentials. Synthetic accepted-parent evidence is admitted only by
the explicit offline API. Production CLI has no synthetic flag.

CLI production entry is run_pilot.py. Root owns the invocation, private handoff,
fresh ledger allocation, cluster nonpreemption check, Slurm submission, complete
post-run review and Git publication. No alternate paid client or automatic
recovery path is provided.

