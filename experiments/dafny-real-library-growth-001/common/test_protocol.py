"""Offline synthetic tests only. They do not establish native proof acceptance."""
import copy
from dataclasses import replace
from pathlib import Path
import unittest

import guard
import review_native as native


def fixture(body="  result := x + 1;\n"):
    """Explicit synthetic bytes, records and host pins for branch qualification."""
    base = {"Base.dfy": b"module Base { function Next(x: int): int { x + 1 } }\n",
            "All.dfy": b'include "Base.dfy"\n'}
    template = ("module Added {\n  method Step(x: int) returns (result: int)\n"
                "    ensures result == x + 1\n  {\n    // BEGIN BODY\n"
                "    // END BODY\n  }\n}\n")
    edit = dict(schema=guard.SCHEMA, project="synthetic-demo", stage=1, stage_id="step",
                base_source_sha256=native.hashes(base), parent_requirement=None,
                addition=dict(path="Added.dfy", template_utf8=template, begin_marker="    // BEGIN BODY\n",
                              end_marker="    // END BODY", kind="method"),
                registrations={"All.dfy": dict(before_sha256=native.sha(base["All.dfy"]),
                                content_utf8='include "Base.dfy"\ninclude "Added.dfy"\n')},
                forbidden_identifiers=[])
    sources, edit_audit = guard.reconstruct(edit, body, base, "synthetic-chain")
    profile = dict(schema=native.PROFILE_SCHEMA, project="synthetic-demo", stage=1, stage_id="step",
                   synthetic=True, inventory_status="qualified", command=["/synthetic/dafny", "verify",
                   "--verify-included-files", "--log-format", "csv", "All.dfy"],
                   toolchain=dict(dafny_version="SYNTHETIC-4.11", executable_sha256="0"*64,
                                  package_sha256="1"*64),
                   csv_columns=list(native.CSV_SCHEMAS[1]), random_seed=0,
                   required_units={"Base.Next (well-formedness)": "Base.dfy",
                                   "Added.Step (correctness)": "Added.dfy"},
                   unitless_files={"All.dfy": "Host-owned include registration only"},
                   inherited_warnings=[], unlogged_definitions=[],
                   ineligible_parent_runs=[], ineligible_parent_raw_fingerprints=[])
    csv_raw = (",".join(profile["csv_columns"]) + "\n"
               "Base.Next (well-formedness),Passed,00:00:00.0001000,10,0\n"
               "Added.Step (correctness),Passed,00:00:00.0001000,20,0\n").encode()
    raw = {"stdout.txt": b"// SYNTHETIC OFFLINE FIXTURE\nDafny program verifier finished with 2 verified, 0 errors\n",
           "stderr.txt": b"", "resources.txt": (b"SYNTHETIC resource observation; no process ran\n"
               b"User time (seconds): 0.01\nSystem time (seconds): 0.00\n"
               b"Elapsed (wall clock) time (h:mm:ss or m:ss): 0:00.01\n"
               b"Maximum resident set size (kbytes): 100\nExit status: 0\n"),
           "csv/TestResults/synthetic.csv": csv_raw}
    record = dict(schema=native.RECORD_SCHEMA, run_id="synthetic-job:stage1", origin="synthetic_offline",
                  source_before_sha256=native.hashes(sources), source_after_sha256=native.hashes(sources),
                  argv=profile["command"], toolchain=profile["toolchain"],
                  toolchain_after=copy.deepcopy(profile["toolchain"]), raw_sha256=native.hashes(raw),
                  exit_code=0, elapsed_seconds=0.0, timeout=False, attempts=1, model_calls=0,
                  host=dict(job_id="SYNTHETIC-NOT-SLURM", hostname="synthetic-compute", partition="synthetic"))
    return dict(base=base, edit=edit, sources=sources, profile=profile, raw=raw, record=record,
                edit_audit=edit_audit)


def pins(value):
    return native.EvidencePins(native.sha(native.canonical(value["profile"])),
                               native.sha(native.canonical(value["record"])),
                               native.sha(native.canonical(native.hashes(value["sources"]))),
                               tuple(sorted(native.hashes(value["raw"]).items())),
                               value["record"]["run_id"], value["record"]["origin"])


def resync_raw(value):
    if value["record"]["exit_code"] is not None:
        import re
        value["raw"]["resources.txt"] = re.sub(rb"Exit status: -?\d+", b"Exit status: " +
            str(value["record"]["exit_code"]).encode(), value["raw"]["resources.txt"])
    value["record"]["raw_sha256"] = native.hashes(value["raw"])


