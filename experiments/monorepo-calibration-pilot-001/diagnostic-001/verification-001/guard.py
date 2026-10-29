"""calibration-body-v1: bounded syntax, exact immutable bytes, no proof repair.
Only trusted, pinned seed templates are supported. Dafny remains the proof checker.
This is an output policy, not a sandbox for arbitrary Dafny programs.
"""
import json,re
MAX_RESPONSE=262144
TOKEN=re.compile(r'\s*(==>|&&|\|\||:=|\.\.|>=|<=|==|!=|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[{}()\[\];,.+<>|!\-])')
PRECEDENCE={'==>':1,'||':2,'&&':3,'==':4,'!=':4,'<':4,'<=':4,'>':4,'>=':4,'+':5,'-':5}
PURE={'conditional_preconditions':{'K.Abs':1,'K.Encode':2,'K.Safe':1,'K.Ready1':2,'K.Ready2':2},'sequence_induction':{'K.Total':1,'K.SplitReady':2,'K.StepReady':2},'relational_join':{'K.LeftFact':2,'K.RightFact':2,'K.Joined':3,'K.Safe':2},'finite_map_frames':{'K.Valid':1,'K.Values':1,'K.Frame':3,'K.Ready':3,'K.FrameTwo':4}}

def unique(pairs):
 out={}
 for k,v in pairs:
  if k in out:raise ValueError('Duplicate JSON key')
  out[k]=v
 return out

def extract(raw,names):
 if not isinstance(raw,str) or len(raw.encode())>MAX_RESPONSE:raise ValueError('Response size/type')
 decoder=json.JSONDecoder();found=[];i=0
 while i<len(raw):
  if raw[i]!='{':i+=1;continue
  try:value,end=decoder.raw_decode(raw[i:])
  except ValueError:i+=1;continue
  found.append((i,i+end));i+=end
 if len(found)!=1:raise ValueError('Expected one unambiguous JSON object')
 a,b=found[0]
 if any(c in raw[:a]+raw[b:] for c in '{}'):raise ValueError('Ambiguous or malformed JSON wrapper')
 files=json.loads(raw[a:b],object_pairs_hook=unique)
 if not isinstance(files,dict) or set(files)!=set(names) or not all(isinstance(v,str) for v in files.values()):raise ValueError('Exact editable filename/string set required')
 return files,dict(start=a,end=b,policy='exact JSON substring; no source or escape repair')

