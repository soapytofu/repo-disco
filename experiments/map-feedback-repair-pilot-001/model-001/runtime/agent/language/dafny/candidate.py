"""Pure guarded candidate preparation; no agenda writes or model requests."""
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Callable, Mapping

from .repository import validate_snapshot, verify_repository


def hashes(files):
    return {name: sha256(content).hexdigest() for name, content in sorted(files.items())}


@dataclass(frozen=True)
class PreparedCandidate:
    files: Mapping[str, bytes]
    base_hashes: Mapping[str, str]
    candidate_hashes: Mapping[str, str]
    changed_files: tuple[str, ...]
    entry: str


def prepare_candidate(base: Mapping[str, bytes], replacements: Mapping[str, bytes],
                      *, entry: str, expected_hashes: Mapping[str, str],
                      guards: Mapping[str, Callable[[bytes, bytes], None]]) -> PreparedCandidate:
    """Create a new snapshot after validating every replacement against its original.

    A trusted task guard must raise ValueError for disallowed edits, including
    contract changes. Guards have no default: each replacement needs one. This is
    not a general Dafny contract parser. No existing snapshot or agenda is edited.
    expected_hashes binds the caller's selected base; it does not lock live agenda
    objects. Publication back into a mutable agenda is deliberately out of scope.
    """
    base, replacements, guards = dict(base), dict(replacements), dict(guards)
    validate_snapshot(base, entry)
    base_hashes = hashes(base)
    if base_hashes != dict(expected_hashes):
        raise ValueError('base snapshot differs from expected hashes')
    if not replacements:
        raise ValueError('no replacements supplied')
    if not set(replacements) <= set(base):
        raise ValueError('cannot add or rename files')
    if not set(guards) <= set(base):
        raise ValueError('guard names must belong to base snapshot')
    candidate = {**base, **replacements}
    validate_snapshot(candidate, entry)
    for name, content in replacements.items():
        if name not in guards:
            raise ValueError(f'immutable file: {name}')
        # Byte strings are immutable; guards cannot rewrite prepared content.
        guards[name](base[name], content)
    changed = tuple(sorted(name for name in replacements if candidate[name] != base[name]))
    if not changed:
        raise ValueError('candidate has no changes')
    return PreparedCandidate(MappingProxyType(candidate), MappingProxyType(base_hashes),
                             MappingProxyType(hashes(candidate)), changed, entry)


def verify_candidate(candidate: PreparedCandidate, timeout: float = 60):
    """Run once on the prepared snapshot; do not promote it or enqueue repairs."""
    if hashes(candidate.files) != dict(candidate.candidate_hashes):
        raise ValueError('candidate hash mismatch')
    result = verify_repository(dict(candidate.files), candidate.entry, timeout=timeout)
    result.evidence['candidate'] = dict(base_sha256=dict(candidate.base_hashes),
        changed_files=list(candidate.changed_files), promoted=False)
    return result
