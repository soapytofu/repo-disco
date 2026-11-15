"""Offline review of two fresh compute observations and eight exact reused controls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
FIX = ROOT / "fixtures-and-controls"
EVIDENCE = FIX / "verification-001"
PINS = {
    "fixtures-and-controls/runtime-manifest.json": "268318d233861c592dc7d0ba52dcf34ce81cbc65fde80f024aa9f7e8560d45a2",
    "fixtures-and-controls/fixture-manifest.json": "e631e5c85dc74ffb5dc0674053a4c13f0f3b5c5face61ea16465bf8ba48068cb",
    "protocol/policy-manifest.json": "c6fdae216ad20a7291391c64dbdf60c17cdbc4f956d0b5afe7c6de138872fe6a",
    "measurement/measurement-manifest.json": "02e6f053757c057503da7464de8677c4728d9a031746cb880d0849fcb1733e5a",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def review():
    for name, digest in PINS.items():
        assert sha(ROOT / name) == digest, name
    for name, key in [("protocol/policy-manifest.json", "files"),
                      ("measurement/measurement-manifest.json", "files_sha256")]:
        for relative, digest in load(ROOT / name)[key].items():
            assert sha((ROOT / name).parent / relative) == digest, relative
    measure = module("migration_seed_measurement", ROOT / "measurement/measure.py")
    verifier = module("migration_seed_verifier", FIX / "verify.py")
    builder = module("migration_seed_builder", FIX / "build.py")
    verifier.validate_pins(FIX)
    verifier.validate_pins(EVIDENCE)
    builder.validate_inputs(FIX)
    transfer = load(FIX / "transfer-001.json")
    for name, digest in transfer["files"].items():
        assert sha(FIX / name) == digest, name
    archived = load(EVIDENCE / "evidence-manifest.json")
    assert {n: h for n, h in measure.inventory(EVIDENCE).items()
            if n != "evidence-manifest.json"} == archived
    environment = load(EVIDENCE / "environment.json")
    submission = load(FIX / "submission-001.json")
    assert environment["job_id"] == submission["job_id"] == "60865223"
    assert environment["partition"] == "test" and "login" not in environment["host"]
    assert "PreemptMode=OFF" in submission["live_partition"] and submission["no_requeue"]
    assert environment["model_calls"] == submission["model_calls"] == 0
    assert "60865223|COMPLETED|00:00:30|0:0|" in (FIX / "accounting-60865223.txt").read_text()
    assert not (FIX / "verify-60865223.err").read_bytes()
    for program, expected in [("dafny", verifier.DAFNY_VERSION), ("z3", verifier.Z3_VERSION)]:
        version = environment[program]
        assert version["exit_code"] == 0 and version["stdout"].strip() == expected
        assert (EVIDENCE / (program + "-version.stdout")).read_bytes() == version["stdout"].encode()
        assert (EVIDENCE / (program + "-version.stderr")).read_bytes() == version["stderr"].encode() == b""
    for name in ("runtime", "fixture"):
        assert environment[name + "_manifest_sha256"] == sha(FIX / (name + "-manifest.json"))
    tasks = {t["task_id"]: t for t in load(FIX / "tasks.json")}
    guard = measure.guard_module()

    def score(task_id, folder, record_path, raw_path):
        task = tasks[task_id]
        files = measure.sources(folder)
        seed = measure.sources(FIX / "fixtures" / task_id / "seed")
        bodies = measure.candidate_bodies(files, task)
        rebuilt, receipt = guard.parse_response(measure.canonical(bodies).decode(),
            {n: b.decode() for n, b in seed.items()}, task)
        assert {n: b.encode() for n, b in rebuilt.items()} == files
        raw = {n: (raw_path / n).read_bytes() for n in measure.inventory(raw_path)}
        record = load(record_path)
        result = measure.score_candidate(task_id, files, measure.source_hashes(files), receipt, record, raw)
        return result, record

    summary = load(EVIDENCE / "summary.json")
    assert summary["completed"] == summary["planned"] == 2 and summary["all_expected"]
    assert summary["model_calls"] == 0
    rows = []
    for case in load(FIX / "cases.json"):
        path = EVIDENCE / (case["case_id"] + ".json")
        result, record = score(case["task_id"], EVIDENCE / case["path"], path,
                               EVIDENCE / "raw" / case["case_id"])
        assert verifier.matches(case, record) and record["matched"]
        assert record["named_evidence"] == verifier.named_details(case, record)
        assert result["outcome"] == "PROOF_FAILURE" and not result["strict_workspace_verified"]
        assert result["warning_count"] == 0
        assert result["named_evidence"]["local_targets"] == {"Helper.Transfer": False, "Client.Target": False}
        assert sha(path) == next(r for r in summary["checks"] if r["case_id"] == case["case_id"])["evidence_sha256"]
        assert measure.source_hashes(measure.sources(FIX / case["path"])) == result["source_sha256"]
        rows.append(dict(case_id=case["case_id"], record_sha256=sha(path),
            source_sha256=result["source_sha256"], raw_sha256=result["raw_sha256"],
            outcome=result["outcome"], named_evidence=result["named_evidence"],
            target_diagnostics=record["named_evidence"]["target_diagnostics"],
            new_verifier_observation=True, guard_receipt_sha256=result["guard_receipt_sha256"]))
    reused = []
    for control in load(FIX / "reused-controls.json"):
        for n, digest in control["source_sha256"].items():
            assert sha(FIX / control["path"] / n) == sha(REPO / control["original_source_path"] / n) == digest
        path = FIX / control["evidence_path"]
        assert sha(path) == sha(REPO / control["original_evidence_path"]) == control["evidence_sha256"]
        result, record = score(control["task_id"], FIX / control["path"], path,
            path.parent / "raw" / control["parent_case_id"])
        assert result["strict_workspace_verified"] == control["strict_workspace_verified"]
        assert result["named_evidence"]["local_targets"] == control["observed_local_targets"]
        assert result["inherited_classifier_category"] == control["actual"]
        reused.append(dict(control_id=control["control_id"], original_job_id=control["original_job_id"],
            record_sha256=sha(path), source_sha256=result["source_sha256"],
            outcome=result["outcome"], named_evidence=result["named_evidence"],
            new_verifier_observation=False, guard_receipt_sha256=result["guard_receipt_sha256"]))
    assert len(rows) == 2 and len(reused) == 8
    return dict(schema="internal-contract-repair-seed-gate-v1", all_expected=True,
        job_id="60865223", new_verifier_checks=2, reused_observations=8,
        new_model_calls=0, execution_authorized=False, pinned_bundles=PINS,
        review_code_sha256=sha(Path(__file__)), transfer_manifest_sha256=sha(FIX / "transfer-001.json"),
        raw_evidence_manifest_sha256=sha(EVIDENCE / "evidence-manifest.json"),
        environment_sha256=sha(EVIDENCE / "environment.json"), fresh_checks=rows, reused_checks=reused,
        limitation="Two fixed-target development migrations; reused controls are not new independent trials. Local client proof assumes the helper contract. No model result or necessary-edit claim.")


if __name__ == "__main__":
    print(json.dumps(review(), indent=2))
