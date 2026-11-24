"""Synthetic archive replay tests only: no native, provider, SSH or key calls.

The production entry point rejects these archives. These fixtures do not
authenticate arbitrary receipt JSON and are never model/native observations.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import review_collection as review
import runtime as rt
from run_pilot import Runner
from test_runner import BODY, FakeHost, FakeRenderer, scope, stages


def write_json(path, value):
    Path(path).write_bytes(rt.canonical(value))


class FullFakeTransport:
    """Provider-shaped data carrying an explicit synthetic raw marker."""
    def __init__(self):
        self.calls = []
        self.error_at = None
        self.texts = {}

    def __call__(self, payload):
        index = len(self.calls) + 1
        self.calls.append(copy.deepcopy(payload))
        if index == self.error_at:
            raise TimeoutError("SYNTHETIC: no provider request")
        text = self.texts.get(index, json.dumps({"body":BODY + " // synthetic trial " + str(index)}))
        content = [{"text":text}]
        usage = dict(inputTokens=5, outputTokens=3, totalTokens=8)
        raw = dict(synthetic=True, output={"message":{"role":"assistant", "content":content}},
            usage=usage, stopReason="end_turn", ResponseMetadata=dict(
                RequestId="SYNTHETIC-REQUEST-" + str(index), RetryAttempts=0, HTTPStatusCode=200))
        return dict(text=text, content=content, usage=usage, stop_reason="end_turn",
            request_id=raw["ResponseMetadata"]["RequestId"], retry_attempts=0, raw_response=raw)


class FullFakeHost(FakeHost):
    """Reuse the established fake native shape with exact capture provenance."""
    def __init__(self):
        super().__init__()
        self.error_at = None

    def run(self, profile, sources, event, destination, adapter):
        if event["slot_id"] == self.error_at:
            raise RuntimeError("SYNTHETIC: no native process")
        result = super().run(profile, sources, event, destination, adapter)
        for name, raw in result.raw.items():
            if name.startswith("csv/"):
                rt.save_bytes(destination / "workspace" / name[4:], raw)
        rt.save(destination / "invocation-start.json",
            dict(schema="dafny-library-native-invocation-v1", synthetic=True,
                event_sha256=rt.sha(rt.canonical(event)), argv=profile["command"],
                wrapper_argv=["/usr/bin/time", "-v", "-o", str(destination / "raw/resources.txt")] + profile["command"],
                host=result.record["host"], before_sha256=rt.native.hashes(sources),
                wall_seconds=adapter["wall_seconds"]))
        return result


class CollectionReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.model = self.root / "model"
        self.stages = stages()
        self.scope = scope()
        self.renderer = FakeRenderer(self.stages)
        self.transport = FullFakeTransport()
        self.host = FullFakeHost()
        self.auth = dict(created_at_epoch=0, expires_at_epoch=100)

    def tearDown(self):
        self.temp.cleanup()

    def collect(self):
        return Runner(self.scope, self.stages, self.renderer, self.host, self.transport,
            self.model, deadline=100, integrity_check=lambda:None, clock=lambda:1,
            offline=True, run_id="SYNTHETIC-COLLECTION").run()

    def audit(self, *, allow_synthetic=True):
        return review._audit_run(self.model, self.scope, self.stages, self.renderer,
            package=self.root, auth=self.auth,
            expected_host=dict(job_id="SYNTHETIC", partition="synthetic"),
            expected_output=str(self.model), allow_synthetic=allow_synthetic)

    def read(self, name):
        return rt.read_json(self.model / name)

    def alter(self, name, change):
        path = self.model / name
        value = rt.read_json(path)
        change(value)
        write_json(path, value)

    def test_complete_eight_independent_replays_and_explicit_synthetic_rejection(self):
        self.collect()
        result = self.audit()
        self.assertEqual(result["status"], "PASS_COMPLETE")
        self.assertEqual(result["score"], {"accepted":8,"returned_trials":8})
        self.assertEqual(result["tokens_from_saved_responses"], dict(inputTokens=40,outputTokens=24,totalTokens=64))
        self.assertEqual(result["unique_request_ids"], 8)
        self.assertEqual(result["replayed_native_records"], 8)
        self.assertTrue(result["synthetic"])
        self.assertFalse(result["acceptance_issued"])
        self.assertEqual(result["native_or_provider_calls_in_review"], 0)
        for counts in result["per_task"].values():
            self.assertEqual(counts["accepted"], 2)
            self.assertEqual(counts["captured_responses"], 2)
        with self.assertRaisesRegex(rt.native.EvidenceError, "Synthetic"):
            self.audit(allow_synthetic=False)

    def test_complete_mixed_policy_proof_and_resource_outcomes(self):
        self.transport.texts[1] = '{"body":"assume false;"}'
        self.host.outcomes = {"slot-02":"PROOF_FAILURE", "slot-03":"RESOURCE_FAILURE",
                              "slot-04":"VERIFIER_TIMEOUT"}
        self.collect()
        result = self.audit()
        self.assertEqual(result["score"], {"accepted":4,"returned_trials":8})
        self.assertEqual(result["outcome_counts"]["OUTPUT_REJECTED"], 1)
        self.assertEqual(result["outcome_counts"]["NATIVE_REJECTED"], 3)
        self.assertEqual(result["native_dispatch_records"], 7)
        self.assertEqual(result["rows"][2]["category"], "RESOURCE_FAILURE")
        self.assertEqual(result["rows"][3]["category"], "VERIFIER_TIMEOUT")

    def test_ambiguous_first_request_has_no_fabricated_zero_of_eight_score(self):
        self.transport.error_at = 1
        self.collect()
        result = self.audit()
        self.assertEqual((result["reserved"],result["captured_responses"],result["recorded_outcomes"]), (1,0,0))
        self.assertEqual(result["ambiguous_or_unsaved"], 1)
        self.assertIsNone(result["score"])
        self.assertIsNone(result["tokens_for_missing_responses"])
        self.assertIsNone(result["sdk_retries"])
        self.assertEqual(result["undispatched_slots"], 7)
        self.assertEqual(result["tokens_from_saved_responses"]["totalTokens"], 0)

    def test_bounded_provider_error_metadata_is_not_a_returned_response(self):
        self.transport.error_at = 1
        diagnostic = dict(schema="repodisco-growth-transport-failure-v1",
            phase="invocation_or_response", capture_status="EXTRACTED",
            provider_error={"Error":{"Code":"ReadTimeoutError","Message":"SYNTHETIC"},
                "ResponseMetadata":{"RequestId":"SYNTHETIC-ERROR-ID","HTTPStatusCode":500,"RetryAttempts":0}})
        self.transport.failure_diagnostic = lambda:copy.deepcopy(diagnostic)
        self.collect()
        result = self.audit()
        self.assertEqual(result["captured_responses"], 0)
        self.assertEqual(result["unique_request_ids"], 0)
        self.assertEqual(result["transport_failure"], diagnostic)
        self.assertEqual(result["sdk_retries"], 0)
        self.assertIsNone(result["score"])

    def test_later_ambiguous_request_retains_only_observed_tokens_and_results(self):
        self.transport.error_at = 3
        self.collect()
        result = self.audit()
        self.assertEqual((result["reserved"],result["captured_responses"],result["accepted_additions"]), (3,2,2))
        self.assertEqual(result["tokens_from_saved_responses"]["totalTokens"], 16)
        self.assertIsNone(result["score"])
        self.assertEqual(result["per_task"]["stdlib-splice"]["captured_responses"], 0)

    def test_response_saved_but_not_committed_is_never_scored(self):
        self.transport.error_at = 1
        self.collect()
        saved = FullFakeTransport()({})
        write_json(self.model / "requests/response-001.json", saved)
        result = self.audit()
        self.assertEqual(result["completed_reservations"], 0)
        self.assertEqual(result["captured_responses"], 1)
        self.assertEqual(result["observed_responses"][0]["state"], "SAVED_BUT_UNCOMMITTED")
        self.assertIsNone(result["observed_responses"][0]["score"])
        self.assertEqual(result["reservations_without_saved_response"], 0)
        self.assertIsNone(result["score"])

    def test_returned_response_then_host_interruption_is_not_a_native_failure_score(self):
        self.host.error_at = "slot-02"
        self.collect()
        result = self.audit()
        self.assertEqual((result["captured_responses"],result["recorded_outcomes"]), (2,1))
        self.assertEqual(result["native_dispatch_records"], 2)
        self.assertEqual(result["replayed_native_records"], 1)
        self.assertFalse(result["unfinished_slots"][0]["candidate_scored"])
        self.assertIsNone(result["score"])

    def test_preflight_stop_spends_zero_and_has_no_score(self):
        self.host.prepare_error = True
        self.collect()
        result = self.audit()
        self.assertEqual((result["reserved"],result["captured_responses"],result["accepted_additions"]), (0,0,0))
        self.assertIsNone(result["score"])
        self.assertFalse(result["native_preflight"]["reviewed"])

    def test_terminal_warning_is_distinct_from_mathematical_failure(self):
        self.host.outcomes = {"slot-01":"WARNING_ONLY"}
        self.collect()
        result = self.audit()
        self.assertEqual(result["rows"][0]["outcome"], "TERMINAL_NATIVE_FAILURE")
        self.assertEqual(result["rows"][0]["category"], "WARNING_ONLY")
        self.assertIsNone(result["score"])
        self.assertEqual(result["captured_responses"], 1)

    def test_exact_payload_and_raw_provider_response_binding(self):
        self.collect()
        self.alter("requests/response-001.json", lambda value:value["raw_response"]["output"]["message"]["content"].append({"text":"tampered"}))
        with self.assertRaisesRegex(rt.native.EvidenceError, "response/content/text"):
            self.audit()

    def test_changed_frozen_prompt_rejected_even_with_matching_ledger_copy(self):
        self.collect()
        self.alter("slots/slot-01/prompt.json", lambda value:value["payload"]["messages"][0]["content"].append({"text":"extra feedback"}))
        prompt = self.read("slots/slot-01/prompt.json")
        self.alter("requests/ledger.json", lambda value:value["reservations"][0].update(prompt=prompt["payload"]))
        with self.assertRaisesRegex(rt.native.EvidenceError, "Frozen request"):
            self.audit()

    def test_duplicate_request_and_retry_metadata_rejected(self):
        self.collect()
        original = (self.model / "requests/response-002.json").read_bytes()
        for field, value in (("RequestId","SYNTHETIC-REQUEST-1"), ("RetryAttempts",1)):
            with self.subTest(field=field):
                (self.model / "requests/response-002.json").write_bytes(original)
                response = self.read("requests/response-002.json")
                response["raw_response"]["ResponseMetadata"][field] = value
                response["request_id" if field == "RequestId" else "retry_attempts"] = value
                write_json(self.model / "requests/response-002.json", response)
                with self.assertRaises(rt.native.EvidenceError):
                    self.audit()

    def test_protected_base_mutation_rejected(self):
        self.collect()
        p = self.model / "slots/slot-01/candidate/Base.dfy"
        p.write_bytes(p.read_bytes() + b"// changed immutable source\n")
        with self.assertRaisesRegex(rt.native.EvidenceError, "Guarded candidate"):
            self.audit()

    def test_stale_or_foreign_native_request_binding_rejected(self):
        self.collect()
        self.alter("slots/slot-01/native-dispatch.json", lambda value:value.update(request_id="SYNTHETIC-OTHER"))
        with self.assertRaisesRegex(rt.native.EvidenceError, "exact new request"):
            self.audit()

    def test_missing_native_unit_or_raw_artifact_rejected(self):
        self.collect()
        path = self.model / "slots/slot-01/native/raw/csv/TestResults/fake.csv"
        path.unlink()
        with self.assertRaises(rt.native.EvidenceError):
            self.audit()

    def test_coherent_raw_rehash_cannot_turn_omitted_unit_into_success(self):
        self.collect()
        folder = self.model / "slots/slot-01"
        raw_root = folder / "native/raw"
        csv_path = raw_root / "csv/TestResults/fake.csv"
        lines = csv_path.read_text().splitlines(True)
        changed = "".join([lines[0]] + [line for line in lines[1:] if not line.startswith("Base.Next")]).encode()
        csv_path.write_bytes(changed)
        (folder / "native/workspace/TestResults/fake.csv").write_bytes(changed)
        stdout = raw_root / "stdout.txt"
        stdout.write_bytes(stdout.read_bytes().replace(b"2 verified", b"1 verified"))
        raw = {p.relative_to(raw_root).as_posix():p.read_bytes() for p in raw_root.rglob("*") if p.is_file()}
        record = rt.read_json(folder / "native/record.json")
        record["raw_sha256"] = rt.native.hashes(raw)
        write_json(folder / "native/record.json", record)
        candidate = rt.source_files(folder / "candidate")
        profile = rt.read_json(folder / "native-profile.json")
        pins = rt.native.EvidencePins(rt.sha(rt.canonical(profile)), rt.sha(rt.canonical(record)),
            rt.sha(rt.canonical(rt.native.hashes(candidate))), tuple(sorted(rt.native.hashes(raw).items())),
            record["run_id"], "synthetic_offline")
        replay = rt.native.review(profile, candidate, record, raw, pins, allow_synthetic=True)
        self.assertFalse(replay["qualified_success"])
        self.assertFalse(replay["proof_coverage_complete"])
        write_json(folder / "native-review.json", replay)
        with self.assertRaisesRegex(rt.native.EvidenceError, "Recorded native outcome"):
            self.audit()

    def test_known_analyst_run_cannot_be_relabelled(self):
        self.collect()
        self.stages[("stdlib-filter",1)].native_profile["ineligible_parent_runs"] = ["SYNTHETIC-COLLECTION:slot-01"]
        # Rebind only the local saved profile to expose the additional denylist
        # check; production profiles cannot change because the freeze pins them.
        folder = self.model / "slots/slot-01"
        profile = rt.read_json(folder / "native-profile.json")
        profile["ineligible_parent_runs"] = ["SYNTHETIC-COLLECTION:slot-01"]
        write_json(folder / "native-profile.json", profile)
        for name in ("native-dispatch.json", "native/event.json"):
            self.alter("slots/slot-01/" + name, lambda value:value.update(profile_sha256=rt.sha(rt.canonical(profile))))
        with self.assertRaisesRegex(rt.native.EvidenceError, "Known analyst"):
            self.audit()

    def test_summary_denominator_per_task_and_observation_counters_rejected(self):
        self.collect()
        path = self.model / "summary.json"
        original = path.read_bytes()
        changes = (lambda s:s.update(reserved=7),
                   lambda s:s["per_task"]["stdlib-filter"].update(accepted=1),
                   lambda s:s.update(native_observations=9),
                   lambda s:s["rows"][0].update(accepted=False))
        for change in changes:
            with self.subTest(change=change):
                path.write_bytes(original)
                self.alter("summary.json", change)
                with self.assertRaises(rt.native.EvidenceError):
                    self.audit()

    def test_open_ledger_extra_response_and_child_receipt_are_rejected(self):
        self.collect()
        ledger = self.model / "requests/ledger.json"
        original = ledger.read_bytes()
        self.alter("requests/ledger.json", lambda value:value.update(closed=False))
        with self.assertRaisesRegex(rt.native.EvidenceError, "closed terminal"):
            self.audit()
        ledger.write_bytes(original)
        write_json(self.model / "requests/response-009.json", {})
        with self.assertRaisesRegex(rt.native.EvidenceError, "extra response"):
            self.audit()
        (self.model / "requests/response-009.json").unlink()
        write_json(self.model / "slots/slot-01/parent-receipt.json", {})
        with self.assertRaisesRegex(rt.native.EvidenceError, "child acceptance"):
            self.audit()

    def test_incomplete_authority_and_archive_tamper_rejected(self):
        authority = review.CollectionAuthority(b"{}", "0"*64, b"{}", "0"*64,
                                               b"{}", "0"*64, "SYNTHETIC", "synthetic")
        with self.assertRaisesRegex(rt.native.EvidenceError, "artifact identity"):
            review.review_collection(self.root, self.model, expected_runtime_sha256="0"*64, authority=authority)
        archive = self.root / "archive"
        archive.mkdir()
        (archive / "saved.txt").write_bytes(b"immutable")
        manifest = rt.canonical({"files":{"saved.txt":{"sha256":rt.sha(b"immutable")}}})
        self.assertEqual(review.review_archive(archive, manifest, rt.sha(manifest)), 1)
        (archive / "saved.txt").write_bytes(b"changed")
        with self.assertRaisesRegex(rt.native.EvidenceError, "archive file"):
            review.review_archive(archive, manifest, rt.sha(manifest))

    def test_production_api_rejects_synthetic_run_after_real_package_authority_checks(self):
        # Existing packaging fixtures explicitly say SYNTHETIC throughout. The
        # manufactured claim below is a negative-test artifact, never a live
        # authorization, allocation or model-origin acceptance receipt.
        from test_build_runtime import fixture
        from test_allocation import authorization
        self.collect()
        package = self.root / "synthetic-package"
        package.mkdir()
        config = fixture(package)
        for name in ("review_collection.py", "test_review_collection.py"):
            relative = "execution-002/" + name
            target = package / relative
            if not target.exists():
                target.write_bytes((Path(__file__).resolve().parent / name).read_bytes())
            config["runtime_inputs"].append(relative)
        write_json(package / "pilot/scope.json", config)
        manifest = package / "execution-002/runtime-freeze.json"
        freeze = review.build_runtime.build(package, "pilot/scope.json", manifest)
        runtime_sha = rt.sha(manifest.read_bytes())
        scope_sha = rt.sha((package / "pilot/scope.json").read_bytes())
        binding, budget_raw, counts = review.allocation.validate_frozen_budget(package, config)
        auth = authorization(binding)
        auth.update(scope_sha256=scope_sha, runtime_manifest_sha256=runtime_sha)
        auth_raw = rt.canonical(auth)
        claim = dict(schema="dafny-library-allocation-claim-v1", state="CONSUMED_NO_RESUME",
            created_at_epoch=2, authorization_sha256=rt.sha(auth_raw), scope_sha256=scope_sha,
            scope_canonical_sha256=rt.sha(rt.canonical(config)), runtime_manifest_sha256=runtime_sha,
            execution_binding=binding, budget_counts=counts,
            no_retry=True, no_resume=True, no_reassignment=True)
        claim_raw = rt.canonical(claim)
        for name, raw in (("authorization.json",auth_raw), ("allocation-claim.json",claim_raw),
                          ("budget-snapshot.json",budget_raw), ("runtime-freeze.json",rt.canonical(freeze))):
            rt.save_bytes(self.model / name, raw)
        authority = review.CollectionAuthority(auth_raw,rt.sha(auth_raw),claim_raw,rt.sha(claim_raw),
            budget_raw,rt.sha(budget_raw),"SYNTHETIC","synthetic")
        with self.assertRaisesRegex(rt.native.EvidenceError, "Synthetic collection"):
            review.review_collection(package,self.model,expected_runtime_sha256=runtime_sha,authority=authority)


if __name__ == "__main__":
    unittest.main(verbosity=2)
