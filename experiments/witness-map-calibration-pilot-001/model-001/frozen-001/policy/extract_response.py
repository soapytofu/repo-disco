"""Conservative envelope extraction around one complete JSON object."""
import hashlib
import json
import re

VERSION = 'single-json-envelope-v1'
MAX_RESPONSE = 262144
START = re.compile(r'[\{\[]')


def unique(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError('Duplicate JSON key')
        result[name] = value
    return result


def reject_constant(value):
    raise ValueError('Nonstandard JSON constant')


def extract_json(raw):
    if not isinstance(raw, str) or len(raw.encode('utf-8')) > MAX_RESPONSE:
        raise ValueError('Response type/size')
    decoder = json.JSONDecoder(object_pairs_hook=unique, parse_constant=reject_constant)
    containers = []
    cursor = 0
    while match := START.search(raw, cursor):
        start = match.start()
        tail = raw[start+1:].lstrip()
        first = tail[:1]
        looks_json = (first in ('"', '}') if raw[start] == '{'
                      else bool(first) and (first in '{["-0123456789]' or tail.startswith(('true', 'false', 'null'))))
        cursor = start+1
        if not looks_json:
            continue
        try:
            value, length = decoder.raw_decode(raw[start:])
        except (ValueError, RecursionError) as error:
            raise ValueError('Malformed or duplicate-key JSON container') from error
        end = start+length
        containers.append((start, end, value))
        if len(containers) > 1:
            raise ValueError('Multiple JSON containers')
        # A wrapper object or array consumes its entire nested payload. Never
        # select a nested proof object from inside it.
        cursor = end
    if len(containers) != 1 or not isinstance(containers[0][2], dict):
        raise ValueError('One complete top-level JSON object required')
    start, end, _ = containers[0]
    payload = raw[start:end]
    return payload, dict(version=VERSION, start_char=start, end_char=end,
                         raw_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                         payload_sha256=hashlib.sha256(payload.encode()).hexdigest())


def parse_response(raw, seeds, task, guard):
    payload, envelope = extract_json(raw)
    candidate, decision = guard.parse_response(payload, seeds, task)
    return candidate, dict(envelope=envelope, body_guard=decision)
