"""Offline regression checks; all accepted-parent fixtures are synthetic.

No test invokes a native verifier, model, socket, Git or accepted-revision writer.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import policy as p

ROOT = Path(__file__).resolve().parent
GROWTH = ROOT.parent
REPO = ROOT.parents[2]
UPSTREAM = REPO / "experiments/real-repository-qualification-001/upstream"


def fixture_source(stage, alternative=False):
    suffix = "alternative" if alternative else "reference"
    paths = {
        "vmc-move": GROWTH / f"dafny/fixtures/move-{suffix}/repodisco-growth/MoveToFront.dfy",
        "vmc-pair": GROWTH / f"dafny/fixtures/pair-{suffix}/repodisco-growth/PickPair.dfy",
        "vest-frame": GROWTH / f"vest/cases/frame-{suffix}/vest_dev/src/formats/growth_frame.rs",
        "vest-batch": GROWTH / f"vest/cases/batch-{suffix}/vest_dev/src/formats/growth_batch.rs",
    }
    return paths[stage].read_bytes()


def body(stage, alternative=False):
    return p.source_body(stage, fixture_source(stage, alternative))


def synthetic_parent(stage, sources, chain="offline-chain", run="offline-parent-1"):
    """NOT a native result, receipt issuer, or runnable acceptance implementation.

    Only tests call this explicitly synthetic constructor. Production entry
    points reject its result unless the caller opts into offline fixture mode.
    """
    st, _, inventory = p.stage_spec(stage)
    hashes = p.source_hashes(sources)
    units = ["SYNTHETIC-UPSTREAM-UNIT-NOT-A-NATIVE-OBSERVATION",
             "SYNTHETIC-" + stage + "-UNIT-NOT-A-NATIVE-OBSERVATION"]
    required_sha = p.sha(p.canonical(units))
    common = dict(project=st["project"], stage_id=stage, evidence_kind="synthetic-offline",
                  policy_sha256=p.policy_digest())
    fake_pin = p.sha(b"SYNTHETIC HOST PIN, NOT NATIVE QUALIFICATION")
    profile = dict(**common, schema="repodisco-growth-native-parent-profile-v1",
                   scope="entire-qualified-project-plus-stage-one",
                   upstream_commit=inventory["projects"][st["project"]]["commit"],
                   source_sha256=hashes, required_units=units, new_file_units=units[1:],
                   inventory_origin="synthetic-fixture-not-native", toolchain_sha256=fake_pin,
                   native_command_sha256=fake_pin, warning_policy_sha256=fake_pin,
                   qualification_review_sha256=fake_pin)
    profile_raw = p.canonical(profile)
    expected = dict(**common, chain_id=chain, run_id=run,
                    revision_sha256=p.digest_map(hashes), profile_sha256=p.sha(profile_raw),
                    required_units_sha256=required_sha)
    raw = {"raw/stdout.txt": b"SYNTHETIC stdout, not a verifier result\n",
           "raw/stderr.txt": b"SYNTHETIC stderr, not a verifier result\n",
           "raw/units.json": p.canonical({"synthetic": True, "names": units}),
           "raw/execution.json": p.canonical({"synthetic": True, "no_process_executed": True})}
    review = dict(**expected, schema="repodisco-growth-parent-review-v1",
                  source_before_sha256=hashes, source_after_sha256=hashes,
                  native_exit_code=0, timed_out=False, frontend_errors=0, proof_failures=0,
                  coverage_complete=True, all_sources_registered=True, source_integrity_passed=True,
                  warning_policy_sha256=fake_pin, warning_gate_passed=True, unreviewed_warnings=0,
                  named_outcomes=[dict(unit=unit, status="Passed") for unit in units],
                  raw_sha256=p.source_hashes(raw),
                  raw_roles=dict(stdout="raw/stdout.txt", stderr="raw/stderr.txt",
                                 native_units="raw/units.json", execution="raw/execution.json"))
    review_raw = p.canonical(review)
    receipt = dict(**expected, schema="repodisco-growth-accepted-parent-v1", status="accepted",
                   source_sha256=hashes, review_sha256=p.sha(review_raw),
                   predecessor_revision_sha256=p.digest_map(inventory["projects"][st["project"]]["files"]))
    artifacts = dict(raw, **{"accepted.json": p.canonical(receipt), "review.json": review_raw,
                             "profile.json": profile_raw})
    binding = p.AcceptedParentBinding(project=st["project"], stage_id=stage, chain_id=chain,
                                     run_id=run, evidence_kind="synthetic-offline",
                                     revision_sha256=p.digest_map(hashes),
                                     receipt_sha256=p.sha(artifacts["accepted.json"]),
                                     review_sha256=p.sha(review_raw), profile_sha256=p.sha(profile_raw),
                                     required_units_sha256=required_sha, policy_sha256=p.policy_digest())
    return binding, artifacts


def repin_synthetic_record(binding, artifacts, filename, change):
    """Exercise semantic validation after a synthetic host record is repinned."""
    artifacts = dict(artifacts)
    obj = json.loads(artifacts[filename])
    change(obj)
    artifacts[filename] = p.canonical(obj)
    key = {"accepted.json": "receipt_sha256", "review.json": "review_sha256",
           "profile.json": "profile_sha256"}[filename]
    binding = replace(binding, **{key: p.sha(artifacts[filename])})
    if filename in ("review.json", "profile.json"):
        receipt = json.loads(artifacts["accepted.json"])
        receipt[key] = getattr(binding, key)
        artifacts["accepted.json"] = p.canonical(receipt)
        binding = replace(binding, receipt_sha256=p.sha(artifacts["accepted.json"]))
    if filename == "profile.json":
        review = json.loads(artifacts["review.json"])
        review["profile_sha256"] = binding.profile_sha256
        artifacts["review.json"] = p.canonical(review)
        binding = replace(binding, review_sha256=p.sha(artifacts["review.json"]))
        receipt = json.loads(artifacts["accepted.json"])
        receipt["review_sha256"] = binding.review_sha256
        artifacts["accepted.json"] = p.canonical(receipt)
        binding = replace(binding, receipt_sha256=p.sha(artifacts["accepted.json"]))
    return binding, artifacts


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, inventory = p.load_assets()
        cls.upstream = {project: {name: (UPSTREAM / project / name).read_bytes()
                                  for name in item["files"]}
                        for project, item in inventory["projects"].items()}
        cls.parents = {}
        for stage in ("vmc-move", "vest-frame"):
            st, _, _ = p.stage_spec(stage)
            sources, _ = p.reconstruct(stage, body(stage, True), cls.upstream[st["project"]],
                                        chain_id="offline-chain")
            binding, artifacts = synthetic_parent(stage, sources)
            cls.parents[stage] = (sources, binding, artifacts)

    def child(self, stage, replacement=None, **overrides):
        st, _, _ = p.stage_spec(stage)
        sources, binding, artifacts = self.parents[st["parent"]]
        args = dict(chain_id="offline-chain", parent_binding=binding,
                    parent_artifacts=artifacts, allow_synthetic=True)
        args.update(overrides)
        return p.reconstruct(stage, body(stage) if replacement is None else replacement, sources, **args)

    def test_eight_reference_and_alternative_sources_reconstruct_exactly(self):
        for stage in p.RULES:
            for alternative in (False, True):
                with self.subTest(stage=stage, alternative=alternative):
                    source, audit = p.render_source(stage, body(stage, alternative))
                    self.assertEqual(source, fixture_source(stage, alternative))
                    self.assertFalse(audit["semantics_checked"])

    def test_stage_one_preserves_all_upstream_files_with_only_exact_registration(self):
        spec, inventory = p.load_assets()
        for stage in ("vmc-move", "vest-frame"):
            st = spec["stages"][stage]
            parent = self.upstream[st["project"]]
            before = p.source_hashes(parent)
            result, audit = p.reconstruct(stage, body(stage), parent, chain_id="offline-chain")
            self.assertEqual(before, p.source_hashes(parent))
            self.assertEqual(set(result), set(parent) | {st["path"]})
            changes = {name for name in parent if parent[name] != result[name]}
            self.assertEqual(changes, {spec["registration"]["path"]} if st["project"] == "vest" else set())
            self.assertEqual(len(parent), len(inventory["projects"][st["project"]]["files"]))
            self.assertTrue(audit["candidate_unverified"])
            self.assertFalse(audit["native_acceptance_performed"])

    def test_stage_two_uses_actual_accepted_alternative_and_preserves_parent(self):
        for child in ("vmc-pair", "vest-batch"):
            st, spec, _ = p.stage_spec(child)
            sources, binding, artifacts = self.parents[st["parent"]]
            parent_path = spec["stages"][st["parent"]]["path"]
            before = p.source_hashes(sources)
            candidate, audit = self.child(child)
            self.assertEqual(candidate[parent_path], fixture_source(st["parent"], True))
            self.assertNotEqual(candidate[parent_path], fixture_source(st["parent"], False))
            self.assertEqual(before, p.source_hashes(sources))
            self.assertEqual(audit["accepted_parent"]["parent_run_id"], binding.run_id)
            self.assertFalse(audit["accepted_parent"]["authenticity_established_by_policy"])
            p.audit_candidate(child, candidate, sources, chain_id="offline-chain", parent_binding=binding,
                              parent_artifacts=artifacts, allow_synthetic=True)

    def test_synthetic_parent_is_not_native_acceptance_by_default(self):
        for child in ("vmc-pair", "vest-batch"):
            with self.subTest(child=child), self.assertRaisesRegex(ValueError, "Synthetic fixture"):
                self.child(child, allow_synthetic=False)

    def test_stage_two_requires_parent_binding_and_complete_artifacts(self):
        sources, binding, artifacts = self.parents["vmc-move"]
        for altered in (None, {}, {k: v for k, v in artifacts.items() if k != "raw/stdout.txt"}):
            with self.subTest(artifacts=altered is None), self.assertRaises(ValueError):
                self.child("vmc-pair", parent_artifacts=altered)
        with self.assertRaises(ValueError):
            self.child("vmc-pair", parent_binding=None)
        for filename in artifacts:
            broken = dict(artifacts)
            broken[filename] += b"CHANGED"
            with self.subTest(file=filename), self.assertRaises(ValueError):
                self.child("vmc-pair", parent_artifacts=broken)

    def test_stale_project_stage_chain_run_policy_and_revision_are_rejected(self):
        _, binding, artifacts = self.parents["vmc-move"]
        changes = [dict(project="vest"), dict(stage_id="vmc-pair"), dict(chain_id="another-chain"),
                   dict(run_id="another-run"), dict(policy_sha256="0" * 64),
                   dict(revision_sha256="0" * 64), dict(required_units_sha256="0" * 64)]
        for fields in changes:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.child("vmc-pair", parent_binding=replace(binding, **fields))
        for filename, key in (("accepted.json", "run_id"), ("review.json", "stage_id"),
                              ("profile.json", "upstream_commit")):
            b, a = repin_synthetic_record(binding, artifacts, filename, lambda obj: obj.update({key: "stale"}))
            with self.subTest(file=filename), self.assertRaises(ValueError):
                self.child("vmc-pair", parent_binding=b, parent_artifacts=a)

    def test_self_consistent_failed_missing_and_warning_results_cannot_be_parents(self):
        _, binding, artifacts = self.parents["vest-frame"]
        fields = [dict(native_exit_code=4), dict(native_exit_code=False), dict(timed_out=True),
                  dict(frontend_errors=1), dict(proof_failures=1), dict(coverage_complete=False),
                  dict(all_sources_registered=False), dict(source_integrity_passed=False),
                  dict(warning_gate_passed=False), dict(unreviewed_warnings=1)]
        for change in fields:
            b, a = repin_synthetic_record(binding, artifacts, "review.json", lambda obj: obj.update(change))
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.child("vest-batch", parent_binding=b, parent_artifacts=a)
        for operation in (lambda obj: obj["named_outcomes"][1].update(status="Failed"),
                          lambda obj: obj["named_outcomes"].pop(),
                          lambda obj: obj["named_outcomes"].append(dict(obj["named_outcomes"][0])),
                          lambda obj: obj.update(source_after_sha256={})): 
            b, a = repin_synthetic_record(binding, artifacts, "review.json", operation)
            with self.assertRaises(ValueError):
                self.child("vest-batch", parent_binding=b, parent_artifacts=a)

    def test_parent_new_file_missing_from_pinned_native_profile_is_rejected(self):
        _, binding, artifacts = self.parents["vmc-move"]
        for change in (dict(new_file_units=[]), dict(new_file_units=["absent"]),
                       dict(toolchain_sha256=""), dict(native_command_sha256=""),
                       dict(warning_policy_sha256=""), dict(qualification_review_sha256=""),
                       dict(scope="only-the-new-file")):
            b, a = repin_synthetic_record(binding, artifacts, "profile.json", lambda obj: obj.update(change))
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.child("vmc-pair", parent_binding=b, parent_artifacts=a)

    def test_reference_substitution_cannot_replace_an_accepted_alternative(self):
        for child in ("vmc-pair", "vest-batch"):
            st, spec, _ = p.stage_spec(child)
            sources, binding, artifacts = self.parents[st["parent"]]
            substituted = dict(sources)
            substituted[spec["stages"][st["parent"]]["path"]] = fixture_source(st["parent"])
            with self.subTest(child=child), self.assertRaisesRegex(ValueError, "reference substitution"):
                p.reconstruct(child, body(child), substituted, chain_id="offline-chain", parent_binding=binding,
                              parent_artifacts=artifacts, allow_synthetic=True)

    def test_candidate_audit_rejects_header_contract_import_and_footer_changes(self):
        parent = self.upstream["dafny-vmc"]
        candidate, _ = p.reconstruct("vmc-move", body("vmc-move"), parent, chain_id="offline-chain")
        path = p.stage_spec("vmc-move")[0]["path"]
        for old, new in ((b"requires k < |xs|", b"requires false"),
                         (b"ensures |ys| == |xs|", b"ensures true"),
                         (b"import Model", b"import Other"),
                         (b"decreases k", b"decreases *"),
                         (b"function MoveToFront", b"function Another"),
                         (b"  }\n}\n", b"  }\n}\n// changed\n")):
            changed = dict(candidate)
            self.assertIn(old, changed[path])
            changed[path] = changed[path].replace(old, new)
            with self.subTest(old=old), self.assertRaises(ValueError):
                p.audit_candidate("vmc-move", changed, parent, chain_id="offline-chain")

    def test_candidate_audit_rejects_omission_parent_build_and_registration_changes(self):
        sources, binding, artifacts = self.parents["vest-frame"]
        candidate, _ = self.child("vest-batch")
        stage, spec, _ = p.stage_spec("vest-batch")
        parent_path = spec["stages"]["vest-frame"]["path"]
        paths = [parent_path, "vest_dev/Cargo.toml", spec["registration"]["path"]]
        for path in paths:
            changed = dict(candidate)
            changed[path] += b"\n"
            with self.subTest(path=path), self.assertRaises(ValueError):
                p.audit_candidate("vest-batch", changed, sources, chain_id="offline-chain",
                                  parent_binding=binding, parent_artifacts=artifacts, allow_synthetic=True)
        for path in (stage["path"], parent_path):
            omitted = dict(candidate)
            del omitted[path]
            with self.subTest(omit=path), self.assertRaises(ValueError):
                p.audit_candidate("vest-batch", omitted, sources, chain_id="offline-chain",
                                  parent_binding=binding, parent_artifacts=artifacts, allow_synthetic=True)

    def test_undeclared_files_missing_upstream_and_already_created_child_rejected(self):
        parent = self.upstream["dafny-vmc"]
        for mutate in (lambda obj: obj.pop(next(iter(obj))),
                       lambda obj: obj.update({"extra.dfy": b"module Extra {}"}),
                       lambda obj: obj.update({"../extra.dfy": b""}),
                       lambda obj: obj.update({"repodisco-growth/MoveToFront.dfy": fixture_source("vmc-move")})):
            altered = dict(parent)
            mutate(altered)
            with self.assertRaises(ValueError):
                p.reconstruct("vmc-move", body("vmc-move"), altered, chain_id="offline-chain")

    def test_declaration_escape_and_trust_bypasses_are_rejected(self):
        forbidden = ["} method Escape() {", "assert {:axiom} false; xs", "assume false; xs",
                     "reveal Model.Swap; xs", "var alias := Model.Swap; alias(xs, 0, 1)",
                     "xs /* swallowed footer */", "xs // swallowed footer", "import Foo; xs",
                     "#[verifier::external_body] fn hidden() {}", "unsafe { arbitrary() }",
                     "assert!(false);", "let f = || false; f();", "unknown::bypass();",
                     "let x = include!(data);", "assert_by_compute!(false);", "admit();"]
        for text in forbidden:
            stage = "vmc-move" if "xs" in text else "vest-frame"
            with self.subTest(text=text), self.assertRaises(ValueError):
                p.validate_body(stage, text)

    def test_protected_names_cannot_be_shadowed_or_assigned(self):
        invalid = [("vmc-move", "var xs := []; xs"), ("vmc-pair", "var Shift := 0; xs"),
                   ("vmc-move", "xs[0] := xs[1]; xs"), ("vmc-pair", "var (xs, x) := ([], []); x"),
                   ("vest-frame", "let frame_format = 0;"), ("vest-frame", "let Seq = 0;"),
                   ("vest-frame", "let x = choose|payload: Seq<u8>| true;"),
                   ("vest-batch", "let batch_roundtrip = 0;"), ("vest-frame", "payload = tail;")]
        for stage, text in invalid:
            with self.subTest(stage=stage, text=text), self.assertRaises(ValueError):
                p.validate_body(stage, text)

    def test_functional_update_negation_quantifiers_and_explicit_seq_types(self):
        valid = [("vmc-move", "assert !(k < 0); xs[k := xs[k]]"),
                 ("vest-frame", "let prefix = choose|prefix: Seq<u8>| prefix + tail == payload; assert(prefix.len() >= 0);"),
                 ("vest-batch", "assert(payloads == Seq::<Seq<u8>>::empty()); assert(seq![tail] =~= seq![tail]);"),
                 ("vest-frame", "assert(forall|x: u8| x == x); assert(exists|x: u8| x == 0);"),
                 ("vest-frame", "let value = frame_value(payload); if !(value.0 == 0) { assert(value.0 > 0); }")]
        for stage, text in valid:
            with self.subTest(stage=stage):
                self.assertFalse(p.validate_body(stage, text)["semantics_checked"])

    def test_direct_child_body_is_admitted_without_claiming_necessary_parent_calls(self):
        direct = "[xs[i], xs[j]] + xs[..i] + xs[i+1..j] + xs[j+1..]"
        candidate, audit = self.child("vmc-pair", direct)
        self.assertEqual(audit["body"]["parent_api_calls"], [])
        self.assertFalse(audit["body"]["parent_call_required"])
        self.assertFalse(audit["body"]["semantics_checked"])
        self.assertTrue(audit["candidate_unverified"])
        # A mathematically wrong body also passes syntax; only Dafny decides proof.
        _, wrong_audit = self.child("vmc-pair", "xs")
        self.assertFalse(wrong_audit["body"]["semantics_checked"])

    def test_json_envelope_is_single_body_not_a_candidate_or_parent_receipt(self):
        parent = self.upstream["dafny-vmc"]
        raw = "Here is the body:\n```json\n" + json.dumps({"replacement": body("vmc-move")}) + "\n```"
        candidate, audit = p.parse_response(raw, "vmc-move", parent, chain_id="offline-chain")
        self.assertEqual(candidate[p.stage_spec("vmc-move")[0]["path"]], fixture_source("vmc-move"))
        self.assertIn("envelope", audit)
        for bad in ('{"replacement":"xs","replacement":"[]"}',
                    '{"replacement":"xs"} {"replacement":"xs"}',
                    '{"replacement":"xs","accepted":true}',
                    '{"replacement":"xs","parent_binding":{}}',
                    '[{"replacement":"xs"}]', '{"replacement":null}'):
            with self.subTest(raw=bad), self.assertRaises(ValueError):
                p.parse_response(bad, "vmc-move", parent, chain_id="offline-chain")

    def test_copied_parser_provenance_and_template_pins(self):
        provenance = json.loads((ROOT / "inherited-inputs.json").read_bytes())
        for name in ("body_guard.py", "extract_response.py"):
            item = provenance[name]
            original = (REPO / item["source"]).read_bytes()
            copied = (ROOT / "inherited" / name).read_bytes()
            self.assertEqual(p.sha(original), item["source_sha256"])
            self.assertEqual(p.sha(copied), item["copied_sha256"])
            if name == "body_guard.py":
                self.assertEqual(copied, original.replace(b"from extract_response import", b"from .extract_response import"))
            else:
                self.assertEqual(copied, original)
        for stage in p.RULES:
            item = provenance[stage]
            self.assertEqual(p.sha((REPO / item["source"]).read_bytes()), item["source_sha256"])
        p.load_assets()

    def test_manifest_only_isolated_package_import_and_reference_reconstruction(self):
        spec, _ = p.load_assets()
        paths = ["policy.py", "policy-spec.json", "upstream-inventory.json"]
        paths += ["inherited/" + name for name in spec["inherited"]]
        paths += ["templates/" + stage["template"] for stage in spec["stages"].values()]
        examples = [dict(stage=stage, body=body(stage, alt), source_sha256=p.sha(fixture_source(stage, alt)))
                    for stage in p.RULES for alt in (False, True)]
        code = """
import json,sys
sys.path.insert(0,sys.argv[1])
import policy
examples=json.loads(sys.stdin.read())
for example in examples:
    raw, audit=policy.render_source(example['stage'],example['body'])
    assert policy.sha(raw)==example['source_sha256']
    assert audit['semantics_checked'] is False
print(json.dumps(dict(status='ISOLATED_OFFLINE_PACKAGE_PASS_NOT_NATIVE_PROOF',
                     examples=len(examples),policy_sha256=policy.policy_digest(),
                     native_verifier_calls=0,model_calls=0),sort_keys=True))
"""
        with tempfile.TemporaryDirectory(prefix=".offline-package-", dir=ROOT) as directory:
            target = Path(directory)
            for name in paths:
                dest = target / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, dest)
            result = subprocess.run([sys.executable, "-I", "-B", "-c", code, directory],
                                    input=p.canonical(examples), capture_output=True, env={},
                                    cwd=directory, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        report = json.loads(result.stdout)
        self.assertEqual(report["examples"], 8)
        self.assertEqual(report["policy_sha256"], p.policy_digest())
        print(result.stdout.decode().strip())


if __name__ == "__main__":
    unittest.main(verbosity=2)
