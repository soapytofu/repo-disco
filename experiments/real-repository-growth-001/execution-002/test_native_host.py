"""Fake processes and explicitly synthetic evidence only. No native/model calls.

fixture_result is a TEST-ONLY helper for host/reviewer integration tests. Its
fabricated verifier rows never claim to prove the supplied source mathematically.
"""
from collections import defaultdict
from dataclasses import asdict, replace
import csv
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import native_host as h

REPO = Path(__file__).resolve().parents[3]


def fake_raw(slot, scope, *, outcome="pass"):
    """Fabricate a full parser-shaped inventory; explicitly not native evidence."""
    failed = outcome == "proof_failure"
    missing = outcome == "missing_coverage"
    project, stage = slot["project"], slot["stage"]
    target = ("MoveToFront" if stage == 1 else "PickPair") if project == "dafny-vmc" else (
        "frame_roundtrip" if stage == 1 else "batch_roundtrip")
    expected = scope["required_inventory"]
    if outcome == "frontend":
        return {"stdout.txt": b"SYNTHETIC TEST ONLY\n1 parse errors detected\n", "stderr.txt": b"",
                "resources.txt": b"SYNTHETIC TEST RESOURCES\n"}, 2
    if project == "dafny-vmc":
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(["TestResult.DisplayName", "TestResult.Outcome", "TestResult.Duration", "TestResult.ResourceCount"])
        rows = [name for name in sorted(expected) if not(missing and target in name)]
        for name in rows:
            writer.writerow([name, "Failed" if failed and target in name else "Passed", "00:00:00", "0"])
        warnings = list(scope["upstream_warnings"])
        if outcome == "warning": warnings.append("synthetic.dfy(1,1): Warning: synthetic diagnostic")
        text = "SYNTHETIC TEST ONLY; NO VERIFIER RAN\n" + "\n".join(warnings) + "\n"
        text += f"Dafny program verifier finished with {len(rows)-int(failed)} verified, {int(failed)} errors\n"
        return {"stdout.txt": text.encode(), "stderr.txt": b"", "resources.txt": b"SYNTHETIC TEST RESOURCES\n",
                "csv/TestResults/synthetic.csv": stream.getvalue().encode()}, 4 if failed else (2 if outcome == "warning" else 0)
    grouped = defaultdict(lambda: defaultdict(list))
    for key, count in expected.items():
        crate, module, label, mode = json.loads(key)
        if missing and label.endswith("::" + target): continue
        for _ in range(count):
            grouped[crate][module].append({"function": label, "mode:": mode,
                "success": not(failed and label.endswith("::" + target)), "synthetic_test_fixture": True})
    reports = []
    for crate, modules in sorted(grouped.items()):
        bad = failed and crate == "vest_dev"
        verified = {"vstd": 2102, "vest_lib": 3279, "vest_dev": 341 if stage == 1 else 346}[crate]
        reports.append({"verus": scope["verus_metadata"]["version"],
            "verification-results": {"encountered-vir-error": False, "encountered-error": bool(bad),
                "errors": int(bad), "verified": verified - int(bad), "is-verifying-entire-crate": True, "success": not bad},
            "times-ms": {"num-threads": 1, "smt": {"smt-run-module-times": [
                {"module": module, "function-breakdown": records} for module, records in sorted(modules.items())]}}})
    stdout = "SYNTHETIC TEST ONLY; NO VERIFIER RAN\n" + "\n".join(json.dumps(r, sort_keys=True) for r in reports) + "\n"
    warnings = list(scope["upstream_warnings"])
    if outcome == "warning": warnings.append("warning: synthetic unclassified warning")
    return {"stdout.txt": stdout.encode(), "stderr.txt": ("\n\n".join(warnings)+"\n\n").encode(),
            "resources.txt": b"SYNTHETIC TEST RESOURCES\n"}, 101 if failed else 0


