# Dafny growth namespace revision 002

The original full-scope reference invocation, job **61747428**, ended with
exit **2**, `RESOLUTION_OR_TYPE_FAILURE`, before any proof gate passed. Dafny
reported this module cycle:

```text
FisherYates → GrowthPick → import Shift → FisherYates
```

The original frozen source, runtime and complete failure evidence stay intact
under `dafny/` and `qualification-001/`. This separate candidate revision has
not been run through Dafny and contains no submission or retry machinery.

Only the module declaration and import-binding lines change:

```diff
-module FisherYates.GrowthShift {
-  import Model
+module RepoDiscoGrowthShift {
+  import Model = FisherYates.Model

-module FisherYates.GrowthPick {
-  import Shift = FisherYates.GrowthShift`Public
+module RepoDiscoGrowthPick {
+  import Shift = RepoDiscoGrowthShift`Public
```

Upstream FisherYates children use sibling imports such as `import Model`.
The original new `GrowthPick` was itself a FisherYates child, but imported its
sibling through the enclosing parent. Dafny's diagnostic confirms that this
forms a dependency cycle. Moving the additions into distinct top-level
modules removes them from that parent. The unchanged `Model` alias is now
explicitly bound to the original `FisherYates.Model`; the unchanged `Shift`
alias refers directly to the new stage-one module's `Public` export. Neither
new top-level name occurs in any of the 91 pinned upstream files.

Every byte after these header lines is unchanged: export visibility,
signatures, requires/ensures, decreases, reference and negative bodies, call
arguments and body markers. File destinations and host-owned omission controls
also remain unchanged. All **12 control overlays** have been regenerated; the
detached failing module is byte-identical. Named new-unit expectations are
updated for the two new namespaces and remain provisional until native CSV
confirms them.

`allowed-source-diffs.patch` shows all template/overlay differences.
`source-provenance.json` binds each old/new source and its permitted line edits.
`design.json` pins the original failure evidence and records the dependency
reasoning. `controls-manifest.json` retains all control outcomes and coverage
requirements. Five offline tests check inverse reconstruction, interface/body
preservation, source identity, catalog preservation and failure preservation.
They do not establish successful native resolution or proof.

Root must review this revision and prepare a distinct source-bound reference
check before any later negative-control execution. No original score changes,
model calls, native calls or automatic resubmission are part of this revision.
