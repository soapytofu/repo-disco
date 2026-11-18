"""New integration branches only; no native process, network or model calls."""
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import integration as p
from test_fixtures import synthetic_parent, repin

b, n = p.b, p.n


class ActualControlIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.replays = {}
        cls.summaries = []
        for project, item in p._catalog()["projects"].items():
            for case in item["cases"]:
                result = p.replay_control(project, case["id"])
                ex = result["extraction"]
                summary = dict(project=project, case=case["id"], stage=case["stage"],
                    category=ex["native_category"], qualified_pass=ex["qualified_pass"],
                    native_proof_pass=ex["native_proof_pass"], native_exit_code=ex["native_exit_code"],
                    coverage_complete=ex["coverage_complete"], named_new_outcomes=result["named_new_outcomes"],
                    missing_required=result["missing_required"], unproved_parent=result["unproved_parent_observation"],
                    inventory_keys=len(ex["inventory"]), occurrences=len(ex["rows"]),
                    failed_occurrences=sum(x["status"] == "Failed" for x in ex["rows"]),
                    full_extraction_sha256=b.sha(b.canonical(ex)), source_revision_sha256=ex["source_revision_sha256"],
                    raw_sha256=ex["raw_sha256"], native_summary=ex.get("native_summary", ex.get("native_summary_verified_total")),
                    warning_review=ex["warning_review"], native_command_sha256=ex["native_command_sha256"],
                    toolchain_sha256=ex["toolchain_sha256"], native_execution=ex["native_execution"],
                    eligible_as_accepted_stage_one=False,
                    reviewed_input_sha256=result["provenance"]["reviewed_input_sha256"])
                cls.summaries.append(summary)
                if case["id"] in ("frame-reference", "move-reference"):
                    cls.replays[project] = result
        if log := os.environ.get("GROWTH_INTEGRATION_REPLAY_LOG"):
            Path(log).write_text(json.dumps(dict(schema="repodisco-control-adapter-replays-v3", model_calls=0,
                native_calls=0, source_observations="23 existing analyst verifier controls replayed, not new trials",
                root_gate_sha256=p.ROOT_GATE_SHA256, policy_sha256=b.policy_digest(),
                results=cls.summaries), sort_keys=True, indent=2) + "\n")

    def test_actual_twenty_three_cases_match_reviewed_full_inventory(self):
        self.assertEqual(len(self.summaries), 23)
        for project, expected in (("dafny-vmc", (11, 3, 7, 1)), ("vest", (12, 3, 7, 2))):
            rows = [x for x in self.summaries if x["project"] == project]
            self.assertEqual((len(rows), sum(x["qualified_pass"] for x in rows),
                sum(x["category"] == "PROOF_FAILURE" for x in rows),
                sum(x["native_proof_pass"] and not x["coverage_complete"] for x in rows)), expected)
            self.assertTrue(all(not x["eligible_as_accepted_stage_one"] for x in rows))

    def test_actual_stage_one_scope_is_not_filtered_stage_two_evidence(self):
        for project, count, keys in (("dafny-vmc", 268, 268), ("vest", 5411, 5301)):
            ex = self.replays[project]["extraction"]
            scope = p.stage_one_scope(project)
            self.assertEqual(len(ex["rows"]), count)
            self.assertEqual(len(ex["inventory"]), keys)
            self.assertEqual(ex["inventory"], scope["required_inventory"])
            self.assertEqual(ex["stage"], 1)
            self.assertFalse(scope["model_origin_acceptance"])
        self.assertEqual(self.replays["vest"]["extraction"]["native_summary_verified_total"], 5722)

    def test_actual_failed_helpers_cannot_hide_behind_passing_children(self):
        for project, case in (("dafny-vmc", "pair-with-unproved-parent"), ("vest", "batch-unproved-frame")):
            row = next(x for x in self.summaries if x["project"] == project and x["case"] == case)
            self.assertEqual(row["unproved_parent"]["parent_outcome"], ["Failed"])
            self.assertEqual(row["unproved_parent"]["child_outcome"], ["Passed"])
            self.assertFalse(row["qualified_pass"])

    def test_actual_omissions_native_pass_but_fail_workspace_coverage(self):
        rows = [x for x in self.summaries if x["case"] in ("detached-omitted", "frame-omitted", "batch-omitted")]
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row["native_exit_code"], 0)
            self.assertTrue(row["native_proof_pass"])
            self.assertFalse(row["qualified_pass"])
            self.assertTrue(row["missing_required"])

    def test_actual_verus_multiplicities_success_and_owning_crate_are_lossless(self):
        ex = self.replays["vest"]["extraction"]
        self.assertEqual(n.inverse_occurrences(ex["rows"]), ex["inventory"])
        self.assertEqual(sum(v > 1 for v in ex["inventory"].values()), 96)
        self.assertEqual(max(ex["inventory"].values()), 11)
        foreign = [r for r in ex["rows"] if r["identity"][2].split("::")[0] in ("alloc", "core", "std", "verus_builtin")]
        self.assertEqual(len(foreign), 26)
        self.assertTrue(all(r["identity"][0] in ("vstd", "vest_lib") for r in foreign))
        for row in ex["rows"]:
            self.assertEqual(row["success"], row["native_record"]["success"])
            self.assertEqual(b.sha(b.canonical(row["native_record"])), row["native_record_sha256"])

    def test_actual_stage_one_duplicate_or_missing_occurrence_cannot_be_deduplicated(self):
        rows = self.replays["vest"]["extraction"]["rows"]
        repeated = next(r for r in rows if r["ordinal"] == 2)
        first = next(r for r in rows if r["identity"] == repeated["identity"] and r["ordinal"] == 1)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            n.inverse_occurrences(rows + [first])
        with self.assertRaisesRegex(ValueError, "gaps"):
            n.inverse_occurrences([r for r in rows if r is not first])

    def test_tampered_missing_duplicate_and_stale_actual_binding_rejected(self):
        native, artifacts, sources, prov = p.control_material("dafny-vmc", "move-reference")
        for key in ("record.json", "bound-record.json", "stdout.txt"):
            bad = dict(artifacts); bad[key] += b" "
            with self.assertRaises(ValueError): n.audit_native(native, bad, sources, analyst_source_sha256=prov["source_sha256"])
        bad = dict(artifacts); del bad["resources.txt"]
        with self.assertRaises(ValueError): n.audit_native(native, bad, sources)
        duplicate = replace(native, artifact_sha256=native.artifact_sha256 + (native.artifact_sha256[0],))
        with self.assertRaises(ValueError): n.audit_native(duplicate, artifacts, sources)
        with self.assertRaises(ValueError): n.audit_native(replace(native, run_id="stale-run"), artifacts, sources)

    def test_all_actual_controls_reject_model_origin_relabeling_and_run_rename(self):
        for project, item in p._catalog()["projects"].items():
            for case in item["cases"]:
                root = p.DEFAULT_REPO / case["root"]
                artifacts = {"bound-record.json": (root / "bound-record.json").read_bytes(),
                             "record.json": (root / "native/record.json").read_bytes()}
                bound = b.read_json(artifacts["bound-record.json"])
                relabeled = p.NativeBinding(project, 1, "model-candidate", bound["run_id"],
                                            b.digest_map(bound["source_sha256"]), b.policy_digest(), ())
                with self.assertRaisesRegex(ValueError, "Known analyst"):
                    p._reject_known_analyst(relabeled, artifacts)
                changed = dict(artifacts)
                bound = b.read_json(changed["bound-record.json"]); bound["run_id"] = "fresh-label-only"
                changed["bound-record.json"] = b.canonical(bound)
                record = b.read_json(changed["record.json"]); record["new_label"] = "does-not-change-raw-evidence"
                changed["record.json"] = b.canonical(record)
                relabeled = repin(relabeled, changed, run_id="fresh-label-only")
                with self.assertRaisesRegex(ValueError, "Known analyst"):
                    p._reject_known_analyst(relabeled, changed)

    def test_full_reference_native_identity_cannot_be_relabelled_as_stage_one(self):
        for project in p.STAGES:
            native, artifacts, _, _ = n.reference_material(project, p.DEFAULT_REPO)
            with self.assertRaisesRegex(ValueError, "Known analyst"):
                p._reject_known_analyst(replace(native, stage=1, origin="model-candidate"), artifacts)

    def test_actual_control_source_exception_cannot_admit_model_candidate(self):
        native, artifacts, sources, prov = p.control_material("dafny-vmc", "detached-omitted")
        with self.assertRaisesRegex(ValueError, "Exact control exception"):
            n.audit_native(replace(native, origin="model-candidate"), artifacts, sources,
                           analyst_source_sha256=prov["source_sha256"])
        with self.assertRaises(ValueError): b.check_workspace("dafny-vmc", 2, sources)


class ProspectiveParentBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = {project: synthetic_parent(project) for project in p.STAGES}

    def test_synthetic_positive_branch_rejected_by_default_both_projects(self):
        for project, (binding, artifacts, sources) in self.fixtures.items():
            child = p.STAGES[project][1]
            with self.assertRaises(ValueError): p.validate_accepted_parent(child, "synthetic-lineage", sources, binding, artifacts)
            audit = p.validate_accepted_parent(child, "synthetic-lineage", sources, binding, artifacts, allow_synthetic=True)
            self.assertTrue(audit["synthetic_fixture"])
            self.assertFalse(audit["acceptance_created_here"])

    def test_synthetic_origin_relabel_does_not_create_model_evidence(self):
        binding, artifacts, sources = self.fixtures["dafny-vmc"]
        metadata = {k: v for k, v in artifacts.items() if k not in ("accepted.json", "native-units.json")}
        relabeled = replace(binding.native, origin="model-candidate")
        for opt in (False, True):
            with self.assertRaisesRegex(ValueError, "Marked synthetic"):
                p.audit_model_parent_native(relabeled, metadata, sources, allow_synthetic=opt)

    def test_nonidentical_actual_parent_survives_reconstruction_unchanged(self):
        for project, (binding, artifacts, sources) in self.fixtures.items():
            child = p.STAGES[project][1]
            parent_path = b.stage_spec(p.STAGES[project][0])[0]["path"]
            _, _, reference, _ = p.control_material(project, "move-reference" if project == "dafny-vmc" else "frame-reference")
            self.assertNotEqual(sources[parent_path], reference[parent_path])
            body = "[xs[i], xs[j]] + xs[..i] + xs[i+1..j] + xs[j+1..]" if project == "dafny-vmc" else ""
            candidate, audit = b.reconstruct(child, body, sources, chain_id="synthetic-lineage",
                parent_binding=binding, parent_artifacts=artifacts, allow_synthetic=True)
            self.assertEqual(candidate[parent_path], sources[parent_path])
            self.assertTrue(audit["candidate_unverified"])
            self.assertFalse(audit["native_acceptance_performed"])
            self.assertEqual(b.audit_candidate(child, candidate, sources, chain_id="synthetic-lineage",
                parent_binding=binding, parent_artifacts=artifacts, allow_synthetic=True)["candidate_revision_sha256"],
                audit["candidate_revision_sha256"])

    def test_reference_body_not_blacklisted_when_observation_is_separately_synthetic(self):
        _, _, ref, _ = p.control_material("dafny-vmc", "move-reference")
        body = b.source_body("vmc-move", ref[b.stage_spec("vmc-move")[0]["path"]])
        binding, artifacts, sources = synthetic_parent(body=body, chain_id="synthetic-reference-same-body")
        self.assertEqual(sources, ref)
        audit = p.validate_accepted_parent("vmc-pair", binding.chain_id, sources, binding, artifacts, allow_synthetic=True)
        self.assertTrue(audit["synthetic_fixture"])
        with self.assertRaises(ValueError): p.validate_accepted_parent("vmc-pair", binding.chain_id, sources, binding, artifacts)

    def test_failed_parent_missing_receipt_wrong_chain_stale_source_and_reference_substitution(self):
        failed, f_artifacts, f_sources = synthetic_parent(failed=True, chain_id="synthetic-failed")
        with self.assertRaisesRegex(ValueError, "Failed, incomplete"):
            p.validate_accepted_parent("vmc-pair", failed.chain_id, f_sources, failed, f_artifacts, allow_synthetic=True)
        binding, artifacts, sources = self.fixtures["dafny-vmc"]
        for missing in ("accepted.json", "native-units.json", "record.json"):
            incomplete = dict(artifacts); del incomplete[missing]
            with self.assertRaises((ValueError, KeyError)):
                p.validate_accepted_parent("vmc-pair", binding.chain_id, sources, binding, incomplete, allow_synthetic=True)
        with self.assertRaisesRegex(ValueError, "lineage"):
            p.validate_accepted_parent("vmc-pair", "another-lineage", sources, binding, artifacts, allow_synthetic=True)
        _, _, ref, _ = p.control_material("dafny-vmc", "move-reference")
        with self.assertRaises(ValueError):
            p.validate_accepted_parent("vmc-pair", binding.chain_id, ref, binding, artifacts, allow_synthetic=True)

    def test_exact_reviewed_scope_gate_resources_tool_and_inventory_are_required(self):
        binding, artifacts, sources = self.fixtures["dafny-vmc"]
        metadata = {k: v for k, v in artifacts.items() if k not in ("accepted.json", "native-units.json")}
        for name, mutate in (
            ("qualification-gate.json", lambda d: d.update(negative_controls_reviewed=False)),
            ("scope.json", lambda d: d["required_inventory"].pop(next(iter(d["required_inventory"])))),
            ("record.json", lambda d: d["command"].extend(["--no-verify"])),
            ("profile.json", lambda d: d["resources"].update(cpus=8)),
            ("tools-before.json", lambda d: d.update(image_sha256="0" * 64)),
        ):
            bad = dict(metadata); item = b.read_json(bad[name]); mutate(item); bad[name] = b.canonical(item)
            with self.assertRaises(ValueError):
                p.audit_model_parent_native(repin(binding.native, bad), bad, sources, allow_synthetic=True)

    def test_actual_analyst_labels_and_changed_body_contract_registration_cannot_advance(self):
        for project, (binding, artifacts, sources) in self.fixtures.items():
            child = p.STAGES[project][1]
            for origin in ("analyst-control", "analyst-reference"):
                altered = replace(binding, native=replace(binding.native, origin=origin))
                with self.assertRaises(ValueError):
                    p.validate_accepted_parent(child, binding.chain_id, sources, altered, artifacts, allow_synthetic=True)
            changed = dict(sources)
            stage = b.stage_spec(p.STAGES[project][0])[0]
            changed[stage["path"]] = changed[stage["path"]].replace(b"ensures", b"requires", 1)
            with self.assertRaises(ValueError): b.check_workspace(project, 1, changed)
            if project == "vest":
                changed = dict(sources); changed["vest_dev/src/formats/mod.rs"] += b"pub mod unexpected;\n"
                with self.assertRaises(ValueError): b.check_workspace(project, 1, changed)

    def test_direct_child_without_helper_call_remains_unverified_syntax_candidate(self):
        binding, artifacts, sources = self.fixtures["dafny-vmc"]
        candidate, audit = b.reconstruct("vmc-pair", "[xs[i], xs[j]] + xs[..i] + xs[i+1..j] + xs[j+1..]", sources,
            chain_id=binding.chain_id, parent_binding=binding, parent_artifacts=artifacts, allow_synthetic=True)
        body = b.source_body("vmc-pair", candidate[b.stage_spec("vmc-pair")[0]["path"]])
        self.assertNotIn("Shift.MoveToFront", body)
        self.assertTrue(audit["candidate_unverified"])
        for illegal in ("assume false; xs", "xs } lemma Escape() {", "{:(verify) false} xs"):
            with self.assertRaises(ValueError): b.render_source("vmc-pair", illegal)


