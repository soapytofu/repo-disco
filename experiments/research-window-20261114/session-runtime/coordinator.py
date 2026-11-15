"""Single-owner, no-restart session orchestration; no provider/credential code.

The caller supplies an already-owned canonical WindowBudget, an already-created
no-retry transport, and a fixed registry of reviewed callbacks. Queue data never
selects/imports/executes arbitrary Python. See README.md for the trust boundary.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import inspect
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat
import threading
import time
import window_budget as w

SCHEMA = 'repodisco-session-descriptor-v1'
ZERO = '0' * 64
MAX_DESCRIPTOR_BYTES = 4 * 1024 * 1024


class SessionError(RuntimeError):
    pass


class SessionClosed(SessionError):
    pass


class SessionBusy(SessionError):
    pass


class _IntentionalStop(SessionClosed):
    pass


def _relative(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Relative POSIX path required')
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError('Unsafe or noncanonical relative path')
    return path


def _file(root, relative):
    path = root
    for part in _relative(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('Symlink in pinned path')
    if not path.is_file():
        raise ValueError('Pinned regular file missing')
    return path


def _read_json(path):
    raw = path.read_bytes()
    if len(raw) > MAX_DESCRIPTOR_BYTES:
        raise ValueError('Metadata exceeds size limit')
    value = json.loads(raw, object_pairs_hook=w.unique_pairs,
                       parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonstandard JSON')))
    return value


def _hash_file(path):
    return w.digest(path.read_bytes())


def _now(clock):
    value = clock()
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Finite clock required')
    return value


@dataclass(frozen=True)
class ReviewedHandler:
    """Code paths are relative to the coordinator's trusted code_root."""
    validator: object
    executor: object
    code_sha256: dict


class BatchContext:
    """The executor receives this capability, never the raw provider transport."""
    def __init__(self, input_directory, output_directory, trial_ids, invoke):
        self.input_directory = input_directory
        self.output_directory = output_directory
        self.trial_ids = tuple(trial_ids)
        self.__invoke = invoke

    def invoke(self, trial_id):
        return self.__invoke(trial_id)


