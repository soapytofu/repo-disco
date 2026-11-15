"""Prospective fixed-template body guard for four development repair tasks.

Grammar inherited from the frozen diverse-repair v1 guard. This version changes
only task bindings, adds one-binder universal expressions, and binds exact
workspace and helper-boundary hashes. It does not evaluate or verify proofs.
Envelope extraction remains a separate pinned repair-envelope-v2 component.
"""
from pathlib import Path
import hashlib
import json
import re

VERSION = 'repair-diversity-bodies-v1-development'
ROOT = Path(__file__).resolve().parent
REGISTRY_SHA256 = '46813ad53fd75dd69e121cc7171adb85e6a05cee39035ca1685ea5af1c138f7b'
MAX_RESPONSE = 262144
MAX_BODY = 65536
MAX_TOKENS = 8192
MAX_STATEMENTS = 256
TOKEN = re.compile(r"\s*(==>|!in\b|::|:=|\.\.|&&|\|\||>=|<=|==|!=|[A-Za-z_][A-Za-z_0-9']*|[0-9]+|[{}()\[\];,.+<>|!\-])")
PRECEDENCE = {'==>':1,'||':2,'&&':3,'==':4,'!=':4,'<':4,'<=':4,'>':4,'>=':4,'in':4,'!in':4,'+':5,'-':5}
RESERVED = set('if then else var assert forall ensures true false in assume reveal expect ghost lemma method function import include module export returns requires decreases modifies reads while match calc new return break map'.split()) | {'K','A','O','D','V','O1','O2','Prove','axiom','opaque','const','predicate','expect','label'}


