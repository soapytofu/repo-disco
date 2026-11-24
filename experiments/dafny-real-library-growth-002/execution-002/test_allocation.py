"""Synthetic allocation/canonical-path replay tests; no live claims or calls."""
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from allocation import (BINDING_FIELDS, PRIOR_SNAPSHOT_SHA256, claim_allocation,
                        validate_budget, validate_frozen_budget)
from runtime import canonical, native, read_json, save_bytes, sha
from test_runner import scope


def binding_fixture(package,config,*,stage_external=True):
    """Synthetic local paths and a copy of the already public prior budget."""
    package=Path(package).resolve()
    trusted=package.parent/(package.name+"-budget")
    allocation="SYNTHETIC-new-8"
    session="SYNTHETIC-session"
    prior=read_json(Path(__file__).resolve().parent/"prior-budget-snapshot.json")
    snapshot=copy.deepcopy(prior)
    snapshot.update(previous_snapshot_sha256=PRIOR_SNAPSHOT_SHA256,budget_session_id=session,
                    total_allocated_request_ceiling=44,unallocated_request_ceiling=56,
                    recorded_utc="SYNTHETIC OFFLINE TEST, NOT AUTHORIZATION")
    snapshot["allocations"].append(dict(execution_id=allocation,runtime_execution_id=config["batch_id"],
        maximum_new_requests=8,requests_reserved=0,returned_responses=0,ambiguous_requests=0,
        no_retries=True,no_reassignment=True,blocked_or_unused_slots_stay_with_this_allocation=True))
    raw=canonical(snapshot)
    binding=dict(package_root=str(package),output_path=str(package.parent/(package.name+"-model-001")),
        allocation_claim_path=str(trusted/"claims"/(allocation+".json")),
        budget_snapshot_path=str(trusted/"budget-005.json"),budget_snapshot_sha256=sha(raw),
        allocation_id=allocation,budget_session_id=session,budget_snapshot_input="pilot/budget-snapshot.json")
    config["execution_binding"]=binding
    save_bytes(package/binding["budget_snapshot_input"],raw)
    if stage_external:
        (trusted/"claims").mkdir(parents=True)
        save_bytes(Path(binding["budget_snapshot_path"]),raw)
    return snapshot,binding


def authorization(binding):
    return dict(schema="dafny-library-independent-execution-authorization-v1",operator="Sophie Zeng",
        scope_sha256="a"*64,runtime_manifest_sha256="b"*64,max_new_calls=8,total_session_ceiling=100,
        no_retry=True,no_reassignment=True,no_resume=True,human_approval_basis="SYNTHETIC UNIT TEST ONLY",
        created_at_epoch=1,expires_at_epoch=100,**{key:binding[key] for key in BINDING_FIELDS})


def claim(auth,config,package,output=None):
    return claim_allocation(auth,config,package,output or Path(auth["output_path"]),
        scope_sha256="a"*64,runtime_sha256="b"*64,authorization_sha256=sha(canonical(auth)),now=2)


class AllocationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.package=Path(self.temp.name).resolve()/"package"
        self.package.mkdir()
        self.scope=scope()
        self.budget,self.binding=binding_fixture(self.package,self.scope)
        self.auth=authorization(self.binding)

    def tearDown(self):
        self.temp.cleanup()

    def test_exclusive_durable_claim_binds_eight_with_prior_thirty_six(self):
        result=claim(self.auth,self.scope,self.package)
        self.assertEqual(result.record["budget_counts"]["total_allocated"],44)
        self.assertEqual(result.record["state"],"CONSUMED_NO_RESUME")
        self.assertFalse(Path(self.binding["output_path"]).exists())
        self.assertEqual(os.stat(result.path).st_mode&0o777,0o600)
        result.validate()
        result.bind_runner(self.package,Path(self.binding["output_path"]),self.scope)
        with self.assertRaises(native.EvidenceError):
            result.bind_runner(self.package,Path(self.binding["output_path"]),self.scope)
        with self.assertRaises(FileExistsError):
            claim(self.auth,self.scope,self.package)

    def test_same_authorization_alternate_output_and_copied_package_fail_before_claim(self):
        with self.assertRaisesRegex(native.EvidenceError,"Alternate"):
            claim(self.auth,self.scope,self.package,self.package.parent/"alternate-output")
        copied=self.package.parent/"copied-package"
        shutil.copytree(self.package,copied)
        with self.assertRaisesRegex(native.EvidenceError,"Alternate"):
            claim(self.auth,self.scope,copied)
        self.assertFalse(Path(self.binding["allocation_claim_path"]).exists())
        self.assertFalse((self.package.parent/"alternate-output").exists())

    def test_changed_authorization_cannot_retarget_frozen_claim(self):
        changed=copy.deepcopy(self.auth)
        changed["allocation_claim_path"]=str(Path(self.binding["allocation_claim_path"]).with_name("other.json"))
        with self.assertRaisesRegex(native.EvidenceError,"binding"):
            claim(changed,self.scope,self.package)
        self.assertFalse(Path(changed["allocation_claim_path"]).exists())

    def test_claim_survives_predispatch_failure_and_absent_output(self):
        result=claim(self.auth,self.scope,self.package)
        try:
            raise RuntimeError("SYNTHETIC preflight failure")
        except RuntimeError:
            pass
        self.assertTrue(result.path.exists())
        self.assertFalse(Path(self.binding["output_path"]).exists())
        with self.assertRaises(FileExistsError):
            claim(self.auth,self.scope,self.package)

    def test_write_failure_still_consumes_claim(self):
        with mock.patch("allocation.os.fsync",side_effect=OSError("SYNTHETIC fsync failure")):
            with self.assertRaises(OSError):
                claim(self.auth,self.scope,self.package)
        self.assertTrue(Path(self.binding["allocation_claim_path"]).exists())
        with self.assertRaises(FileExistsError):
            claim(self.auth,self.scope,self.package)

    def test_concurrent_claims_have_only_one_winner(self):
        def attempt():
            try:
                return claim(self.auth,self.scope,self.package)
            except FileExistsError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:attempt(),range(2)))
        self.assertEqual(sum(x is not None for x in results),1)

    def test_external_or_frozen_budget_drift_blocks_claim(self):
        for location in ("external","frozen"):
            with self.subTest(location=location):
                path=(Path(self.binding["budget_snapshot_path"]) if location=="external"
                      else self.package/self.binding["budget_snapshot_input"])
                original=path.read_bytes()
                path.write_bytes(original+b" ")
                with self.assertRaises(native.EvidenceError):
                    claim(self.auth,self.scope,self.package)
                path.write_bytes(original)
        self.assertFalse(Path(self.binding["allocation_claim_path"]).exists())

    def test_overflow_missing_history_reallocation_and_current_used_are_rejected(self):
        for kind in ("overflow","history","reassign","used","total","session","duplicate"):
            changed=copy.deepcopy(self.budget)
            if kind=="overflow":
                changed["allocations"][-1]["maximum_new_requests"]=90
                changed["total_allocated_request_ceiling"]=106
                changed["unallocated_request_ceiling"]=-6
            elif kind=="history":
                changed["allocations"].pop(0)
            elif kind=="reassign":
                changed["allocations"][0]["maximum_new_requests"]=1
            elif kind=="used":
                changed["allocations"][-1]["requests_reserved"]=1
                changed["confirmed_total_new_requests_reserved"]=8
            elif kind=="total":changed["total_allocated_request_ceiling"]=12
            elif kind=="session":changed["budget_session_id"]="other"
            else:changed["allocations"][-1]["execution_id"]=changed["allocations"][0]["execution_id"]
            with self.subTest(kind=kind),self.assertRaises(native.EvidenceError):
                validate_budget(changed,self.binding,self.scope)

    def test_claim_or_budget_postclaim_drift_is_terminal(self):
        result=claim(self.auth,self.scope,self.package)
        for path in (result.path,Path(self.binding["budget_snapshot_path"])):
            original=path.read_bytes()
            path.write_bytes(original+b" ")
            with self.assertRaises(native.EvidenceError):result.validate()
            path.write_bytes(original)

    def test_claim_and_snapshot_must_be_outside_copied_packages(self):
        for key,path in (("allocation_claim_path",self.package/"claims"/(self.binding["allocation_id"]+".json")),
                         ("budget_snapshot_path",self.package/"budget.json")):
            changed=copy.deepcopy(self.scope)
            changed["execution_binding"][key]=str(path)
            with self.subTest(key=key),self.assertRaises(native.EvidenceError):
                validate_frozen_budget(self.package,changed)

    def test_symlinked_canonical_claim_directory_is_rejected(self):
        claims=Path(self.binding["allocation_claim_path"]).parent
        real=claims.with_name("moved-claims")
        claims.rename(real)
        claims.symlink_to(real,target_is_directory=True)
        with self.assertRaises(native.EvidenceError):
            claim(self.auth,self.scope,self.package)
        self.assertFalse((real/(self.binding["allocation_id"]+".json")).exists())

    def test_prior_budget_copy_is_exact_anchor(self):
        raw=(Path(__file__).resolve().parent/"prior-budget-snapshot.json").read_bytes()
        self.assertEqual(sha(raw),PRIOR_SNAPSHOT_SHA256)

    def test_live_cli_claim_precedes_preflight_and_private_handoff(self):
        from test_build_runtime import fixture
        from build_runtime import build
        import run_pilot
        with tempfile.TemporaryDirectory() as tmp:
            package=Path(tmp).resolve()/"cli-package";package.mkdir()
            config=fixture(package)
            binding=config["execution_binding"]
            Path(binding["allocation_claim_path"]).parent.mkdir(parents=True)
            Path(binding["budget_snapshot_path"]).write_bytes((package/binding["budget_snapshot_input"]).read_bytes())
            manifest=package/"execution-002/runtime-freeze.json"
            build(package,"pilot/scope.json",manifest)
            auth=authorization(binding)
            auth.update(scope_sha256=sha((package/"pilot/scope.json").read_bytes()),
                        runtime_manifest_sha256=sha(manifest.read_bytes()),created_at_epoch=time.time(),
                        expires_at_epoch=time.time()+60)
            auth_path=Path(tmp)/"synthetic-authorization.json";auth_path.write_bytes(canonical(auth))
            argv=["run_pilot.py","--scope",str(package/"pilot/scope.json"),"--authorization",str(auth_path),
                "--runtime-freeze",str(manifest),"--expected-runtime-sha",sha(manifest.read_bytes()),
                "--output",binding["output_path"],"--private-handoff",str(Path(tmp)/"must-not-be-read")]
            observed=[]
            def stop_preflight(host,stages,destination):
                observed.append(Path(binding["allocation_claim_path"]).is_file())
                raise RuntimeError("SYNTHETIC preflight stops before provider")
            with mock.patch.object(run_pilot,"PACKAGE",package),mock.patch.object(sys,"argv",argv),\
                 mock.patch.dict(os.environ,{"SLURM_JOB_ID":"SYNTHETIC","SLURM_CPUS_PER_TASK":"1",
                                            "SLURM_JOB_PARTITION":"SYNTHETIC"},clear=True),\
                 mock.patch("native_host.socket.gethostname",return_value="synthetic-compute"),\
                 mock.patch("native_host.FreshNativeHost.check_tools"),\
                 mock.patch("native_host.FreshNativeHost.prepare",new=stop_preflight),\
                 mock.patch("run_pilot.load_private_token",side_effect=AssertionError("Private handoff touched")) as key:
                with self.assertRaises(SystemExit) as exit_result:
                    run_pilot.main()
                self.assertEqual(exit_result.exception.code,2)
                key.assert_not_called()
                self.assertEqual(observed,[True])
                report=read_json(Path(binding["output_path"])/"summary.json")
                self.assertEqual((report["reserved"],report["native_dispatches"]),(0,0))
                # Output deletion cannot reopen the canonical consumed claim.
                shutil.rmtree(binding["output_path"])
                with self.assertRaises(FileExistsError):
                    run_pilot.main()
                key.assert_not_called()


if __name__=="__main__":
    unittest.main(verbosity=2)

