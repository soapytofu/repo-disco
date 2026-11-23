"""Fixture integrity checks only; no Dafny parsing, verification or model calls."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PRIOR = REPO / "experiments/dafny-real-library-growth-001"
sys.path.insert(0, str(PRIOR / "common"))
import guard
import build


def load(path):
    return json.loads(path.read_bytes())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sources(case):
    root = HERE / case["workspace_dir"]
    return {p.relative_to(root).as_posix():p.read_bytes() for p in sorted(root.rglob("*.dfy"))}


def body(case, source_map):
    profile = load(HERE / case["edit_profile_path"])
    addition = profile["addition"]
    return source_map[addition["path"]].decode().split(addition["begin_marker"], 1)[1].split(addition["end_marker"], 1)[0]


class ConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load(HERE / "cases.json")
        cls.by_id = {case["id"]:case for case in cls.cases}
        cls.origins = load(HERE / "origin-pins.json")

    def test_manifest_and_imported_guard_origins(self):
        manifest = load(HERE / "manifest.json")
        for name, expected in manifest["files"].items():
            self.assertEqual(sha((HERE / name).read_bytes()), expected, name)
        for name, expected in self.origins["guard_dependency_pins"].items():
            self.assertEqual(sha((REPO / name).read_bytes()), expected, name)
        self.assertEqual(Path(guard.__file__).resolve(), PRIOR / "common/guard.py")
        self.assertFalse(manifest["mathematical_qualification"])

    def test_original_failure_evidence_and_fixture_are_unchanged(self):
        revision = load(HERE / "revision.json")
        self.assertEqual(revision["prior_manifest_sha256"], build.ORIGINAL_MANIFEST_SHA)
        for name, expected in revision["preserved_input_pins"].items():
            self.assertEqual(sha((REPO / name).read_bytes()), expected, name)
        old_manifest = load(build.ORIGINAL / "manifest.json")
        for name, expected in old_manifest["files"].items():
            self.assertEqual(sha((build.ORIGINAL / name).read_bytes()), expected, name)
        self.assertEqual([entry["diagnostic_count"] for entry in revision["failed_observations"]], [1])
        for entry in revision["failed_observations"]:
            self.assertEqual(entry["exit_code"], 4)
            self.assertEqual(entry["status"], "PRESERVED_NATIVE_PROOF_FAILURE")
        self.assertEqual(revision["revised_splice_native_status"], "UNKNOWN")
        self.assertEqual(revision["new_native_reference_ids"], ["splice-reference"])
        self.assertEqual(revision["reused_native_reference_ids"], ["filter-reference"])
        reuse, = revision["reused_observations"]
        self.assertEqual(reuse["diagnostic_count"], 0)
        self.assertEqual(reuse["exit_code"], 0)
        self.assertEqual(reuse["status"], "REUSED_SOURCE_IDENTICAL_REFERENCE_PASS")
        self.assertFalse(reuse["model_acceptance"])
        self.assertFalse(reuse["new_independent_observation"])

    def test_all_protected_headers_and_semantics_match_revision_three(self):
        for task in build.TASKS.values():
            name = "templates/" + task["template"]
            old = (build.ORIGINAL / name).read_text()
            revised = (HERE / name).read_text()
            self.assertEqual(revised, old)
        self.assertEqual((HERE / "header-diff.patch").read_bytes(), b"")
        self.assertTrue((HERE / "body-diff.patch").read_bytes())
        for name in ("filter-alternative", "splice-alternative"):
            relative = "bodies/" + name + ".txt"
            self.assertEqual((HERE / relative).read_bytes(), (build.ORIGINAL / relative).read_bytes())
        for case in self.cases:
            old_case = next(item for item in load(build.ORIGINAL / "cases.json") if item["id"] == case["id"])
            self.assertEqual(case["argv"], old_case["argv"])
            self.assertEqual(case["expected_category"], old_case["expected_category"])
            self.assertEqual(case["declared_scope_files"], old_case["declared_scope_files"])

    def test_filter_cases_and_reference_reuse_are_byte_identical(self):
        old_cases = {item["id"]:item for item in load(build.ORIGINAL / "cases.json")}
        for case in self.cases:
            if case["project"] != "stdlib-filter":
                continue
            self.assertEqual(case, old_cases[case["id"]])
            for name, raw in sources(case).items():
                self.assertEqual(raw, (build.ORIGINAL / case["workspace_dir"] / name).read_bytes())
        self.assertEqual((HERE / "bodies/filter-reference.txt").read_bytes(),
                         (build.ORIGINAL / "bodies/filter-reference.txt").read_bytes())
        reuse, = load(HERE / "revision.json")["reused_observations"]
        self.assertEqual(reuse["source_sha256"], self.by_id["filter-reference"]["source_sha256"])

    def test_exact_upstream_and_real_accepted_seed_base(self):
        for name, entry in self.origins["sources"].items():
            raw = (HERE / "base" / name).read_bytes()
            self.assertEqual(sha(raw), entry["sha256"])
            self.assertEqual(raw, (REPO / entry["path"]).read_bytes())
        for name, expected in self.origins["evidence_pins"].items():
            self.assertEqual(sha((REPO / name).read_bytes()), expected)
        self.assertEqual(self.origins["accepted_seed"]["slot_id"], "slot-01")
        self.assertEqual(self.origins["accepted_seed"]["request_id"], "08525845-0393-41c3-bcfd-0a75a3be8e7e")

    def test_case_hashes_exact_sources_and_source_order(self):
        for case in self.cases:
            got = sources(case)
            self.assertEqual({name:sha(raw) for name,raw in got.items()}, case["source_sha256"])
            self.assertEqual(set(got), set(case["declared_scope_files"]))
            self.assertEqual(case["argv"][-len(case["command_files"]):], case["command_files"])
            self.assertEqual(case["command_files"], [p for p in case["declared_scope_files"] if p not in case["omit_from_command"]])
            self.assertEqual(case["argv"][case["argv"].index("--cores") + 1], "1")

    def test_every_ordinary_case_reconstructs_exactly_under_body_guard(self):
        for case in self.cases:
            if not case["protected_source_candidate"]:
                continue
            got = sources(case)
            profile = load(HERE / case["edit_profile_path"])
            candidate_body = body(case, got)
            base = {name:got[name] for name in profile["base_source_sha256"]}
            reconstructed, receipt = guard.reconstruct(profile, candidate_body, base, "offline-construction")
            self.assertEqual(reconstructed, got, case["id"])
            self.assertEqual(sha(candidate_body.encode()), case["body_sha256"])
            self.assertIsNone(receipt["parent"])
            self.assertFalse(receipt["acceptance_issued"])

    def test_unproved_seed_is_narrow_native_only_control(self):
        case = self.by_id["splice-unproved-seed"]
        reference = sources(self.by_id["splice-reference"])
        changed = sources(case)
        differences = [name for name in reference if reference[name] != changed[name]]
        self.assertEqual(differences, [build.APPEND])
        for text in (reference[build.APPEND], changed[build.APPEND]):
            self.assertEqual(text.split(build.BEGIN.encode())[0], reference[build.APPEND].split(build.BEGIN.encode())[0])
            self.assertEqual(text.split(build.END.encode())[1], reference[build.APPEND].split(build.END.encode())[1])
        profile = load(HERE / case["edit_profile_path"])
        base = {name:changed[name] for name in profile["base_source_sha256"]}
        with self.assertRaisesRegex(guard.EvidenceError, "source identity"):
            guard.reconstruct(profile, body(case, changed), base, "offline-construction")
        self.assertEqual(case["expected_failed_targets"], ["RepoDiscoStdAppend.AppendAll"])
        self.assertEqual(case["inspect_targets"], ["RepoDiscoSplice.Splice"])

    def test_omissions_preserve_exact_failing_sources(self):
        for prefix in ("filter", "splice"):
            omitted, empty = self.by_id[prefix + "-omitted"], self.by_id[prefix + "-empty"]
            self.assertEqual(sources(omitted), sources(empty))
            self.assertEqual(omitted["expected_category"], "COVERAGE_OMISSION")
            self.assertEqual(omitted["expected_native_category"], "PROOF_PASS")
            self.assertEqual(len(omitted["omit_from_command"]), 1)
            self.assertNotEqual(omitted["command_files"], omitted["declared_scope_files"])

    def test_independent_profiles_protect_contracts_helpers_and_old_seed(self):
        for task in build.TASKS:
            profile = load(HERE / "profiles" / (task + ".json"))
            self.assertEqual(profile["stage"], 1)
            self.assertIsNone(profile["parent_requirement"])
            self.assertEqual(profile["registrations"], {})
            self.assertEqual(profile["project"], task)
            template = profile["addition"]["template_utf8"]
            self.assertIn("requires a.size == |a.items|", template)
            self.assertIn("ensures fresh(a.Repr - old(a.Repr))", template)
            self.assertIn("    reads *\n    modifies a, a.Repr\n", template)
            self.assertNotIn("capacity", template)
            self.assertEqual(template.split(build.BEGIN, 1)[1].split(build.END, 1)[0], "")
        splice = load(HERE / "profiles/stdlib-splice.json")
        self.assertEqual(splice["base_source_sha256"][build.APPEND], build.EXPECTED[build.APPEND])
        self.assertIn("function KeepBelow", load(HERE / "profiles/stdlib-filter.json")["addition"]["template_utf8"])

    def test_exact_mutation_intent_and_algorithmically_distinct_alternatives(self):
        f = (HERE / "bodies/filter-reference.txt").read_text()
        s = (HERE / "bodies/splice-reference.txt").read_text()
        self.assertEqual(body(self.by_id["filter-inclusive-threshold"], sources(self.by_id["filter-inclusive-threshold"])),
                         f.replace("      if value < limit {", "      if value <= limit {", 1))
        self.assertEqual(body(self.by_id["splice-missing-growth-call"], sources(self.by_id["splice-missing-growth-call"])),
                         s.replace("      Append.AppendAll(a, replacement[..growth]);\n", "", 1))
        self.assertIn("removed := StableFilterBelow(a, limit);", (HERE / "bodies/filter-alternative.txt").read_text())
        self.assertIn("var snapshot: seq<T> := [];", (HERE / "bodies/splice-alternative.txt").read_text())
        self.assertIn("while remaining > 0", s)
        self.assertIn("while done < suffixCount", s)

    def test_no_native_claims_and_positive_gate_precedes_controls(self):
        self.assertEqual(len(self.cases), 17)
        counts = {kind:sum(case["expected_category"] == kind for case in self.cases)
                  for kind in ("PROOF_PASS", "PROOF_FAILURE", "COVERAGE_OMISSION")}
        self.assertEqual(counts, {"PROOF_PASS":4, "PROOF_FAILURE":11, "COVERAGE_OMISSION":2})
        self.assertEqual([case["id"] for case in self.cases if not case["gated_until_positive_review"]],
                         ["filter-reference", "splice-reference"])
        for case in self.cases:
            self.assertEqual(case["native_status"], "UNKNOWN")
            self.assertIsNone(case["actual_native_unit_labels"])
            self.assertFalse(case["native_dispatch_authorized"])
            self.assertFalse(case["model_acceptance"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