class ResearchSession:
    @classmethod
    def create(cls, directory, *, budget, transport, handlers, artifact_root,
               code_root, clock=time.time, sleep=time.sleep):
        """Create once; neither this class nor run() has a recovery path."""
        if not isinstance(budget, w.WindowBudget) or not callable(transport):
            raise ValueError('Owned WindowBudget and reviewed callable transport required')
        if budget.pid != os.getpid() or budget.closed or budget.poisoned:
            raise SessionClosed('Budget is not live and owned by this process')
        state = budget.snapshot()
        if state['terminal_reason'] or any(r['status'] != 'COMPLETED' for r in state['reservations']):
            raise SessionClosed('Budget is not clean')
        declared = sum(b['manifest']['max_calls'] for b in state['batches'])
        if declared != len(state['reservations']):
            raise SessionClosed('Prior batch has unused or incomplete slots')
        expected_root = state['scope'].get('central_ledger_path')
        if expected_root and Path(expected_root).resolve() != budget.root.resolve():
            raise ValueError('Canonical ledger path differs from the authorized scope')
        obj = cls.__new__(cls)
        obj.root = Path(directory)
        obj.artifact_root = Path(artifact_root).resolve(strict=True)
        obj.code_root = Path(code_root).resolve(strict=True)
        obj.budget, obj.__transport = budget, transport
        obj.clock, obj.sleep = clock, sleep
        obj.pid = os.getpid()
        obj.thread_id = threading.get_ident()
        obj.lock = threading.Lock()
        obj.running = False
        obj.terminal = False
        obj.failed = False
        obj.scope = w.cloned(state['scope'])
        obj.budget_prefix = w.cloned(state)
        obj.starting_calls = len(state['reservations'])
        obj.handlers = {}
        for name, handler in handlers.items():
            if not w.IDENTIFIER.fullmatch(name) or not isinstance(handler, ReviewedHandler):
                raise ValueError('Fixed reviewed handler registry required')
            pins = w.cloned(handler.code_sha256)
            if not pins or any(not isinstance(h, str) or not w.DIGEST.fullmatch(h) for h in pins.values()):
                raise ValueError('Callback source hashes required')
            for callback in (handler.validator, handler.executor):
                source = inspect.getsourcefile(callback)
                if not callable(callback) or not source:
                    raise ValueError('Callbacks must be inspectable reviewed Python functions')
                source = Path(source).resolve(strict=True)
                if source not in {_file(obj.code_root, p).resolve() for p in pins}:
                    raise ValueError('Callback source missing from reviewed code bindings')
            obj.handlers[name] = ReviewedHandler(handler.validator, handler.executor, pins)
        if not obj.handlers:
            raise ValueError('At least one reviewed handler required')
        obj.self_hash = _hash_file(Path(__file__))
        obj.window_hash = _hash_file(Path(w.__file__))
        obj._check_code()
        # Both markers are retained permanently, even after intentional close.
        # A failed creation leaves evidence and does not clear a prior owner.
        obj.root.mkdir(mode=0o700, exist_ok=False)
        try:
            (budget.root / 'research-session.lock').mkdir(mode=0o700)
        except FileExistsError as error:
            raise SessionBusy('Canonical budget already has a session owner; never clear it') from error
        owner = dict(pid=obj.pid, created_at_epoch=_now(clock),
                     coordinator_sha256=obj.self_hash, window_gate_sha256=obj.window_hash,
                     scope_sha256=state['scope_sha256'])
        w.exclusive_bytes(budget.root / 'research-session.lock' / 'owner.json', w.canonical(owner) + b'\n')
        w.exclusive_bytes(obj.root / 'owner.json', w.canonical(owner) + b'\n')
        for name in ('queue', 'events', 'runs'):
            (obj.root / name).mkdir(mode=0o700)
        obj.queue = []
        obj.completed = []
        obj.active = None
        obj.event_count = 0
        obj.status_bytes = None
        obj._persist('idle', 'created')
        obj._control()
        return obj

    @contextmanager
    def _operation(self):
        if os.getpid() != self.pid or threading.get_ident() != self.thread_id:
            raise SessionBusy('Only the creating process and thread may operate the coordinator')
        if not self.lock.acquire(blocking=False):
            raise SessionBusy('Concurrent or reentrant coordinator operation refused')
        try:
            if self.terminal:
                raise SessionClosed('Session is terminal; no restart or retry')
            yield
        finally:
            self.lock.release()

    def _check_code(self):
        if _hash_file(Path(__file__)) != self.self_hash or _hash_file(Path(w.__file__)) != self.window_hash:
            raise ValueError('Coordinator or window runtime changed')
        for handler in self.handlers.values():
            for name, expected in handler.code_sha256.items():
                if _hash_file(_file(self.code_root, name)) != expected:
                    raise ValueError('Reviewed callback code changed')

    def _persist(self, phase, reason, error_type=None):
        self.event_count += 1
        status = dict(schema='repodisco-session-status-v1', phase=phase, reason=reason,
                      event_sequence=self.event_count, at_epoch=_now(self.clock),
                      queued=[dict(sequence=d['sequence'], batch_id=d['batch_id'],
                                   descriptor_sha256=h) for d, h in self.queue],
                      completed_batch_ids=list(self.completed), active_batch_id=self.active,
                      window_reservations=len(self.budget.snapshot()['reservations']),
                      deadline_epoch=self.scope['deadline_epoch'])
        if error_type is not None:
            # No exception message, repr, traceback, environment or client repr.
            status['error_type'] = error_type
        w.exclusive_bytes(self.root / 'events' / f'{self.event_count:05}.json', w.canonical(status) + b'\n')
        w.durable_json(self.root / 'status.json', status)
        self.status_bytes = w.canonical(status) + b'\n'

    def _finish_budget(self):
        try:
            self.budget.finish()
        except BaseException:
            # The canonical gate retains its owner marker after errors. This
            # coordinator never clears it, reopens it, or creates another gate.
            pass

    def _close(self, reason):
        self.terminal = True
        self.__transport = None
        self._finish_budget()
        self._persist('closed', reason)

    def _fail(self, error):
        if self.failed:
            self._finish_budget()
            return
        self.failed = True
        self.terminal = True
        self.__transport = None
        self._finish_budget()
        try:
            self._persist('error', 'terminal_execution_error', type(error).__name__)
        except BaseException:
            # Persistence failure is not recovery permission. Retained ownership
            # and in-memory terminal state prevent further dispatch here.
            pass

    def _marker(self, name):
        path = self.root / name
        if not path.exists() and not path.is_symlink():
            return False
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode) or path.read_bytes() != b'':
            raise ValueError('Control marker must be an empty regular file')
        return True

    def _control(self):
        if self.terminal:
            raise _IntentionalStop('Session terminal')
        if self._marker('STOP'):
            self._close('stop_requested')
            raise _IntentionalStop('Stop requested')
        if _now(self.clock) >= self.scope['deadline_epoch']:
            self._close('deadline')
            raise _IntentionalStop('Window deadline reached')
        state = self.budget.snapshot()
        if state['scope'] != self.scope or state['terminal_reason'] or self.budget.closed or self.budget.poisoned:
            raise SessionClosed('Canonical budget changed or became terminal')

    def _audit(self):
        self._check_code()
        ledger = self.budget.root / 'ledger.json'
        if ledger.is_symlink() or ledger.read_bytes() != w.canonical(self.budget.snapshot()) + b'\n':
            raise ValueError('Canonical durable ledger differs from live authority')
        if (self.root / 'status.json').is_symlink() or (self.root / 'status.json').read_bytes() != self.status_bytes:
            raise ValueError('Durable session status changed')
        expected = set()
        for descriptor, expected_hash in self.queue:
            name = f"{descriptor['sequence']:04}-{descriptor['batch_id']}.json"
            expected.add(name)
            path = self.root / 'queue' / name
            if path.is_symlink() or _hash_file(path) != expected_hash:
                raise ValueError('Published queue descriptor changed')
        if {p.name for p in (self.root / 'queue').iterdir()} != expected:
            raise ValueError('Unpublished or missing queue descriptor')

    def _validate(self, value):
        descriptor = w.cloned(value)
        required = {'schema', 'sequence', 'previous_descriptor_sha256', 'batch_id',
                    'handler_id', 'handler_binding_sha256', 'artifact_directory',
                    'freeze_path', 'freeze_sha256', 'runtime_path', 'runtime_sha256',
                    'input_sha256', 'slots', 'max_calls', 'sdk_total_max_attempts'}
        if not isinstance(descriptor, dict) or set(descriptor) != required or descriptor['schema'] != SCHEMA:
            raise ValueError('Exact descriptor schema required')
        if type(descriptor['sequence']) is not int or descriptor['sequence'] < 1:
            raise ValueError('Invalid descriptor order')
        if not w.DIGEST.fullmatch(descriptor['previous_descriptor_sha256']):
            raise ValueError('Missing previous-descriptor hash')
        handler = self.handlers.get(descriptor['handler_id'])
        if handler is None or descriptor['handler_binding_sha256'] != w.digest(w.canonical(handler.code_sha256)):
            raise ValueError('Unreviewed handler or code binding')
        directory = self.artifact_root.joinpath(*_relative(descriptor['artifact_directory']).parts)
        if not directory.is_dir() or any(p.is_symlink() for p in [directory, *directory.parents] if p != self.artifact_root.parent):
            raise ValueError('Missing or symlinked artifact directory')
        pins = descriptor['input_sha256']
        if not isinstance(pins, dict) or not pins:
            raise ValueError('Complete frozen input tree required')
        actual_files = set()
        for path in directory.rglob('*'):
            if path.is_symlink() or (not path.is_file() and not path.is_dir()):
                raise ValueError('Nonregular frozen input')
            if path.is_file():
                actual_files.add(path.relative_to(directory).as_posix())
        if actual_files != set(pins):
            raise ValueError('Input inventory differs from frozen descriptor')
        for name, expected in pins.items():
            if not isinstance(expected, str) or not w.DIGEST.fullmatch(expected) or _hash_file(_file(directory, name)) != expected:
                raise ValueError('Frozen input hash differs')
        for kind in ('freeze', 'runtime'):
            if pins.get(descriptor[kind + '_path']) != descriptor[kind + '_sha256']:
                raise ValueError('Freeze/runtime must bind actual pinned files')
        slots = descriptor['slots']
        if not isinstance(slots, list) or not slots:
            raise ValueError('Ordered slots required')
        for slot in slots:
            if (not isinstance(slot, dict) or set(slot) != {'trial_id', 'request_path', 'request_sha256'}
                    or pins.get(slot['request_path']) != slot['request_sha256']):
                raise ValueError('Slot must bind an exact pinned request')
            payload = _read_json(_file(directory, slot['request_path']))
            if not isinstance(payload, dict):
                raise ValueError('Request JSON object required')
        manifest = {k: descriptor[k] for k in ('batch_id', 'freeze_sha256', 'runtime_sha256', 'max_calls', 'sdk_total_max_attempts')}
        manifest['slots'] = [{k: s[k] for k in ('trial_id', 'request_sha256')} for s in slots]
        manifest = w._manifest(manifest)
        if handler.validator(w.cloned(descriptor), directory) is not True:
            raise ValueError('Reviewed batch validator did not explicitly pass')
        # A validator is trusted code, but accidental mutation still fails.
        for name, expected in pins.items():
            if _hash_file(_file(directory, name)) != expected:
                raise ValueError('Validator mutated frozen input')
        self._check_code()
        return descriptor, directory, handler, manifest

    @property
    def next_sequence(self):
        return len(self.queue) + 1

    @property
    def previous_descriptor_sha256(self):
        return self.queue[-1][1] if self.queue else ZERO

    def publish(self, value):
        """The owner atomically publishes a reviewed descriptor; no execution."""
        with self._operation():
            try:
                self._control()
                self._audit()
                if self.active is not None or self._marker('SEAL'):
                    raise ValueError('Publishing during a batch or after seal is forbidden')
                descriptor, directory, handler, manifest = self._validate(value)
                if (descriptor['sequence'] != self.next_sequence
                        or descriptor['previous_descriptor_sha256'] != self.previous_descriptor_sha256):
                    raise ValueError('Descriptor sequence or predecessor differs')
                prior = [b['manifest'] for b in self.budget_prefix['batches']] + [self._window_manifest(d) for d, h in self.queue]
                if any(m['batch_id'] == manifest['batch_id'] or m['freeze_sha256'] == manifest['freeze_sha256'] for m in prior):
                    raise ValueError('Duplicate batch or freeze')
                prior_ids = {s['trial_id'] for m in prior for s in m['slots']}
                if prior_ids.intersection(s['trial_id'] for s in manifest['slots']):
                    raise ValueError('Duplicate global trial ID')
                if sum(m['max_calls'] for m in prior) + manifest['max_calls'] > self.scope['max_calls']:
                    raise ValueError('Queued allocations exceed aggregate window budget')
                raw = w.canonical(descriptor) + b'\n'
                if len(raw) > MAX_DESCRIPTOR_BYTES:
                    raise ValueError('Descriptor exceeds size limit')
                name = f"{descriptor['sequence']:04}-{descriptor['batch_id']}.json"
                destination = self.root / 'queue' / name
                temporary = destination.with_suffix('.tmp')
                w.exclusive_bytes(temporary, raw)
                if destination.exists():
                    raise ValueError('Descriptor already published')
                os.rename(temporary, destination)
                w._sync_directory(destination.parent)
                self.queue.append((descriptor, w.digest(raw)))
                self._persist('idle', 'descriptor_published')
                return self.queue[-1][1]
            except _IntentionalStop:
                raise
            except BaseException as error:
                self._fail(error)
                raise

    @staticmethod
    def _window_manifest(descriptor):
        manifest = {k: descriptor[k] for k in ('batch_id', 'freeze_sha256', 'runtime_sha256', 'max_calls', 'sdk_total_max_attempts')}
        manifest['slots'] = [{k: s[k] for k in ('trial_id', 'request_sha256')} for s in descriptor['slots']]
        return manifest

    def _write_marker(self, name):
        with self._operation():
            try:
                self._control()
                self._audit()
                w.exclusive_bytes(self.root / name, b'')
            except _IntentionalStop:
                raise
            except BaseException as error:
                self._fail(error)
                raise

    def seal(self):
        self._write_marker('SEAL')

    def request_stop(self):
        self._write_marker('STOP')

    def step(self):
        """Run at most one full batch, or return idle/closed. Never retries."""
        with self._operation():
            try:
                self._control()
                self._audit()
                if len(self.completed) == len(self.queue):
                    if self._marker('SEAL'):
                        self._close('sealed_queue_complete')
                        return 'closed'
                    return 'idle'
                descriptor, descriptor_hash = self.queue[len(self.completed)]
                descriptor, directory, handler, manifest = self._validate(descriptor)
                self._control()
                self._audit()
                before = self.budget.snapshot()
                if any(r['status'] != 'COMPLETED' for r in before['reservations']):
                    raise SessionError('Previous request incomplete')
                if len(before['reservations']) != self.starting_calls + sum(d['max_calls'] for d, h in self.queue[:len(self.completed)]):
                    raise SessionError('Canonical ledger has unexpected requests')
                manifest_hash = self.budget.register_batch(manifest)
                self.active = descriptor['batch_id']
                output = self.root / 'runs' / f"{descriptor['sequence']:04}-{descriptor['batch_id']}"
                output.mkdir(mode=0o700, exist_ok=False)
                self._persist('running', 'batch_started')
                call_count = 0
                in_invoke = False
                capability_live = True
                def invoke(trial_id):
                    nonlocal call_count, in_invoke
                    if os.getpid() != self.pid or threading.get_ident() != self.thread_id:
                        raise SessionBusy('Batch capability belongs to its creating process and thread')
                    try:
                        if not capability_live or in_invoke or self.terminal:
                            raise SessionClosed('Inactive, inherited or reentrant batch capability')
                        in_invoke = True
                        self._control()
                        self._audit()
                        self._validate(descriptor)
                        if call_count >= len(descriptor['slots']) or descriptor['slots'][call_count]['trial_id'] != trial_id:
                            raise ValueError('Attempted duplicate or out-of-order trial')
                        slot = descriptor['slots'][call_count]
                        raw = _file(directory, slot['request_path']).read_bytes()
                        if w.digest(raw) != slot['request_sha256']:
                            raise ValueError('Request changed before dispatch')
                        self._control()
                        def dispatch(payload):
                            # Recheck operator/deadline controls after the gate's
                            # durable reservation and immediately before transport.
                            # The gate is intentionally busy/poisoned in this callback.
                            if self.terminal:
                                raise SessionClosed('Session became terminal before dispatch')
                            if self._marker('STOP'):
                                self._close('stop_requested')
                                raise _IntentionalStop('Stop before transport')
                            if _now(self.clock) >= self.scope['deadline_epoch']:
                                self._close('deadline')
                                raise _IntentionalStop('Deadline before transport')
                            return self.__transport(payload)
                        response = self.budget.invoke(batch_id=descriptor['batch_id'], trial_id=trial_id,
                            manifest_sha256=manifest_hash, request_bytes=raw, transport=dispatch)
                        call_count += 1
                        return response
                    except _IntentionalStop:
                        raise
                    except BaseException as error:
                        self._fail(error)
                        raise
                    finally:
                        in_invoke = False
                context = BatchContext(directory, output, [s['trial_id'] for s in descriptor['slots']], invoke)
                try:
                    receipt = handler.executor(w.cloned(descriptor), context)
                finally:
                    capability_live = False
                if self.terminal:
                    if self.failed:
                        raise SessionError('Executor caught a terminal error; no next batch')
                    return 'closed'
                self._audit()
                self._validate(descriptor)
                if not isinstance(receipt, dict) or set(receipt) != {'completed_trials', 'evidence_sha256'}:
                    raise ValueError('Complete fixed receipt required')
                if receipt['completed_trials'] != list(context.trial_ids) or call_count != descriptor['max_calls']:
                    raise ValueError('Executor did not finish every frozen slot exactly once')
                rows = self.budget.snapshot()['reservations'][len(before['reservations']):]
                if (len(rows) != call_count or any(r['status'] != 'COMPLETED' for r in rows)
                        or [r['trial_id'] for r in rows] != list(context.trial_ids)):
                    raise SessionError('Returned requests do not match complete batch')
                evidence = receipt['evidence_sha256']
                if not isinstance(evidence, dict):
                    raise ValueError('Exact output evidence inventory required')
                output_paths = list(output.rglob('*'))
                if any(p.is_symlink() or (not p.is_file() and not p.is_dir()) for p in output_paths):
                    raise ValueError('Nonregular output evidence')
                if {p.relative_to(output).as_posix() for p in output_paths if p.is_file()} != set(evidence):
                    raise ValueError('Unaccounted output evidence')
                for path, expected in evidence.items():
                    if _hash_file(_file(output, path)) != expected:
                        raise ValueError('Output evidence hash mismatch')
                result = dict(batch_id=descriptor['batch_id'], descriptor_sha256=descriptor_hash,
                              completed_trials=receipt['completed_trials'], evidence_sha256=evidence,
                              request_ids=[r['request_id'] for r in rows])
                w.exclusive_bytes(output / 'completion.json', w.canonical(result) + b'\n')
                self.completed.append(descriptor['batch_id'])
                self.active = None
                self._persist('completed', 'batch_complete')
                # In-flight work may finish after the deadline; preserve its
                # accounted result, then prohibit all later dispatches.
                self._control()
                return 'completed'
            except _IntentionalStop:
                return 'closed'
            except BaseException as error:
                self._fail(error)
                raise

    def run(self, *, poll_interval=30, supply=None):
        """Wait in memory; optional reviewed supplier returns data, never code.

        supply(next_sequence, previous_hash) may return one descriptor or None.
        It runs only while idle. It is trusted integration code, not a queue file
        plugin. The caller must bind it in its separately reviewed live runner.
        """
        if type(poll_interval) not in (int, float) or not 0 < poll_interval <= 60:
            raise ValueError('Bounded positive polling interval required')
        if self.running:
            raise SessionBusy('Run loop already active')
        self.running = True
        try:
            while not self.terminal:
                outcome = self.step()
                if outcome == 'closed':
                    break
                if outcome == 'idle':
                    if supply is not None:
                        value = supply(self.next_sequence, self.previous_descriptor_sha256)
                        if value is not None:
                            self.publish(value)
                            continue
                    remaining = self.scope['deadline_epoch'] - _now(self.clock)
                    if remaining > 0:
                        self.sleep(min(poll_interval, remaining))
            return 'error' if self.failed else 'closed'
        except _IntentionalStop:
            return 'closed'
        except BaseException as error:
            if not self.terminal:
                self._fail(error)
            raise
        finally:
            self.running = False
