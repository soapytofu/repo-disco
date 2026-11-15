# Initial local packaging correction

The first local staging snippet used `Path('.')` without resolving it before
forming a sibling path. It looked for
`repository-repair-selection-001/witness/verify.py` inside this experiment and
raised `FileNotFoundError` before copying the adapter or writing manifests.
The subsequent offline entry therefore failed to import `verify`; that original
trace is preserved in `offline-tests-001.log`.

The deliberate correction resolves the experiment root before locating the
reviewed sibling adapter. No Dafny, model, scheduler or remote operation ran,
and no fixture source, expected outcome or public contract changed.
