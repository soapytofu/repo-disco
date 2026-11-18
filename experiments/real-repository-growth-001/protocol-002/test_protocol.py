"""Read-only actual-reference replay and explicitly synthetic integration tests."""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import unittest

import body_policy as b
import native_adapter as n

ROOT = Path(__file__).resolve().parent
GROWTH = ROOT.parent
REPO = ROOT.parents[2]


def fixture(stage, alternative=False):
    suffix = "alternative" if alternative else "reference"
    return {
        "vmc-move": GROWTH / f"dafny-revision-002/fixtures/move-{suffix}/repodisco-growth/MoveToFront.dfy",
        "vmc-pair": GROWTH / f"dafny-revision-002/fixtures/pair-{suffix}/repodisco-growth/PickPair.dfy",
        "vest-frame": GROWTH / f"vest/cases/frame-{suffix}/vest_dev/src/formats/growth_frame.rs",
        "vest-batch": GROWTH / f"vest/cases/batch-{suffix}/vest_dev/src/formats/growth_batch.rs",
    }[stage].read_bytes()


def replacement(stage, alternative=False):
    return b.source_body(stage, fixture(stage, alternative))


def raw_parts(artifacts):
    return {name: artifacts[name] for name in b.read_json(artifacts["bound-record.json"])["raw_sha256"]}


def mutate_as_synthetic(binding, artifacts, operation):
    """Negative fixtures only: never alter saved artifacts or label these native."""
    data = dict(artifacts)
    operation(data)
    profile = b.read_json(data["profile.json"])
    bound = b.read_json(data["bound-record.json"])
    record = b.read_json(data["record.json"])
    raw = {name: data[name] for name in bound["raw_sha256"]}
    bound["profile_sha256"] = b.sha(b.canonical(profile))
    bound["raw_sha256"] = b.source_hashes(raw)
    record["artifacts"] = {name: b.sha(raw[name]) for name in ("stdout.txt", "stderr.txt", "resources.txt")}
    data["bound-record.json"], data["record.json"] = b.canonical(bound), b.canonical(record)
    return replace(binding, origin="synthetic-offline", artifact_sha256=tuple(sorted(b.source_hashes(data).items()))), data


def update_json(data, name, operation):
    obj = b.read_json(data[name])
    operation(obj)
    data[name] = b.canonical(obj)


def modified_reports(raw, operation):
    """Synthetic mutation of decoded saved reports, retaining each duplicate."""
    documents = [deepcopy(doc) for doc, _ in n._native_json(raw, "stdout.txt")]
    operation(documents)
    return ("SYNTHETIC MUTATION FOR OFFLINE NEGATIVE TEST ONLY\n" +
            "\n".join(json.dumps(doc) for doc in documents) + "\n").encode()


