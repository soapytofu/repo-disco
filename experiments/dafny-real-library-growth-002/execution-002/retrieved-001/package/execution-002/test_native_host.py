"""Fake process and capture tests; no native verifier, network, or credentials."""
import copy
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from native_host import FreshNativeHost, capture, fingerprint
from runtime import canonical, native, read_json, sha


class CaptureTests(unittest.TestCase):
    def test_preflight_exact_dafny_and_z3_version_argv(self):
        from test_runner import stages
        source_stages=stages()
        for key,stage in source_stages.items():
            stage.native_profile["toolchain"].update(dafny_version="fake Dafny",solver_version="fake Z3")
            stage.adapter.update(solver="/synthetic/z3")
        calls=[]
        def fake_capture(argv,cwd,seconds,out,err):
            calls.append(argv)
            Path(out).write_bytes(b"fake Z3\n" if argv[0].endswith("z3") else b"fake Dafny\n")
            Path(err).write_bytes(b"")
            return dict(exit_code=0,elapsed_seconds=0.01,timeout=False)
        with tempfile.TemporaryDirectory() as tmp,\
             mock.patch.dict(os.environ,{"SLURM_JOB_ID":"SYNTHETIC","SLURM_CPUS_PER_TASK":"1",
                                        "SLURM_JOB_PARTITION":"SYNTHETIC"},clear=True),\
             mock.patch("native_host.socket.gethostname",return_value="synthetic-compute"),\
             mock.patch("native_host.fingerprint",side_effect=lambda adapter,profile:profile["toolchain"]),\
             mock.patch("native_host.capture",side_effect=fake_capture):
            FreshNativeHost().prepare(source_stages,Path(tmp)/"preflight")
        self.assertEqual(calls,[["/synthetic/dafny","--version"],["/synthetic/z3","-version"]])

    def test_native_child_excludes_provider_environment(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ,
                {"AWS_BEARER_TOKEN_BEDROCK":"SYNTHETIC-SECRET", "AWS_SECRET_ACCESS_KEY":"SYNTHETIC-SECRET",
                 "AWS_SESSION_TOKEN":"SYNTHETIC-SECRET", "BEDROCK_API_KEY":"SYNTHETIC-SECRET",
                 "BOTO_CONFIG":"synthetic-config", "SLURM_JOB_ID":"SYNTHETIC-KEPT"}):
            root=Path(tmp)
            script="import os,json;print(json.dumps({'provider_keys':[k for k in os.environ if k.startswith('AWS_') or k in {'BOTO_CONFIG','BOTO_PATH','BEDROCK_API_KEY'}], 'slurm':os.environ.get('SLURM_JOB_ID')}))"
            meta=capture([sys.executable,"-c",script],root,3,root/"out",root/"err")
            self.assertEqual(meta["exit_code"],0)
            import json
            self.assertEqual(json.loads((root/"out").read_bytes()),{"provider_keys":[],"slurm":"SYNTHETIC-KEPT"})
            self.assertNotIn(b"SYNTHETIC-SECRET",(root/"out").read_bytes())

    def test_complete_process_bytes_and_nonzero_exit_are_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/"out";err=root/"err"
            meta=capture([sys.executable,"-c","import os;os.write(1,b'out\\x00');os.write(2,b'err');raise SystemExit(4)"],
                         root,3,out,err)
            self.assertEqual(meta["exit_code"],4)
            self.assertFalse(meta["timeout"])
            self.assertEqual(out.read_bytes(),b"out\x00")
            self.assertEqual(err.read_bytes(),b"err")
            with self.assertRaises(FileExistsError):
                capture([sys.executable,"-c","pass"],root,3,out,err)

    def test_outer_wall_timeout_closes_process_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            meta=capture([sys.executable,"-c","import time;print('began',flush=True);time.sleep(10)"],
                         root,0.2,root/"out",root/"err")
            self.assertTrue(meta["timeout"])
            self.assertLess(meta["elapsed_seconds"],7)
            self.assertIn(b"began", (root/"out").read_bytes())
            self.assertNotEqual(meta["exit_code"],0)

    def test_normal_parent_exit_cannot_leave_child_mutating_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); marker=root/"escaped"
            child="import time;from pathlib import Path;time.sleep(0.6);Path("+repr(str(marker))+").write_text('bad')"
            parent="import subprocess,sys;subprocess.Popen([sys.executable,'-c',"+repr(child)+"]);print('parent')"
            meta=capture([sys.executable,"-c",parent],root,3,root/"out",root/"err")
            self.assertEqual(meta["exit_code"],0)
            time.sleep(0.8)
            self.assertFalse(marker.exists())

    def test_missing_executable_preserves_opened_streams(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(FileNotFoundError):
                capture([str(root/"no-executable")],root,2,root/"out",root/"err")
            self.assertEqual((root/"out").read_bytes(),b"")
            self.assertEqual((root/"err").read_bytes(),b"")

    def test_compute_and_single_cpu_restrictions(self):
        for environ,host in [({},"compute"),({"SLURM_JOB_ID":"1","SLURM_CPUS_PER_TASK":"1"},"holylogin01"),
                             ({"SLURM_JOB_ID":"1","SLURM_CPUS_PER_TASK":"2"},"compute")]:
            with self.subTest(environ=environ),mock.patch.dict(os.environ,environ,clear=True),\
                 mock.patch("native_host.socket.gethostname",return_value=host),\
                 self.assertRaises(native.EvidenceError):
                FreshNativeHost()

    def test_tool_fingerprint_exact_package_solver_and_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);tool=root/"tool";tool.mkdir()
            (tool/"dafny").write_bytes(b"synthetic program")
            (tool/"support.dll").write_bytes(b"synthetic support")
            solver=root/"solver";solver.write_bytes(b"synthetic solver")
            tools=dict(dafny_version="SYNTHETIC",executable_sha256=sha((tool/"dafny").read_bytes()),
                solver_sha256=sha(solver.read_bytes()),dafny_package_sha256={
                    "dafny":sha((tool/"dafny").read_bytes()),"support.dll":sha((tool/"support.dll").read_bytes())})
            profile={"command":[str(tool/"dafny")],"toolchain":tools}
            adapter={"toolchain_root":str(tool),"solver":str(solver)}
            self.assertEqual(fingerprint(adapter,profile),tools)
            (tool/"support.dll").write_bytes(b"changed")
            with self.assertRaises(native.EvidenceError):fingerprint(adapter,profile)
            self.assertNotEqual(fingerprint(adapter,profile,check_match=False),tools)

    def test_nonfinite_wall_cap_is_rejected_before_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for cap in (float("inf"),float("nan"),0,-1):
                with self.subTest(cap=cap),self.assertRaises(native.EvidenceError):
                    capture([sys.executable,"-c","pass"],root,cap,root/"out",root/"err")

    def test_source_drift_and_record_origin_preserved_for_common_review(self):
        # Inject only subprocess capture/fingerprints; exercise production host
        # source isolation, exact argv, raw CSV discovery and record construction.
        with tempfile.TemporaryDirectory() as tmp,\
             mock.patch.dict(os.environ,{"SLURM_JOB_ID":"SYNTHETIC","SLURM_CPUS_PER_TASK":"1",
                                        "SLURM_JOB_PARTITION":"SYNTHETIC"},clear=True),\
             mock.patch("native_host.socket.gethostname",return_value="synthetic-compute"):
            root=Path(tmp);host=FreshNativeHost();host.prepared=True
            sources={"A.dfy":b"synthetic source"}
            profile={"command":["/not-called/dafny","verify","A.dfy"],"toolchain":{"synthetic":True}}
            event=dict(schema="dafny-library-fresh-native-event-v1",synthetic=False,
                       run_id="SYNTHETIC:test",candidate_sha256=sha(canonical(native.hashes(sources))),
                       profile_sha256=sha(canonical(profile)))
            calls=[]
            def fake_capture(argv,cwd,seconds,out,err):
                calls.append(argv)
                Path(out).write_bytes(b"SYNTHETIC no native process")
                Path(err).write_bytes(b"")
                resources=Path(argv[3]);resources.write_bytes(b"SYNTHETIC")
                (Path(cwd)/"results.csv").write_bytes(b"SYNTHETIC")
                (Path(cwd)/"A.dfy").write_bytes(b"changed by fake process")
                return dict(exit_code=0,elapsed_seconds=0.01,timeout=False)
            with mock.patch("native_host.fingerprint",return_value=profile["toolchain"]),\
                 mock.patch("native_host.capture",side_effect=fake_capture):
                result=host.run(profile,sources,event,root/"native",{"wall_seconds":3})
                self.assertNotEqual(result.record["source_before_sha256"],result.record["source_after_sha256"])
                self.assertEqual(result.record["origin"],"model_candidate")
                self.assertEqual(calls[0][4:],profile["command"])
                self.assertIn("csv/results.csv",result.raw)
                self.assertEqual(read_json(root/"native/record.json"),result.record)
                with self.assertRaises(native.EvidenceError):
                    host.run(profile,sources,event,root/"duplicate",{"wall_seconds":3})


if __name__=="__main__":
    unittest.main(verbosity=2)

