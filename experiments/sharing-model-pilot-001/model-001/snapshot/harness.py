"""Offline request preparation and response evaluation. No API SDK or dispatcher."""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parent
CLIENTS = ('ClientA.dfy', 'ClientB.dfy')


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def parse_response(raw, originals):
    files = json.loads(raw, object_pairs_hook=strict_object)
    if not isinstance(files, dict) or set(files) != set(CLIENTS):
        raise ValueError('Expected exactly two client files')
    accepted = {}
    for name in CLIENTS:
        if not isinstance(files[name], str):
            raise ValueError('File content must be a string')
        candidate = files[name].strip() + '\n'
        original = originals[name]
        suffix = '  }\n}\n'
        prefix = original[:-len(suffix)]
        if not original.endswith(suffix) or not candidate.startswith(prefix) or not candidate.endswith(suffix):
            raise ValueError('Protected client bytes changed')
        body = candidate[len(prefix):-len(suffix)]
        calls = re.finditer(r'F\.[A-Za-z_][A-Za-z_0-9]*\s*\(([^;{}]*)\)\s*;', body)
        end = 0
        for call in calls:
            if body[end:call.start()].strip():
                raise ValueError('Only qualified lemma calls allowed')
            args = call.group(1)
            if re.search(r'[^A-Za-z_0-9,()\s+\-]', args):
                raise ValueError('Forbidden argument syntax')
            if set(re.findall(r'[A-Za-z_][A-Za-z_0-9]*', args)) - {'s','t','u','k'}:
                raise ValueError('Unknown argument identifier')
            depth = 0
            for char in args:
                depth += (char == '(') - (char == ')')
                if depth < 0:
                    raise ValueError('Unbalanced parentheses')
            if depth:
                raise ValueError('Unbalanced parentheses')
            end = call.end()
        if body[end:].strip():
            raise ValueError('Only qualified lemma calls allowed')
        accepted[name] = candidate
    return accepted


def request_for(sequence):
    if type(sequence) is not int or not 1 <= sequence <= 8:
        raise ValueError('Sequence must be 1 through 8')
    plan = json.loads((ROOT/'plan.json').read_text())
    trial = plan[sequence-1]
    data = (ROOT/trial['prompt_file']).read_bytes()
    if hashlib.sha256(data).hexdigest() != trial['prompt_sha256']:
        raise ValueError('Frozen prompt hash mismatch')
    return trial, json.loads(data)


def verify(folder, entry, timeout=60):
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():
        raise RuntimeError('Verification requires a Slurm compute node')
    cmd = ['dafny','verify','--verify-included-files',entry]
    start = time.monotonic()
    try:
        proc = subprocess.run(cmd,cwd=folder,text=True,capture_output=True,timeout=timeout)
        code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as error:
        code = 124
        stdout, stderr = error.stdout or b'', error.stderr or b''
        stdout = stdout.decode(errors='replace') if isinstance(stdout,bytes) else stdout
        stderr = stderr.decode(errors='replace') if isinstance(stderr,bytes) else stderr
    match = re.search(r'(\d+) verified, (\d+) errors?',stdout)
    outcome = 'VERIFIER_ERROR'
    if code == 0 and match and int(match[1]) > 0 and int(match[2]) == 0:
        outcome = 'SUCCESS'
    elif code in (124,137):
        outcome = 'TIMEOUT'
    elif code == 2:
        outcome = 'RESOLUTION_OR_PARSE_ERROR'
    elif code == 4 and match and int(match[2]) > 0:
        outcome = 'PROOF_FAILURE'
    return dict(command=cmd,exit_code=code,outcome=outcome,seconds=round(time.monotonic()-start,3),stdout=stdout,stderr=stderr)


def evaluate(condition, raw, out, verifier=verify):
    if condition not in ('shared','separate'):
        raise ValueError('Unknown condition')
    out = Path(out)
    out.mkdir(parents=True,exist_ok=False)
    (out/'response.txt').write_text(raw)
    source = ROOT/'fixtures'/f'{condition}_missing'
    originals = {name:(source/name).read_text() for name in CLIENTS}
    try:
        candidates = parse_response(raw, originals)
    except (ValueError, TypeError) as error:
        result = dict(outcome='EDIT_REJECTED',reason=str(error),verification=[])
    else:
        for f in source.glob('*.dfy'):
            (out/f.name).write_bytes(candidates[f.name].encode() if f.name in candidates else f.read_bytes())
        checks = []
        for entry in ('All.dfy', *CLIENTS):
            record = verifier(out,entry)
            for stream in ('stdout','stderr'):
                (out/(entry+'.'+stream+'.txt')).write_text(record.pop(stream))
            checks.append(dict(entry=entry,**record))
            if record['outcome'] in ('TIMEOUT','VERIFIER_ERROR'):
                break
        success = len(checks)==3 and all(r['outcome']=='SUCCESS' for r in checks)
        outcome = 'SUCCESS' if success else next(r['outcome'] for r in checks if r['outcome']!='SUCCESS')
        result = dict(outcome=outcome,verification=checks,source_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.glob('*.dfy'))})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