def synthetic_parent(project, upstream):
    """Create fake native/acceptance records only to test opt-in code paths.

    Tiny synthetic inventories are deliberately unrelated to the real 267/5410
    upstream counts. These records must NEVER be published as native evidence.
    """
    first = "vmc-move" if project == "dafny-vmc" else "vest-frame"
    sources, _ = b.reconstruct(first, replacement(first, True), upstream, chain_id="synthetic-chain")
    hashes = b.source_hashes(sources)
    toolchain = {"synthetic": True, "native_tool_was_not_run": True}
    tools = dict(project=project, toolchain=toolchain, synthetic=True)
    command = ["SYNTHETIC_ONLY_NO_PROCESS_EXECUTED"]
    logical = list(command)
    if project == "dafny-vmc":
        inventory = {"SYNTHETIC_UPSTREAM (correctness)": 1, "SYNTHETIC_PARENT (correctness)": 1}
        raw = {"stdout.txt": b"SYNTHETIC TEST ONLY\nDafny program verifier finished with 2 verified, 0 errors\n",
               "stderr.txt": b"", "resources.txt": b"SYNTHETIC NO EXECUTION\n",
               "csv/synthetic.csv": ("TestResult.DisplayName,TestResult.Outcome,TestResult.Duration,TestResult.ResourceCount\n" +
                                      "".join(f"{name},Passed,00:00:00.0,0\n" for name in inventory)).encode()}
        metadata = None
    else:
        documents = []
        for crate in ("vstd", "vest_lib", "vest_dev"):
            documents.append({"verus": {"version": "SYNTHETIC_NO_NATIVE_RUN"},
                              "verification-results": {"encountered-error": False, "encountered-vir-error": False,
                                                       "is-verifying-entire-crate": True, "success": True,
                                                       "errors": 0, "verified": 1},
                              "times-ms": {"num-threads": 1, "smt": {"smt-run-module-times": [
                                  {"module": "SYNTHETIC", "function-breakdown": [
                                      {"function": crate + "::SYNTHETIC_NOT_NATIVE", "mode:": "proof", "success": True}]}]}}})
        raw = {"stdout.txt": ("SYNTHETIC TEST ONLY\n" + "\n".join(json.dumps(doc) for doc in documents)).encode(),
               "stderr.txt": b"", "resources.txt": b"SYNTHETIC NO EXECUTION\n"}
        _, extracted = n.extract_native(project, raw, 0)
        inventory = extracted["inventory"]
        metadata = dict(crates=["vstd", "vest_lib", "vest_dev"],
                        version={"version": "SYNTHETIC_NO_NATIVE_RUN"}, num_threads=1)
    gate = dict(schema="repodisco-growth-stage-one-scope-qualification-v1", project=project, stage=1,
                status="SOURCE_AND_NATIVE_INVENTORY_REVIEW_PASSED", reference_reviewed=True,
                negative_controls_reviewed=True, model_acceptance=False,
                required_inventory_sha256=b.sha(b.canonical(inventory)), synthetic=True,
                notice="OFFLINE FIXTURE, NOT ACTUAL QUALIFICATION")
    scope = dict(schema="repodisco-native-growth-scope-v2", project=project, stage=1,
                 readiness="STAGE_ONE_REFERENCE_AND_NEGATIVES_REVIEWED",
                 qualification_gate_sha256=b.sha(b.canonical(gate)), required_inventory=inventory,
                 command_sha256=b.sha(b.canonical(command)), logical_command=logical, toolchain=toolchain,
                 tools_record_sha256=b.sha(b.canonical(tools)), upstream_warnings=[], unlogged_definitions=[],
                 warning_policy_sha256=b.sha((ROOT / "native_parsers/warning_policy.py").read_bytes()), synthetic=True)
    if metadata:
        scope["verus_metadata"] = metadata
    profile = dict(project=project, source_sha256=hashes, logical_command=logical, toolchain=toolchain, synthetic=True)
    run_id = "synthetic-no-job:parent"
    bound = dict(run_id=run_id, profile_sha256=b.sha(b.canonical(profile)), source_sha256=hashes,
                 source_after_sha256=hashes, logical_command=logical, toolchain=toolchain,
                 raw_sha256=b.source_hashes(raw), model_calls=0, attempts=1, exit_code=0, elapsed_seconds=0.0)
    record = dict(command=command, cwd="/SYNTHETIC-NO-PROCESS", model_calls=0, attempts=1,
                  exit_code=0, elapsed_seconds=0.0, timeout=False,
                  artifacts={name: b.sha(raw[name]) for name in ("stdout.txt", "stderr.txt", "resources.txt")})
    artifacts = dict(raw, **{"scope.json": b.canonical(scope), "qualification-gate.json": b.canonical(gate),
                             "profile.json": b.canonical(profile), "bound-record.json": b.canonical(bound),
                             "record.json": b.canonical(record), "tools-before.json": b.canonical(tools),
                             "tools-after.json": b.canonical(tools)})
    native = n.NativeBinding(project=project, stage=1, origin="synthetic-offline", run_id=run_id,
                             source_revision_sha256=b.digest_map(hashes), policy_sha256=b.policy_digest(),
                             artifact_sha256=tuple(sorted(b.source_hashes(artifacts).items())))
    extraction = n.audit_native(native, artifacts, sources, allow_synthetic=True)
    extracted_raw = b.canonical(extraction)
    receipt = dict(schema="repodisco-growth-host-accepted-stage-one-v2", status="accepted", stage=1,
                   project=project, chain_id="synthetic-chain", run_id=run_id, origin="synthetic-offline",
                   source_revision_sha256=native.source_revision_sha256, source_sha256=hashes,
                   policy_sha256=b.policy_digest(), native_binding_sha256=b.sha(b.canonical(asdict(native))),
                   native_extraction_sha256=b.sha(extracted_raw), qualification_gate_sha256=b.sha(artifacts["qualification-gate.json"]),
                   synthetic=True, notice="NOT A NATIVE OR MODEL ACCEPTANCE")
    artifacts.update({"native-units.json": extracted_raw, "accepted.json": b.canonical(receipt)})
    accepted = n.AcceptedParentBinding(native, "synthetic-chain", b.sha(artifacts["accepted.json"]), b.sha(extracted_raw))
    return sources, accepted, artifacts


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.references = {project: n.reference_material(project, REPO) for project in ("dafny-vmc", "vest")}
        _, inventory = b.load_assets()
        cls.upstream = {project: {name: (REPO / "experiments/real-repository-qualification-001/upstream" / project / name).read_bytes()
                                  for name in row["files"]}
                        for project, row in inventory["projects"].items()}
        cls.parents = {project: synthetic_parent(project, cls.upstream[project]) for project in cls.upstream}

    def test_actual_full_references_replay_without_becoming_stage_one_acceptances(self):
        for project, count in (("dafny-vmc", 269), ("vest", 5416)):
            result = n.replay_reference(project, REPO)
            self.assertEqual(len(result["extraction"]["rows"]), count)
            self.assertEqual(result["stage"], 2)
            self.assertFalse(result["eligible_as_accepted_stage_one"])
            self.assertFalse(result["model_generated_growth"])
            self.assertFalse(result["extraction"]["accepted_revision_issued"])

    def test_vest_occurrences_retain_multiplicity_raw_positions_and_actual_success(self):
        native, artifacts, sources, _ = self.references["vest"]
        result = n.audit_native(native, artifacts, sources)
        self.assertEqual(result["distinct_tuple_keys"], 5306)
        self.assertEqual(result["timed_occurrences"], 5416)
        self.assertEqual(result["native_summary_verified_total"], 5727)
        self.assertFalse(result["summary_count_is_timing_count"])
        counts = n.inverse_occurrences(result["rows"])
        self.assertEqual(sum(counts.values()), 5416)
        self.assertEqual(sum(value > 1 for value in counts.values()), 96)
        self.assertEqual(max(counts.values()), 11)
        raw = raw_parts(artifacts)
        decoded_reports = {(item["location"]["stream"], item["location"]["start_byte"], item["location"]["end_byte"]):
                           json.loads(raw[item["location"]["stream"]][item["location"]["start_byte"]:item["location"]["end_byte"]])
                           for item in result["native_reports"]}
        foreign = 0
        for row in result["rows"]:
            loc = row["raw_location"]
            report = decoded_reports[(loc["stream"], loc["start_byte"], loc["end_byte"])]
            original = report["times-ms"]["smt"]["smt-run-module-times"][loc["module_index"]]["function-breakdown"][loc["function_breakdown_index"]]
            self.assertEqual(row["native_record"], original)
            self.assertIs(row["success"], original["success"])
            self.assertEqual(row["identity"][0], result["native_reports"][loc["report_index"]]["crate"])
            self.assertEqual(row["native_record_sha256"], b.sha(b.canonical(original)))
            if original["function"].split("::")[0] != row["identity"][0]:
                foreign += 1
        self.assertEqual(foreign, 26)

    def test_inverse_rejects_duplicate_gap_noncanonical_and_mismatched_occurrences(self):
        native, artifacts, sources, _ = self.references["vest"]
        rows = n.audit_native(native, artifacts, sources)["rows"]
        for mutate in (lambda values: values.append(deepcopy(values[0])),
                       lambda values: values[0].update(unit='["bad"]'),
                       lambda values: values[0].update(ordinal=2),
                       lambda values: values[0].update(success=False),
                       lambda values: values[0].update(unit=json.dumps(json.loads(values[0]["unit"])))):
            changed = deepcopy(rows[:2])
            mutate(changed)
            with self.assertRaises(ValueError):
                n.inverse_occurrences(changed)

    def test_exact_raw_and_metadata_pins_reject_missing_tampered_and_duplicate_artifacts(self):
        for project, (native, artifacts, sources, _) in self.references.items():
            for filename in ("stdout.txt", "profile.json", "bound-record.json", "record.json", "tools-before.json", "qualification-gate.json"):
                changed = dict(artifacts)
                changed[filename] += b"CHANGED"
                with self.subTest(project=project, file=filename), self.assertRaises(ValueError):
                    n.audit_native(native, changed, sources)
            missing = dict(artifacts)
            del missing["stdout.txt"]
            with self.assertRaises(ValueError):
                n.audit_native(native, missing, sources)
            duplicate = replace(native, artifact_sha256=native.artifact_sha256 + (native.artifact_sha256[0],))
            with self.assertRaisesRegex(ValueError, "Duplicate artifact"):
                n.audit_native(duplicate, artifacts, sources)

    def test_stale_run_source_profile_tool_and_command_are_not_relabelled(self):
        native, artifacts, sources, _ = self.references["dafny-vmc"]
        for change in (dict(run_id="stale:run"), dict(stage=1), dict(source_revision_sha256="0" * 64),
                       dict(policy_sha256="0" * 64)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                n.audit_native(replace(native, **change), artifacts, sources)
        for filename, operation in (
            ("profile.json", lambda obj: obj.update(project="vest")),
            ("bound-record.json", lambda obj: obj.update(source_after_sha256={})),
            ("record.json", lambda obj: obj.update(command=["wrong-command"])),
            ("tools-after.json", lambda obj: obj.update(project="vest")),
            ("scope.json", lambda obj: obj.update(required_inventory={"invented-label": 1})),
        ):
            changed_native, changed = mutate_as_synthetic(native, artifacts, lambda data: update_json(data, filename, operation))
            with self.subTest(file=filename), self.assertRaises(ValueError):
                n.audit_native(changed_native, changed, sources, allow_synthetic=True)

    def test_synthetic_mutation_of_repeated_native_key_cannot_silently_deduplicate(self):
        native, artifacts, sources, _ = self.references["vest"]
        original = n.audit_native(native, artifacts, sources)
        repeated = next(key for key, count in original["inventory"].items() if count > 1)
        identity = json.loads(repeated)
        def remove_occurrence(documents):
            for document in documents:
                for module in document["times-ms"]["smt"]["smt-run-module-times"]:
                    for index, record in enumerate(module["function-breakdown"]):
                        if module["module"] == identity[1] and record["function"] == identity[2] and record["mode:"] == identity[3]:
                            del module["function-breakdown"][index]
                            return
            self.fail("Repeated raw record not found")
        changed_native, changed = mutate_as_synthetic(native, artifacts, lambda data: data.update(
            {"stdout.txt": modified_reports(data["stdout.txt"], remove_occurrence)}))
        result = n.audit_native(changed_native, changed, sources, allow_synthetic=True)
        self.assertEqual(result["distinct_tuple_keys"], 5306)
        self.assertEqual(result["timed_occurrences"], 5415)
        self.assertFalse(result["coverage_complete"])
        self.assertFalse(result["qualified_pass"])

    def test_synthetic_duplicate_and_failed_timing_records_are_not_success(self):
        native, artifacts, sources, _ = self.references["vest"]
        for operation in (lambda docs: docs[0]["times-ms"]["smt"]["smt-run-module-times"][0]["function-breakdown"].append(
                deepcopy(docs[0]["times-ms"]["smt"]["smt-run-module-times"][0]["function-breakdown"][0])),
                lambda docs: docs[0]["times-ms"]["smt"]["smt-run-module-times"][0]["function-breakdown"][0].update(success=False)):
            changed_native, changed = mutate_as_synthetic(native, artifacts, lambda data: data.update(
                {"stdout.txt": modified_reports(data["stdout.txt"], operation)}))
            result = n.audit_native(changed_native, changed, sources, allow_synthetic=True)
            self.assertFalse(result["qualified_pass"])

    def test_malformed_missing_duplicate_native_reports_and_csv_fail_closed(self):
        native, artifacts, _, _ = self.references["vest"]
        raw = raw_parts(artifacts)
        parsed, empty = n.extract_native("vest", dict(raw, **{"stdout.txt": b""}), 0)
        self.assertFalse(parsed["proof_pass"])
        self.assertEqual(empty["timed_occurrences"], 0)
        for changed in (b'{"verification-results":', raw["stdout.txt"] + b"\n" + raw["stdout.txt"],
                        b'{"verification-results":{},"verification-results":{}}'):
            data = dict(raw, **{"stdout.txt": changed})
            with self.subTest(size=len(changed)), self.assertRaises(ValueError):
                n.extract_native("vest", data, 0)
        _, artifacts, _, _ = self.references["dafny-vmc"]
        raw = raw_parts(artifacts)
        name = next(key for key in raw if key.endswith(".csv"))
        data = dict(raw)
        data[name] += raw[name].splitlines(keepends=True)[1]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            n.extract_native("dafny-vmc", data, 0)
        data = {key: value for key, value in raw.items() if key != name}
        parsed, extracted = n.extract_native("dafny-vmc", data, 0)
        self.assertFalse(parsed["proof_pass"])
        self.assertEqual(extracted["logged_named_units"], 0)

    def test_eight_revised_source_reconstructions_and_old_namespace_rejection(self):
        for stage in b.RULES:
            for alternate in (False, True):
                raw, audit = b.render_source(stage, replacement(stage, alternate))
                self.assertEqual(raw, fixture(stage, alternate))
                self.assertFalse(audit["semantics_checked"])
        old = (GROWTH / "dafny/fixtures/move-reference/repodisco-growth/MoveToFront.dfy").read_bytes()
        with self.assertRaises(ValueError):
            b.source_body("vmc-move", old)

    def test_trust_bypasses_header_changes_and_unknown_calls_are_rejected(self):
        for stage, bad in (("vmc-move", "assume false; xs"), ("vmc-pair", "var Shift := 0; xs"),
                           ("vmc-move", "} method Escape() {"), ("vest-frame", "admit();"),
                           ("vest-frame", "#[verifier::external_body] fn f() {}"),
                           ("vest-batch", "let f = || false; f();")):
            with self.subTest(body=bad), self.assertRaises(ValueError):
                b.validate_body(stage, bad)
        source = fixture("vmc-move")
        for old, new in ((b"requires k < |xs|", b"requires false"),
                         (b"ensures |ys| == |xs|", b"ensures true"),
                         (b"import Model = FisherYates.Model", b"import Model = Other")):
            with self.subTest(old=old), self.assertRaises(ValueError):
                b.source_body("vmc-move", source.replace(old, new))

    def test_synthetic_parent_fixture_rejected_by_default_but_exercises_both_lineages(self):
        for project, (sources, accepted, artifacts) in self.parents.items():
            child = "vmc-pair" if project == "dafny-vmc" else "vest-batch"
            args = dict(chain_id="synthetic-chain", parent_binding=accepted, parent_artifacts=artifacts)
            with self.assertRaises(ValueError):
                b.reconstruct(child, replacement(child), sources, **args)
            candidate, audit = b.reconstruct(child, replacement(child), sources, allow_synthetic=True, **args)
            first = "vmc-move" if project == "dafny-vmc" else "vest-frame"
            first_path = b.stage_spec(first)[0]["path"]
            self.assertEqual(candidate[first_path], fixture(first, True))
            self.assertNotEqual(candidate[first_path], fixture(first, False))
            self.assertTrue(audit["candidate_unverified"])
            self.assertFalse(audit["native_acceptance_performed"])
            b.audit_candidate(child, candidate, sources, allow_synthetic=True, **args)

    def test_analyst_full_reference_cannot_be_sliced_into_an_accepted_parent(self):
        for project, (native, artifacts, sources, _) in self.references.items():
            fake = n.AcceptedParentBinding(native, "no-acceptance", "0" * 64, "0" * 64)
            child = "vmc-pair" if project == "dafny-vmc" else "vest-batch"
            with self.assertRaisesRegex(ValueError, "full-stage-two reference"):
                n.validate_accepted_parent(child, "no-acceptance", sources, fake, artifacts)
            with self.assertRaisesRegex(ValueError, "Analyst reference/control"):
                n.validate_accepted_parent(child, "no-acceptance", sources,
                    replace(fake, native=replace(native, stage=1)), artifacts)

    def test_stale_or_substituted_actual_parent_and_changed_registration_are_rejected(self):
        for project, (sources, accepted, artifacts) in self.parents.items():
            first, child = ("vmc-move", "vmc-pair") if project == "dafny-vmc" else ("vest-frame", "vest-batch")
            changed = dict(sources)
            changed[b.stage_spec(first)[0]["path"]] = fixture(first, False)
            args = dict(chain_id="synthetic-chain", parent_binding=accepted, parent_artifacts=artifacts, allow_synthetic=True)
            with self.assertRaisesRegex(ValueError, "Actual source revision differs"):
                b.reconstruct(child, replacement(child), changed, **args)
            with self.assertRaises(ValueError):
                b.reconstruct(child, replacement(child), sources, **{**args, "chain_id": "stale-chain"})
            candidate, _ = b.reconstruct(child, replacement(child), sources, **args)
            protected = "vest_dev/src/formats/mod.rs" if project == "vest" else "dfyconfig.toml"
            candidate[protected] += b"\n"
            with self.assertRaises(ValueError):
                b.audit_candidate(child, candidate, sources, **args)

    def test_derived_native_units_require_exact_replay_not_just_an_accepted_flag(self):
        sources, accepted, artifacts = self.parents["dafny-vmc"]
        changed = dict(artifacts)
        extraction = b.read_json(changed["native-units.json"])
        extraction["rows"][0]["status"] = "Failed"
        changed["native-units.json"] = b.canonical(extraction)
        rebound = replace(accepted, extraction_sha256=b.sha(changed["native-units.json"]))
        with self.assertRaisesRegex(ValueError, "does not replay exactly"):
            n.validate_accepted_parent("vmc-pair", "synthetic-chain", sources, rebound, changed, allow_synthetic=True)

    def test_unproved_synthetic_parent_cannot_advance_even_with_accepted_receipt(self):
        sources, accepted, artifacts = self.parents["dafny-vmc"]
        metadata = {key: value for key, value in artifacts.items() if key not in ("accepted.json", "native-units.json")}
        def fail(data):
            data["stdout.txt"] = b"SYNTHETIC TEST ONLY\nDafny program verifier finished with 1 verified, 1 error\n"
            data["csv/synthetic.csv"] = data["csv/synthetic.csv"].replace(b"SYNTHETIC_PARENT (correctness),Passed", b"SYNTHETIC_PARENT (correctness),Failed")
            update_json(data, "record.json", lambda obj: obj.update(exit_code=4))
            update_json(data, "bound-record.json", lambda obj: obj.update(exit_code=4))
        native, changed = mutate_as_synthetic(accepted.native, metadata, fail)
        extraction = n.audit_native(native, changed, sources, allow_synthetic=True)
        self.assertFalse(extraction["qualified_pass"])
        changed["accepted.json"] = artifacts["accepted.json"]
        changed["native-units.json"] = b.canonical(extraction)
        rebound = replace(accepted, native=native, extraction_sha256=b.sha(changed["native-units.json"]))
        with self.assertRaisesRegex(ValueError, "Unproved, incomplete or failed parent"):
            n.validate_accepted_parent("vmc-pair", "synthetic-chain", sources, rebound, changed, allow_synthetic=True)

    def test_stage_one_qualification_must_exist_separately_from_full_reference(self):
        sources, accepted, artifacts = self.parents["dafny-vmc"]
        metadata = {key: value for key, value in artifacts.items() if key not in ("accepted.json", "native-units.json")}
        native, changed = mutate_as_synthetic(accepted.native, metadata, lambda data: update_json(
            data, "scope.json", lambda obj: obj.update(readiness="REFERENCE_ONLY_NOT_STAGE_ONE_ACCEPTANCE")))
        extraction = n.audit_native(native, changed, sources, allow_synthetic=True)
        changed["accepted.json"] = artifacts["accepted.json"]
        changed["native-units.json"] = b.canonical(extraction)
        rebound = replace(accepted, native=native, extraction_sha256=b.sha(changed["native-units.json"]))
        with self.assertRaises(ValueError):
            n.validate_accepted_parent("vmc-pair", "synthetic-chain", sources, rebound, changed, allow_synthetic=True)

    def test_direct_child_body_and_single_json_scope_remain_honest(self):
        sources, accepted, artifacts = self.parents["dafny-vmc"]
        args = dict(chain_id="synthetic-chain", parent_binding=accepted, parent_artifacts=artifacts, allow_synthetic=True)
        text = "[xs[i], xs[j]] + xs[..i] + xs[i+1..j] + xs[j+1..]"
        _, audit = b.parse_response(json.dumps({"replacement": text}), "vmc-pair", sources, **args)
        self.assertEqual(audit["body"]["parent_api_calls"], [])
        self.assertFalse(audit["body"]["parent_call_required"])
        for raw in ('{"replacement":"xs","accepted":true}', '{"replacement":"xs","replacement":"xs"}',
                    '{"replacement":"xs"} {"replacement":"xs"}'):
            with self.assertRaises(ValueError):
                b.parse_response(raw, "vmc-pair", sources, **args)


if __name__ == "__main__":
    unittest.main(verbosity=2)
