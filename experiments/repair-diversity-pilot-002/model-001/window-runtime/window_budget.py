"""Single-owner, window-wide request accounting; no provider or credential code.

This gate admits exactly one injected transport invocation per fixed slot. The
transport itself MUST have retries disabled; this library cannot police hidden
network activity inside a callable. All participating processes must use this
same directory on a filesystem with atomic mkdir/replace and durable fsync.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import threading
import time

MAX_WINDOW_CALLS = 128
LATEST_DEADLINE = datetime(2026, 11, 16, 4, 5, 12, tzinfo=timezone.utc).timestamp()
SCHEMA = "repodisco-window-budget-v1"
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class GateClosed(RuntimeError):
    pass


class OwnerBusy(GateClosed):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def cloned(value):
    return json.loads(canonical(value))


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def exclusive_bytes(path, raw):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    _sync_directory(path.parent)


def durable_json(path, value):
    # A leftover temporary file is evidence of interrupted persistence. Refuse
    # to overwrite it rather than silently repairing an uncertain ledger.
    temporary = path.with_name(path.name + ".tmp")
    exclusive_bytes(temporary, canonical(value) + b"\n")
    os.replace(temporary, path)
    _sync_directory(path.parent)


def _scope(scope):
    result = cloned(scope)
    if (result.get("authorized") is not True or result.get("no_retries") is not True
            or type(result.get("max_calls")) is not int
            or not 1 <= result["max_calls"] <= MAX_WINDOW_CALLS
            or not IDENTIFIER.fullmatch(result.get("window_id", ""))
            or not isinstance(result.get("authorization_basis"), str)
            or not result["authorization_basis"].strip()):
        raise ValueError("Explicit bounded window authorization required")
    deadline = result.get("deadline_epoch")
    if (type(deadline) not in (int, float) or not math.isfinite(deadline)
            or not 0 < deadline <= LATEST_DEADLINE):
        raise ValueError("Invalid or extended window deadline")
    return result


def _manifest(manifest):
    result = cloned(manifest)
    required = {"batch_id", "freeze_sha256", "runtime_sha256", "slots",
                "max_calls", "sdk_total_max_attempts"}
    if set(result) != required:
        raise ValueError("Frozen batch manifest fields differ")
    if not IDENTIFIER.fullmatch(result.get("batch_id", "")):
        raise ValueError("Invalid batch ID")
    for field in ("freeze_sha256", "runtime_sha256"):
        if not DIGEST.fullmatch(result.get(field, "")):
            raise ValueError("Invalid frozen hash")
    slots = result["slots"]
    if (not isinstance(slots, list) or not slots
            or type(result["max_calls"]) is not int
            or result["max_calls"] != len(slots)
            or result["sdk_total_max_attempts"] != 1
            or type(result["sdk_total_max_attempts"]) is not int):
        raise ValueError("One declared request per slot; one SDK attempt required")
    seen = set()
    for slot in slots:
        if (set(slot) != {"trial_id", "request_sha256"}
                or not IDENTIFIER.fullmatch(slot.get("trial_id", ""))
                or not DIGEST.fullmatch(slot.get("request_sha256", ""))
                or slot["trial_id"] in seen):
            raise ValueError("Invalid or duplicate frozen slot")
        seen.add(slot["trial_id"])
    return result


class WindowBudget:
    """A single directory is the authority for every batch in this window.

    Create once. Explicit open_existing is permitted only after a clean owner
    release and a complete audit of all prior returned requests. No method
    removes a stale owner lock, repairs a ledger, resets a spent slot, changes a
    frozen batch, or returns unused declared capacity to a different batch.
    """

    @classmethod
    def create(cls, directory, scope, *, clock=time.time):
        scope = _scope(scope)
        root = Path(directory)
        root.mkdir(mode=0o700, parents=False, exist_ok=False)
        (root / "requests").mkdir(mode=0o700)
        obj = cls._owner(root, clock)
        obj.state = dict(schema=SCHEMA, scope=scope, scope_sha256=digest(canonical(scope)),
                         batches=[], reservations=[], terminal_reason=None,
                         owner_session=obj.session)
        obj._persist()
        obj._check_live()
        return obj

    @classmethod
    def open_existing(cls, directory, scope, *, clock=time.time):
        expected = _scope(scope)
        obj = cls._owner(Path(directory), clock)
        try:
            obj.state = json.loads((obj.root / "ledger.json").read_bytes())
            obj._audit(expected)
            if obj.state["terminal_reason"]:
                raise GateClosed("Window is terminal; no recovery or retry supported")
            obj.state["owner_session"] = obj.session
            obj._persist()
            obj._check_live()
        except BaseException:
            # A failed audit retains this newly acquired lock as evidence. No
            # implicit repair/recovery path can produce another request.
            obj.poisoned = True
            raise
        return obj

    @classmethod
    def _owner(cls, root, clock):
        obj = cls.__new__(cls)
        obj.root, obj.clock = root, clock
        obj.pid = os.getpid()
        obj.session = dict(pid=obj.pid, host=socket.gethostname(), acquired_at_epoch=clock())
        obj.closed = False
        obj.poisoned = False
        obj.lock = threading.Lock()
        try:
            (root / "owner.lock").mkdir(mode=0o700)
        except FileExistsError as error:
            raise OwnerBusy("Owner lock exists; never clear it automatically") from error
        exclusive_bytes(root / "owner.lock" / "owner.json", canonical(obj.session) + b"\n")
        _sync_directory(root)
        return obj

    @contextmanager
    def _operation(self):
        if os.getpid() != self.pid:
            raise OwnerBusy("Inherited gate objects cannot be used after fork")
        if not self.lock.acquire(blocking=False):
            raise OwnerBusy("Concurrent or reentrant use refused")
        try:
            if self.closed or self.poisoned:
                raise GateClosed("Owner closed or poisoned")
            yield
        finally:
            self.lock.release()

    def _persist(self):
        self.poisoned = True
        durable_json(self.root / "ledger.json", self.state)
        self.poisoned = False

    def _stop(self, reason, record=None, status=None):
        self.state["terminal_reason"] = reason
        if record is not None and status is not None:
            record["status"] = status
        try:
            self._persist()
        finally:
            self.poisoned = True

    def _check_live(self):
        if self.state["terminal_reason"]:
            raise GateClosed("Window is terminal")
        if self.clock() >= self.state["scope"]["deadline_epoch"]:
            self._stop("deadline")
            raise GateClosed("Window deadline reached")

    def _audit(self, expected_scope):
        state = self.state
        if (state.get("schema") != SCHEMA
                or state.get("scope") != expected_scope
                or state.get("scope_sha256") != digest(canonical(expected_scope))
                or state.get("owner_session") is not None):
            raise GateClosed("Scope or clean-owner binding mismatch")
        batches = state["batches"]
        expected_slots = []
        batch_ids, freeze_ids, slot_ids = set(), set(), set()
        for batch in batches:
            manifest = _manifest(batch["manifest"])
            if batch["manifest_sha256"] != digest(canonical(manifest)):
                raise GateClosed("Frozen batch changed")
            if manifest["batch_id"] in batch_ids or manifest["freeze_sha256"] in freeze_ids:
                raise GateClosed("Duplicate batch or freeze")
            batch_ids.add(manifest["batch_id"])
            freeze_ids.add(manifest["freeze_sha256"])
            for slot in manifest["slots"]:
                if slot["trial_id"] in slot_ids:
                    raise GateClosed("Duplicate global trial ID")
                slot_ids.add(slot["trial_id"])
                expected_slots.append((manifest["batch_id"], batch["manifest_sha256"], slot))
        if len(expected_slots) > expected_scope["max_calls"]:
            raise GateClosed("Declared allocations exceed window cap")
        reservations = state["reservations"]
        if len(reservations) > len(expected_slots):
            raise GateClosed("Unexpected reservations")
        ids, expected_files = set(), set()
        for index, row in enumerate(reservations, 1):
            batch_id, manifest_hash, slot = expected_slots[index-1]
            if (row["sequence"] != index or row["batch_id"] != batch_id
                    or row["manifest_sha256"] != manifest_hash
                    or row["trial_id"] != slot["trial_id"]
                    or row["request_sha256"] != slot["request_sha256"]
                    or row["status"] != "COMPLETED"):
                raise GateClosed("Incomplete, ambiguous or conflicting reservation")
            request_name, response_name = f"request-{index:03}.json", f"response-{index:03}.json"
            expected_files.update((request_name, response_name))
            request = (self.root / "requests" / request_name).read_bytes()
            response_raw = (self.root / "requests" / response_name).read_bytes()
            response = json.loads(response_raw)
            if (digest(request) != row["request_sha256"] or digest(response_raw) != row["response_sha256"]
                    or not response.get("request_id") or response["request_id"] in ids
                    or response.get("retry_attempts") != 0
                    or response["request_id"] != row["request_id"]
                    or row["dispatch_intent_at_epoch"] >= expected_scope["deadline_epoch"]):
                raise GateClosed("Saved request or response evidence mismatch")
            ids.add(response["request_id"])
        if {p.name for p in (self.root / "requests").iterdir()} != expected_files:
            raise GateClosed("Unaccounted request evidence; manual review required")

    def register_batch(self, manifest):
        manifest = _manifest(manifest)
        with self._operation():
            self._check_live()
            batches = self.state["batches"]
            if any(b["manifest"]["batch_id"] == manifest["batch_id"] or
                   b["manifest"]["freeze_sha256"] == manifest["freeze_sha256"] for b in batches):
                raise ValueError("Batch ID or freeze already registered")
            prior_ids = {s["trial_id"] for b in batches for s in b["manifest"]["slots"]}
            if prior_ids.intersection(s["trial_id"] for s in manifest["slots"]):
                raise ValueError("Global trial ID already declared")
            declared = sum(b["manifest"]["max_calls"] for b in batches)
            if declared + manifest["max_calls"] > self.state["scope"]["max_calls"]:
                raise GateClosed("Declared batches exceed total window cap")
            bound = dict(manifest=manifest, manifest_sha256=digest(canonical(manifest)))
            self.state["batches"].append(bound)
            self._persist()
            return bound["manifest_sha256"]

    def invoke(self, *, batch_id, trial_id, manifest_sha256, request_bytes, transport):
        if not isinstance(request_bytes, bytes):
            raise TypeError("Exact frozen UTF-8 request bytes required")
        payload = json.loads(request_bytes, object_pairs_hook=unique_pairs)
        if not isinstance(payload, dict):
            raise ValueError("Request must be a JSON object")
        payload = cloned(payload)
        with self._operation():
            self._check_live()
            rows = self.state["reservations"]
            if len(rows) >= self.state["scope"]["max_calls"]:
                raise GateClosed("Total window request budget exhausted")
            slots = [(b["manifest"]["batch_id"], b["manifest_sha256"], s)
                     for b in self.state["batches"] for s in b["manifest"]["slots"]]
            if len(rows) >= len(slots):
                raise GateClosed("No unconsumed declared slot")
            expected_batch, expected_hash, slot = slots[len(rows)]
            if (batch_id != expected_batch or manifest_sha256 != expected_hash
                    or trial_id != slot["trial_id"]
                    or digest(request_bytes) != slot["request_sha256"]):
                raise ValueError("Frozen batch/slot/order/request binding differs")
            number = len(rows) + 1
            record = dict(sequence=number, batch_id=batch_id, trial_id=trial_id,
                          manifest_sha256=manifest_sha256, request_sha256=digest(request_bytes),
                          reserved_at_epoch=self.clock(), status="RESERVED")
            rows.append(record)
            self._persist()  # Reservation is charged before any transport.
            self.poisoned = True
            try:
                exclusive_bytes(self.root / "requests" / f"request-{number:03}.json", request_bytes)
                if self.clock() >= self.state["scope"]["deadline_epoch"]:
                    self._stop("deadline_before_dispatch", record, "EXPIRED_NO_DISPATCH")
                    raise GateClosed("Deadline after reservation")
                record.update(status="DISPATCHING", dispatch_intent_at_epoch=self.clock())
                self._persist()
                self.poisoned = True
                if self.clock() >= self.state["scope"]["deadline_epoch"]:
                    self._stop("deadline_before_dispatch", record, "EXPIRED_NO_DISPATCH")
                    raise GateClosed("Deadline after dispatch-intent persistence")
                response = cloned(transport(copy.deepcopy(payload)))
                response_bytes = canonical(response) + b"\n"
                exclusive_bytes(self.root / "requests" / f"response-{number:03}.json", response_bytes)
                previous_ids = {r.get("request_id") for r in rows[:-1]}
                if (not isinstance(response, dict) or not isinstance(response.get("request_id"), str)
                        or not response["request_id"] or response["request_id"] in previous_ids
                        or type(response.get("retry_attempts")) is not int or response["retry_attempts"] != 0):
                    self._stop("response_metadata", record, "RESPONSE_METADATA_REJECTED")
                    raise GateClosed("Missing/duplicate ID or retry metadata")
                record.update(status="COMPLETED", response_sha256=digest(response_bytes),
                              request_id=response["request_id"], returned_at_epoch=self.clock())
                self._persist()
                return response
            except BaseException as error:
                if not self.state["terminal_reason"]:
                    record["error_type"] = type(error).__name__
                    self._stop("transport_or_persistence_failure", record, "AMBIGUOUS_OR_UNSAVED")
                self.poisoned = True
                raise

    def snapshot(self):
        return cloned(self.state)

    def close(self):
        """Release ownership only after a clean, accounted session.

        Unused frozen slots remain allocated to their original batch. A later
        explicitly opened owner may continue those same slots, never replace
        the batch or resend completed/ambiguous requests.
        """
        with self._operation():
            if self.state["terminal_reason"] or any(r["status"] != "COMPLETED" for r in self.state["reservations"]):
                raise GateClosed("Unclean session cannot release ownership")
            self.state["owner_session"] = None
            self._persist()
            self.poisoned = True
            (self.root / "owner.lock" / "owner.json").unlink()
            (self.root / "owner.lock").rmdir()
            _sync_directory(self.root)
            self.closed = True

    def finish(self):
        """Terminally finish the window. The lock is retained; never resumes."""
        with self._operation():
            self._stop("finished")

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        if exception_type is None and not self.poisoned:
            self.close()
        elif not self.poisoned:
            self._stop("owner_exception")
