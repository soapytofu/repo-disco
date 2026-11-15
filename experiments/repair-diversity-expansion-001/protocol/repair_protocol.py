"""Body replacement against a frozen failing base; no writes or verification.

The host must pin expected_base_hashes in its prospective trial freeze. A prior
failing body need not pass the output grammar; its protected bytes must match the
pinned empty template. Only new output bodies pass through the new grammar.
"""
from pathlib import Path
import hashlib
import importlib.util

ROOT=Path(__file__).resolve().parent
ENVELOPE_SHA256='60446deb6d0ec4bcf9d788a3fd0ea7ba9e7275255769c61e61382513cb77e7de'

def hashes(files):
    if not isinstance(files,dict) or not all(isinstance(n,str) and isinstance(s,str) for n,s in files.items()):
        raise ValueError('Source dictionary required')
    try:return {n:hashlib.sha256(s.encode('utf-8')).hexdigest() for n,s in sorted(files.items())}
    except UnicodeError as error:raise ValueError('Source Unicode') from error

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value);return value

def apply_response(raw,base,template,task,expected_base_hashes,guard=None,envelope=None):
    guard=guard or module('repair_diversity_guard',ROOT/'body_guard.py')
    envelope=envelope or module('repair_diversity_envelope',ROOT/'extract_response.py')
    if guard.VERSION!='repair-diversity-bodies-v1-development':raise ValueError('Body guard version')
    if (envelope.VERSION!='repair-envelope-v2-explicit-json-001'
        or hashlib.sha256(Path(envelope.__file__).read_bytes()).hexdigest()!=ENVELOPE_SHA256):
        raise ValueError('Pinned envelope changed')
    guard.validate_template(template,task)
    if hashes(base)!=expected_base_hashes:raise ValueError('Failing base changed')
    if set(base)!=set(template):raise ValueError('Base/template file-set mismatch')
    for name,source in template.items():
        if name in task['editable_files']:
            prefix,suffix=guard.split_seed(source)
            if len(base[name])<len(prefix)+len(suffix) or not base[name].startswith(prefix) or not base[name].endswith(suffix):
                raise ValueError('Failing base changes protected contract bytes')
        elif base[name]!=source:raise ValueError('Failing base changes protected file')
    candidate,decision=envelope.parse_response(raw,template,task,guard)
    for name,source in base.items():
        if name not in task['editable_files'] and candidate[name]!=source:
            raise ValueError('Replacement changes protected file')
    return candidate,dict(failing_base_sha256=expected_base_hashes,
        candidate_sha256=hashes(candidate),original_guard_decision=decision,
        model_calls=0,semantic_verification_performed=False)
