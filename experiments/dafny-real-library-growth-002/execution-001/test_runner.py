"""Synthetic/offline integration tests. No provider or verifier is invoked."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from bounded_requests import GateClosed, RequestGate, bedrock_transport
from credential_transport import BEARER_ENV, ScopedBearerTransport
from native_host import NativeObservation
from run_pilot import Runner
from runtime import (Stage, canonical, file_snapshot, guard, materialize_profile, native, parse_body,
                     read_json, save, save_bytes, save_sources, sha, validate_authorization, validate_scope, TASK_ORDER)

SETTINGS = dict(model_id="SYNTHETIC-NO-MODEL", region="SYNTHETIC", inference_config={"maxTokens":100})
BODY = "result := x + 1;"


def stages():
    result = {}
    for project in TASK_ORDER:
        base = {"Base.dfy": b"module Base { function Next(x: int): int { x + 1 } }\n"}
        inputs = ["Base.dfy", "Added1.dfy"]
        edit = dict(schema=guard.SCHEMA, project=project, stage=1, stage_id="Added1",
            base_source_sha256=native.hashes(base), parent_requirement=None,
            addition=dict(path="Added1.dfy", template_utf8="module Added1 {\n"
                " method Step(x: int) returns (result: int)\n ensures result == x + 1\n {\n"
                " // BEGIN BODY\n // END BODY\n }\n}\n",
                begin_marker=" // BEGIN BODY\n", end_marker=" // END BODY", kind="method"),
            registrations={}, verification_inputs=inputs, forbidden_identifiers=[])
        profile = dict(schema=native.PROFILE_SCHEMA, project=project, stage=1, stage_id="Added1",
            synthetic=True, inventory_status="qualified", command=["/synthetic/dafny", "verify"] + inputs,
            verification_inputs=inputs, toolchain=dict(dafny_version="SYNTHETIC-NO-DAFNY",
                executable_sha256="0"*64, package_sha256="1"*64),
            csv_columns=list(native.CSV_SCHEMAS[1]), random_seed=0,
            required_units={"Base.Next (well-formedness)":"Base.dfy", "Added1.Step (correctness)":"Added1.dfy"},
            unitless_files={}, inherited_warnings=[], unlogged_definitions=[],
            ineligible_parent_runs=[], ineligible_parent_raw_fingerprints=[])
        result[(project,1)] = Stage(edit, profile, dict(base), {"wall_seconds":1})
    return result


def scope():
    slots = []
    for index, project in enumerate(list(TASK_ORDER) + list(reversed(TASK_ORDER))):
        replicate = 1 if index < 4 else 2
        slots.append(dict(id="slot-%02d" % (index+1), project=project, stage=1,
                     chain_id=project+"-attempt-"+str(replicate), cohort="pilot", replicate=replicate))
    return dict(schema="dafny-library-independent-extension-scope-v1", batch_id="SYNTHETIC-TEST", max_calls=8,
                independent_trials=True, adaptive_expansion=False, settings=copy.deepcopy(SETTINGS),
                projects={task:{} for task in TASK_ORDER}, slots=slots)


class FakeRenderer:
    def __init__(self, stages):
        self.stages = stages
        self.mutate = None
        self.calls = []

    def render_stage1(self, project, chain_id, *, root=None):
        stage = self.stages[(project,1)]
        self.calls.append((project,chain_id))
        sources = stage.base_sources
        text = "\n".join(path+"\n"+raw.decode() for path,raw in sorted(sources.items()))
        payload = dict(modelId=SETTINGS["model_id"], system=[{"text":"SYNTHETIC OFFLINE"}],
            messages=[{"role":"user", "content":[{"text":text}]}], inferenceConfig=SETTINGS["inference_config"])
        value = dict(payload=payload, payload_sha256=sha(canonical(payload)), project=project,
            stage=1, stage_id=stage.edit_profile["stage_id"], chain_id=chain_id,
            guard_profile_sha256=sha(canonical(stage.edit_profile)),
            source_revision_sha256=sha(canonical(native.hashes(sources))), parent_audit=None,
            dispatch_eligible=False)
        if self.mutate: self.mutate(value)
        return value


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.responses = {}
        self.error_at = None

    def __call__(self, payload):
        index = len(self.calls)+1
        self.calls.append(copy.deepcopy(payload))
        if index == self.error_at:
            raise TimeoutError("SYNTHETIC NO REQUEST MADE")
        default = dict(text=json.dumps({"body":BODY+" // distinct synthetic "+str(index)}),
            content=[], usage={"inputTokens":1,"outputTokens":1}, stop_reason="end_turn",
            request_id="SYNTHETIC-REQUEST-"+str(index), retry_attempts=0,
            raw_response={"synthetic":True})
        return copy.deepcopy(self.responses.get(index, default))


class FakeHost:
    synthetic = True

    def __init__(self):
        self.outcomes = {}
        self.calls = []
        self.mutate = None
        self.prepare_error = False

    def prepare(self, stages, destination):
        if self.prepare_error:
            raise RuntimeError("SYNTHETIC PREFLIGHT FAILURE")
        Path(destination).mkdir()
        save(Path(destination)/"offline.json", {"synthetic":True,"native_calls":0})

    def run(self, profile, sources, event, destination, adapter):
        self.calls.append(copy.deepcopy(event))
        category = self.outcomes.get(event["slot_id"], "VERIFIED")
        labels = list(profile["required_units"])
        outcomes = {name:"Passed" for name in labels}
        code, timeout, text = 0, False, ""
        if category == "PROOF_FAILURE":
            outcomes[labels[-1]] = "Failed"
            code, text = 4, "Added.dfy(1,1): Error: a postcondition could not be proved\n"
        elif category in {"RESOURCE_FAILURE","VERIFIER_TIMEOUT"}:
            outcomes[labels[-1]] = "OutOfResource" if category=="RESOURCE_FAILURE" else "Timeout"
            code, text = 4, ("Added.dfy(1,1): Error: out of resource limit\n" if category=="RESOURCE_FAILURE"
                            else "Added.dfy(1,1): Error: timed out\n")
        elif category == "WARNING_ONLY":
            code, text = 2, "Added.dfy(1,1): Warning: new trigger\n"
        elif category == "NEW_WARNING":
            text = "Added.dfy(1,1): Warning: new trigger\n"
        elif category == "FRONTEND_PARSE_FAILURE":
            outcomes = {}
            code, text = 2, "1 parse error detected\n"
        elif category == "TIMEOUT":
            outcomes = {}
            code, timeout = -15, True
        elif category == "COVERAGE_FAILURE":
            outcomes.pop(labels[0])
        passed = sum(v=="Passed" for v in outcomes.values())
        failures = sum(v=="Failed" for v in outcomes.values())
        if category not in {"TIMEOUT","FRONTEND_PARSE_FAILURE"}:
            text += "Dafny program verifier finished with %d verified, %d errors\n" % (passed,failures)
        raw = {"stdout.txt":("// SYNTHETIC OFFLINE\n"+text).encode(), "stderr.txt":b"",
               "resources.txt":("SYNTHETIC NO PROCESS\nUser time (seconds): 0.01\n"
                   "System time (seconds): 0.00\nElapsed (wall clock) time (h:mm:ss or m:ss): 0:00.01\n"
                   "Maximum resident set size (kbytes): 100\nExit status: "+str(code)+"\n").encode()}
        if outcomes:
            raw["csv/TestResults/fake.csv"] = (",".join(profile["csv_columns"])+"\n"+
                "".join(name+","+outcome+",00:00:00.0001000,10,0\n" for name,outcome in outcomes.items())).encode()
        record = dict(schema=native.RECORD_SCHEMA, run_id=event["run_id"], origin="synthetic_offline",
            source_before_sha256=native.hashes(sources), source_after_sha256=native.hashes(sources),
            argv=profile["command"], toolchain=profile["toolchain"], toolchain_after=profile["toolchain"],
            raw_sha256=native.hashes(raw), exit_code=code, elapsed_seconds=0.01, timeout=timeout,
            attempts=1, model_calls=0, host=dict(job_id="SYNTHETIC",hostname="synthetic-compute",partition="synthetic"))
        if self.mutate:
            self.mutate(record,raw,event)
        destination.mkdir()
        save(destination/"event.json", event)
        save(destination/"record.json", record)
        save_sources(destination/"workspace", sources)
        for path, data in raw.items():
            save_bytes(destination/"raw"/path,data)
        return NativeObservation(sha(canonical(event)),record,raw)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.stages = stages()
        self.scope = scope()
        self.renderer = FakeRenderer(self.stages)
        self.transport = FakeTransport()
        self.host = FakeHost()
        self.check = lambda: None


    def tearDown(self):
        self.temp.cleanup()


    def runner(self, **kwargs):
        return Runner(self.scope, self.stages, self.renderer, self.host, self.transport,
            self.root/"run", deadline=100, integrity_check=lambda:self.check(),
            clock=lambda:1, offline=True, **kwargs)


    def test_output_rejection_does_not_run_native_or_repair(self):
        default = self.transport({"synthetic":"not sent"})
        self.transport.calls = []
        default["text"] = '{"body":"assume false;"}'
        self.transport.responses[1] = default
        result = self.runner().run()
        self.assertEqual(result["rows"][0]["outcome"],"OUTPUT_REJECTED")
        self.assertEqual(result["reserved"],8)
        self.assertEqual(len(self.host.calls),7)


    def test_transport_ambiguity_stops_all_and_never_retries(self):
        self.transport.error_at = 1
        result = self.runner().run()
        self.assertEqual((result["status"],result["reserved"],result["completed"]),("TERMINAL",1,0))
        self.assertEqual(result["ambiguous_or_unsaved"],1)
        self.assertEqual(len(self.transport.calls),1)
        self.assertEqual(len(self.host.calls),0)


    def test_diagnostic_failure_cannot_hide_terminal_summary(self):
        self.transport.error_at = 1
        def broken_diagnostic():
            raise RuntimeError("SYNTHETIC")
        self.transport.failure_diagnostic = broken_diagnostic
        result = self.runner().run()
        self.assertEqual((result["status"],result["reserved"]),("TERMINAL",1))
        self.assertTrue(result["fatal"]["transport_diagnostic_unavailable"])


    def test_preflight_failure_spends_zero(self):
        self.host.prepare_error = True
        result = self.runner().run()
        self.assertEqual(result["reserved"],0)
        self.assertEqual(len(self.transport.calls),0)


    def test_duplicate_request_id_and_nonzero_retries_stop(self):
        for change in ({"request_id":"SYNTHETIC-REQUEST-1"},{"retry_attempts":1}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temp:
                transport = FakeTransport()
                first = transport({})
                transport.calls = []
                second = dict(first,request_id="SYNTHETIC-REQUEST-2",**({} if "request_id" in change else {}))
                second.update(change)
                transport.responses[2] = second
                runner = Runner(self.scope,stages(),FakeRenderer(stages()),FakeHost(),transport,Path(temp)/"run",
                    deadline=100,integrity_check=lambda:None,clock=lambda:1,offline=True)
                result = runner.run()
                self.assertEqual((result["status"],result["reserved"]),("TERMINAL",2))


    def test_analyst_baseline_and_stale_run_cannot_be_relabelled(self):
        for field,value in (("origin","analyst_qualification"),("run_id","old-native-run")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                host = FakeHost()
                host.mutate = lambda record,raw,event:record.update({field:value})
                s = stages()
                result = Runner(self.scope,s,FakeRenderer(s),host,FakeTransport(),Path(temp)/"run",
                    deadline=100,integrity_check=lambda:None,clock=lambda:1,offline=True).run()
                self.assertEqual((result["status"],result["reserved"],result["accepted_stages"]),("TERMINAL",1,0))


    def test_known_control_fingerprint_is_ineligible_even_with_current_identity(self):
        captured = {}
        def deny(record,raw,event):
            captured["hash"] = sha(canonical(native.hashes(raw)))
            # Pin before invocation by making a second fresh runner below.
        first = self.runner()
        first.host.mutate = deny
        first.run()
        denied = captured["hash"]
        with tempfile.TemporaryDirectory() as temp:
            s = stages()
            # All successful stages emit the same raw at their stage.
            s[("stdlib-filter",1)].native_profile["ineligible_parent_raw_fingerprints"] = [denied]
            result = Runner(self.scope,s,FakeRenderer(s),FakeHost(),FakeTransport(),Path(temp)/"run",
                deadline=100,integrity_check=lambda:None,clock=lambda:1,offline=True).run()
            self.assertEqual(result["status"],"TERMINAL")
            self.assertEqual(result["accepted_stages"],0)


    def test_native_frontend_coverage_outer_timeout_warning_stop_all(self):
        for category in ("FRONTEND_PARSE_FAILURE","COVERAGE_FAILURE","TIMEOUT","WARNING_ONLY","NEW_WARNING"):
            with self.subTest(category=category), tempfile.TemporaryDirectory() as temp:
                s=stages(); host=FakeHost(); host.outcomes={"slot-01":category}
                result=Runner(self.scope,s,FakeRenderer(s),host,FakeTransport(),Path(temp)/"run",
                    deadline=100,integrity_check=lambda:None,clock=lambda:1,offline=True).run()
                self.assertEqual((result["status"],result["reserved"]),("TERMINAL",1))
                self.assertEqual(result["accepted_stages"],0)


    def test_complete_verifier_resource_outcomes_are_bounded_failed_stages(self):
        self.host.outcomes={"slot-01":"RESOURCE_FAILURE","slot-02":"VERIFIER_TIMEOUT"}
        result=self.runner().run()
        self.assertEqual((result["status"],result["reserved"]),("COMPLETE",8))
        self.assertEqual([r["category"] for r in result["rows"][:2]],["RESOURCE_FAILURE","VERIFIER_TIMEOUT"])


    def test_new_warning_with_proof_failure_is_terminal(self):
        def mutate(record,raw,event):
            raw["stderr.txt"]=b"Added.dfy(1,1): Warning: new warning\n"
            record["raw_sha256"]=native.hashes(raw)
        self.host.outcomes={"slot-01":"PROOF_FAILURE"}
        self.host.mutate=mutate
        self.assertEqual(self.runner().run()["status"],"TERMINAL")


    def test_provider_error_metadata_redaction_survives_terminal(self):
        class Denied(Exception):
            response={"Error":{"Code":"AccessDeniedException","Message":"denied SECRET"},
                      "ResponseMetadata":{"RequestId":"request-x","HTTPStatusCode":403,"RetryAttempts":0}}
        calls=[]
        def factory(settings):
            def call(payload):
                calls.append(payload)
                raise Denied()
            return call
        transport=ScopedBearerTransport(SETTINGS,lambda:"SECRET",transport_factory=factory,environ={})
        result=Runner(self.scope,self.stages,self.renderer,self.host,transport,self.root/"run",
            deadline=100,integrity_check=lambda:None,clock=lambda:1,offline=True).run()
        diagnostic=read_json(self.root/"run/transport-failure.json")
        self.assertEqual(result["reserved"],1)
        self.assertEqual(len(calls),1)
        self.assertEqual(diagnostic["provider_error"]["Error"]["Code"],"AccessDeniedException")
        self.assertNotIn("SECRET",json.dumps(diagnostic))
        self.assertEqual(diagnostic["provider_error"]["ResponseMetadata"]["RequestId"],"request-x")


    def test_unlogged_materialization_changes_only_predeclared_source_hash(self):
        template={"unlogged_definitions":[{"name":"M.Total","file":"New.dfy",
                    "source_sha256":"0"*64,"counted_as_pass":False}],"fixed":{"a":1}}
        materialized=materialize_profile(template,{"New.dfy":b"exact model candidate"})
        restored=copy.deepcopy(materialized)
        restored["unlogged_definitions"][0]["source_sha256"]="0"*64
        self.assertEqual(restored,template)
        self.assertEqual(template["unlogged_definitions"][0]["source_sha256"],"0"*64)


    def test_sdk_config_has_exact_one_attempt_and_no_retry(self):
        configs=[];calls=[]
        class Client:
            def converse(self,**payload):
                calls.append(payload)
                return {"output":{"message":{"content":[{"text":"x"}]}},
                        "ResponseMetadata":{"RequestId":"fake","RetryAttempts":0}}
        def config(**kwargs):configs.append(kwargs);return kwargs
        transport=bedrock_transport(SETTINGS,client_factory=lambda *a,**kw:Client(),config_factory=config)
        payload=dict(modelId=SETTINGS["model_id"],system=[],messages=[],inferenceConfig=SETTINGS["inference_config"])
        transport(payload)
        self.assertEqual(configs,[dict(connect_timeout=15,read_timeout=180,
                                       retries={"mode":"standard","total_max_attempts":1})])
        self.assertEqual(len(calls),1)


    def test_parser_exact_json_fence_and_rejections(self):
        fence=chr(96)*3
        self.assertEqual(parse_body('{"body":"return;"}'),"return;")
        self.assertEqual(parse_body('Here is the body: {"body":"return;"} End.'),"return;")
        self.assertEqual(parse_body(fence+'json\n{"body":"return;"}\n'+fence),"return;")
        for text in ('{"body":"x","body":"y"}','{"body":1}','{"body":"x","contract":"evil"}',
                     '[{"body":"x"}]','{"body":"x"}{"body":"y"}',None):
            with self.subTest(text=text),self.assertRaises(native.EvidenceError):parse_body(text)


    def test_authorization_exact_fresh_eight_from_hundred(self):
        auth=dict(schema="dafny-library-independent-execution-authorization-v1",operator="Sophie Zeng",
            scope_sha256="a"*64,runtime_manifest_sha256="b"*64,max_new_calls=8,total_session_ceiling=100,
            no_retry=True,no_reassignment=True,no_resume=True,allocation_id="fresh",budget_session_id="session",
            human_approval_basis="Explicit user instruction",created_at_epoch=10,expires_at_epoch=100)
        self.assertEqual(validate_authorization(auth,"a"*64,"b"*64,20),100)
        for key,value in (("max_new_calls",100),("scope_sha256","c"*64),("expires_at_epoch",15),
                          ("created_at_epoch",21),("no_resume",False)):
            changed=dict(auth);changed[key]=value
            with self.subTest(key=key),self.assertRaises(native.EvidenceError):
                validate_authorization(changed,"a"*64,"b"*64,20)


    def test_copied_transport_exact_original_digest(self):
        root=Path(__file__).resolve().parent
        provenance=read_json(root/"copy-provenance.json")
        for item in provenance["copies"]:
            self.assertEqual(sha((root/item["file"]).read_bytes()),item["sha256"])
            self.assertFalse(item["changed"])


    def test_all_eight_are_independent_and_closed(self):
        runner = self.runner(); result = runner.run()
        self.assertEqual((result["status"],result["reserved"],result["accepted_stages"]),("COMPLETE",8,8))
        self.assertEqual(len(self.renderer.calls),8)
        self.assertTrue(all(v == {"returned":2,"accepted":2} for v in result["per_task"].values()))
        self.assertFalse(any((self.root/"run").rglob("parent-receipt.json")))
        self.assertTrue(read_json(self.root/"run/requests/ledger.json")["closed"])
        with self.assertRaises(native.EvidenceError): runner.run()
        with self.assertRaises(FileExistsError): self.runner()

    def test_all_proof_failures_still_complete_fixed_sample(self):
        self.host.outcomes = {s["id"]:"PROOF_FAILURE" for s in self.scope["slots"]}
        result=self.runner().run()
        self.assertEqual((result["status"],result["reserved"],result["accepted_stages"]),("COMPLETE",8,0))
        self.assertEqual(len(self.transport.calls),8)

    def test_completed_candidate_drift_blocks_next_request(self):
        def check():
            path=self.root/"run/slots/slot-01/candidate/Added1.dfy"
            if path.exists() and len(self.transport.calls)==1: path.write_bytes(path.read_bytes()+b" ")
        self.check=check
        result=self.runner().run()
        self.assertEqual((result["status"],result["reserved"]),("TERMINAL",1))

    def test_wrong_base_prompt_stops_before_request(self):
        self.renderer.mutate=lambda value:value.update(source_revision_sha256="f"*64)
        result=self.runner().run()
        self.assertEqual((result["status"],result["reserved"]),("TERMINAL",0))

    def test_scope_forbids_child_adaptive_order_and_extra_slots(self):
        for change in ("cap","order","identity","slots","child","adaptive"):
            bad=scope()
            if change=="cap":bad["max_calls"]=9
            if change=="order":bad["slots"][4],bad["slots"][5]=bad["slots"][5],bad["slots"][4]
            if change=="identity":bad["slots"][4]["chain_id"]=bad["slots"][0]["chain_id"]
            if change=="slots":bad["slots"].append(copy.deepcopy(bad["slots"][0]))
            if change=="child":bad["slots"][4]["stage"]=2
            if change=="adaptive":bad["adaptive_expansion"]=True
            with self.subTest(change=change),self.assertRaises(native.EvidenceError):validate_scope(bad)

    def test_eight_cap_cannot_send_ninth(self):
        calls=[]
        gate=RequestGate(self.root/"gate",8,100,lambda p:calls.append(p) or {},clock=lambda:1)
        for n in range(8):gate.invoke({"n":n},task_id=str(n),attempt_id=str(n))
        with self.assertRaises(GateClosed):gate.invoke({},task_id="9",attempt_id="9")
        self.assertEqual(len(calls),8)
        self.assertTrue(gate.closed)


if __name__=="__main__":
    unittest.main(verbosity=2)