def replay(value, **kwargs):
    return native.review(value["profile"], value["sources"], value["record"], value["raw"],
                         kwargs.pop("host_pins", pins(value)), **kwargs)


def synthetic_parent(value):
    observed = replay(value, allow_synthetic=True)
    receipt = dict(schema=guard.RECEIPT_SCHEMA, project=value["edit"]["project"], stage=1,
                   stage_id=value["edit"]["stage_id"], chain_id="synthetic-chain",
                   origin=value["record"]["origin"], guard_profile_sha256=native.sha(native.canonical(value["edit"])),
                   source_revision_sha256=observed["source_revision_sha256"],
                   native_profile_sha256=observed["profile_sha256"],
                   native_record_sha256=observed["record_sha256"], native_run_id=observed["run_id"],
                   native_raw_fingerprint_sha256=observed["raw_fingerprint_sha256"],
                   request_id="SYNTHETIC-NO-PROVIDER-REQUEST", response_sha256="a"*64, accepted=True)
    return guard.ParentEvidence(value["profile"], value["record"], value["raw"], pins(value), receipt,
                                native.sha(native.canonical(receipt)))


def child_profile(value):
    template = ("module Child {\n  method Use(x: int) returns (result: int)\n"
                "    ensures result == x + 1\n  {\n    // BEGIN BODY\n"
                "    // END BODY\n  }\n}\n")
    return dict(schema=guard.SCHEMA, project=value["edit"]["project"], stage=2, stage_id="use",
                base_source_sha256={name: digest for name, digest in native.hashes(value["sources"]).items()
                                    if name != "Added.dfy"},
                addition=dict(path="Child.dfy", template_utf8=template, begin_marker="    // BEGIN BODY\n",
                              end_marker="    // END BODY", kind="method"),
                registrations={"All.dfy": dict(before_sha256=native.sha(value["sources"]["All.dfy"]),
                               content_utf8=value["sources"]["All.dfy"].decode() + 'include "Child.dfy"\n')},
                parent_requirement=dict(stage_id="step", addition_path="Added.dfy",
                                        guard_profile_sha256=native.sha(native.canonical(value["edit"]))),
                forbidden_identifiers=[])


