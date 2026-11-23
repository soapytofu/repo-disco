"""Source/control consistency checks, not Dafny verification or model tests."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import tempfile
import unittest

import build as b


class ConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent
        cls.cases = json.loads((cls.root / "cases.json").read_bytes())
        cls.by_id = {entry["id"]: entry for entry in cls.cases}

    def test_exact_release_blob_identity_and_dependency_closure(self):
        old = b.upstream_sources(self.root)
        self.assertEqual(set(old), set(b.BASE_FILES))
        imports = {}
        for path, raw in old.items():
            text = raw.decode()
            imports[Path(path).stem] = re.findall(r"^\s*import opened (\w+)\s*$", text, re.M)
            self.assertFalse(re.search(r"^\s*include\s", text, re.M))
        self.assertEqual(imports, dict(BoundedInts=[], Wrappers=[], DynamicArray=["BoundedInts", "Wrappers"]))
        for entry in self.cases:
            for name, raw in old.items():
                self.assertEqual((self.root / entry["workspace_dir"] / name).read_bytes(), raw)

    def test_deterministic_construction_and_exact_source_manifests(self):
        material = b.material(self.root)
        self.assertEqual(len(self.cases), 12)
        self.assertEqual(len(self.by_id), 12)
        for name, raw in material.items():
            self.assertEqual((self.root / name).read_bytes(), raw)
        for entry in self.cases:
            folder = self.root / entry["workspace_dir"]
            actual = {p.relative_to(folder).as_posix(): b.sha(p.read_bytes()) for p in folder.rglob("*") if p.is_file()}
            self.assertEqual(actual, entry["source_sha256"])

    def test_only_replacement_bodies_differ_contracts_types_and_frames_are_fixed(self):
        for entry in self.cases:
            for path, name in ((b.APPEND, "AppendAll.dfy"), (b.ROTATE, "AppendRotated.dfy")):
                if path not in entry["source_sha256"]:
                    continue
                before, after = b.fixed_parts(name, self.root)
                source = (self.root / entry["workspace_dir"] / path).read_text()
                self.assertTrue(source.startswith(before))
                self.assertTrue(source.endswith(after))
                body = source[len(before):len(source) - len(after)]
                self.assertNotIn(b.BEGIN, body)
                self.assertNotIn(b.END, body)
                self.assertNotRegex(body, r"(?m)^\s*(?:requires|ensures|reads|modifies)\b")
                self.assertNotRegex(body, r"\ba\.(?:items|Repr|size|capacity|data)\s*:=")

    def test_no_new_verification_or_termination_bypasses(self):
        forbidden = r"\bassume\b|\bexpect\b|\baxiom\b|\bdecreases\s+\*|\{:\s*(?:verify|extern|axiom|options)\b"
        for file in (self.root / "cases").rglob("*.dfy"):
            self.assertNotRegex(file.read_text(), forbidden)
        for source in (self.root / "bodies").glob("*.txt"):
            self.assertNotIn("a.data", source.read_text())

    def test_parent_is_byte_identical_and_unproved_parent_is_never_a_pass(self):
        reference = self.by_id["append-reference"]["source_sha256"][b.APPEND]
        for entry in self.cases:
            if entry["stage"] == 2 and entry["id"] != "rotate-unproved-append":
                self.assertEqual(entry["source_sha256"][b.APPEND], reference)
        unproved = self.by_id["rotate-unproved-append"]
        self.assertEqual(unproved["source_sha256"][b.APPEND], self.by_id["append-empty"]["source_sha256"][b.APPEND])
        self.assertEqual(unproved["expected_failed_targets"], [b.APPEND_TARGET])
        self.assertEqual(unproved["expected_passed_targets"], [b.ROTATE_TARGET])
        self.assertEqual(unproved["expected_category"], "PROOF_FAILURE")
        self.assertEqual(unproved["source_sha256"][b.ROTATE], self.by_id["rotate-reference"]["source_sha256"][b.ROTATE])

    def test_omissions_are_staged_but_not_passed_as_checked(self):
        for ident, target, path in (("append-omitted", b.APPEND_TARGET, b.APPEND),
                                   ("rotate-omitted", b.ROTATE_TARGET, b.ROTATE)):
            entry = self.by_id[ident]
            self.assertIn(path, entry["source_sha256"])
            self.assertIn(path, entry["declared_scope_files"])
            self.assertNotIn(path, entry["command_files"])
            self.assertIn(target, entry["required_targets"])
            self.assertEqual(entry["omitted_targets"], [target])
            self.assertEqual(entry["expected_native_category"], "PROOF_PASS")
            self.assertEqual(entry["expected_category"], "COVERAGE_OMISSION")
        for entry in self.cases:
            self.assertTrue(set(b.BASE_FILES) <= set(entry["command_files"]))

    def test_executable_algorithms_cover_empty_boundaries_and_wrong_behavior_examples(self):
        # These finite Python sequence checks validate the design oracle and
        # counterexamples only. They are not a translation/compiler/native proof.
        for length in range(5):
            for values in itertools.product((0, 1), repeat=length):
                for initial in ([], [8, 9]):
                    for pivot in range(length + 1):
                        expected = initial + list(values[pivot:]) + list(values[:pivot])
                        through_parent = list(initial)
                        through_parent.extend(values[pivot:]); through_parent.extend(values[:pivot])
                        direct = list(initial)
                        for value in values[pivot:] + values[:pivot]: direct.append(value)
                        self.assertEqual(through_parent, expected)
                        self.assertEqual(direct, expected)
                        self.assertEqual(len(expected) - len(initial), length)
        design = json.loads((self.root / "design.json").read_bytes())
        for row in design["deliberate_counterexamples"].values():
            self.assertNotEqual(row["expected"], row["wrong"])
        self.assertEqual([9] + list(reversed([1, 2])), design["deliberate_counterexamples"]["append-reverse"]["wrong"])
        self.assertEqual([9] + [1, 2, 3], design["deliberate_counterexamples"]["rotate-original-order"]["wrong"])

    def test_reuse_is_observed_and_drafts_do_not_issue_acceptance_or_native_claims(self):
        reference = (self.root / "bodies/rotate-reference.txt").read_text()
        direct = (self.root / "bodies/rotate-direct.txt").read_text()
        self.assertEqual(reference.count("Append.AppendAll("), 2)
        self.assertNotIn("Append.AppendAll(", direct)
        self.assertIn("a.Push(", direct)
        for entry in self.cases:
            self.assertFalse(entry["model_acceptance"])
            self.assertTrue(entry["analyst_authored"])
            self.assertEqual(entry["native_status"], "UNKNOWN")
            self.assertIsNone(entry["actual_native_unit_labels"])
        design = json.loads((self.root / "design.json").read_bytes())
        self.assertFalse(design["model_execution_authorized"])
        self.assertFalse(design["toolchain"]["default_standard_library_bundle_allowed"])


if __name__ == "__main__":
    unittest.main()
