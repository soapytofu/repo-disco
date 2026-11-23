"""Offline draft tests. Synthetic parents are never live/model acceptances."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import prepare
import render


def synthetic_parent(project, root, *, origin="synthetic_offline", failed=False):
    """Visibly synthetic native observations; no provider or native process ran."""
    guard,native = render.common_api()
    _,scope = render.bundle(root)
    stage = scope["projects"][project]["stages"]["1"]
    edit = json.loads((root/stage["edit_profile_path"]).read_bytes())
    base = render._base_sources(root,scope,project)
    chain = project+"-lineage-01"
    text = "    // SYNTHETIC OFFLINE PARENT, NOT A NATIVE PROOF\n"
    text += "    return;\n" if project=="stdlib" else '    Failure("synthetic test body")\n'
    sources,_ = guard.reconstruct(edit,text,base,chain)
    target = edit["addition"]["path"]
    label = "Synthetic.Target (correctness)"
    argv = ["/synthetic/dafny","verify"]+sorted(sources)
    tool = dict(dafny_version="SYNTHETIC-NOT-NATIVE",package_sha256="1"*64)
    profile = dict(schema=native.PROFILE_SCHEMA,project=project,stage=1,stage_id=stage["stage_id"],
        synthetic=True,inventory_status="qualified",command=argv,verification_inputs=sorted(sources),
        toolchain=tool,csv_columns=list(native.CSV_SCHEMAS[1]),random_seed=0,
        required_units={label:target},unitless_files={name:"SYNTHETIC unlogged fixture; no actual coverage claim"
            for name in sources if name!=target},inherited_warnings=[],unlogged_definitions=[],
        ineligible_parent_runs=[],ineligible_parent_raw_fingerprints=[])
    outcome = "Failed" if failed else "Passed"
    stdout = ("SYNTHETIC OFFLINE OBSERVATION\n" +
        ("Target.dfy(1,1): Error: assertion might not hold\nDafny program verifier finished with 0 verified, 1 error\n"
         if failed else "Dafny program verifier finished with 1 verified, 0 errors\n")).encode()
    code=4 if failed else 0
    raw={"stdout.txt":stdout,"stderr.txt":b"",
        "resources.txt":("SYNTHETIC OFFLINE RESOURCE RECORD\nUser time (seconds): 0.00\n"
         "System time (seconds): 0.00\nElapsed (wall clock) time (h:mm:ss or m:ss): 0:00.01\n"
         "Maximum resident set size (kbytes): 1\nExit status: "+str(code)+"\n").encode(),
        "csv/synthetic.csv":(",".join(profile["csv_columns"])+"\n"+label+","+outcome+",00:00:00.0,1,0\n").encode()}
    record=dict(schema=native.RECORD_SCHEMA,run_id="SYNTHETIC:"+project,origin=origin,
        source_before_sha256=native.hashes(sources),source_after_sha256=native.hashes(sources),
        argv=argv,toolchain=tool,toolchain_after=tool,raw_sha256=native.hashes(raw),
        exit_code=code,elapsed_seconds=0.01,timeout=False,attempts=1,model_calls=0,
        host=dict(job_id="SYNTHETIC",hostname="synthetic-compute",partition="synthetic"))
    pins=native.EvidencePins(native.sha(native.canonical(profile)),native.sha(native.canonical(record)),
        native.sha(native.canonical(native.hashes(sources))),tuple(sorted(native.hashes(raw).items())),record["run_id"],origin)
    reviewed=native.review(profile,sources,record,raw,pins,allow_synthetic=True)
    receipt=dict(schema=guard.RECEIPT_SCHEMA,project=project,stage=1,stage_id=stage["stage_id"],chain_id=chain,
        origin=origin,guard_profile_sha256=native.sha(native.canonical(edit)),
        source_revision_sha256=reviewed["source_revision_sha256"],native_profile_sha256=reviewed["profile_sha256"],
        native_record_sha256=reviewed["record_sha256"],native_run_id=reviewed["run_id"],
        native_raw_fingerprint_sha256=reviewed["raw_fingerprint_sha256"],accepted=True,
        request_id="SYNTHETIC-NO-REQUEST",response_sha256="2"*64)
    parent=guard.ParentEvidence(profile,record,raw,pins,receipt,native.sha(native.canonical(receipt)))
    return sources,parent


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix="repodisco-library-pilot-offline-")
        cls.root=Path(cls.temporary.name).resolve()/"draft"
        prepare.prepare(destination=cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_twelve_fixed_slots_and_child_dependency_gate(self):
        _,scope=render.bundle(self.root)
        self.assertEqual(scope["maximum_calls"],12)
        self.assertEqual(len(scope["slots"]),12)
        self.assertEqual([slot["cohort"] for slot in scope["slots"][:4]],["pilot"]*4)
        self.assertEqual(len({slot["chain_id"] for slot in scope["slots"]}),6)
        for child in (slot for slot in scope["slots"] if slot["stage"]==2):
            parent=next(slot for slot in scope["slots"] if slot["id"]==child["parent_slot_id"])
            self.assertEqual(parent["chain_id"],child["chain_id"])
            self.assertEqual(parent["stage"],1)
        self.assertEqual(scope["expansion_gate"]["minimum_accepted_stage1"],1)
        self.assertTrue(scope["expansion_gate"]["requires_complete_healthy_accounting"])
        self.assertFalse(scope["execution_enabled"])
        self.assertIsNone(scope["qualification_release"])

    def test_stage_one_exact_settings_and_no_solution_labels(self):
        for project in ("stdlib","aws"):
            result=render.render_stage1(project,project+"-lineage-01",root=self.root)
            payload=result["payload"]
            self.assertEqual(payload["modelId"],prepare.MODEL)
            self.assertEqual(payload["body"]["temperature"],1)
            self.assertEqual(payload["body"]["max_tokens"],4096)
            text=prepare.canonical(payload).decode()
            for forbidden in ("RepoDisco analyst reference", "Native verification is UNKNOWN",
                              "stage1-wrong-payload", "reference-001", prepare.BEGIN.strip()+"\\n    if |input|"):
                self.assertNotIn(forbidden,text)
            self.assertFalse(result["dispatch_eligible"])
            self.assertFalse(result["authorization_issued"])

    def test_upstream_excerpts_verbatim_with_exact_positions(self):
        for project in ("stdlib","aws"):
            ctx=json.loads((self.root/"context"/(project+".json")).read_bytes())
            base=prepare.EXPERIMENT/(prepare.STDLIB_BASE if project=="stdlib" else prepare.AWS_BASE)
            for item in ctx["excerpts"]:
                raw=(base/item["file"]).read_bytes()
                selected=b"".join(raw.splitlines(keepends=True)[item["first_line"]-1:item["last_line"]])
                self.assertEqual(selected,item["text"].encode())
                self.assertEqual(prepare.sha(raw),item["source_sha256"])
                self.assertEqual(prepare.sha(selected),item["excerpt_sha256"])
            if project=="aws":
                self.assertEqual(len(ctx["complete_source_files_shown"]),4)
                self.assertGreater(len(ctx["omitted_or_partial_source_files"]),50)

    def test_include_graph_and_import_declarations_are_real_source_lines(self):
        for project in ("stdlib","aws"):
            ctx=json.loads((self.root/"context"/(project+".json")).read_bytes())
            base=prepare.EXPERIMENT/(prepare.STDLIB_BASE if project=="stdlib" else prepare.AWS_BASE)
            graph=ctx["dependency_inventory"]
            for file,info in graph.items():
                lines=(base/file).read_text().splitlines()
                for entry in info["includes"]+info["imports"]+info["module_declarations"]:
                    self.assertEqual(entry["text"],lines[entry["line"]-1])
                for entry in info["includes"]:
                    self.assertIn(entry["resolved_file"],graph)

    def test_trust_inventory_blocks_names_and_alias_references(self):
        guard,_=render.common_api()
        audit=json.loads((self.root/"context/aws-inherited-trust.json").read_bytes())
        names=audit["forbidden_identifiers"]
        self.assertTrue({"Encode","Decode","ValueIsSafeBecauseItIsInMemory"}<=set(names))
        profile=json.loads((self.root/"guard-profiles/aws-stage1.json").read_bytes())
        for body in ("var f := UTF8.Encode; Failure(\"no\")",
                     "MemoryMath.ValueIsSafeBecauseItIsInMemory(x); Failure(\"no\")"):
            with self.assertRaises(ValueError): guard.render_body(profile,body)
        for row in audit["observations"]:
            raw=(prepare.EXPERIMENT/prepare.AWS_BASE/row["file"]).read_bytes()
            self.assertEqual(prepare.sha(raw),row["source_sha256"])

    def test_stage_two_only_templates_and_null_live_payloads(self):
        _,scope=render.bundle(self.root)
        for project in ("stdlib","aws"):
            stage=scope["projects"][project]["stages"]["2"]
            self.assertIsNone(stage["exact_live_payload"])
            self.assertIsNone(stage["exact_payload_path"])
            self.assertIsNone(stage["native_profile_path"])
            payload=json.loads((self.root/stage["child_template_payload_path"]).read_bytes())
            self.assertEqual(prepare.canonical(payload).decode().count(render.PLACEHOLDER),1)

    def test_default_rejects_synthetic_parent_and_opt_in_preserves_body(self):
        for project in ("stdlib","aws"):
            sources,parent=synthetic_parent(project,self.root)
            chain=project+"-lineage-01"
            with self.assertRaisesRegex(ValueError,"Synthetic"):
                render.render_stage2(project,chain,sources,parent,root=self.root)
            result=render.render_stage2(project,chain,sources,parent,root=self.root,allow_synthetic=True)
            text=result["payload"]["body"]["messages"][0]["content"][0]["text"]
            self.assertIn("SYNTHETIC OFFLINE PARENT",text)
            self.assertNotIn("RepoDisco analyst reference",text)
            self.assertNotIn(render.PLACEHOLDER,text)
            self.assertTrue(result["synthetic"])
            self.assertFalse(result["dispatch_eligible"])
            self.assertIn("native_review",result["parent_audit"])

    def test_failed_stale_wrong_lineage_and_substituted_parents_rejected(self):
        for project in ("stdlib","aws"):
            sources,parent=synthetic_parent(project,self.root,failed=True)
            with self.assertRaisesRegex(ValueError,"qualified"):
                render.render_stage2(project,project+"-lineage-01",sources,parent,root=self.root,allow_synthetic=True)
            sources,parent=synthetic_parent(project,self.root)
            with self.assertRaises(ValueError):
                render.render_stage2(project,project+"-lineage-02",sources,parent,root=self.root,allow_synthetic=True)
            path=prepare.AWS_STAGE1 if project=="aws" else "growth/AppendAll.dfy"
            changed=dict(sources); changed[path]=changed[path].replace(b"SYNTHETIC OFFLINE PARENT",b"SUBSTITUTED DIFFERENT PARENT")
            with self.assertRaises(ValueError):
                render.render_stage2(project,project+"-lineage-01",changed,parent,root=self.root,allow_synthetic=True)

    def test_analyst_parent_receipt_is_not_model_origin(self):
        sources,parent=synthetic_parent("aws",self.root,origin="analyst_qualification")
        with self.assertRaisesRegex(ValueError,"model-origin"):
            render.render_stage2("aws","aws-lineage-01",sources,parent,root=self.root,allow_synthetic=True)

    def test_all_files_are_explicit_roots_and_context_remains_a_subset(self):
        for project in ("stdlib","aws"):
            first=json.loads((self.root/"guard-profiles"/(project+"-stage1.json")).read_bytes())
            second=json.loads((self.root/"guard-profiles"/(project+"-stage2.json")).read_bytes())
            self.assertEqual(first["registrations"],{})
            self.assertEqual(set(first["verification_inputs"]),set(first["base_source_sha256"])|{first["addition"]["path"]})
            self.assertEqual(set(second["verification_inputs"]),set(first["verification_inputs"])|{second["addition"]["path"]})
            self.assertEqual(second["parent_requirement"]["guard_profile_sha256"],prepare.sha(prepare.canonical(first)))


if __name__=="__main__":
    unittest.main(verbosity=2)