class ProtocolTests(unittest.TestCase):
    def test_explicit_source_registration_exact_inputs_and_command(self):
        value = fixture()
        value["edit"]["registrations"] = {}
        value["edit"]["verification_inputs"] = sorted(set(value["base"]) | {"Added.dfy"})
        candidate, audit = guard.reconstruct(value["edit"], "result := x + 1;", value["base"], "chain")
        self.assertEqual(candidate["All.dfy"], value["base"]["All.dfy"])
        self.assertEqual(audit["verification_inputs"], value["edit"]["verification_inputs"])
        for inputs in (None, ["Added.dfy"], sorted(candidate) + ["Extra.dfy"], sorted(candidate) + ["Added.dfy"]):
            changed = copy.deepcopy(value["edit"])
            changed["verification_inputs"] = inputs
            with self.subTest(inputs=inputs), self.assertRaises(native.EvidenceError):
                guard.reconstruct(changed, "result := x + 1;", value["base"], "chain")
        value = fixture()
        inputs = sorted(value["sources"])
        value["profile"]["verification_inputs"] = inputs
        value["profile"]["command"] = ["/synthetic/dafny", "verify"] + inputs
        value["record"]["argv"] = value["profile"]["command"]
        self.assertTrue(replay(value, allow_synthetic=True)["qualified_success"])
        for argv in (["/synthetic/dafny", "verify", "All.dfy"],
                     ["/synthetic/dafny", "verify"] + inputs + ["Extra.dfy"]):
            value["profile"]["command"] = argv
            value["record"]["argv"] = argv
            with self.assertRaisesRegex(native.EvidenceError, "explicit"):
                replay(value, allow_synthetic=True)

    def test_actual_stdlib_control_bodies_reconstruct_as_drafts(self):
        """Real proposed source syntax only; no native proof or parent acceptance."""
        library = Path(__file__).resolve().parent.parent / "stdlib"
        cases = [("AppendAll.dfy", "append-reference.txt"),
                 ("AppendAll.dfy", "append-alternative.txt"),
                 ("AppendRotated.dfy", "rotate-reference.txt"),
                 ("AppendRotated.dfy", "rotate-direct.txt")]
        for template_name, body_name in cases:
            profile = fixture()["edit"]
            template = (library / "templates" / template_name).read_text()
            body = (library / "bodies" / body_name).read_text()
            profile["addition"].update(template_utf8=template,
                begin_marker="    // BEGIN REPLACEMENT\n", end_marker="    // END REPLACEMENT")
            raw, audit = guard.render_body(profile, body)
            with self.subTest(body=body_name):
                self.assertEqual(raw, template.replace("    // BEGIN REPLACEMENT\n",
                                                      "    // BEGIN REPLACEMENT\n" + body).encode())
                self.assertEqual(audit["body_sha256"], native.sha(body.encode()))

    def test_broader_method_function_bodies_are_lexically_admitted(self):
        body = """var a := new int[2];
var i := 0;
while i < 2
  invariant 0 <= i <= 2
  decreases 2 - i
{ a[i] := i; i := i + 1; }
forall k | 0 <= k < 2 ensures a[k] == k { assert a[k] == k; }
calc { 1 + 1; == 2; }
result := Base.Next(x);
"""
        self.assertGreater(guard.check_body(body, "method")["token_count"], 40)
        guard.check_body("if x > 0 then x + 1 else Base.Next(x)", "function")

    def test_literals_comments_primes_do_not_escape(self):
        body = "var x' := 1; var s := \"assume } import\"; var c := '}';\n" \
               "var t := @\"method \"\"}axiom\"\"\"; /* nested /* } */ comment */\nreturn; // trailing }"
        guard.check_body(body, "method")

    def test_scope_and_trust_bypasses_rejected(self):
        attempts = ["} method Escape() {", "assume false;", "expect false;", "halt;",
                    "assert {:axiom} false;", "assert { /* gap */ : verify false } true;",
                    "while true decreases * {}", "import X = Evil;", "function F(): int { 0 }",
                    "...", "/* unclosed", 'var x := "unclosed', "if true {", "([)]", "admit;"]
        for body in attempts:
            with self.subTest(body=body), self.assertRaises(native.EvidenceError):
                guard.check_body(body, "method")

    def test_host_forbidden_identifiers_cover_callable_aliases(self):
        value = fixture()
        value["edit"]["forbidden_identifiers"] = ["ValueIsSafeBecauseItIsInMemory", "Encode", "Decode"]
        for body in ["MemoryMath.ValueIsSafeBecauseItIsInMemory(x);", "var f := UTF8.Encode;",
                     "var g := UTF8.Decode; g(x);", "var Encode := 1;"]:
            with self.subTest(body=body), self.assertRaises(native.EvidenceError):
                guard.render_body(value["edit"], body)
        guard.render_body(value["edit"], 'var message := "Encode"; // Decode\nresult := x + 1;')

    def test_host_contract_registration_and_old_sources_exact(self):
        value = fixture()
        sources, audit = guard.reconstruct(value["edit"], "result := Base.Next(x);", value["base"], "chain")
        self.assertEqual(sources["Base.dfy"], value["base"]["Base.dfy"])
        self.assertEqual(sources["All.dfy"].decode(), value["edit"]["registrations"]["All.dfy"]["content_utf8"])
        prefix, suffix = guard._profile(value["edit"])
        self.assertTrue(sources["Added.dfy"].startswith(prefix.encode()))
        self.assertTrue(sources["Added.dfy"].endswith(suffix.encode()))
        self.assertFalse(audit["acceptance_issued"])
        altered = dict(value["base"], **{"Base.dfy": b"module Base {}"})
        with self.assertRaises(native.EvidenceError):
            guard.reconstruct(value["edit"], "", altered, "chain")
        altered = copy.deepcopy(value["edit"])
        altered["registrations"]["All.dfy"]["before_sha256"] = "f"*64
        with self.assertRaises(native.EvidenceError):
            guard.reconstruct(altered, "", value["base"], "chain")

    def test_input_bounds_and_missing_host_markers(self):
        for body in ["x" * 65537, "{" * 129 + "}" * 129, "\u202eassume false;"]:
            with self.subTest(length=len(body)), self.assertRaises(native.EvidenceError):
                guard.check_body(body, "method")
        value = fixture()
        value["edit"]["addition"]["template_utf8"] = "module Evil {}"
        with self.assertRaises(native.EvidenceError):
            guard.render_body(value["edit"], "")

    def test_synthetic_evidence_is_default_rejected_and_never_acceptance(self):
        value = fixture()
        with self.assertRaisesRegex(native.EvidenceError, "Synthetic"):
            replay(value)
        report = replay(value, allow_synthetic=True)
        self.assertEqual(report["category"], "VERIFIED")
        self.assertTrue(report["qualified_success"])
        self.assertTrue(report["synthetic"])
        self.assertFalse(report["acceptance_issued"])
        with self.assertRaisesRegex(native.EvidenceError, "EvidencePins"):
            native.review(value["profile"], value["sources"], value["record"], value["raw"],
                          vars(pins(value)), allow_synthetic=True)

    def test_failed_helper_with_passing_client_is_proof_failure(self):
        value = fixture()
        path = "csv/TestResults/synthetic.csv"
        value["raw"][path] = value["raw"][path].replace(b"Base.Next (well-formedness),Passed", b"Base.Next (well-formedness),Failed")
        value["raw"]["stdout.txt"] = b"Base.dfy(1,1): Error: a postcondition could not be proved\nDafny program verifier finished with 1 verified, 1 error\n"
        value["record"]["exit_code"] = 4
        resync_raw(value)
        report = replay(value, allow_synthetic=True)
        self.assertEqual(report["category"], "PROOF_FAILURE")
        self.assertEqual(report["failed_units"], 1)
        self.assertFalse(report["qualified_success"])
        self.assertFalse(report["terminal"])

    def test_omitted_module_exit_zero_is_coverage_failure(self):
        value = fixture()
        path = "csv/TestResults/synthetic.csv"
        value["raw"][path] = b"\n".join(line for line in value["raw"][path].split(b"\n") if not line.startswith(b"Base.Next"))
        value["raw"]["stdout.txt"] = b"Dafny program verifier finished with 1 verified, 0 errors\n"
        resync_raw(value)
        report = replay(value, allow_synthetic=True)
        self.assertEqual(report["category"], "COVERAGE_FAILURE")
        self.assertEqual(report["missing_units"], ["Base.Next (well-formedness)"])
        self.assertFalse(report["qualified_success"])

    def test_duplicate_csv_unknown_units_and_summary_counts(self):
        value = fixture()
        path = "csv/TestResults/synthetic.csv"
        value["raw"][path] += value["raw"][path].splitlines(keepends=True)[1]
        resync_raw(value)
        with self.assertRaisesRegex(native.EvidenceError, "duplicate"):
            replay(value, allow_synthetic=True)
        value = fixture()
        value["raw"][path] = value["raw"][path].replace(b"Base.Next", b"Unreviewed.Next")
        resync_raw(value)
        self.assertEqual(replay(value, allow_synthetic=True)["category"], "COVERAGE_FAILURE")
        value = fixture()
        value["raw"]["stdout.txt"] = b"Dafny program verifier finished with 3 verified, 0 errors\n"
        resync_raw(value)
        self.assertEqual(replay(value, allow_synthetic=True)["category"], "SUMMARY_INVENTORY_MISMATCH")

    def test_four_and_five_column_schemas_seed_preserved(self):
        value = fixture()
        path = "csv/TestResults/synthetic.csv"
        self.assertEqual(replay(value, allow_synthetic=True)["units"][0]["fields"]["RandomSeed"], "0")
        value["profile"]["csv_columns"] = list(native.CSV_SCHEMAS[0])
        value["raw"][path] = b"\n".join(line.rsplit(b",", 1)[0] for line in value["raw"][path].splitlines()) + b"\n"
        resync_raw(value)
        self.assertTrue(replay(value, allow_synthetic=True)["qualified_success"])
        value = fixture()
        value["raw"][path] = value["raw"][path].replace(b",20,0", b",20,1")
        resync_raw(value)
        with self.assertRaisesRegex(native.EvidenceError, "seed"):
            replay(value, allow_synthetic=True)
        value = fixture()
        value["raw"][path] = value["raw"][path].replace(b"TestResult.DisplayName", b"Definition")
        resync_raw(value)
        with self.assertRaisesRegex(native.EvidenceError, "columns"):
            replay(value, allow_synthetic=True)

    def test_sources_commands_tools_and_raw_are_bound(self):
        for key, mutate in [
            ("source", lambda v: v["sources"].update({"Added.dfy": b"module Added {}"})),
            ("command", lambda v: v["record"].update(argv=["dafny", "verify", "Wrong.dfy"])),
            ("tools", lambda v: v["record"].update(toolchain_after={"dafny_version": "other"})),
            ("missing", lambda v: v["raw"].pop("stderr.txt")),
            ("raw", lambda v: v["raw"].update({"stdout.txt": b"stale"})),
            ("retry", lambda v: v["record"].update(attempts=2))]:
            value = fixture()
            mutate(value)
            with self.subTest(key=key), self.assertRaises(native.EvidenceError):
                replay(value, allow_synthetic=True)
        value = fixture()
        before = pins(value)
        value["record"]["elapsed_seconds"] = 1.0
        with self.assertRaisesRegex(native.EvidenceError, "record"):
            replay(value, host_pins=before, allow_synthetic=True)

    def test_warning_only_is_separate_and_inherited_warnings_exact(self):
        value = fixture()
        warning = "Added.dfy(1,1): Warning: selected inherited warning"
        value["raw"]["stdout.txt"] = warning.encode() + b"\n" + value["raw"]["stdout.txt"]
        value["record"]["exit_code"] = 2
        resync_raw(value)
        report = replay(value, allow_synthetic=True)
        self.assertEqual(report["category"], "WARNING_ONLY")
        self.assertFalse(report["qualified_success"])
        value["record"]["exit_code"] = 0
        resync_raw(value)
        self.assertFalse(replay(value, allow_synthetic=True)["qualified_success"])
        value["profile"]["inherited_warnings"] = [warning]
        report = replay(value, allow_synthetic=True)
        self.assertTrue(report["qualified_success"])
        self.assertFalse(report["strict_zero_warning_success"])
        value["raw"]["stdout.txt"] += b"2 warnings\n"
        resync_raw(value)
        self.assertFalse(replay(value, allow_synthetic=True)["qualified_success"])

    def test_frontend_resource_timeout_and_unknown_are_not_proof_results(self):
        cases = [("1 parse error detected\n", 2, False, "FRONTEND_PARSE_FAILURE"),
                 ("1 resolution/type error detected\n", 2, False, "FRONTEND_RESOLUTION_FAILURE"),
                 ("X(1,1): Error: out of resource limit\n", 4, False, "RESOURCE_FAILURE"),
                 ("X(1,1): Error: timed out\n", 4, False, "VERIFIER_TIMEOUT"),
                 ("", -15, True, "TIMEOUT"), ("native crashed", -9, False, "PROCESS_FAILURE")]
        for text, code, timeout, expected in cases:
            value = fixture()
            value["raw"] = {key: data for key, data in value["raw"].items() if not key.startswith("csv/")}
            value["raw"]["stdout.txt"] = text.encode()
            value["record"].update(exit_code=code, timeout=timeout)
            resync_raw(value)
            report = replay(value, allow_synthetic=True)
            with self.subTest(expected=expected):
                self.assertEqual(report["category"], expected)
                self.assertTrue(report["terminal"])
                self.assertFalse(report["qualified_success"])

    def test_missing_or_disagreeing_resource_measurements_block_success(self):
        value = fixture()
        self.assertEqual(replay(value, allow_synthetic=True)["resources"]["max_rss_kib"], 100)
        for raw in (b"", b"Exit status: 0\n"):
            value["raw"]["resources.txt"] = raw
            resync_raw(value)
            result = replay(value, allow_synthetic=True)
            self.assertEqual(result["category"], "RESOURCE_OBSERVATION_MISMATCH")
            self.assertFalse(result["qualified_success"])
        value = fixture()
        value["raw"]["resources.txt"] = value["raw"]["resources.txt"].replace(b"Exit status: 0", b"Exit status: 4")
        value["record"]["raw_sha256"] = native.hashes(value["raw"])
        self.assertEqual(replay(value, allow_synthetic=True)["category"], "RESOURCE_OBSERVATION_MISMATCH")

    def test_pending_and_explicit_unlogged_definitions_never_add_passes(self):
        value = fixture()
        value["profile"]["inventory_status"] = "pending"
        self.assertFalse(replay(value, allow_synthetic=True)["qualified_success"])
        value["profile"]["inventory_status"] = "qualified"
        value["profile"]["unlogged_definitions"] = [dict(name="Base.Unlogged", file="Base.dfy",
            source_sha256=native.sha(value["sources"]["Base.dfy"]), counted_as_pass=False)]
        report = replay(value, allow_synthetic=True)
        self.assertEqual(report["passed_units"], 2)
        value["profile"]["unlogged_definitions"][0]["name"] = "Base.Next"
        with self.assertRaisesRegex(native.EvidenceError, "unlogged"):
            replay(value, allow_synthetic=True)

    def test_stage_two_preserves_actual_alternative_parent_and_allows_direct_body(self):
        value = fixture("  var y := x + 1;\n  result := y;\n")
        parent, child = synthetic_parent(value), child_profile(value)
        with self.assertRaisesRegex(native.EvidenceError, "Synthetic"):
            guard.reconstruct(child, "result := x + 1;", value["sources"], "synthetic-chain", parent=parent)
        sources, audit = guard.reconstruct(child, "result := x + 1;", value["sources"], "synthetic-chain",
                                           parent=parent, allow_synthetic=True)
        self.assertEqual(sources["Added.dfy"], value["sources"]["Added.dfy"])
        self.assertNotIn(b"Added.Step", sources["Child.dfy"])
        self.assertTrue(audit["synthetic"])
        self.assertFalse(audit["acceptance_issued"])

    def test_parent_missing_stale_wrong_chain_and_reference_substitution_rejected(self):
        value = fixture("  var y := x + 1; result := y;\n")
        parent, child = synthetic_parent(value), child_profile(value)
        for name, candidate_sources, candidate_parent, chain in [
            ("missing", value["sources"], None, "synthetic-chain"),
            ("chain", value["sources"], parent, "other-chain"),
            ("reference-substitution", fixture()["sources"], parent, "synthetic-chain"),
            ("stale-receipt", value["sources"], replace(parent, receipt_sha256="f"*64), "synthetic-chain")]:
            with self.subTest(name=name), self.assertRaises(native.EvidenceError):
                guard.reconstruct(child, "result := x + 1;", candidate_sources, chain,
                                  parent=candidate_parent, allow_synthetic=True)

    def test_analyst_and_failed_parents_rejected_even_with_receipts(self):
        value = fixture()
        value["profile"].pop("synthetic")
        value["record"]["origin"] = "analyst_qualification"
        parent, child = synthetic_parent(value), child_profile(value)
        with self.assertRaisesRegex(native.EvidenceError, "model-origin"):
            guard.reconstruct(child, "result := x + 1;", value["sources"], "synthetic-chain",
                              parent=parent, allow_synthetic=True)
        value = fixture()
        value["raw"]["csv/TestResults/synthetic.csv"] = value["raw"]["csv/TestResults/synthetic.csv"].replace(
            b"Added.Step (correctness),Passed", b"Added.Step (correctness),Failed")
        value["raw"]["stdout.txt"] = b"Added.dfy(1,1): Error: a postcondition could not be proved\nDafny program verifier finished with 1 verified, 1 error\n"
        value["record"]["exit_code"] = 4
        resync_raw(value)
        with self.assertRaisesRegex(native.EvidenceError, "qualified"):
            guard.reconstruct(child_profile(value), "result := x + 1;", value["sources"], "synthetic-chain",
                              parent=synthetic_parent(value), allow_synthetic=True)

    def test_known_analyst_run_and_full_evidence_cannot_be_relabeled(self):
        for deny_by in ("run", "raw"):
            value = fixture()
            if deny_by == "run":
                value["profile"]["ineligible_parent_runs"] = [value["record"]["run_id"]]
            else:
                value["profile"]["ineligible_parent_raw_fingerprints"] = [native.sha(native.canonical(native.hashes(value["raw"])))]
                value["record"]["run_id"] = "synthetic-job:new-label"
            with self.subTest(deny_by=deny_by), self.assertRaisesRegex(native.EvidenceError, "Known analyst"):
                guard.reconstruct(child_profile(value), "result := x + 1;", value["sources"], "synthetic-chain",
                                  parent=synthetic_parent(value), allow_synthetic=True)

    def test_parent_receipt_is_not_sufficient_without_exact_native_evidence(self):
        value = fixture()
        parent = synthetic_parent(value)
        bad_raw = dict(parent.raw, **{"stdout.txt": b"forged VERIFIED"})
        with self.assertRaises(native.EvidenceError):
            guard.reconstruct(child_profile(value), "result := x + 1;", value["sources"], "synthetic-chain",
                              parent=replace(parent, raw=bad_raw), allow_synthetic=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
