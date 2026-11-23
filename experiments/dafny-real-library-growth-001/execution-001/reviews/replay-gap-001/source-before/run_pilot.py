"""One fresh twelve-slot pilot/expansion state machine; no resume or retries.

Importing this module performs no provider, credential, or native operation.
Production uses the fixed frozen renderer and FreshNativeHost. Fake transports
and synthetic native observations exist only through the explicit offline API.
"""
import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import socket
import time
import uuid

from runtime import (HERE, PACKAGE, MAX_CALLS, PILOT_SLOTS, canonical, checked_path,
                     file_snapshot, guard, json_copy, load_renderer, load_stages,
                     materialize_profile, native, parse_body_receipt, read_json, require,
                     save, save_bytes, save_sources, sha, source_files,
                     validate_authorization, validate_payload, validate_runtime,
                     validate_scope)
from bounded_requests import RequestGate
from credential_transport import ScopedBearerTransport, load_private_token, validate_failure_diagnostic


@dataclass
class AcceptedParent:
    sources: dict
    evidence: guard.ParentEvidence
    slot_id: str
    request_sequence: int
    response_sha256: str


class TerminalNativeError(RuntimeError):
    pass


class Runner:
    """Single process, one new output directory, one new bounded ledger."""
    def __init__(self, scope, stages, renderer, native_host, transport, output, *,
                 deadline, integrity_check, renderer_root=None, clock=time.time,
                 offline=False, run_id=None):
        self.scope = validate_scope(scope)
        self.stages = stages
        require(set(stages) == {(p, n) for p in ("stdlib", "aws") for n in (1, 2)},
                "Four qualified stages required")
        self.stage_pins = {(p, n): sha(canonical(dict(edit=s.edit_profile, native=s.native_profile,
                                      base=native.hashes(s.base_sources), adapter=s.adapter)))
                           for (p, n), s in stages.items()}
        self.renderer, self.renderer_root = renderer, renderer_root
        self.host, self.transport = native_host, transport
        self.offline = offline
        require(type(offline) is bool, "Explicit fake mode required")
        require(bool(getattr(native_host, "synthetic", False)) == offline, "Native host mode differs")
        if not offline:
            from native_host import FreshNativeHost
            require(type(native_host) is FreshNativeHost, "Production host is fixed")
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=False)
        self.run_id = run_id or self.scope["batch_id"] + ":" + uuid.uuid4().hex
        self.integrity_check = integrity_check
        self.clock = clock
        self.gate = RequestGate(self.output / "requests", MAX_CALLS, deadline, transport, clock=clock)
        self.parents, self.rows, self.snapshots, self.request_ids = {}, [], {}, set()
        self.native_dispatches = 0
        self.native_observations = 0
        self.fatal = None
        self.pilot_gate = None
        self.current_slot = None
        self.current_path = None
        self.executed = False
        save(self.output / "run.json", dict(schema="dafny-library-model-run-v1", run_id=self.run_id,
             scope_sha256=sha(canonical(self.scope)), offline=offline, synthetic=offline,
             max_calls=MAX_CALLS, no_retry=True, no_reassignment=True, no_resume=True))

    def _check(self):
        self.integrity_check()
        if not self.offline:
            self.host.check_tools(self.stages)
        require(self.clock() < self.gate.deadline, "Authorization deadline reached")
        for key, stage in self.stages.items():
            current = sha(canonical(dict(edit=stage.edit_profile, native=stage.native_profile,
                          base=native.hashes(stage.base_sources), adapter=stage.adapter)))
            require(current == self.stage_pins[key], "Stage inputs drifted in memory")
        for slot_id, expected in self.snapshots.items():
            require(file_snapshot(self.output / "slots" / slot_id) == expected,
                    "Completed slot evidence drifted")
        require(read_json(self.output / "requests" / "ledger.json") == self.gate.state,
                "Durable request ledger differs")
        completed = [r for r in self.gate.state["reservations"] if r["status"] == "COMPLETED"]
        require(all(r["status"] == "COMPLETED" for r in self.gate.state["reservations"]),
                "Unresolved request prevents dispatch")
        for row in self.rows:
            if row.get("request_sequence") is None:
                continue
            matches = [r for r in completed if r["sequence"] == row["request_sequence"]]
            require(len(matches) == 1 and matches[0]["task_id"] == row["id"],
                    "Response provenance does not match this completed reservation")
            response = read_json(self.output / "requests" / ("response-%03d.json" % row["request_sequence"]))
            require(sha(canonical(response)) == row["response_sha256"]
                    and response["request_id"] == row["request_id"], "Saved provider response drifted")
        for parent in self.parents.values():
            row = next((r for r in self.rows if r["id"] == parent.slot_id), None)
            require(row and row["accepted"] and row["request_sequence"] == parent.request_sequence
                    and row["response_sha256"] == parent.response_sha256,
                    "Parent was not accepted in this current run")
            require(parent.evidence.receipt["host_run_id"] == self.run_id
                    and parent.evidence.receipt["slot_id"] == parent.slot_id,
                    "Foreign accepted parent receipt")
            require(source_files(self.output / "slots" / parent.slot_id / "candidate") == parent.sources,
                    "Accepted parent source drifted")
            receipt = read_json(self.output / "slots" / parent.slot_id / "parent-receipt.json")
            require(receipt == parent.evidence.receipt
                    and sha(canonical(receipt)) == parent.evidence.receipt_sha256,
                    "Accepted parent receipt drifted")

    def _prepare(self, slot):
        stage = self.stages[(slot["project"], slot["stage"])]
        parent = self.parents.get((slot["project"], slot["chain_id"]))
        if slot["stage"] == 2 and parent is None:
            return None
        sources = dict(stage.base_sources if slot["stage"] == 1 else parent.sources)
        kwargs = {"root": self.renderer_root}
        if slot["stage"] == 1:
            require(native.hashes(sources) == stage.edit_profile["base_source_sha256"], "Base source differs")
            rendered = self.renderer.render_stage1(slot["project"], slot["chain_id"], **kwargs)
            parent_audit = None
        else:
            parent_audit = guard.validate_parent(stage.edit_profile, sources, slot["chain_id"],
                                                parent.evidence, allow_synthetic=self.offline)
            rendered = self.renderer.render_stage2(slot["project"], slot["chain_id"], sources,
                       parent.evidence, allow_synthetic=self.offline, **kwargs)
        expected = dict(project=slot["project"], stage=slot["stage"],
                        stage_id=stage.edit_profile["stage_id"], chain_id=slot["chain_id"],
                        guard_profile_sha256=sha(canonical(stage.edit_profile)),
                        source_revision_sha256=sha(canonical(native.hashes(sources))),
                        parent_audit=parent_audit, dispatch_eligible=False)
        require(isinstance(rendered, dict) and all(rendered.get(k) == v for k, v in expected.items()),
                "Prompt/source/parent binding differs")
        validate_payload(rendered["payload"], self.scope["settings"])
        require(rendered.get("payload_sha256") == sha(canonical(rendered["payload"])), "Payload digest differs")
        return stage, sources, parent, rendered

    def _finish_row(self, row):
        save(self.current_path / "outcome.json", row)
        self.rows.append(row)
        self.snapshots[row["id"]] = file_snapshot(self.current_path)

    def _accept_parent(self, slot, sources, profile, observation, pins, report, row):
        # Called only after this run's durable response, guard reconstruction,
        # fresh host event, complete native replay and qualified success.
        sequence = row["request_sequence"]
        reservation = self.gate.state["reservations"][sequence - 1]
        require(reservation["status"] == "COMPLETED" and reservation["task_id"] == slot["id"],
                "No current completed reservation")
        require(row["request_id"] in self.request_ids and row["accepted"], "Unaccepted model output")
        origin = "synthetic_offline" if self.offline else "model_candidate"
        receipt = dict(schema=guard.RECEIPT_SCHEMA, project=slot["project"], stage=1,
            stage_id=profile["stage_id"], chain_id=slot["chain_id"], origin=origin,
            guard_profile_sha256=sha(canonical(self.stages[(slot["project"], 1)].edit_profile)),
            source_revision_sha256=report["source_revision_sha256"],
            native_profile_sha256=report["profile_sha256"],
            native_record_sha256=report["record_sha256"], native_run_id=report["run_id"],
            native_raw_fingerprint_sha256=report["raw_fingerprint_sha256"],
            accepted=True, request_id=row["request_id"], response_sha256=row["response_sha256"],
            request_sequence=sequence, host_run_id=self.run_id, slot_id=slot["id"],
            native_event_sha256=observation.event_sha256, synthetic=self.offline)
        save(self.current_path / "parent-receipt.json", receipt)
        evidence = guard.ParentEvidence(profile, observation.record, observation.raw, pins,
                                        receipt, sha(canonical(receipt)))
        parent = AcceptedParent(dict(sources), evidence, slot["id"], sequence, row["response_sha256"])
        self.parents[(slot["project"], slot["chain_id"])] = parent

    def _slot(self, slot):
        self.current_slot = slot
        self.current_path = self.output / "slots" / slot["id"]
        self.current_path.mkdir(parents=True, exist_ok=False)
        row = dict(slot, accepted=False, request_sequence=None, native_invoked=False,
                   response_sha256=None, request_id=None, synthetic=self.offline)
        prepared = self._prepare(slot)
        if prepared is None:
            row.update(outcome="BLOCKED_PARENT", category=None)
            self._finish_row(row)
            return
        stage, sources, parent, rendered = prepared
        save(self.current_path / "prompt.json", rendered)
        self._check()
        response = self.gate.invoke(rendered["payload"], task_id=slot["id"],
                                    attempt_id=self.run_id + ":" + slot["id"])
        sequence = len(self.gate.state["reservations"])
        require(isinstance(response, dict) and isinstance(response.get("request_id"), str)
                and response["request_id"] and response["request_id"] not in self.request_ids,
                "Missing or repeated provider request identity")
        require(type(response.get("retry_attempts")) is int and response["retry_attempts"] == 0,
                "Unexpected SDK retry count")
        self.request_ids.add(response["request_id"])
        row.update(request_sequence=sequence, response_sha256=sha(canonical(response)),
                   request_id=response["request_id"])
        save(self.current_path / "response-binding.json",
             dict(request_sequence=sequence, request_id=row["request_id"], response_sha256=row["response_sha256"]))
        try:
            body, envelope = parse_body_receipt(response.get("text"))
            # This is the only policy rejection catch. Input/provenance errors
            # in reconstruct remain terminal rather than model failures.
            guard.render_body(stage.edit_profile, body)
        except native.EvidenceError as error:
            row.update(outcome="OUTPUT_REJECTED", category="ENVELOPE_OR_BODY_POLICY",
                       rejection_type=type(error).__name__)
            self._finish_row(row)
            return
        save_bytes(self.current_path / "body.txt", body.encode("utf-8"))
        save(self.current_path / "envelope.json", envelope)
        candidate, edit_review = guard.reconstruct(stage.edit_profile, body, sources, slot["chain_id"],
                        parent=parent.evidence if parent else None, allow_synthetic=self.offline)
        save_sources(self.current_path / "candidate", candidate)
        save(self.current_path / "edit-review.json", edit_review)
        profile = materialize_profile(stage.native_profile, candidate)
        save(self.current_path / "native-profile.json", profile)
        native_id = self.run_id + ":" + slot["id"]
        event = dict(schema="dafny-library-fresh-native-event-v1", host_run_id=self.run_id,
                     run_id=native_id, slot_id=slot["id"], request_id=row["request_id"],
                     request_sequence=sequence, response_sha256=row["response_sha256"],
                     payload_sha256=rendered["payload_sha256"],
                     candidate_sha256=sha(canonical(native.hashes(candidate))),
                     profile_sha256=sha(canonical(profile)), nonce=uuid.uuid4().hex,
                     synthetic=self.offline)
        save(self.current_path / "native-dispatch.json", event)
        self.native_dispatches += 1
        observation = self.host.run(profile, candidate, event, self.current_path / "native", stage.adapter)
        from native_host import NativeObservation
        require(type(observation) is NativeObservation, "Fresh native host result required")
        require(observation.event_sha256 == sha(canonical(event)) and observation.record["run_id"] == native_id,
                "Native result does not belong to this fresh dispatch")
        expected_origin = "synthetic_offline" if self.offline else "model_candidate"
        require(observation.record["origin"] == expected_origin, "Analyst/baseline evidence cannot be model evidence")
        require(observation.record["run_id"] not in profile["ineligible_parent_runs"]
                and sha(canonical(native.hashes(observation.raw))) not in profile["ineligible_parent_raw_fingerprints"],
                "Known qualification evidence is ineligible")
        require(read_json(self.current_path / "native" / "event.json") == event
                and read_json(self.current_path / "native" / "record.json") == observation.record,
                "Fresh native disk receipt differs")
        require(file_snapshot(self.current_path / "native" / "raw") == native.hashes(observation.raw),
                "Saved native raw evidence differs")
        require(source_files(self.current_path / "native" / "workspace") == candidate,
                "Actual native workspace differs")
        self.native_observations += 1
        row["native_invoked"] = True
        pins = native.EvidencePins(sha(canonical(profile)), sha(canonical(observation.record)),
                 sha(canonical(native.hashes(candidate))), tuple(sorted(native.hashes(observation.raw).items())),
                 native_id, expected_origin)
        report = native.review(profile, candidate, observation.record, observation.raw, pins,
                               allow_synthetic=self.offline)
        save(self.current_path / "native-review.json", report)
        category = report["category"]
        row.update(category=category, native_run_id=native_id,
                   native_record_sha256=report["record_sha256"], passed_units=report["passed_units"],
                   failed_units=report["failed_units"], warnings=report["warnings"],
                   elapsed_seconds=report["elapsed_seconds"], accepted=report["qualified_success"])
        if report["qualified_success"]:
            row["outcome"] = "ACCEPTED"
            if slot["stage"] == 1:
                self._accept_parent(slot, candidate, profile, observation, pins, report, row)
        else:
            # A closed verifier-resource result is a nonacceptance only when
            # the process returned normally with complete exact unit coverage.
            resource_closed = (category in {"RESOURCE_FAILURE", "VERIFIER_TIMEOUT"}
                and observation.record["exit_code"] == 4 and not observation.record["timeout"]
                and report["resources"]["complete"] and report["resources"]["exit_status"] == 4
                and report["proof_coverage_complete"])
            nonfatal = (category == "PROOF_FAILURE" or resource_closed) and report["warning_policy_matches"]
            row["outcome"] = "NATIVE_REJECTED" if nonfatal else "TERMINAL_NATIVE_FAILURE"
            self._finish_row(row)
            if not nonfatal:
                raise TerminalNativeError(category)
            return
        self._finish_row(row)

    def _pilot_review(self):
        self._check()
        require(len(self.rows) == PILOT_SLOTS and all(r["cohort"] == "pilot" for r in self.rows),
                "Incomplete pilot accounting")
        accepted_first = sum(r["stage"] == 1 and r["accepted"] for r in self.rows)
        result = dict(schema="dafny-library-pilot-continuation-v1", complete_accounting=True,
             accepted_first_stages=accepted_first, infrastructure_failure=False,
             continue_expansion=accepted_first >= 1, reservations=len(self.gate.state["reservations"]),
             response_count=len(self.request_ids), synthetic=self.offline,
             artifacts={row["id"]:self.snapshots[row["id"]] for row in self.rows})
        save(self.output / "pilot-continuation.json", result)
        self.pilot_gate = result
        return result["continue_expansion"]

    def run(self):
        require(not self.executed, "A Runner cannot restart or resume")
        self.executed = True
        stopped = "COMPLETE"
        try:
            self._check()
            self.host.prepare(self.stages, self.output / "native-preflight")
            for index, slot in enumerate(self.scope["slots"]):
                if index == PILOT_SLOTS and not self._pilot_review():
                    stopped = "PILOT_STOPPED"
                    break
                self._check()
                self._slot(slot)
            self._check()
        except BaseException as error:
            stopped = "TERMINAL"
            self.fatal = dict(error_type=type(error).__name__,
                              slot_id=self.current_slot["id"] if self.current_slot else None)
            # Never archive arbitrary exception text, traceback or environment.
            if isinstance(error, TerminalNativeError):
                self.fatal["native_category"] = str(error)
            try:
                diagnostic = getattr(self.transport, "failure_diagnostic", lambda: None)()
                if diagnostic is not None:
                    save(self.output / "transport-failure.json", validate_failure_diagnostic(diagnostic))
            except BaseException:
                self.fatal["transport_diagnostic_unavailable"] = True
            save(self.output / "fatal.json", self.fatal)
        finally:
            self.gate.close(stopped.lower())
        reservations = self.gate.state["reservations"]
        summary = dict(schema="dafny-library-growth-summary-v1", run_id=self.run_id, status=stopped,
             declared_slots=MAX_CALLS, reserved=len(reservations),
             completed=sum(r["status"] == "COMPLETED" for r in reservations),
             ambiguous_or_unsaved=sum(r["status"] == "AMBIGUOUS_OR_UNSAVED" for r in reservations),
             accepted_stages=sum(r["accepted"] for r in self.rows),
             accepted_parents=sum(r["accepted"] and r["stage"] == 1 for r in self.rows),
             completed_lineages=sum(r["accepted"] and r["stage"] == 2 for r in self.rows),
             blocked_children=sum(r["outcome"] == "BLOCKED_PARENT" for r in self.rows),
             native_dispatches=self.native_dispatches, native_observations=self.native_observations,
             unused_request_capacity=MAX_CALLS-len(reservations),
             recorded_slots=len(self.rows), unprocessed_slots=MAX_CALLS-len(self.rows),
             rows=self.rows, fatal=self.fatal, synthetic=self.offline,
             no_retry=True, no_reassignment=True, no_resume=True, earlier_scores_unchanged=True)
        save(self.output / "summary.json", summary)
        return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--runtime-freeze", type=Path, required=True)
    parser.add_argument("--expected-runtime-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-handoff", type=Path, required=True)
    args = parser.parse_args()
    require(os.environ.get("SLURM_JOB_ID") and "login" not in socket.gethostname().lower()
            and os.environ.get("SLURM_CPUS_PER_TASK") == "1", "One-CPU compute node required")
    freeze = validate_runtime(PACKAGE, args.runtime_freeze, args.expected_runtime_sha)
    scope_path = args.scope.resolve()
    require(scope_path.is_relative_to(PACKAGE.resolve())
            and freeze["files"].get(scope_path.relative_to(PACKAGE.resolve()).as_posix()) == sha(scope_path.read_bytes()),
            "Scope must be frozen")
    from build_runtime import validate_complete
    freeze, scope, stages = validate_complete(PACKAGE, scope_path.relative_to(PACKAGE.resolve()).as_posix(),
                                             args.runtime_freeze, args.expected_runtime_sha)
    auth = read_json(args.authorization)
    deadline = validate_authorization(auth, sha(scope_path.read_bytes()), args.expected_runtime_sha, time.time())
    auth_sha = sha(args.authorization.read_bytes())
    renderer = load_renderer(PACKAGE, scope["renderer"])
    def integrity():
        validate_runtime(PACKAGE, args.runtime_freeze, args.expected_runtime_sha)
        require(sha(args.authorization.read_bytes()) == auth_sha, "Authorization drifted")
    from native_host import FreshNativeHost
    host = FreshNativeHost()
    transport = ScopedBearerTransport(scope["settings"], lambda: load_private_token(args.private_handoff))
    runner = Runner(scope, stages, renderer, host, transport, args.output,
                    deadline=deadline, integrity_check=integrity, renderer_root=PACKAGE)
    save(args.output / "authorization.json", auth)
    save(args.output / "runtime-freeze.json", freeze)
    result = runner.run()
    print(canonical({k:result[k] for k in ("status", "reserved", "completed", "accepted_stages", "fatal")}).decode())
    raise SystemExit(0 if result["status"] in {"COMPLETE", "PILOT_STOPPED"} else 2)


if __name__ == "__main__":
    main()

