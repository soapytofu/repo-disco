"""body-json-v2: strict JSON of bodies, inserted into pinned, trusted seeds.
No source repair, arbitrary declarations or provider transport. Not a sandbox.
"""
import hashlib
import json
from grammar import Grammar, split_seed, unique
VERSION = 'body-json-v2'
MAX_RESPONSE = 262144

def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def parse_response(raw, seeds, task):
    if not isinstance(raw, str) or len(raw.encode('utf-8')) > MAX_RESPONSE:
        raise ValueError('Response size/type')
    if not all(isinstance(n, str) and isinstance(s, str) for n, s in seeds.items()):
        raise ValueError('Trusted source type')
    if {n: digest(s) for n, s in seeds.items()} != task['source_sha256']:
        raise ValueError('Seed hash/file-set drift')
    names = task['editable_files']
    if len(names) != len(set(names)) or not names or not set(names) <= set(seeds):
        raise ValueError('Invalid editable file set')
    # A single optional whole-response Markdown fence is unambiguous. No prose
    # search, double decoding, backslash repair or declaration stripping.
    content = raw.strip()
    wrapper = 'plain JSON'
    if content.startswith('```'):
        lines = content.splitlines()
        if len(lines) < 3 or lines[0] not in ('```json', '```') or lines[-1] != '```':
            raise ValueError('Malformed whole-response fence')
        content = '\n'.join(lines[1:-1]); wrapper = 'whole-response JSON fence'
    bodies = json.loads(content, object_pairs_hook=unique)
    if not isinstance(bodies, dict) or set(bodies) != set(names) or not all(isinstance(b, str) for b in bodies.values()):
        raise ValueError('Exact editable filename/body-string set required')
    candidate = dict(seeds); trees = {}; boundaries = {}
    for name, body in bodies.items():
        prefix, suffix = split_seed(seeds[name])
        grammar = Grammar(body, task)
        trees[name] = grammar.sequence()
        if grammar.peek() is not None:
            raise ValueError('Trailing proof tokens')
        candidate[name] = prefix + body + suffix
        boundaries[name] = dict(prefix_sha256=digest(prefix), suffix_sha256=digest(suffix), body_sha256=digest(body))
    return candidate, dict(version=VERSION, wrapper=wrapper, syntax_trees=trees,
                          boundaries=boundaries, parent_sha256=task['source_sha256'],
                          candidate_sha256={n: digest(s) for n, s in candidate.items()})
