"""Offline replacement-body adapter for an immutable failing repository base.

The existing grammar binds an empty trusted template. Never pass the populated
failing source to its empty-body splitter or silently erase it in model context.
"""
import hashlib

def hashes(files):
    return {n:hashlib.sha256(s.encode()).hexdigest() for n,s in files.items()}

def apply_response(raw,base,template,task,expected_base_hashes,guard,envelope):
    if hashes(base)!=expected_base_hashes:raise ValueError('Failing base changed')
    if set(base)!=set(template):raise ValueError('Base/template file-set mismatch')
    for name,source in template.items():
        if name in task['editable_files']:
            prefix,suffix=guard.split_seed(source)
            if not base[name].startswith(prefix) or not base[name].endswith(suffix):
                raise ValueError('Failing base changes protected contract bytes')
        elif base[name]!=source:raise ValueError('Failing base changes protected file')
    candidate,decision=envelope.parse_response(raw,template,task,guard)
    for name,source in base.items():
        if name not in task['editable_files'] and candidate[name]!=source:
            raise ValueError('Replacement changes protected file')
    return candidate,dict(failing_base_sha256=expected_base_hashes,
                          candidate_sha256=hashes(candidate),original_guard_decision=decision)
