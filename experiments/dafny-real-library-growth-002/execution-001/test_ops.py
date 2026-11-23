"""Offline operations boundary tests. No SSH, Slurm, provider or native calls."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import types
import unittest
from unittest import mock

import ops
from test_allocation import authorization,binding_fixture
from test_runner import scope
from runtime import canonical,sha


def staged_payload(base):
    source=base/"source";source.mkdir()
    config=scope()
    config["renderer"]="pilot/render.py"
    budget,binding=binding_fixture(source,config,stage_external=False)
    execution=base/"remote-execution"
    binding.update(package_root=str(execution/"package"),output_path=str(execution/"model-001"))
    config["execution_binding"]=binding
    files={"pilot/scope.json":canonical(config),
           binding["budget_snapshot_input"]:(source/binding["budget_snapshot_input"]).read_bytes(),
           "execution-001/model.sbatch":(Path(__file__).parent/"model.sbatch").read_bytes(),
           "pilot/test_render.py":b"# SYNTHETIC smoke entry point; never executed\n",
           "pilot/render.py":b"# SYNTHETIC renderer; never executed\n",
           "common/data.txt":b"frozen nonsensitive input"}
    freeze=dict(schema="dafny-library-execution-runtime-v1",scope="pilot/scope.json",
                files={name:sha(raw) for name,raw in files.items()})
    files[ops.FREEZE_NAME]=canonical(freeze)
    return binding,sha(files[ops.FREEZE_NAME]),ops.make_archive(files),config


def accounting(job="123",parent="COMPLETED",step="COMPLETED"):
    header="|".join(ops.ACCOUNTING_FIELDS)
    row=lambda ident,state:"|".join([ident,state,"00:00:01","1","0:0","1","00:00:01","1","1K","synthetic-compute"])
    return header+"\n"+row(job,parent)+"\n"+row(job+".batch",step)+"\n"


class OpsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name).resolve()
        self.binding,self.digest,self.payload,self.scope=staged_payload(self.base)

    def tearDown(self):self.temp.cleanup()

    def stage(self):
        with mock.patch("ops.command",return_value=""):
            return ops.stage_remote(self.binding,self.digest,self.payload)

    def preflight_records(self):
        root=Path(self.binding["package_root"]).parent
        ops.save(root/"preflight.intent.json",{"synthetic":True})
        ops.save(root/"sdk-imports.json",{"synthetic":True})
        ops.write(root/"preflight.stdout.txt",b"synthetic unit output")
        ops.write(root/"preflight.stderr.txt",b"")
        with mock.patch("ops.capture_preflight",side_effect=self.smoke_capture):
            smoke=ops.capture_renderer_smoke(self.binding,self.digest,
                ops.read(Path(self.binding["package_root"])/ops.FREEZE_NAME))
        self.assertEqual(smoke["status"],"PASS")
        ops.save(root/"preflight-001.json",dict(runtime_sha256=self.digest,exit_code=0,timed_out=False,
                 sdk={"client_created":False},canonical_claim_created=False,renderer_smoke=smoke,
                 renderer_smoke_record_sha256=sha((root/"renderer-smoke.json").read_bytes())))
        return root

    def smoke_capture(self,argv,cwd,seconds):
        self.assertIn("--smoke",argv)
        root=Path(self.binding["package_root"]).parent
        ops.save(root/"synthetic-smoke/summary.json",dict(status="COMPLETE",synthetic=True,
            reserved=8,completed=8,accepted_stages=8,independent_trials=True,
            native_dispatches=8,native_observations=8))
        ops.save(root/"synthetic-smoke/requests/ledger.json",dict(synthetic=True,closed=True))
        receipt=dict(mode="smoke",synthetic=True,provider_calls=0,native_processes=0,
            fake_transport_dispatches=8,fake_native_observations=8,reserved=8,completed=8,
            accepted_synthetic_stages=8,exact_base_view_assertions=8,default_synthetic_rejection_assertions=8,actual_renderer="pilot/render.py",
            staged_module_path_verified=True,manifest_sha256=self.digest)
        return dict(exit_code=0,timed_out=False,wall_cap_seconds=seconds),canonical(receipt),b""

    def auth_bytes(self):
        auth=authorization(self.binding)
        auth.update(scope_sha256=sha(canonical(self.scope)),runtime_manifest_sha256=self.digest,
                    created_at_epoch=time.time(),expires_at_epoch=time.time()+120)
        return canonical(auth)

    def cluster_command(self,argv,seconds=20):
        if argv[0]=="scontrol":
            return "PartitionName=test PreemptMode=OFF State=UP MaxTime=12:00:00 MaxMemPerNode=8192"
        if argv[0]=="squeue":return ""
        raise AssertionError("Unexpected command "+repr(argv))

    def fake_sdk(self):
        return {"boto3":types.SimpleNamespace(__version__="SYNTHETIC"),
                "botocore":types.SimpleNamespace(__version__="SYNTHETIC"),
                "botocore.config":types.SimpleNamespace(Config=lambda **kw:types.SimpleNamespace(**kw))}

    def test_exact_staging_creates_no_claim_or_output(self):
        result=self.stage()
        self.assertFalse(result["allocation_claim_created"])
        self.assertFalse(Path(self.binding["allocation_claim_path"]).exists())
        self.assertFalse(Path(self.binding["output_path"]).exists())
        self.assertEqual(sha(Path(self.binding["budget_snapshot_path"]).read_bytes()),self.binding["budget_snapshot_sha256"])
        with mock.patch("ops.command",return_value=""),self.assertRaises(ValueError):
            ops.stage_remote(self.binding,self.digest,self.payload)

    def test_stage_conflicting_budget_and_matching_queue_block_before_mutation(self):
        budget=Path(self.binding["budget_snapshot_path"]);budget.parent.mkdir(parents=True)
        budget.write_bytes(b"different")
        with mock.patch("ops.command",return_value=""),self.assertRaises(ValueError):
            ops.stage_remote(self.binding,self.digest,self.payload)
        self.assertFalse(Path(self.binding["package_root"]).exists())
        budget.unlink()
        queue="10|"+str(Path(self.binding["package_root"]).parent)+"|other|RUNNING\n"
        with mock.patch("ops.command",return_value=queue),self.assertRaises(ValueError):
            ops.stage_remote(self.binding,self.digest,self.payload)
        self.assertFalse(Path(self.binding["package_root"]).exists())

    def test_extra_archive_member_and_file_directory_collision_rejected(self):
        files=ops.archive_members(self.payload);files["not-in-manifest"]=b"extra"
        with mock.patch("ops.command",return_value=""),self.assertRaises(ValueError):
            ops.stage_remote(self.binding,self.digest,ops.make_archive(files))
        with self.assertRaises(ValueError):
            ops.archive_members(ops.make_archive({"x":b"a","x/y":b"b"}))

    def test_tar_traversal_link_duplicate_and_absolute_rejected(self):
        for name,kind,duplicate in (("../escape",tarfile.REGTYPE,False),("/absolute",tarfile.REGTYPE,False),
                                    ("link",tarfile.SYMTYPE,False),("same",tarfile.REGTYPE,True)):
            raw=io.BytesIO()
            with tarfile.open(fileobj=raw,mode="w:gz") as archive:
                member=tarfile.TarInfo(name);member.type=kind;member.size=0
                archive.addfile(member,io.BytesIO())
                if duplicate:archive.addfile(member,io.BytesIO())
            with self.subTest(name=name),self.assertRaises(ValueError):ops.archive_members(raw.getvalue())

    def test_partition_requires_live_test_up_off_and_three_hours(self):
        self.assertEqual(ops.partition_seconds("PartitionName=test PreemptMode=OFF State=UP MaxTime=03:00:00"),10800)
        for text in ("PartitionName=test PreemptMode=REQUEUE State=UP MaxTime=12:00:00",
                     "PartitionName=shared PreemptMode=OFF State=UP MaxTime=12:00:00",
                     "PartitionName=test PreemptMode=OFF State=DOWN MaxTime=12:00:00",
                     "PartitionName=test PreemptMode=OFF State=UP MaxTime=02:59:59",
                     "PartitionName=test PreemptMode=OFF State=UP MaxTime=12:00:00 MaxMemPerNode=2048",
                     "PartitionName=test PreemptMode=OFF State=UP MaxTime=12:99:00"):
            with self.subTest(text=text),self.assertRaises(ValueError):ops.partition_seconds(text)

    def test_all_relevant_accounting_steps_must_be_terminal(self):
        self.assertTrue(ops.terminal_accounting(accounting(),"123")["all_relevant_rows_terminal"])
        for state in ("RUNNING","PENDING","SUSPENDED","REQUEUE_FED","STOPPED","UNKNOWN","OUT_OF_ME+"):
            with self.subTest(state=state),self.assertRaises(ValueError):
                ops.terminal_accounting(accounting(step=state),"123")
        self.assertEqual(ops.terminal_accounting(accounting(parent="CANCELLED by 1000"),"123")["rows"][0]["normalized_state"],"CANCELLED")
        for text in (accounting().replace("123|","124|"),accounting()+accounting().splitlines()[1]+"\n"):
            with self.assertRaises(ValueError):ops.terminal_accounting(text,"123")

    def test_remote_command_uses_only_existing_socket_and_hard_timeout(self):
        result=subprocess.CompletedProcess([],0,b"{}",b"")
        with mock.patch("ops.subprocess.run",return_value=result) as call:
            self.assertEqual(ops.remote("inspect",self.binding,self.digest,seconds=31),b"{}")
        argv=call.call_args.args[0]
        self.assertIn(str(ops.SOCKET),argv)
        self.assertIn("BatchMode=yes",argv)
        self.assertIn("ControlMaster=no",argv)
        self.assertIn("ProxyCommand=false",argv)
        self.assertIn("NumberOfPasswordPrompts=0",argv)
        self.assertEqual(call.call_args.kwargs["timeout"],31)
        self.assertNotIn("prepare_key",repr(argv))

    def test_actual_remote_stage_program_uses_same_tested_archive_boundary(self):
        program=ops.remote_program("stage",self.binding,self.digest)
        fake_input=types.SimpleNamespace(buffer=io.BytesIO(self.payload))
        fake_output=io.StringIO()
        completed=subprocess.CompletedProcess([],0,b"",b"")
        with mock.patch("sys.stdin",fake_input),mock.patch("sys.stdout",fake_output),\
             mock.patch("subprocess.run",return_value=completed):
            exec(compile(program,"synthetic-remote-program","exec"),{})
        self.assertTrue(json.loads(fake_output.getvalue())["files"]>0)
        self.assertFalse(Path(self.binding["allocation_claim_path"]).exists())

    def test_fake_preflight_imports_sdk_without_client_or_claim(self):
        self.stage()
        config_calls=[]
        def config(**kw):
            config_calls.append(kw);return types.SimpleNamespace(**kw)
        modules={"boto3":types.SimpleNamespace(__version__="SYNTHETIC"),
                 "botocore":types.SimpleNamespace(__version__="SYNTHETIC"),
                 "botocore.config":types.SimpleNamespace(Config=config)}
        def fake_spawn(argv,**kwargs):
            child=mock.Mock(pid=99999999,returncode=0)
            streams=(self.smoke_capture(argv,kwargs["cwd"],120)[1:] if "--smoke" in argv
                     else (b"synthetic passed",b""))
            child.communicate.return_value=streams;child.wait.return_value=0
            return child
        with mock.patch("ops.command",return_value=""),mock.patch.dict(sys.modules,modules),\
             mock.patch("ops.subprocess.Popen",side_effect=fake_spawn) as spawn,mock.patch("ops.os.killpg"):
            result=ops.preflight_remote(self.binding,self.digest)
        self.assertEqual(result["exit_code"],0)
        self.assertFalse(result["sdk"]["client_created"])
        self.assertFalse(Path(self.binding["allocation_claim_path"]).exists())
        self.assertEqual(config_calls[0]["retries"]["total_max_attempts"],1)
        self.assertIn("test_allocation",spawn.call_args_list[0].args[0])
        self.assertIn("test_ops",spawn.call_args_list[0].args[0])
        self.assertEqual(spawn.call_args_list[1].args[0],
            [ops.PYTHON,"-B",str(Path(self.binding["package_root"])/"pilot/test_render.py"),
             "--smoke",self.binding["package_root"],"pilot/scope.json"])
        self.assertEqual(result["renderer_smoke"]["status"],"PASS")

    def test_submit_one_exact_cpu_memory_time_attempt_and_no_claim(self):
        self.stage();root=self.preflight_records()
        completed=subprocess.CompletedProcess([],0,b"123;cluster\n",b"")
        with mock.patch("ops.command",side_effect=self.cluster_command),\
             mock.patch("ops.subprocess.run",return_value=completed) as submit:
            result=ops.submit_remote(self.binding,self.digest,self.auth_bytes())
            self.assertEqual(result["job_id"],"123")
            with self.assertRaises(ValueError):
                ops.submit_remote(self.binding,self.digest,self.auth_bytes())
        self.assertEqual(submit.call_count,1)
        argv=submit.call_args.args[0]
        for value in ("--partition=test","--cpus-per-task=1","--mem=4G","--time=03:00:00","--no-requeue"):
            self.assertIn(value,argv)
        self.assertFalse(Path(self.binding["allocation_claim_path"]).exists())
        self.assertFalse(Path(self.binding["output_path"]).exists())
        self.assertTrue((root/"submissions/model.intent.json").exists())

    def test_sdk_import_failure_is_preserved_without_tests_or_claim(self):
        self.stage()
        with mock.patch("ops.command",return_value=""),mock.patch.dict(sys.modules,{"boto3":None}),\
             mock.patch("ops.subprocess.Popen") as spawn:
            result=ops.preflight_remote(self.binding,self.digest)
        self.assertEqual(result["exit_code"],2)
        self.assertFalse(result["tests_started"])
        spawn.assert_not_called()
        self.assertFalse(Path(self.binding["allocation_claim_path"]).exists())
        root=Path(self.binding["package_root"]).parent
        self.assertTrue((root/"preflight.stderr.txt").is_file())

    def test_existing_local_intents_block_mutations(self):
        with mock.patch.object(ops,"ROOT",self.base/"local"):
            ops.save(ops.ROOT/"submissions/model.intent.json",{"synthetic":True})
            with self.assertRaises(ValueError):ops.local_fresh("submit")
            ops.save(ops.ROOT/"stage.intent.json",{"synthetic":True})
            with self.assertRaises(ValueError):ops.local_fresh("stage")
            ops.save(ops.ROOT/"fetch.intent.json",{"synthetic":True})
            with self.assertRaises(ValueError):ops.local_fresh("fetch")

    def test_ambiguous_sbatch_timeout_is_recorded_once_and_blocks_repeat(self):
        self.stage();root=self.preflight_records()
        with mock.patch("ops.command",side_effect=self.cluster_command),\
             mock.patch("ops.subprocess.run",side_effect=subprocess.TimeoutExpired(["sbatch"],25)) as submit:
            result=ops.submit_remote(self.binding,self.digest,self.auth_bytes())
            self.assertTrue(result["ambiguous_submission"])
            self.assertNotIn("job_id",result)
            with self.assertRaises(ValueError):
                ops.submit_remote(self.binding,self.digest,self.auth_bytes())
        self.assertEqual(submit.call_count,1)
        self.assertTrue((root/"submissions/model.json").is_file())

    def test_fetch_complete_nonsecret_inventory_terminal_only_and_no_refetch(self):
        self.stage();root=self.preflight_records()
        ops.write(root/"authorization.json",self.auth_bytes())
        ops.save(root/"submissions/model.intent.json",{"synthetic":True})
        ops.save(root/"submissions/model.json",{"job_id":"123"})
        ops.write(root/"library-growth-123.log",b"synthetic scheduler output")
        ops.save(Path(self.binding["output_path"])/"summary.json",{"synthetic":True,"reserved":0})
        ops.write(root/"unrelated-private-file",b"SYNTHETIC NOT A REAL SECRET")
        with mock.patch("ops.accounting",return_value=accounting()),mock.patch("ops.command",return_value=""):
            files,inventory=ops.transfer_files(self.binding,self.digest,"123")
            self.assertNotIn("unrelated-private-file",files)
            self.assertIn("accounting-review.json",files)
            self.assertIn("model-001/summary.json",files)
            self.assertIn("renderer-smoke.stdout.txt",files)
            self.assertIn("renderer-smoke-receipt.json",files)
            self.assertIn("synthetic-smoke/requests/ledger.json",files)
            raw=ops.fetch_remote(self.binding,self.digest,"123",inventory)
            self.assertEqual(ops.archive_members(raw),files)
            with self.assertRaises(ValueError):ops.fetch_remote(self.binding,self.digest,"123",inventory)

    def test_fetch_running_step_is_refused_before_any_marker(self):
        self.stage()
        with mock.patch("ops.accounting",return_value=accounting(step="RUNNING")),\
             mock.patch("ops.command",return_value=""),self.assertRaises(ValueError):
            ops.transfer_files(self.binding,self.digest,"123")
        self.assertFalse((Path(self.binding["package_root"]).parent/"fetch.intent.json").exists())

    def test_archive_space_counts_existing_raw_archive_only_once(self):
        size=100*1024**2;space=types.SimpleNamespace(free=180*1024**2)
        with mock.patch("ops.shutil.disk_usage",return_value=space):
            with self.assertRaises(ValueError):ops.check_space({"source_bytes":size})
            self.assertGreater(ops.check_space({"source_bytes":size},archive_saved=True)["available_free_bytes"],0)

    def test_sbatch_fixed_resources_and_canonical_root(self):
        text=(Path(__file__).parent/"model.sbatch").read_text()
        for line in ("#SBATCH --partition=test","#SBATCH --cpus-per-task=1","#SBATCH --mem=4G",
                     "#SBATCH --time=03:00:00","#SBATCH --no-requeue"):
            self.assertIn(line,text)
        self.assertIn("formal-disco/outputs/dafny-real-library-growth-002/execution-001",text)
        self.assertIn('--scope "$1" --expected-runtime-sha "$2"',text)
        self.assertNotIn("prepare_key.py",text)

    def test_renderer_smoke_failure_blocks_before_authorization_or_sbatch(self):
        self.stage()
        unit=(dict(exit_code=0,timed_out=False,wall_cap_seconds=60),b"unit passed",b"")
        failed=(dict(exit_code=1,timed_out=False,wall_cap_seconds=120),b"partial smoke",b"SYNTHETIC FAILURE")
        with mock.patch("ops.command",return_value=""),mock.patch.dict(sys.modules,self.fake_sdk()),\
             mock.patch("ops.capture_preflight",side_effect=[unit,failed]) as invoke:
            pre=ops.preflight_remote(self.binding,self.digest)
        self.assertEqual(pre["exit_code"],2)
        self.assertEqual(invoke.call_args_list[1].args[2],120)
        root=Path(self.binding["package_root"]).parent
        self.assertEqual((root/"renderer-smoke.stdout.txt").read_bytes(),b"partial smoke")
        with mock.patch("ops.command",side_effect=self.cluster_command),\
             mock.patch("ops.subprocess.run") as submit,self.assertRaises(ValueError):
            ops.submit_remote(self.binding,self.digest,self.auth_bytes())
        submit.assert_not_called()
        self.assertFalse((root/"authorization.json").exists())
        self.assertFalse(Path(self.binding["allocation_claim_path"]).exists())

    def test_smoke_timeout_is_saved_as_failure(self):
        self.stage()
        failed=(dict(exit_code=-9,timed_out=True,wall_cap_seconds=120),b"partial",b"")
        with mock.patch("ops.capture_preflight",return_value=failed):
            record=ops.capture_renderer_smoke(self.binding,self.digest,
                ops.read(Path(self.binding["package_root"])/ops.FREEZE_NAME))
        self.assertEqual(record["status"],"FAIL")
        self.assertTrue(record["timed_out"])

    def test_smoke_wrong_count_is_not_a_pass_despite_clean_process_exit(self):
        self.stage()
        def wrong(*args):
            meta,out,err=self.smoke_capture(*args)
            report=json.loads(out);report["accepted_synthetic_stages"]=11
            return meta,canonical(report),err
        with mock.patch("ops.capture_preflight",side_effect=wrong):
            record=ops.capture_renderer_smoke(self.binding,self.digest,
                ops.read(Path(self.binding["package_root"])/ops.FREEZE_NAME))
        self.assertEqual(record["status"],"FAIL")
        self.assertEqual(record["exit_code"],0)

    def test_persisted_smoke_stdout_summary_and_ledger_drift_block_submission(self):
        self.stage();root=self.preflight_records()
        for name in ("renderer-smoke.stdout.txt","synthetic-smoke/summary.json","synthetic-smoke/requests/ledger.json"):
            path=root/name;original=path.read_bytes();path.write_bytes(original+b" ")
            with self.subTest(name=name),mock.patch("ops.command",side_effect=self.cluster_command),\
                 mock.patch("ops.subprocess.run") as submit,self.assertRaises(ValueError):
                ops.submit_remote(self.binding,self.digest,self.auth_bytes())
            submit.assert_not_called();path.write_bytes(original)
        self.assertFalse((root/"authorization.json").exists())
        self.assertFalse((root/"submissions/model.intent.json").exists())

    def test_only_exact_synthetic_smoke_is_excluded_and_must_be_absent_before_preflight(self):
        self.stage();root=Path(self.binding["package_root"]).parent
        ops.save(root/"synthetic-smoke/requests/ledger.json",{"synthetic":True})
        with mock.patch("ops.command",return_value=""):
            observed=ops.inspect_state(self.binding)
            self.assertEqual(observed["ledger_files"],[])
            self.assertTrue(observed["synthetic_smoke_exists"])
            with self.assertRaises(ValueError):ops.preflight_remote(self.binding,self.digest)
            ops.save(root/"synthetic-other/ledger.json",{"synthetic":True})
            observed=ops.inspect_state(self.binding)
            self.assertEqual(observed["ledger_files"],["synthetic-other/ledger.json"])
            with self.assertRaises(ValueError):ops.fresh_state(observed,self.binding)
        self.assertFalse((root/"preflight.intent.json").exists())

    def test_smoke_receipt_requires_zero_real_calls_and_exact_base_checks(self):
        self.stage()
        _,raw,_=self.smoke_capture(["--smoke"],None,120)
        receipt=json.loads(raw)
        summary=ops.read(Path(self.binding["package_root"]).parent/"synthetic-smoke/summary.json")
        for changed in ({"synthetic":False},{"provider_calls":1},{"provider_calls":False},
                        {"native_processes":1},{"exact_base_view_assertions":7},
                        {"manifest_sha256":"f"*64}):
            value=dict(receipt,**changed)
            with self.subTest(changed=changed),self.assertRaises(ValueError):
                ops.validate_smoke_receipt(value,summary,self.digest,self.scope["renderer"])

    def test_unit_failure_skips_renderer_smoke(self):
        self.stage()
        failed=(dict(exit_code=1,timed_out=False,wall_cap_seconds=60),b"unit failure",b"")
        with mock.patch("ops.command",return_value=""),mock.patch.dict(sys.modules,self.fake_sdk()),\
             mock.patch("ops.capture_preflight",return_value=failed) as invoke:
            pre=ops.preflight_remote(self.binding,self.digest)
        self.assertEqual(pre["exit_code"],2)
        self.assertEqual(invoke.call_count,1)
        self.assertIsNone(pre["renderer_smoke"])

    def test_bounded_smoke_process_timeout_kills_group_and_preserves_partial_streams(self):
        child=mock.Mock(pid=99999999,returncode=-9)
        child.communicate.side_effect=[subprocess.TimeoutExpired(["synthetic-python"],120),(b"partial stdout",b"partial stderr")]
        child.wait.return_value=-9
        with mock.patch("ops.subprocess.Popen",return_value=child),mock.patch("ops.os.killpg") as kill:
            meta,out,err=ops.capture_preflight(["synthetic-python"],self.base,120)
        self.assertTrue(meta["timed_out"])
        self.assertEqual(meta["exit_code"],-9)
        self.assertEqual((out,err),(b"partial stdout",b"partial stderr"))
        self.assertGreaterEqual(kill.call_count,2)
        self.assertEqual(child.communicate.call_args_list[0].kwargs["timeout"],120)
        self.assertEqual(child.communicate.call_args_list[1].kwargs["timeout"],10)

    def test_stdin_bootstrap_preserves_program_and_binary_payload(self):
        import shlex
        actual_run=subprocess.run
        payload=b"\x00\xff\nBINARY-STAGE\x00"
        program="import sys\n# "+("large inventory "*15000)+"\nsys.stdout.buffer.write(sys.stdin.buffer.read())\n"
        observed=[]
        def fake_ssh(argv,**kwargs):
            command=shlex.split(argv[-1]);observed.append((argv,kwargs))
            self.assertLess(len(argv[-1].encode()),4096)
            self.assertNotIn(program,repr(argv))
            return actual_run([sys.executable,"-B","-c",command[-1]],**kwargs)
        with mock.patch("ops.remote_program",return_value=program),mock.patch("ops.subprocess.run",side_effect=fake_ssh):
            returned=ops.remote("stage",self.binding,self.digest,payload=payload,seconds=5)
        self.assertEqual(returned,payload)
        wire=observed[0][1]["input"];size=int.from_bytes(wire[:8],"big")
        self.assertEqual(wire[8:8+size].decode(),program)
        self.assertEqual(wire[8+size:],payload)

    def test_oversized_remote_program_is_blocked_before_ssh(self):
        with mock.patch("ops.remote_program",return_value="x"*(2*1024**2+1)),\
             mock.patch("ops.subprocess.run") as dispatch,self.assertRaises(ValueError):
            ops.remote("inspect",self.binding,self.digest)
        dispatch.assert_not_called()


if __name__=="__main__":unittest.main(verbosity=2)

