"""Real staged renderer/Runner integration; all process/provider results fake.

These fixtures exercise serialization, module loading, reconstruction and
lineage gates. Invented native inventories/observations are explicitly synthetic
and cannot qualify AWS mathematics or issue a live execution authorization.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def copied(path, source):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source.read_bytes())
    return dict(path=path, sha256=sha(path.read_bytes()))


def fixture(root):
    """Actual source/templates, synthetic native gates, no native subprocess."""
    public_json = {"copy-provenance.json", "prior-budget-snapshot.json", "budget-snapshot.json", "execution-binding.json"}
    for folder in ("common", "execution-001"):
        for path in (EXPERIMENT/folder).iterdir():
            if path.is_file() and (path.suffix == ".py" or path.name in public_json | {"README.md", "model.sbatch"}):
                copied(root/folder/path.name, path)
    for name in ("prepare.py", "prepare_v2.py", "render_v2.py", "test_render_v2.py"):
        copied(root/"pilot"/name, HERE/name)
    shutil.copytree(HERE/"draft-001", root/"pilot/draft-001")
    projects = {}
    paths = {
        "stdlib": ("stdlib/cases/baseline", [
            ("append-all", "growth/AppendAll.dfy", "AppendAll", "method",
             "qualification-003/retrieved-stdlib/qualification-003/output-stdlib/append-reference/workspace/growth/AppendAll.dfy"),
            ("append-rotated", "growth/AppendRotated.dfy", "AppendRotated", "method",
             "qualification-003/retrieved-stdlib/qualification-003/output-stdlib/rotate-reference/workspace/growth/AppendRotated.dfy")]),
        "aws": ("aws/revision-002/cases/baseline/workspace", [
            ("u16-frame", "StandardLibrary/src/RepoDiscoU16Frame.dfy", "ReadU16Frame", "function",
             "aws/revision-002/cases/stage1-reference/workspace/StandardLibrary/src/RepoDiscoU16Frame.dfy"),
            ("frame-pair", "StandardLibrary/src/RepoDiscoFramePair.dfy", "ReadFramePair", "function",
             "aws/revision-002/cases/stage2-reference/workspace/StandardLibrary/src/RepoDiscoFramePair.dfy")])}
    for project, (base, definitions) in paths.items():
        bases = {}
        for source in sorted((EXPERIMENT/base).rglob("*.dfy")):
            name = source.relative_to(EXPERIMENT/base).as_posix()
            target = "fixture-inputs/"+project+"/base/"+name
            copied(root/target, source)
            bases[name] = dict(path=target, sha256=sha(source.read_bytes()))
        profiles, references, interfaces, gate_profiles = {}, {}, {}, {}
        gate_inputs = {entry["path"]:entry["sha256"] for entry in bases.values()}
        for stage, (stage_id, name, callable_name, kind, reference) in enumerate(definitions, 1):
            index = str(stage)
            reference_path = "fixture-inputs/"+project+"/reference-"+index+".dfy"
            copied(root/reference_path, EXPERIMENT/reference)
            references[index] = dict(path=reference_path, sha256=sha((root/reference_path).read_bytes()))
            gate_inputs[reference_path] = references[index]["sha256"]
            interfaces[index] = dict(stage_id=stage_id, target_file=name, callable_name=callable_name, kind=kind)
            # Deliberately different from draft001's sorted input list, so
            # accidentally retaining that list is observable in these tests.
            inputs = list(reversed(sorted(bases))) + [row[1] for row in definitions[:stage]]
            required = {"SYNTHETIC.Unit"+str(n)+" (correctness)":source for n,source in enumerate(inputs)}
            profile = dict(schema="dafny-library-native-profile-v1", project=project, stage=stage, stage_id=stage_id,
                inventory_status="qualified", qualification_fixture_only=True,
                command=["/SYNTHETIC-NO-DAFNY/dafny", "verify", "--cores", "1"]+inputs,
                verification_inputs=inputs, toolchain={"dafny_version":"SYNTHETIC-NO-DAFNY", "executable_sha256":"0"*64},
                csv_columns=["TestResult.DisplayName","TestResult.Outcome","TestResult.Duration","TestResult.ResourceCount","RandomSeed"],
                random_seed=0, required_units=required, unitless_files={}, unlogged_definitions=[], inherited_warnings=[],
                ineligible_parent_runs=["SYNTHETIC-ANALYST-CONTROL"], ineligible_parent_raw_fingerprints=["f"*64])
            profile_path = "fixture-inputs/"+project+"/native-"+index+".json"
            save(root/profile_path, profile)
            profiles[index] = dict(path=profile_path, sha256=sha((root/profile_path).read_bytes()))
            gate_profiles[index] = dict(file_sha256=profiles[index]["sha256"])
        gate = dict(schema="SYNTHETIC-FIXTURE-ONLY", project=project, synthetic=True, model_calls=0, native_calls=0,
            counts=dict(total_expected=3,total_matching=3), observations=[dict(expected_match=True, synthetic=True)]*3,
            profiles=gate_profiles, input_files=gate_inputs, authorization_issued=False)
        gate_path = "fixture-inputs/"+project+"/synthetic-gate.json"
        save(root/gate_path, gate)
        projects[project] = dict(control_gate=dict(path=gate_path,sha256=sha((root/gate_path).read_bytes())),
            native_profiles=profiles, reference_sources=references, base_sources=bases, interfaces=interfaces,
            native_adapter=dict(toolchain_root="/SYNTHETIC-NO-DAFNY",solver="/SYNTHETIC-NO-Z3",wall_seconds=1))
    return dict(schema="dafny-library-pilot-preparation-input-v2", synthetic=True, projects=projects,
        region="SYNTHETIC-NO-PROVIDER", batch_id="dafny-real-library-growth-001-execution-001")


def worker(root, mode, scope_path="pilot/draft-002/scope.json"):
    """Fresh interpreter importing only the manifest-staged runtime package."""
    root = Path(root).resolve()
    sys.path.insert(0, str(root/"execution-001"))
    from runtime import load_renderer, load_stages, read_json, guard, native
    from build_runtime import validate_complete
    from run_pilot import Runner
    from test_runner import FakeHost, FakeTransport
    import time
    freeze = root/"execution-001/runtime-freeze.json"
    freeze_sha = sha(freeze.read_bytes())
    _, scope, stages = validate_complete(root,scope_path,freeze,freeze_sha)
    renderer = load_renderer(root,scope["renderer"])
    assert Path(renderer.__file__).resolve() == root/"pilot/render_v2.py"
    assert Path(guard.__file__).resolve() == root/"common/guard.py"
    assert "prepare" not in sys.modules
    host, transport = FakeHost(), FakeTransport()
    for index in range(1, 13):
        # The generic balanced body is deliberately not mathematical evidence.
        body = 'assert true; // SYNTHETIC ONLY body '+str(index)+'\n'
        transport.responses[index] = dict(text=json.dumps({"body":body}),content=[],usage={"inputTokens":1,"outputTokens":1},
            stop_reason="end_turn",request_id="SYNTHETIC-REQUEST-"+str(index),retry_attempts=0,raw_response={"synthetic":True})
    if mode == "failed-parent":
        host.outcomes[scope["slots"][0]["id"]] = "PROOF_FAILURE"
    output = root.parent/("synthetic-"+mode)
    runner = Runner(scope,stages,renderer,host,transport,output,deadline=time.time()+90,
        integrity_check=lambda: validate_complete(root,scope_path,freeze,freeze_sha),
        renderer_root=root,offline=True,run_id="SYNTHETIC-NO-NATIVE-OR-MODEL-"+mode)
    summary = runner.run()
    assert summary["status"] == "COMPLETE", summary
    assert summary["synthetic"] is True
    inspected_parents = 0
    if mode == "failed-parent":
        assert summary["reserved"] == summary["completed"] == 11
        assert summary["accepted_stages"] == 10 and summary["blocked_children"] == 1
        row = next(row for row in summary["rows"] if row["id"]==scope["slots"][2]["id"])
        assert row["outcome"]=="BLOCKED_PARENT" and row["request_sequence"] is None
        assert not (output/"slots"/row["id"]/"prompt.json").exists()
    else:
        assert summary["reserved"] == summary["completed"] == summary["accepted_stages"] == 12
        assert summary["completed_lineages"] == 6
        for slot in scope["slots"]:
            if slot["stage"]!=2:
                continue
            parent = runner.parents[(slot["project"],slot["chain_id"])]
            stage = stages[(slot["project"],2)]
            name = stage.edit_profile["parent_requirement"]["addition_path"]
            rendered = read_json(output/"slots"/slot["id"]/"prompt.json")
            text = rendered["payload"]["messages"][0]["content"][0]["text"]
            prefix = scope["projects"][slot["project"]]["stages"]["2"]["parent_display_fixed_prefix_utf8"].encode()
            assert parent.sources[name][len(prefix):].decode() in text
            assert "{{ACCEPTED_PARENT_SOURCE}}" not in text
            assert rendered["parent_source_sha256"] == sha(parent.sources[name])
            assert rendered["parent_audit"]["synthetic"] is True
            assert rendered["dispatch_eligible"] is False
            try:
                renderer.render_stage2(slot["project"],slot["chain_id"],parent.sources,parent.evidence,root=root)
            except native.EvidenceError as error:
                assert "Synthetic" in str(error)
            else:
                raise AssertionError("Synthetic accepted parent passed the default live boundary")
            inspected_parents += 1
        slot = scope["slots"][2]
        parent = runner.parents[(slot["project"],slot["chain_id"])]
        wrong_chain = scope["slots"][6]["chain_id"]
        for label,chain,sources in [("wrong-chain",wrong_chain,parent.sources),
             ("stale-source",slot["chain_id"],{**parent.sources, next(iter(parent.sources)):b"stale"})]:
            try:
                renderer.render_stage2(slot["project"],chain,sources,parent.evidence,root=root,allow_synthetic=True)
            except (native.EvidenceError,ValueError):
                pass
            else:
                raise AssertionError(label+" was accepted")
    assert all(set(payload)=={"modelId","system","messages","inferenceConfig"} for payload in transport.calls)
    assert all(payload["inferenceConfig"]=={"temperature":1,"maxTokens":4096} for payload in transport.calls)
    print(json.dumps(dict(mode=mode,synthetic=True,provider_calls=0,native_processes=0,
        fake_transport_dispatches=len(transport.calls),fake_native_observations=len(host.calls),
        reserved=summary["reserved"],completed=summary["completed"],accepted_synthetic_stages=summary["accepted_stages"],
        blocked_children=summary["blocked_children"],
        exact_parent_view_assertions=inspected_parents,
        default_synthetic_rejection_assertions=inspected_parents,actual_renderer=scope["renderer"],
        staged_module_path_verified=True,manifest_sha256=freeze_sha),sort_keys=True))


class RenderV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.source = Path(cls.temp.name).resolve()/"source"
        cls.source.mkdir()
        cls.specification = fixture(cls.source)
        spec=importlib.util.spec_from_file_location("test_prepare_v2",cls.source/"pilot/prepare_v2.py")
        cls.preparer=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.preparer)
        cls.prepared=cls.preparer.prepare(cls.source,cls.specification,allow_synthetic=True)
        sys.path.insert(0,str(cls.source/"execution-001"))
        import build_runtime
        cls.builder=build_runtime
        cls.manifest=cls.source/"execution-001/runtime-freeze.json"
        cls.freeze=cls.builder.build(cls.source,cls.prepared["scope"],cls.manifest)
        cls.staged=Path(cls.temp.name).resolve()/"staged"
        cls.builder.package_frozen(cls.source,cls.manifest,sha(cls.manifest.read_bytes()),cls.staged)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_worker(self,mode):
        result=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),"--worker",str(self.staged),mode],
            capture_output=True,text=True,timeout=110,cwd=self.staged)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(result.stderr,result.stderr)
        report=json.loads(result.stdout)
        print(json.dumps(report,sort_keys=True))
        return report

    def test_actual_staged_loader_renderer_and_runner_complete_synthetic_lineages(self):
        report=self.run_worker("all")
        self.assertEqual(report["accepted_synthetic_stages"],12)
        self.assertEqual(report["provider_calls"],0)

    def test_actual_renderer_blocks_failed_parent_without_consuming_child(self):
        report=self.run_worker("failed-parent")
        self.assertEqual(report["blocked_children"],1)
        self.assertEqual(report["fake_transport_dispatches"],11)

    def test_staged_smoke_cli_needs_no_historical_references(self):
        result=subprocess.run([sys.executable,"-B",str(self.staged/"pilot/test_render_v2.py"),
            "--smoke",str(self.staged),self.prepared["scope"]],capture_output=True,text=True,timeout=110,cwd=self.staged)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(result.stderr,result.stderr)
        report=json.loads(result.stdout)
        print(json.dumps(report,sort_keys=True))
        self.assertEqual(report["accepted_synthetic_stages"],12)
        self.assertEqual(report["exact_parent_view_assertions"],6)
        self.assertEqual(report["provider_calls"],0)

    def test_exact_profile_input_order_converse_and_narrowed_context(self):
        scope=json.loads((self.staged/self.prepared["scope"]).read_bytes())
        self.assertEqual([s["project"] for s in scope["slots"]],
            ["stdlib","aws","stdlib","aws","stdlib","aws","stdlib","aws","aws","stdlib","aws","stdlib"])
        for project in ("stdlib","aws"):
            self.assertEqual(scope["projects"][project]["upstream_source_files"],3)
            for number in ("1","2"):
                row=scope["projects"][project]["stages"][number]
                guard=json.loads((self.staged/row["edit_profile"]).read_bytes())
                native=json.loads((self.staged/row["native_profile"]).read_bytes())
                self.assertEqual(guard["verification_inputs"],native["verification_inputs"])
                self.assertEqual(native["command"][-len(guard["verification_inputs"]):],guard["verification_inputs"])
                payload=json.loads((self.staged/(row["exact_payload_path"] or row["child_template_payload_path"])).read_bytes())
                text=payload["messages"][0]["content"][0]["text"]
                self.assertNotIn("enforce-determinism",text)
                self.assertNotIn("analyst reference",text)
                self.assertNotIn("SYNTHETIC ONLY body",text)
                if project=="aws":
                    self.assertNotIn("EncryptionContext",text)
                    self.assertNotIn("ValidUTF8Seq",text)
                self.assertEqual(text.count("{{ACCEPTED_PARENT_SOURCE}}"),int(number=="2"))

    def test_synthetic_or_missing_qualification_is_not_a_production_prepare(self):
        with self.assertRaisesRegex(ValueError,"Synthetic preparation"):
            self.preparer.prepare(self.source,self.specification)
        changed=copy.deepcopy(self.specification)
        changed["projects"]["aws"]["control_gate"]["path"]="unavailable-native-gate.json"
        with self.assertRaisesRegex(ValueError,"Missing preparation input"):
            self.preparer.prepare(self.source,changed,allow_synthetic=True)

    def test_unreviewed_upstream_source_selector_is_rejected(self):
        changed=copy.deepcopy(self.specification)
        entry=next(iter(changed["projects"]["stdlib"]["base_sources"].values()))
        source=self.source/entry["path"]
        destination=self.source/"unreviewed-base.dfy"
        destination.write_bytes(source.read_bytes())
        entry["path"]="unreviewed-base.dfy"
        with self.assertRaisesRegex(ValueError,"Upstream source is not bound"):
            self.preparer.prepare(self.source,changed,allow_synthetic=True)

    def test_staged_closure_excludes_reference_bodies_and_historical_draft(self):
        names=set(self.freeze["files"])
        self.assertFalse(any("reference-" in name or "draft-001/" in name for name in names))
        self.assertIn("pilot/render_v2.py",names)
        self.assertIn("pilot/draft-002/renderer-inputs.json",names)
        self.assertIn("execution-001/execution-binding.json",names)
        self.assertIn("execution-001/budget-snapshot.json",names)
        self.assertFalse((self.staged/"pilot/prepare.py").exists())
        self.assertFalse((self.staged/"authorization.json").exists())


if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="--worker":
        worker(sys.argv[2],sys.argv[3])
    elif len(sys.argv)>1 and sys.argv[1]=="--smoke":
        worker(sys.argv[2],"smoke",sys.argv[3] if len(sys.argv)>3 else "pilot/draft-002/scope.json")
    else:
        unittest.main(verbosity=2)
