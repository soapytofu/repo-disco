# Repository import-map audit

October 23, 2026. Non-paid static analysis; no Dafny or model execution.

All three composition-pilot-001 maps have three modules, three distinct directed import edges, root import depth two, and no unreachable modules. This is a measurement of the archived maps, not independent confirmation that every source import is represented, nor evidence of model success or proof depth. The queued pilot sources and prompts were not changed.

`results.json` records input paths, SHA-256 hashes, and deterministic metrics. Reproduce an individual result with:

```sh
python3 scripts/repository_map_metrics.py experiments/composition-pilot-001/tasks/range_precondition/dependency-map.json --root Client
```

The utility accepts the existing modules/imports map format, rejects unknown targets, duplicate module IDs, missing entries, and cycles (including unreachable cycles), counts alias bindings separately from distinct edges, and leaves proof depth unknown. It is a structural validator, not a Dafny parser or complete corpus-manifest validator.

Validation: `python3 tests/test_repository_map_metrics.py` — six tests passed, covering diamond paths, duplicate aliases, disconnected modules, cycles, malformed maps, isolated modules, and the three current fixtures.
