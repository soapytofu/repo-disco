"""One-shot canonical allocation claim, separate from every copied package.

The claim is a permanent consumption marker, not a resumable ledger. Creation is
exclusive and durable before output creation, native preflight, provider/client
construction or private handoff access. Even a later pre-dispatch failure leaves
the claim consumed. No helper removes, replaces or resumes a claim.
"""
import json
import os
from pathlib import Path
import stat
import time

from runtime import (MAX_CALLS, canonical, checked_path, json_copy, native, read_json,
                     require, sha, validate_authorization)

PRIOR_SNAPSHOT_SHA256 = "77d2095433f0464b5697a726e04c11ab112136349a2e3d55be0fa96207ba18e9"
PRIOR_ALLOCATIONS_SHA256 = "1738532f78a0ebf09c1c7cd4acfb7c58bfbc1b4d5574e5c992cbc636d7b6f2b5"
BINDING_FIELDS = ("package_root", "output_path", "allocation_claim_path", "budget_snapshot_path",
                  "budget_snapshot_sha256", "allocation_id", "budget_session_id")


def canonical_path(value):
    require(isinstance(value,str) and value and "\x00" not in value, "Canonical absolute path required")
    path=Path(value)
    require(path.is_absolute() and str(path)==value and str(path.resolve())==value,
            "Path is not exact canonical absolute spelling")
    for part in (path,*path.parents):
        require(not part.is_symlink(), "Canonical allocation paths cannot traverse symlinks")
    return path


def validate_budget(snapshot,binding,scope):
    require(snapshot.get("schema")=="repodisco-new-research-budget-snapshot-v1"
            and snapshot.get("approved_by")=="Sophie Zeng"
            and snapshot.get("maximum_total_new_requests")==100, "Wrong cumulative research budget")
    require(all(type(snapshot.get(key)) is int for key in
        ("maximum_total_new_requests","total_allocated_request_ceiling","unallocated_request_ceiling",
         "confirmed_total_new_requests_reserved","confirmed_total_returned_responses")),
        "Cumulative budget counts must be explicit integers")
    require(snapshot.get("previous_snapshot_sha256")==PRIOR_SNAPSHOT_SHA256,
            "Cumulative snapshot does not extend the frozen prior snapshot")
    require(snapshot.get("budget_session_id")==binding["budget_session_id"],"Budget session differs")
    allocations=snapshot.get("allocations")
    require(isinstance(allocations,list) and len(allocations)==3
            and sha(canonical(allocations[:2]))==PRIOR_ALLOCATIONS_SHA256,
            "Historical allocations cannot be dropped, changed or reassigned")
    identities=[]
    total=reserved=returned=0
    for allocation in allocations:
        identity=allocation.get("execution_id")
        require(isinstance(identity,str) and identity and identity not in identities,"Duplicate allocation identity")
        identities.append(identity)
        cap=allocation.get("maximum_new_requests")
        used=allocation.get("requests_reserved")
        responses=allocation.get("returned_responses")
        require(type(cap) is int and 0<cap<=100 and type(used) is int and 0<=used<=cap
                and type(responses) is int and 0<=responses<=used,"Malformed cumulative allocation counts")
        require(all(allocation.get(key) is True for key in
                    ("no_retries","no_reassignment","blocked_or_unused_slots_stay_with_this_allocation")),
                "Historical unused slots cannot be reused")
        total+=cap;reserved+=used;returned+=responses
    require(total<=100 and total==snapshot.get("total_allocated_request_ceiling")
            and 100-total==snapshot.get("unallocated_request_ceiling"),"Cumulative budget overflow/count mismatch")
    require(reserved==snapshot.get("confirmed_total_new_requests_reserved")
            and returned==snapshot.get("confirmed_total_returned_responses"),"Cumulative observation counts differ")
    current=allocations[-1]
    require(current["execution_id"]==binding["allocation_id"]
            and current["runtime_execution_id"]==scope["batch_id"]
            and current["maximum_new_requests"]==MAX_CALLS
            and current["requests_reserved"]==0 and current["returned_responses"]==0
            and type(current.get("ambiguous_requests")) is int and current["ambiguous_requests"]==0,
            "Current allocation is not fresh exact twelve-slot scope")
    require(total==28 and snapshot.get("historical_budget_reuse") is False,
            "This scope allocates exactly twelve beyond the preserved sixteen")
    return dict(total_allocated=total,total_ceiling=100,current_allocation=MAX_CALLS,
                prior_allocated=16,remaining_unallocated=100-total)