class Grammar:
 def __init__(self,body,task):
  if len(body.encode())>65536:raise ValueError('Body size')
  self.tokens=[];i=0
  while i<len(body):
   if not body[i:].strip():break
   m=TOKEN.match(body,i)
   if not m:raise ValueError('Forbidden token, comment, or attribute')
   self.tokens.append(m[1]);i=m.end()
   if len(self.tokens)>8192:raise ValueError('Token count')
  self.i=0;self.statements=0;self.task=task
 def peek(self):return self.tokens[self.i] if self.i<len(self.tokens) else None
 def take(self,x=None):
  t=self.peek()
  if t is None or x is not None and t!=x:raise ValueError('Unexpected proof token')
  self.i+=1;return t
 def name(self):
  name=self.take()
  if self.peek()=='.':self.take();name+='.'+self.take()
  return name
 def arguments(self,depth):
  self.take('(');a=[]
  if self.peek()!=')':
   a.append(self.expr(depth+1))
   while self.peek()==',':self.take();a.append(self.expr(depth+1))
  self.take(')');return a
 def atom(self,depth):
  if depth>32:raise ValueError('Expression nesting')
  t=self.peek()
  if t=='if':
   self.take();condition=self.expr(depth+1);self.take('then');yes=self.expr(depth+1);self.take('else');no=self.expr(depth+1);node=['if_expression',condition,yes,no]
  elif t in ('+','-','!'):self.take();node=['unary',t,self.atom(depth+1)]
  elif t=='(':
   self.take();node=self.expr(depth+1);self.take(')')
  elif t=='|':
   self.take();node=['length',self.expr(depth+1)];self.take('|')
  elif t=='[':self.take();self.take(']');node=['empty_sequence']
  elif t is not None and re.fullmatch('[0-9]{1,12}',t):node=['integer',self.take()]
  elif t in ('true','false'):node=['boolean',self.take()]
  else:
   name=self.name()
   if name in self.task['variables']:node=['variable',name]
   elif name in PURE[self.task['family']]:
    a=self.arguments(depth)
    if len(a)!=PURE[self.task['family']][name]:raise ValueError('Pure function arity')
    node=['pure',name,a]
   else:raise ValueError('Unknown expression name')
  postfixes=0
  while self.peek()=='[':
   postfixes+=1
   if postfixes>32:raise ValueError('Postfix nesting')
   self.take();lo=None if self.peek()=='..' else self.expr(depth+1)
   if self.peek()=='..':
    self.take();hi=None if self.peek()==']' else self.expr(depth+1);node=['slice',node,lo,hi]
   elif self.peek()==':=':
    self.take();node=['update',node,lo,self.expr(depth+1)]
   else:node=['index',node,lo]
   self.take(']')
  return node
 def expr(self,depth=0,min_precedence=1):
  node=self.atom(depth);count=0
  while self.peek() in PRECEDENCE and PRECEDENCE[self.peek()]>=min_precedence:
   count+=1
   if count>128:raise ValueError('Expression operations')
   op=self.take();node=['binary',op,node,self.expr(depth+1,PRECEDENCE[op]+1)]
  return node
 def block(self,depth):
  self.take('{');s=self.sequence(depth,True);self.take('}');return s
 def statement(self,depth):
  if depth>24:raise ValueError('Statement nesting')
  self.statements+=1
  if self.statements>256:raise ValueError('Statement count')
  if self.peek()=='if':
   self.take();condition=self.expr();yes=self.block(depth+1);no=[]
   if self.peek()=='else':
    self.take();no=[self.statement(depth+1)] if self.peek()=='if' else self.block(depth+1)
   return ['if',condition,yes,no]
  if self.peek()=='assert':
   self.take();e=self.expr();self.take(';');return ['assert',e]
  name=self.name()
  if name not in self.task['calls']:raise ValueError('Forbidden statement or lemma call')
  a=self.arguments(0)
  if len(a)!=self.task['calls'][name]:raise ValueError('Lemma arity')
  self.take(';');return ['call',name,a]
 def sequence(self,depth=0,closing=False):
  out=[]
  while self.peek() is not None and not(closing and self.peek()=='}'):out.append(self.statement(depth))
  return out

def split_seed(text):
 # Trusted seed contains one uniquely delimited empty target lemma body. Do not
 # use regex replacement across nested braces or parse untrusted declarations.
 marker='  {\n  }\n}\n'
 if text.count(marker)!=1 or not text.endswith(marker):raise ValueError('Unsupported seed body boundary')
 start=text.index(marker)+len('  {');end=start+1
 return text[:start],text[end:]

def validate_files(files,seeds,task):
 if set(files)!=set(task['editable_files']):raise ValueError('Unexpected editable files')
 trees={}
 for n,text in files.items():
  if not isinstance(text,str):raise ValueError('Source must be string')
  prefix,suffix=split_seed(seeds[n])
  if not text.startswith(prefix) or not text.endswith(suffix) or len(text)<len(prefix)+len(suffix):raise ValueError('Protected source changed')
  body=text[len(prefix):len(text)-len(suffix)]
  g=Grammar(body,task);trees[n]=g.sequence()
  if g.peek() is not None:raise ValueError('Trailing tokens')
 return dict(files),dict(version='diagnostic-inline-if-v1',syntax_trees=trees)

def parse_response(raw,seeds,task):
 files,extraction=extract(raw,task['editable_files']);files,meta=validate_files(files,seeds,task)
 meta['extraction']=extraction
 return files,meta
