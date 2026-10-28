"""Bounded syntactic edit guard for branching tasks; not a Dafny verifier."""
import re
from json_payload import extract,CLIENTS
TOKEN=re.compile(r'\s*(>=|<=|==|!=|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[{}().;,+<>-])')
HELPERS={'Case0A','Case1A','Case0B','Case1B'}
MAX_TOKENS=2048
MAX_DEPTH=24
MAX_STATEMENTS=64

class Grammar:
    def __init__(self,body):
        self.tokens=[];i=0
        while i<len(body):
            if not body[i:].strip():break
            match=TOKEN.match(body,i)
            if not match:raise ValueError('Forbidden body token')
            self.tokens.append(match[1]);i=match.end()
            if len(self.tokens)>MAX_TOKENS:raise ValueError('Token limit')
        self.i=0;self.statements=0
    def peek(self):return self.tokens[self.i] if self.i<len(self.tokens) else None
    def take(self,expected=None):
        value=self.peek()
        if value is None or (expected is not None and value!=expected):raise ValueError('Unexpected token')
        self.i+=1;return value
    def atom(self,depth):
        if depth>MAX_DEPTH:raise ValueError('Expression depth limit')
        if self.peek() in ('+','-'):
            op=self.take();return dict(unary=op,value=self.atom(depth+1))
        if self.peek()=='(':
            self.take();value=self.expr(depth+1);self.take(')');return value
        token=self.take()
        if token in ('x','y'):return dict(parameter=token)
        if re.fullmatch('[0-9]{1,12}',token):return dict(integer=token)
        raise ValueError('Unknown expression identifier')
    def expr(self,depth=0):
        value=self.atom(depth);operators=0
        while self.peek() in ('+','-'):
            operators+=1
            if operators>128:raise ValueError('Expression operation limit')
            op=self.take();value=dict(operator=op,left=value,right=self.atom(depth))
        return value
    def condition(self):
        left=self.expr();op=self.take()
        if op not in ('<','<=','>','>=','==','!='):raise ValueError('Comparison required')
        return dict(operator=op,left=left,right=self.expr())
    def block(self,depth):
        self.take('{');items=self.sequence(depth,closing=True);self.take('}');return items
    def statement(self,depth):
        if depth>MAX_DEPTH:raise ValueError('Statement depth limit')
        self.statements+=1
        if self.statements>MAX_STATEMENTS:raise ValueError('Statement limit')
        if self.peek()=='if':
            self.take();cond=self.condition();yes=self.block(depth+1);no=[]
            if self.peek()=='else':
                self.take();no=[self.statement(depth+1)] if self.peek()=='if' else self.block(depth+1)
            return dict(kind='if',condition=cond,then=yes,otherwise=no)
        self.take('F');self.take('.');helper=self.take()
        if helper not in HELPERS:raise ValueError('Unknown helper')
        self.take('(');arg=self.expr();self.take(')');self.take(';')
        return dict(kind='call',helper=helper,argument=arg)
    def sequence(self,depth=0,closing=False):
        items=[]
        while self.peek() is not None and not (closing and self.peek()=='}'):items.append(self.statement(depth))
        return items

def validate_body(body):
    grammar=Grammar(body);tree=grammar.sequence()
    if grammar.peek() is not None:raise ValueError('Trailing tokens')
    return tree

def parse_response(raw,originals):
    files,metadata=extract(raw);accepted={};trees={}
    for name in CLIENTS:
        original=originals[name];suffix='  }\n}\n'
        if not original.endswith(suffix):raise ValueError('Unsupported fixture')
        prefix=original[:-len(suffix)];candidate=files[name].strip()+'\n'
        if not candidate.startswith(prefix) or not candidate.endswith(suffix):raise ValueError('Protected client bytes changed')
        trees[name]=validate_body(candidate[len(prefix):-len(suffix)]);accepted[name]=candidate
    return accepted,dict(extraction=metadata,guard_version='branch-v1',syntax_trees=trees)