def validate_frozen_budget(package,scope):
    binding=scope.get("execution_binding")
    require(isinstance(binding,dict) and set(BINDING_FIELDS)|{"budget_snapshot_input"}<=set(binding),
            "Frozen canonical execution binding required")
    for name in ("allocation_id","budget_session_id"):
        require(native.safe_path(binding[name]) and "/" not in binding[name],"Unsafe budget/allocation identity")
    for name in ("package_root","output_path","allocation_claim_path","budget_snapshot_path"):
        canonical_path(binding[name])
    package_path=Path(binding["package_root"])
    output_path=Path(binding["output_path"])
    claim_path=Path(binding["allocation_claim_path"])
    budget_path=Path(binding["budget_snapshot_path"])
    require(not output_path.is_relative_to(package_path) and not package_path.is_relative_to(output_path),
            "Output must be outside the immutable package")
    require(not claim_path.is_relative_to(package_path) and not claim_path.is_relative_to(output_path)
            and not budget_path.is_relative_to(package_path) and not budget_path.is_relative_to(output_path),
            "Canonical claim and budget must be outside copied package/output roots")
    require(claim_path.name==binding["allocation_id"]+".json","Claim filename must be the exact allocation identity")
    require(claim_path.parent.name=="claims" and claim_path.parent.parent==budget_path.parent,
            "Claim must live in the canonical session budget directory")
    require(isinstance(binding["budget_snapshot_sha256"],str)
            and native.HEX.fullmatch(binding["budget_snapshot_sha256"]),"Missing immutable budget snapshot digest")
    raw=checked_path(package,binding["budget_snapshot_input"]).read_bytes()
    require(sha(raw)==binding["budget_snapshot_sha256"],"Frozen cumulative budget snapshot drifted")
    budget=read_json(checked_path(package,binding["budget_snapshot_input"]))
    return binding,raw,validate_budget(budget,binding,scope)


def validate_execution_binding(auth,scope,package,output):
    binding,raw,counts=validate_frozen_budget(package,scope)
    require(all(auth.get(key)==binding[key] for key in BINDING_FIELDS),"Authorization canonical binding differs")
    require(canonical_path(str(Path(package).resolve()))==canonical_path(binding["package_root"])
            and canonical_path(str(Path(output)))==canonical_path(binding["output_path"]),
            "Alternate package root or output is not authorized")
    require(Path(package).is_dir() and Path(output).parent.is_dir() and not Path(output).exists(),
            "Package/output preparation differs or output already exists")
    budget_path=canonical_path(binding["budget_snapshot_path"])
    claim_path=canonical_path(binding["allocation_claim_path"])
    require(budget_path.is_file() and claim_path.parent.is_dir(),"Canonical budget/claims directory must be staged")
    require(budget_path.read_bytes()==raw,"Canonical cumulative budget differs from frozen snapshot")
    return binding,raw,counts


class AllocationClaim:
    """In-memory capability minted only after a fresh exclusive on-disk claim."""
    def __init__(self,path,record,binding,scope_hash,budget_raw):
        self.path=path
        self.record=json_copy(record)
        self.digest=sha(canonical(record))
        self.binding=json_copy(binding)
        self.scope_hash=scope_hash
        self.budget_raw=budget_raw
        self.bound=False

    def validate(self):
        canonical_path(str(self.path))
        canonical_path(self.binding["budget_snapshot_path"])
        require(self.path.is_file() and not self.path.is_symlink()
                and sha(self.path.read_bytes())==self.digest,"Canonical allocation claim drifted or missing")
        require(Path(self.binding["budget_snapshot_path"]).read_bytes()==self.budget_raw,
                "Canonical cumulative budget drifted after claim")

    def bind_runner(self,package,output,scope):
        require(not self.bound,"An allocation capability cannot create a second runner")
        require(str(Path(package).resolve())==self.binding["package_root"]
                and str(Path(output))==self.binding["output_path"]
                and sha(canonical(scope))==self.scope_hash,"Allocation is bound to another runtime/output/scope")
        self.validate()
        self.bound=True


def claim_allocation(auth,scope,package,output,*,scope_sha256,runtime_sha256,authorization_sha256,now=None):
    epoch=time.time() if now is None else now
    validate_authorization(auth,scope_sha256,runtime_sha256,epoch)
    require(isinstance(authorization_sha256,str) and native.HEX.fullmatch(authorization_sha256),
            "Exact authorization artifact digest required")
    binding,raw,counts=validate_execution_binding(auth,scope,package,output)
    require(auth.get("scope_sha256")==scope_sha256 and auth.get("runtime_manifest_sha256")==runtime_sha256,
            "Claim authorization freeze differs")
    path=Path(binding["allocation_claim_path"])
    record=dict(schema="dafny-library-allocation-claim-v1",state="CONSUMED_NO_RESUME",
                created_at_epoch=epoch,
                authorization_sha256=authorization_sha256,scope_sha256=scope_sha256,
                scope_canonical_sha256=sha(canonical(scope)),runtime_manifest_sha256=runtime_sha256,
                execution_binding=binding,budget_counts=counts,
                no_retry=True,no_resume=True,no_reassignment=True)
    payload=canonical(record)
    # Do not create parent directories, rename over an old claim, or remove an
    # empty claim after I/O failure. Its existence permanently fails closed.
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(descriptor,"wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        directory=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(directory)
        finally:os.close(directory)
    except BaseException:
        # Claim intentionally remains, including partial/empty write failures.
        raise
    return AllocationClaim(path,record,binding,sha(canonical(scope)),raw)