def fixture_result(slot, sources, repo=REPO, *, run_id="synthetic-host:slot", outcome="pass"):
    """TEST ONLY: create a fully shaped synthetic result for either stage.

    It is rejected by production defaults. No source is mathematically verified,
    no request provenance or accepted receipt is fabricated, and no file is made.
    """
    api = h.protocol_api(repo)
    slot = h._slot(slot, repo)
    hashes = api.b.check_workspace(slot["project"], slot["stage"], sources)
    scope, gate_raw, tools_raw = h._scope(slot["project"], slot["stage"], repo)
    command = [x.replace("<WORKSPACE>", "/synthetic/workspace").replace("<FRESH_TARGET>", "/synthetic/target")
               for x in scope["command_template"]]
    raw, exit_code = fake_raw(slot, scope, outcome=outcome)
    profile = dict(project=slot["project"], source_sha256=hashes, logical_command=scope["logical_command"],
                   toolchain=scope["toolchain"], resources=scope["resources"], model_calls=0, synthetic_offline_fixture=True)
    record = dict(command=command, cwd="/synthetic", exit_code=exit_code, elapsed_seconds=1.0,
                  timeout=False, model_calls=0, attempts=1, synthetic_offline_fixture=True,
                  artifacts={name: h.sha(raw[name]) for name in ("stdout.txt", "stderr.txt", "resources.txt")})
    bound = dict(run_id=run_id, profile_sha256=h.sha(h.canonical(profile)), source_sha256=hashes,
                 source_after_sha256=hashes, logical_command=scope["logical_command"], toolchain=scope["toolchain"],
                 raw_sha256={name: h.sha(data) for name, data in sorted(raw.items())}, model_calls=0, attempts=1,
                 exit_code=exit_code, elapsed_seconds=1.0, synthetic_offline_fixture=True)
    native_scope = dict(schema="repodisco-native-growth-scope-v2", project=slot["project"], stage=slot["stage"],
        qualification_gate_sha256=h.sha(gate_raw), readiness=scope["readiness"], command_sha256=h.sha(h.canonical(command)),
        logical_command=scope["logical_command"], toolchain=scope["toolchain"], tools_record_sha256=scope["tools_record_sha256"],
        warning_policy_sha256=scope["warning_policy_sha256"], upstream_warnings=scope["upstream_warnings"],
        required_inventory=scope["required_inventory"],
        unlogged_definitions=[dict(item, source_sha256=hashes[item["file"]]) for item in scope["fixed_unlogged_units"]])
    if slot["project"] == "vest": native_scope["verus_metadata"] = scope["verus_metadata"]
    artifacts = {**raw, "scope.json": h.canonical(native_scope), "qualification-gate.json": gate_raw,
        "profile.json": h.canonical(profile), "record.json": h.canonical(record), "bound-record.json": h.canonical(bound),
        "tools-before.json": tools_raw, "tools-after.json": tools_raw}
    binding = api.NativeBinding(slot["project"], slot["stage"], "synthetic-offline", run_id,
        api.b.digest_map(hashes), h.PROTOCOL_RUNTIME_SHA256, tuple(sorted((name,h.sha(data)) for name,data in artifacts.items())))
    extraction = h.audit_candidate_native(binding, artifacts, sources, repo, allow_synthetic=True)
    classification, terminal = h.classify(extraction)
    return h.NativeResult(binding, artifacts, extraction, classification, terminal, Path("/synthetic"), True)


class FakeProcess:
    def __init__(self, slot, scope, outcome="pass"):
        self.slot, self.scope, self.outcome = slot, scope, outcome
        self.calls = []

    def __call__(self, args, *, cwd, env, stdout, stderr, timeout):
        self.calls.append(dict(args=args, cwd=cwd, timeout=timeout, environment_keys=sorted(env)))
        if self.outcome == "raise": raise h.NativeLaunchError("synthetic process creation failure")
        raw, code = fake_raw(self.slot, self.scope,
                             outcome=self.outcome if self.outcome in ("pass","proof_failure","missing_coverage","warning","frontend") else "pass")
        stdout.write(raw["stdout.txt"]); stderr.write(raw["stderr.txt"])
        if self.outcome != "missing_resources": Path(args[3]).write_bytes(raw["resources.txt"])
        work = Path(args[args.index("--pwd")+1])
        for name,data in raw.items():
            if name.startswith("csv/"):
                path=work/name[4:];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        if self.outcome == "source_mutation":
            path=work/"README.md";path.write_bytes(path.read_bytes()+b"SYNTHETIC MUTATION\n")
        if self.outcome == "timeout": raise subprocess.TimeoutExpired(args,timeout)
        if self.outcome == "signal": return -9
        return code


class NativeHostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api=h.protocol_api(REPO)
        cls.slots=h._pilot(REPO)[1]
        cls.sources={}
        for project in ("dafny-vmc","vest"):
            _,_,parent,_=cls.api.control_material(project,"move-alternative" if project=="dafny-vmc" else "frame-alternative",REPO)
            _,_,full,_=cls.api.n.reference_material(project,REPO)
            cls.sources[(project,1)]=parent;cls.sources[(project,2)]=full

    def adapter(self,slot,outcome="pass",**kwargs):
        scope,_,_=h._scope(slot['project'],slot['stage'],REPO)
        fake=FakeProcess(slot,scope,outcome)
        env=dict(SLURM_JOB_ID="SYNTHETIC",SLURM_CPUS_PER_TASK="1",SLURM_JOB_PARTITION="test",SLURM_NTASKS="1",SLURM_JOB_NUM_NODES="1")
        adapter=h.NativeVerifier(REPO,process_runner=fake,tool_observer=lambda project,expected:expected,
            environment=env,hostname="synthetic-compute",synthetic=True,**kwargs)
        return adapter,fake

    def test_fake_one_invocation_both_projects_both_stages_full_scope_and_replay(self):
        for slot in self.slots[:4]:
            with self.subTest(project=slot['project'],stage=slot['stage']),tempfile.TemporaryDirectory(prefix="repodisco-native-fake-") as tmp:
                adapter,fake=self.adapter(slot);sources=self.sources[(slot['project'],slot['stage'])]
                result=adapter.verify(slot,sources,Path(tmp).resolve()/"run", "synthetic-run:"+slot['slot_id'])
                self.assertEqual(result.classification,"QUALIFIED_PASS",result.error)
                self.assertFalse(result.terminal);self.assertEqual(len(fake.calls),1)
                self.assertEqual(result.native_invocations,1);self.assertTrue(result.invocation_attempted)
                self.assertEqual(fake.calls[0]['timeout'],325 if slot['project']=='dafny-vmc' else 925)
                self.assertEqual(fake.calls[0]['args'][7],"300s" if slot['project']=='dafny-vmc' else "900s")
                self.assertTrue(h.audit_result(slot,sources,result,REPO,allow_synthetic=True)['qualified_pass'])
                with self.assertRaises(ValueError):h.audit_result(slot,sources,result,REPO)
                self.assertNotIn("native-units.json",result.artifacts)
                self.assertFalse((result.destination/'accepted.json').exists())
                for name,digest in result.binding.artifact_sha256:
                    if name in ('stdout.txt','stderr.txt','resources.txt','record.json') or name.startswith('csv/'):
                        path=result.destination/'native'/name
                    else:path=result.destination/name
                    self.assertEqual(h.file_sha(path),digest)
                with self.assertRaises(ValueError):adapter.verify(slot,sources,result.destination,"other-run")
                self.assertEqual(len(fake.calls),1)

    def test_proof_failure_is_returned_outcome_not_retry(self):
        slot=self.slots[0]
        with tempfile.TemporaryDirectory() as tmp:
            adapter,fake=self.adapter(slot,"proof_failure")
            result=adapter(slot,self.sources[('dafny-vmc',1)],Path(tmp).resolve()/'run','synthetic-failure')
            self.assertEqual(result.classification,'PROOF_FAILURE');self.assertFalse(result.terminal)
            self.assertEqual(len(fake.calls),1)
            self.assertFalse(result.extraction['qualified_pass'])

    def test_warning_only_is_preserved_unaccepted_returned_outcome(self):
        slot=self.slots[0]
        with tempfile.TemporaryDirectory() as tmp:
            adapter,fake=self.adapter(slot,"warning");result=adapter(slot,self.sources[('dafny-vmc',1)],Path(tmp).resolve()/'run','synthetic-warning')
            self.assertEqual(result.classification,'WARNING_POLICY_REJECTION');self.assertFalse(result.terminal)
            self.assertEqual(result.extraction['native_exit_code'],2);self.assertEqual(len(fake.calls),1)

    def test_timeout_signal_frontend_missing_coverage_and_resources_are_terminal(self):
        slot=self.slots[0]
        for outcome in ('timeout','signal','frontend','missing_coverage','missing_resources','raise'):
            with self.subTest(outcome=outcome),tempfile.TemporaryDirectory() as tmp:
                adapter,fake=self.adapter(slot,outcome);result=adapter(slot,self.sources[('dafny-vmc',1)],Path(tmp).resolve()/'run','synthetic-'+outcome)
                self.assertTrue(result.terminal);self.assertTrue(result.classification.startswith('TERMINAL_'))
                self.assertEqual(len(fake.calls),1)
                self.assertEqual(result.native_invocations,0 if outcome=='raise' else 1)
                self.assertTrue((result.destination/'native/stdout.txt').exists())
                self.assertFalse((result.destination/'accepted.json').exists())

    def test_source_mutation_stops_and_preserves_before_after_and_native_raw(self):
        slot=self.slots[0]
        with tempfile.TemporaryDirectory() as tmp:
            adapter,fake=self.adapter(slot,'source_mutation');result=adapter(slot,self.sources[('dafny-vmc',1)],Path(tmp).resolve()/'run','synthetic-source')
            self.assertTrue(result.terminal);self.assertIsNone(result.extraction)
            self.assertFalse(json.loads((result.destination/'source-after.json').read_text())['match'])
            self.assertTrue((result.destination/'native/record.json').exists());self.assertEqual(len(fake.calls),1)

    def test_provider_credentials_are_neither_retained_nor_forwarded(self):
        slot=self.slots[0];adapter,fake=self.adapter(slot)
        keys=('AWS_BEARER_TOKEN_BEDROCK','AWS_SECRET_ACCESS_KEY','AWS_SESSION_TOKEN','ANTHROPIC_API_KEY','OPENAI_API_KEY')
        env=dict(adapter.environment,**{key:'SYNTHETIC_CREDENTIAL_NOT_REAL' for key in keys})
        clean=h.NativeVerifier(REPO,process_runner=fake,tool_observer=lambda project,expected:expected,
            environment=env,hostname='synthetic-compute',synthetic=True)
        self.assertTrue(all(key not in clean.environment for key in keys))
        clean.environment.update({key:'SYNTHETIC_CREDENTIAL_NOT_REAL' for key in keys})
        with tempfile.TemporaryDirectory() as tmp:
            result=clean(slot,self.sources[('dafny-vmc',1)],Path(tmp).resolve()/'run','synthetic-env')
            self.assertEqual(result.classification,'QUALIFIED_PASS')
            self.assertTrue(all(key not in fake.calls[0]['environment_keys'] for key in keys))

    def test_tool_integrity_failure_before_or_after_dispatch_preserves_exact_invocation_count(self):
        slot=self.slots[0]
        for fail_call in (1,2):
            with self.subTest(fail_call=fail_call),tempfile.TemporaryDirectory() as tmp:
                adapter,fake=self.adapter(slot);calls=[]
                def observe(project,expected):
                    calls.append(project)
                    return dict(expected,image_sha256='0'*64) if len(calls)==fail_call else expected
                adapter.tool_observer=observe
                result=adapter(slot,self.sources[('dafny-vmc',1)],Path(tmp).resolve()/'run','synthetic-tools')
                self.assertTrue(result.terminal);self.assertIsNone(result.extraction)
                self.assertEqual(result.native_invocations,fail_call-1)
                self.assertEqual(result.invocation_attempted,fail_call==2)
                self.assertEqual(len(fake.calls),fail_call-1)
                self.assertTrue((result.destination/'failure.json').exists())

    def test_no_real_fallback_or_unallocated_multicore_or_unfrozen_slot(self):
        slot=self.slots[0];scope,_,_=h._scope('dafny-vmc',1,REPO);fake=FakeProcess(slot,scope)
        with self.assertRaises(ValueError):h.NativeVerifier(REPO,process_runner=fake)
        with tempfile.TemporaryDirectory() as tmp:
            adapter,_=self.adapter(slot)
            adapter.environment['SLURM_CPUS_PER_TASK']='8'
            with self.assertRaises(ValueError):adapter(slot,self.sources[('dafny-vmc',1)],Path(tmp).resolve()/'badcpu','synthetic')
            adapter.environment['SLURM_CPUS_PER_TASK']='1';adapter.hostname='holylogin07'
            with self.assertRaises(ValueError):adapter(slot,self.sources[('dafny-vmc',1)],Path(tmp).resolve()/'login','synthetic')
            adapter.hostname='synthetic-compute';bad=dict(slot,maximum_requests=2)
            with self.assertRaises(ValueError):adapter(bad,self.sources[('dafny-vmc',1)],Path(tmp).resolve()/'badslot','synthetic')
            self.assertEqual(fake.calls,[])

    def test_synthetic_pure_fixture_both_stages_rejects_relabeling(self):
        for slot in self.slots[:4]:
            sources=self.sources[(slot['project'],slot['stage'])]
            result=fixture_result(slot,sources,run_id='synthetic-pure:'+slot['slot_id'])
            self.assertEqual(result.classification,'QUALIFIED_PASS')
            self.assertTrue(h.audit_result(slot,sources,result,REPO,allow_synthetic=True)['qualified_pass'])
            relabeled=replace(result.binding,origin='model-candidate')
            with self.assertRaises(ValueError):h.audit_candidate_native(relabeled,result.artifacts,sources,REPO)

    def test_stage_two_cannot_reuse_stage_one_inventory_or_changed_sources(self):
        slot=self.slots[3];sources=self.sources[('vest',2)];result=fixture_result(slot,sources)
        self.assertEqual(len(result.extraction['rows']),5416)
        self.assertEqual(len(result.extraction['fixed_unlogged_definitions']),6)
        bad=dict(result.artifacts);scope=json.loads(bad['scope.json']);scope['required_inventory']=h._scope('vest',1,REPO)[0]['required_inventory'];bad['scope.json']=h.canonical(scope)
        binding=replace(result.binding,artifact_sha256=tuple(sorted((n,h.sha(v)) for n,v in bad.items())))
        with self.assertRaisesRegex(ValueError,'scope changed'):h.audit_candidate_native(binding,bad,sources,REPO,allow_synthetic=True)
        changed=dict(sources);changed['vest_dev/src/formats/growth_frame.rs']+=b'\n'
        with self.assertRaises(ValueError):h.audit_candidate_native(result.binding,result.artifacts,changed,REPO,allow_synthetic=True)

    def test_changed_native_extraction_or_result_classification_rejected(self):
        slot=self.slots[0];sources=self.sources[('dafny-vmc',1)];result=fixture_result(slot,sources)
        altered=dict(result.extraction,qualified_pass=False)
        with self.assertRaises(ValueError):h.audit_result(slot,sources,replace(result,extraction=altered),REPO,allow_synthetic=True)
        with self.assertRaises(ValueError):h.audit_result(slot,sources,replace(result,classification='PROOF_FAILURE'),REPO,allow_synthetic=True)

    def test_stage_one_artifacts_fit_protocol_parent_audit_without_acceptance_issuance(self):
        slot=self.slots[0];sources=self.sources[('dafny-vmc',1)];result=fixture_result(slot,sources)
        replay=self.api.audit_model_parent_native(result.binding,result.artifacts,sources,repo=REPO,allow_synthetic=True)
        self.assertEqual(h.canonical(replay),h.canonical(result.extraction))
        self.assertNotIn('accepted.json',result.artifacts)
        self.assertFalse(result.extraction['accepted_revision_issued'])


if __name__=='__main__':unittest.main(verbosity=2)
