"""Bounded proof-body parser; preserves all provider bytes outside target bodies."""
import re
from provider_payload import extract
TOKEN=re.compile(r'\s*(\.\.|>=|<=|==|!=|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[{}()\[\];,+<>|\-])')

class Grammar:
    def __init__(self,body,helper):
        self.tokens=[];i=0;self.helper=helper;self.i=0;self.count=0
        while i<len(body):
            if not body[i:].strip():break
            m=TOKEN.match(body,i)
            if not m:raise ValueError('Forbidden proof token')
            self.tokens.append(m[1]);i=m.end()
            if len(self.tokens)>2048:raise ValueError('Token limit')
    def peek(self):return self.tokens[self.i] if self.i<len(self.tokens) else None
    def take(self,expected=None):
        t=self.peek()
        if t is None or (expected is not None and t!=expected):raise ValueError('Unexpected token')
        self.i+=1;return t
    def atom(self,depth):
        if depth>24:raise ValueError('Expression depth limit')
        token=self.take()
        if token in ('+','-'):node={'unary':token,'value':self.atom(depth+1)}
        elif token=='(':
            node=self.expr(depth+1);self.take(')')
        elif token=='|':
            node={'length':self.expr(depth+1)};self.take('|')
        elif token=='[':self.take(']');node={'empty_sequence':True}
        elif token=='Total':
            self.take('(');node={'Total':self.expr(depth+1)};self.take(')')
        elif token in ('s','t'):node={'parameter':token}
        elif re.fullmatch('[0-9]{1,12}',token):node={'integer':token}
        else:raise ValueError('Unknown expression token')
        postfixes=0
        while self.peek()=='[':
            postfixes+=1
            if postfixes>24:raise ValueError('Postfix limit')
            self.take();low=None if self.peek()=='..' else self.expr(depth+1)
            if self.peek()=='..':
                self.take();high=None if self.peek()==']' else self.expr(depth+1);node={'slice':node,'low':low,'high':high}
            else:node={'index':node,'at':low}
            self.take(']')
        return node
    def expr(self,depth=0):
        node=self.atom(depth);operations=0
        while self.peek() in ('+','-'):
            operations+=1
            if operations>128:raise ValueError('Operation limit')
            op=self.take();node={'operator':op,'left':node,'right':self.atom(depth)}
        return node
    def comparison(self):
        left=self.expr();op=self.take()
        if op not in ('<','<=','>','>=','==','!='):raise ValueError('Comparison required')
        return {'operator':op,'left':left,'right':self.expr()}
    def block(self,depth):
        self.take('{');items=self.sequence(depth,True);self.take('}');return items
    def statement(self,depth):
        if depth>24:raise ValueError('Statement depth limit')
        self.count+=1
        if self.count>64:raise ValueError('Statement limit')
        token=self.take()
        if token=='if':
            condition=self.comparison();yes=self.block(depth+1);no=[]
            if self.peek()=='else':
                self.take();no=[self.statement(depth+1)] if self.peek()=='if' else self.block(depth+1)
            return {'if':condition,'then':yes,'else':no}
        if token=='assert':
            value=self.comparison();self.take(';');return {'assert':value}
        if token!=self.helper:raise ValueError('Only self-recursive helper calls allowed')
        self.take('(');a=self.expr();self.take(',');b=self.expr();self.take(')');self.take(';')
        return {'call':token,'arguments':[a,b]}
    def sequence(self,depth=0,closing=False):
        items=[]
        while self.peek() is not None and not(closing and self.peek()=='}'):items.append(self.statement(depth))
        return items

def spans(text,headers):
    result=[]
    for name,header in headers:
        if text.count(header)!=1:raise ValueError('Protected header missing or duplicated')
        start=text.index(header)+len(header);depth=1;end=start
        for end in range(start,len(text)):
            depth+=(text[end]=='{')-(text[end]=='}')
            if depth==0:break
        if depth:raise ValueError('Unclosed helper body')
        result.append((start,end,name))
    result.sort()
    if any(a[1]>=b[0] for a,b in zip(result,result[1:])):raise ValueError('Overlapping helper bodies')
    return result

def skeleton(text,ranges):
    for start,end,name in reversed(ranges):text=text[:start]+'<BODY:'+name+'>'+text[end:]
    return text

def parse_response(raw,original):
    files,meta=extract(raw);candidate=files['Facts.dfy'].strip()+'\n'
    pattern=r'  lemma \{:induction false\} (Append[AB])\(s: seq<int>, t: seq<int>\)\n    ensures [^\n]+\n    decreases \|s\|\n  \{'
    headers=[(m[1],m[0]) for m in re.finditer(pattern,original)]
    if not headers or len({n for n,h in headers})!=len(headers):raise ValueError('Unsupported original')
    a=spans(original,headers);b=spans(candidate,headers)
    if skeleton(original,a)!=skeleton(candidate,b):raise ValueError('Protected provider bytes changed')
    trees={}
    for start,end,name in b:
        grammar=Grammar(candidate[start:end],name);trees[name]=grammar.sequence()
        if grammar.peek() is not None:raise ValueError('Trailing proof tokens')
    return candidate,{'guard_version':'provider-v1','extraction':meta,'syntax_trees':trees}
