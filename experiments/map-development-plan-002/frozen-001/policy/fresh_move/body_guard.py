"""Bounded grammar with explicit per-task module bindings; not a semantic verifier.

Trusted host-owned task metadata and pinned empty fixtures are required. This
module only admits syntax and reconstructs sources. Dafny checks types and truth.
It never invokes a verifier or model, and never writes files or promotes edits.
New pure syntax: primed identifiers, set displays, functional map updates and
one-binder map comprehensions. No automatic rewrite or old-result rescoring.
"""
import hashlib
import json
import re

VERSION = 'fresh-move-development-body-v1'
MAX_RESPONSE = 262144
MAX_BODY = 65536
MAX_TOKENS = 8192
MAX_STATEMENTS = 256
TOKEN = re.compile(r"\s*(==>|!in\b|::|:=|\.\.|&&|\|\||>=|<=|==|!=|[A-Za-z_][A-Za-z_0-9']*|[0-9]+|[{}()\[\];,.+<>|!\-])")
PRECEDENCE = {'==>':1,'||':2,'&&':3,'==':4,'!=':4,'<':4,'<=':4,'>':4,'>=':4,'in':4,'!in':4,'+':5,'-':5}
RESERVED = set('if then else var assert forall ensures true false in assume reveal expect ghost lemma method function import include module export returns requires decreases modifies reads while match calc new return break map'.split()) | {'K','A','O1','O2','Prove'}


def digest(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def policy(task):
    if task['semantic_instance'] != 'fresh_move': raise ValueError('Unsupported semantic instance')
    depth=task['depth']
    if depth not in ('shallow','deep'): raise ValueError('Unsupported depth')
    calls={'A.Equal':2}
    calls.update({'A.ObserveMove':3} if depth=='shallow' else
                 {'O1.Certify':3,'O2.MoveKeys':3,'O2.MoveAt':4})
    return dict(variables=['m','a','b','c'], calls=calls,
                pure={'K.Move':3,'K.Ready':3})


class Grammar:
    def __init__(self,body,task):
        if not isinstance(body,str) or len(body.encode())>MAX_BODY: raise ValueError('Body size/type')
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
        if token=='if':
            self.take(); condition=self.expr(depth+1); self.take('then')
            yes=self.expr(depth+1); self.take('else'); no=self.expr(depth+1)
            node=['if_expression',condition,yes,no]
        elif token=='forall':
            self.take(); name=self.identifier(); self.scopes.append(set())
            try:
                self.declare(name); self.take('::')
                node=['forall_expression',name,self.expr(depth+1)]
            finally: self.scopes.pop()
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
    marker='  {\n  }\n}\n'
    if source.count(marker)!=1 or not source.endswith(marker): raise ValueError('Unsupported trusted seed boundary')
    start=source.index(marker)+len('  {'); end=start+1
    return source[:start],source[end:]


def parse_response(raw,seeds,task):
    if not isinstance(raw,str) or len(raw.encode())>MAX_RESPONSE: raise ValueError('Response size/type')
    if not isinstance(seeds,dict) or not all(isinstance(n,str) and isinstance(s,str) for n,s in seeds.items()):
        raise ValueError('Trusted source types')
    if {n:digest(s) for n,s in seeds.items()}!=task['source_sha256']: raise ValueError('Seed byte/file drift')
    names=task['editable_files']
    if not names or len(names)!=len(set(names)) or not set(names)<=set(seeds): raise ValueError('Invalid editable set')
    content=raw.strip(); wrapper='plain JSON'
    if content.startswith('```'):
        lines=content.splitlines()
        if len(lines)<3 or lines[0] not in ('```json','```') or lines[-1]!='```': raise ValueError('Ambiguous fence')
        content='\n'.join(lines[1:-1]); wrapper='whole-response JSON fence'
    try: bodies=json.loads(content,object_pairs_hook=unique)
    except (json.JSONDecodeError,RecursionError) as error: raise ValueError('Invalid body JSON') from error
    if not isinstance(bodies,dict) or set(bodies)!=set(names) or not all(isinstance(b,str) for b in bodies.values()):
        raise ValueError('Exact editable filename/body-string set required')
    candidate=dict(seeds); decisions={}
    for name,body in bodies.items():
        prefix,suffix=split_seed(seeds[name]); grammar=Grammar(body,task); tree=grammar.sequence()
        if grammar.peek() is not None: raise ValueError('Trailing body tokens')
        candidate[name]=prefix+body+suffix
        decisions[name]=dict(prefix_sha256=digest(prefix),suffix_sha256=digest(suffix),body_sha256=digest(body),
            syntax=tree,tokens=len(grammar.tokens),statements=grammar.statements)
    return candidate,dict(version=VERSION,wrapper=wrapper,parent_sha256=task['source_sha256'],
        candidate_sha256={n:digest(s) for n,s in candidate.items()},bodies=decisions,
        semantic_verification_performed=False)