def digest(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()

def hashes(files): return {n:digest(s) for n,s in sorted(files.items())}

def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('Duplicate JSON key')
        result[key]=value
    return result

def reject_constant(value): raise ValueError('Nonstandard JSON constant')

def registry():
    raw=(ROOT/'registry.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=REGISTRY_SHA256: raise ValueError('Pinned registry changed')
    return json.loads(raw)['tasks']

def task_entry(task):
    if not isinstance(task,dict): raise ValueError('Trusted task object required')
    entries=registry(); entry=entries.get(task.get('task_id'))
    if entry is None: raise ValueError('Unsupported task identifier')
    for key in ('task_id','semantic_instance','sharing','depth','entry','editable_files','source_sha256'):
        if task.get(key)!=entry[key]: raise ValueError('Task binding changed: '+key)
    # Ignore incidental provenance fields, but reject conflicting environment or
    # boundary metadata instead of silently accepting a misleading task record.
    for key,expected in (('params',entry['rules']['variables']),('calls',entry['rules']['calls']),('pure',entry['rules']['pure'])):
        if key in task and task[key]!=expected: raise ValueError('Task policy changed: '+key)
    if 'body_boundaries' in task:
        for name,boundary in task['body_boundaries'].items():
            saved=entry['body_boundaries'].get(name)
            if saved is None or boundary.get('start')!=saved['start_utf8_byte'] or boundary.get('end')!=saved['end_utf8_byte'] or boundary.get('protected_sha256')!=saved['protected_sha256']:
                raise ValueError('Task boundary changed')
        if set(task['body_boundaries'])!=set(entry['editable_files']): raise ValueError('Task boundary file set')
    return entry

def policy(task): return task_entry(task)['rules']

class Grammar:
    def __init__(self,body,task):
        if not isinstance(body,str): raise ValueError('Body type')
        try: encoded=body.encode('utf-8')
        except UnicodeError as error: raise ValueError('Unpaired body surrogate') from error
        if len(encoded)>MAX_BODY: raise ValueError('Body size')
        self.tokens=[]; position=0
        while position<len(body):
            if not body[position:].strip(): break
            match=TOKEN.match(body,position)
            if not match: raise ValueError('Forbidden token, comment, string, or attribute')
            self.tokens.append(match[1]); position=match.end()
            if len(self.tokens)>MAX_TOKENS: raise ValueError('Token count')
        self.i=0; self.statements=0; self.rules=policy(task)
        self.scopes=[set(self.rules['variables'])]

    def peek(self): return self.tokens[self.i] if self.i<len(self.tokens) else None
    def take(self,expected=None):
        token=self.peek()
        if token is None or expected is not None and token!=expected: raise ValueError('Unexpected proof token')
        self.i+=1; return token
    def identifier(self):
        name=self.take()
        if not re.fullmatch("[A-Za-z_][A-Za-z_0-9']*",name): raise ValueError('Identifier required')
        return name
    def bound(self,name): return any(name in scope for scope in self.scopes)
    def declare(self,name):
        aliases={symbol.split('.')[0] for symbol in [*self.rules['calls'],*self.rules['pure']] if '.' in symbol}
        if name in RESERVED or name in aliases or self.bound(name): raise ValueError('Reserved or shadowed local name')
        self.scopes[-1].add(name)
    def qualified(self):
        name=self.identifier()
        if self.peek()=='.': self.take(); name+='.'+self.identifier()
        return name
    def arguments(self,depth):
        self.take('('); args=[]
        if self.peek()!=')':
            args.append(self.expr(depth+1))
            while self.peek()==',': self.take(); args.append(self.expr(depth+1))
        self.take(')'); return args

    def atom(self,depth):
        if depth>32: raise ValueError('Expression nesting')
        token=self.peek()
        if token=='forall':
            self.take(); name=self.identifier(); self.scopes.append(set())
            try:
                self.declare(name); domain=None
                if self.peek()=='|': self.take(); domain=self.expr(depth+1)
                self.take('::'); post=self.expr(depth+1)
                node=['forall_expression',name,domain,post]
            finally: self.scopes.pop()
        elif token=='if':
            self.take(); condition=self.expr(depth+1); self.take('then')
            yes=self.expr(depth+1); self.take('else'); no=self.expr(depth+1)
            node=['if_expression',condition,yes,no]
        elif token in ('+','-','!'):
            self.take(); node=['unary',token,self.atom(depth+1)]
        elif token=='(':
            self.take(); node=self.expr(depth+1); self.take(')')
        elif token=='|':
            self.take(); node=['cardinality',self.expr(depth+1)]; self.take('|')
        elif token=='[':
            self.take(); values=[]
            if self.peek()!=']':
                values.append(self.expr(depth+1))
                while self.peek()==',': self.take(); values.append(self.expr(depth+1))
            self.take(']'); node=['sequence_literal',values]
        elif token=='{':
            self.take(); values=[]
            if self.peek()!='}':
                values.append(self.expr(depth+1))
                while self.peek()==',': self.take(); values.append(self.expr(depth+1))
            self.take('}'); node=['set_literal',values]
        elif token=='map':
            self.take(); name=self.identifier(); self.scopes.append(set())
            try:
                self.declare(name); self.take('|'); domain=self.expr(depth+1)
                self.take('::'); value=self.expr(depth+1)
                node=['map_comprehension',name,domain,value]
            finally: self.scopes.pop()
        elif token is not None and re.fullmatch('[0-9]{1,12}',token): node=['integer',self.take()]
        elif token in ('true','false'): node=['boolean',self.take()]
        else:
            name=self.identifier()
            if self.bound(name): node=['variable',name]
            else:
                if self.peek()=='.': self.take(); name+='.'+self.identifier()
                if name not in self.rules['pure']: raise ValueError('Unknown expression name')
                args=self.arguments(depth)
                if len(args)!=self.rules['pure'][name]: raise ValueError('Pure function arity')
                node=['pure',name,args]
        count=0
        while self.peek() in ('[','.'):
            count+=1
            if count>32: raise ValueError('Postfix nesting')
            if self.peek()=='.':
                self.take(); self.take('Keys'); node=['keys',node]; continue
            self.take('['); lo=None if self.peek()=='..' else self.expr(depth+1)
            if self.peek()=='..':
                self.take(); hi=None if self.peek()==']' else self.expr(depth+1)
                node=['slice',node,lo,hi]
            elif self.peek()==':=':
                self.take(); value=self.expr(depth+1)
                node=['functional_update',node,lo,value]
            else: node=['index',node,lo]
            self.take(']')
        return node

    def expr(self,depth=0,minimum=1):
        node=self.atom(depth); count=0
        while self.peek() in PRECEDENCE and PRECEDENCE[self.peek()]>=minimum:
            count+=1
            if count>128: raise ValueError('Expression operations')
            operator=self.take()
            node=['infix_syntax',operator,node,self.expr(depth+1,PRECEDENCE[operator]+1)]
        # This is a syntax inventory, not a typed/evaluated expression tree.
        # Dafny gives chained comparisons and overloaded operators their meaning.
        return node

    def block(self,depth):
        self.take('{'); self.scopes.append(set())
        try: result=self.sequence(depth,True); self.take('}'); return result
        finally: self.scopes.pop()

    def statement(self,depth):
        if depth>24: raise ValueError('Statement nesting')
        self.statements+=1
        if self.statements>MAX_STATEMENTS: raise ValueError('Statement count')
        token=self.peek()
        if token=='if':
            self.take(); condition=self.expr(); yes=self.block(depth+1); no=[]
            if self.peek()=='else':
                self.take(); no=[self.statement(depth+1)] if self.peek()=='if' else self.block(depth+1)
            return ['if_statement',condition,yes,no]
        if token=='var':
            self.take(); name=self.identifier(); self.take(':='); expression=self.expr(); self.take(';')
            self.declare(name); return ['local',name,expression]
        if token=='assert':
            self.take(); expression=self.expr(); self.take(';'); return ['assert',expression]
        if token=='forall':
            self.take(); name=self.identifier(); self.scopes.append(set())
            try:
                self.declare(name); self.take('|'); domain=self.expr(); self.take('ensures'); post=self.expr()
                body=self.block(depth+1)
                return ['forall_proof',name,domain,post,body]
            finally: self.scopes.pop()
        name=self.qualified()
        if name not in self.rules['calls']: raise ValueError('Forbidden statement or lemma call')
        args=self.arguments(0)
        if len(args)!=self.rules['calls'][name]: raise ValueError('Lemma arity')
        self.take(';'); return ['call',name,args]

    def sequence(self,depth=0,closing=False):
        statements=[]
        while self.peek() is not None and not (closing and self.peek()=='}'):
            statements.append(self.statement(depth))
        return statements


def split_seed(source):
    """Split the pinned empty body after its opening newline; no source rewrite."""
    if not isinstance(source,str): raise ValueError('Template source type')
    marker='  {\n  }\n}\n'
    if source.count(marker)!=1 or not source.endswith(marker): raise ValueError('Unsupported trusted empty body boundary')
    start=source.index(marker)+len('  {\n')
    return source[:start],source[start:]

def validate_template(seeds,task):
    entry=task_entry(task)
    if not isinstance(seeds,dict) or not all(isinstance(n,str) and isinstance(s,str) for n,s in seeds.items()):
        raise ValueError('Trusted source types')
    try: actual=hashes(seeds)
    except UnicodeError as error: raise ValueError('Template Unicode') from error
    if actual!=entry['source_sha256']: raise ValueError('Seed byte/file drift')
    for name,b in entry['body_boundaries'].items():
        prefix,suffix=split_seed(seeds[name])
        if (len(prefix.encode())!=b['start_utf8_byte'] or b['end_utf8_byte']!=b['start_utf8_byte']
            or digest(prefix)!=b['prefix_sha256'] or digest(suffix)!=b['suffix_sha256']
            or digest(prefix+'<EDITABLE_BODY>\n'+suffix)!=b['protected_sha256']):
            raise ValueError('Pinned body boundary drift')
    return entry

def parse_response(payload,seeds,task):
    """Accept strict JSON only; call the separate extractor for prose/fences."""
    if not isinstance(payload,str): raise ValueError('Payload type')
    try: encoded=payload.encode('utf-8')
    except UnicodeError as error: raise ValueError('Payload Unicode') from error
    if len(encoded)>MAX_RESPONSE: raise ValueError('Payload size')
    entry=validate_template(seeds,task)
    try: bodies=json.loads(payload,object_pairs_hook=unique,parse_constant=reject_constant)
    except (ValueError,RecursionError) as error: raise ValueError('Invalid body JSON') from error
    if not isinstance(bodies,dict) or set(bodies)!=set(entry['editable_files']) or not all(isinstance(b,str) for b in bodies.values()):
        raise ValueError('Exact editable filename/body-string set required')
    candidate=dict(seeds); decisions={}
    for name in entry['editable_files']:
        body=bodies[name]; grammar=Grammar(body,task); tree=grammar.sequence()
        if grammar.peek() is not None: raise ValueError('Trailing body tokens')
        prefix,suffix=split_seed(seeds[name]); candidate[name]=prefix+body+suffix
        decisions[name]=dict(**entry['body_boundaries'][name],body_sha256=digest(body),
            syntax=tree,tokens=len(grammar.tokens),statements=grammar.statements)
    return candidate,dict(version=VERSION,registry_sha256=REGISTRY_SHA256,task_id=entry['task_id'],
        parent_sha256=entry['source_sha256'],candidate_sha256=hashes(candidate),bodies=decisions,
        semantic_verification_performed=False)