class ForwardingEntryPoint(unittest.TestCase):
    def test_both_public_parent_entry_points_reach_actual_scope_and_provenance_gate(self):
        binding, artifacts, sources = synthetic_parent()
        for entry in (p.validate_accepted_parent, n.validate_accepted_parent):
            with self.assertRaises(ValueError):
                entry("vmc-pair", binding.chain_id, sources, binding, artifacts)
            result = entry("vmc-pair", binding.chain_id, sources, binding, artifacts, allow_synthetic=True)
            self.assertTrue(result["known_analyst_native_reuse_rejected"] if "known_analyst_native_reuse_rejected" in result
                            else result["evidence_replayed"])
            self.assertEqual(result["host_scope_sha256"], b.sha(b.canonical(p.stage_one_scope("dafny-vmc"))))
            self.assertTrue(result["synthetic_fixture"])
        with patch.object(p, "validate_accepted_parent", wraps=p.validate_accepted_parent) as forward:
            with self.assertRaises(ValueError):
                n.validate_accepted_parent("vmc-pair", binding.chain_id, sources, binding, artifacts)
            self.assertEqual(forward.call_count, 1)
            self.assertIs(forward.call_args.kwargs["allow_synthetic"], False)
        native, metadata, actual_sources, _ = p.control_material("dafny-vmc", "move-reference")
        known = p.AcceptedParentBinding(replace(native, origin="model-candidate"), "actual-analyst",
                                        b.sha(b"{}"), b.sha(b"{}"))
        labeled = {**metadata, "accepted.json": b"{}", "native-units.json": b"{}"}
        for entry in (p.validate_accepted_parent, n.validate_accepted_parent):
            with self.assertRaisesRegex(ValueError, "Known analyst"):
                entry("vmc-pair", known.chain_id, actual_sources, known, labeled)


if __name__ == "__main__":
    unittest.main(verbosity=2)
