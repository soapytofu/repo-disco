"""Bounded repair-body envelope policy v2, for prospectively frozen pilots only.

Accept one whole-response filename/body JSON object, or one explicit JSON fence.
Other clearly non-JSON explanatory fences/prose are permitted under the documented
ambiguity checks. This is a narrow protocol parser, not a general prose classifier.
"""
import hashlib,json,re
VERSION='repair-envelope-v2-explicit-json-001'
MAX_RESPONSE=262144
SPACE=' \t\r\n'
FENCE_LINE=re.compile(r'(?m)^[ \t]*(?P<mark>`{3,}|~{3,})(?P<label>[^\r\n]*)(?:\r?\n|$)')
INLINE=re.compile(r'(?<!`)(?P<ticks>`{1,2})(?!`)(?P<body>[^\r\n]*?)(?P=ticks)(?!`)')


def unique(pairs):
    obj={}
    for key,value in pairs:
        if key in obj:raise ValueError('Duplicate JSON key')
        obj[key]=value
    return obj

def reject_constant(value):raise ValueError('Nonstandard JSON constant')

def _decode_object(payload):
    try:obj=json.loads(payload,object_pairs_hook=unique,parse_constant=reject_constant)
    except (ValueError,RecursionError) as error:raise ValueError('Invalid or duplicate-key JSON object') from error
    if not isinstance(obj,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in obj.items()):
        raise ValueError('Require a flat filename-to-body-string JSON object')
    try:
        for key,value in obj.items():key.encode('utf-8');value.encode('utf-8')
    except UnicodeError as error:raise ValueError('Unpaired Unicode surrogate') from error
    return obj

def _bounds(raw,start,end):
    while start<end and raw[start] in SPACE:start+=1
    while end>start and raw[end-1] in SPACE:end-=1
    return start,end

def _jsonlike_array(tail):
    content=tail[1:].lstrip(SPACE)
    return bool(content) and (content[0] in '[{"-0123456789]' or content.startswith(('true','false','null','NaN','Infinity','-Infinity')))

def _outside(text,*,code=False):
    """Reject alternate structured payloads; recognize limited explanatory syntax."""
    stripped=text.lstrip(SPACE)
    if stripped[:1] in ('{','"') or (stripped.startswith('[') and _jsonlike_array(stripped)):
        # A standalone root is ambiguous even under a non-JSON fence label.
        # This intentionally rejects a bare sequence display as an answer block.
        raise ValueError('Alternate structured root outside the selected JSON fence')
    # JSON-shaped braces are never hidden by inline-code quoting or code labels.
    # Ordinary Dafny if/forall blocks start with statements, not JSON member syntax.
    for match in re.finditer(r'\{',text):
        start=match.start();tail=text[start+1:].lstrip(SPACE);first=tail[:1]
        lineprefix=text[text.rfind('\n',0,start)+1:start].strip()
        if first in ('"',"'",'}','[') or not lineprefix or lineprefix.endswith((':','=')):
            raise ValueError('Extra complete or JSON-looking malformed object')
    if code:
        # Non-JSON code blocks may contain sequence literals, but not a separate
        # structured root on its own line. This is stricter than Dafny syntax.
        for line in text.splitlines():
            if line.lstrip().startswith('[') and _jsonlike_array(line.lstrip()):
                raise ValueError('Alternate structured array line in explanatory code')
        return
    # Inline code is explanation, unless its entire content resembles a root.
    # Examples like K.Weave([],[]) and s[1..] therefore remain ordinary code.
    visible=list(text)
    for match in INLINE.finditer(text):
        inner=match.group('body').strip(SPACE)
        if inner.startswith(('{','"')) or (inner.startswith('[') and _jsonlike_array(inner)):
            raise ValueError('Alternate structured root in inline code')
        for i in range(match.start(),match.end()):visible[i]=' '
    prose=''.join(visible)
    if '`' in prose:raise ValueError('Unclosed or unsupported inline-code delimiter')
    for match in re.finditer(r'\[',prose):
        start=match.start()
        # Immediately attached identifier/closing-index syntax denotes a
        # displayed index or slice, not an independent response container.
        if start and (prose[start-1].isalnum() or prose[start-1] in "_'])"):
            continue
        if _jsonlike_array(prose[start:]):
            raise ValueError('Alternate structured array in explanatory prose')

def _fences(raw):
    blocks=[];opened=None;markers=list(FENCE_LINE.finditer(raw))
    for marker in markers:
        if marker.group('mark')!='```':raise ValueError('Unsupported or stray fence delimiter')
        label=marker.group('label').strip()
        if opened is None:
            opened=(marker,label)
        else:
            if label:raise ValueError('Nested or unclosed fenced block')
            first,tag=opened
            blocks.append(dict(start=first.start(),end=marker.end(),content_start=first.end(),content_end=marker.start(),tag=tag))
            opened=None
    if opened is not None:raise ValueError('Unclosed fenced block')
    return blocks

def extract_json(raw):
    if not isinstance(raw,str):raise ValueError('Response must be text')
    try:encoded=raw.encode('utf-8')
    except UnicodeError as error:raise ValueError('Unpaired Unicode surrogate') from error
    if len(encoded)>MAX_RESPONSE:raise ValueError('Response exceeds byte limit')
    start,end=_bounds(raw,0,len(raw));trimmed=raw[start:end]
    if not trimmed:raise ValueError('Empty response')
    if trimmed[0] in '{["':
        # Never search inside a wrapper, malformed root or quoted JSON string.
        _decode_object(trimmed);mode='whole_response';extra={}
    else:
        blocks=_fences(raw);selected=[b for b in blocks if b['tag'].casefold()=='json']
        if len(selected)!=1:raise ValueError('Require exactly one explicitly JSON-tagged fence')
        chosen=selected[0];start,end=_bounds(raw,chosen['content_start'],chosen['content_end'])
        _decode_object(raw[start:end])
        cursor=0
        for block in blocks:
            outside=raw[cursor:block['start']]
            if '```' in outside or '~~~' in outside:raise ValueError('Stray fence marker')
            _outside(outside)
            if block is not chosen:_outside(raw[block['content_start']:block['content_end']],code=True)
            cursor=block['end']
        outside=raw[cursor:]
        if '```' in outside or '~~~' in outside:raise ValueError('Stray fence marker')
        _outside(outside)
        mode='explicit_json_fence';extra=dict(fence_start_char=chosen['start'],fence_end_char=chosen['end'],
            surrounding_non_json_fences=len(blocks)-1)
    payload=raw[start:end]
    return payload,dict(version=VERSION,mode=mode,start_char=start,end_char=end,
        start_utf8_byte=len(raw[:start].encode()),end_utf8_byte=len(raw[:end].encode()),
        raw_sha256=hashlib.sha256(encoded).hexdigest(),payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),**extra)

def parse_response(raw,seeds,task,guard):
    payload,envelope=extract_json(raw)
    candidate,decision=guard.parse_response(payload,seeds,task)
    return candidate,dict(envelope=envelope,body_guard=decision)
