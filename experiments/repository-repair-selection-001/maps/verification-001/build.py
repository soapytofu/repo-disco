"""Two fixed-architecture map repair candidates; construction only, no execution."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
MAP = 'map<int,int>'
SET = 'set<int>'

INVERSE_KERNEL = '''module Kernel {
  export Public provides Put, Exchange reveals Inverse
  export Internal reveals Put, Exchange, Inverse
  opaque function Put(m: map<int,int>, key: int, value: int): map<int,int> {
    m[key := value]
  }
  opaque function Exchange(m: map<int,int>, p: int, q: int): map<int,int>
    requires p in m && q in m
  {
    Put(Put(m,p,m[q]),q,m[p])
  }
  predicate Inverse(m: map<int,int>, n: map<int,int>) {
    (forall x :: x in m ==> m[x] in n && n[m[x]] == x) &&
    (forall y :: y in n ==> n[y] in m && m[n[y]] == y)
  }
}
'''
INVERSE_OPS = '''include "Kernel.dfy"
module Ops {
  export Public provides K, PutKeys, PutAt, ExchangeShape
  export Hidden provides K, HiddenPutAt
  import K = Kernel`Internal
  lemma PutKeys(m: map<int,int>, key: int, value: int)
    ensures K.Put(m,key,value).Keys == m.Keys + {key}
  { reveal K.Put(); }
  lemma PutAt(m: map<int,int>, key: int, value: int, x: int)
    requires x in m || x == key
    ensures x in K.Put(m,key,value)
    ensures K.Put(m,key,value)[x] == (if x == key then value else m[x])
  { reveal K.Put(); }
  lemma ExchangeShape(m: map<int,int>, p: int, q: int)
    requires p in m && q in m
    ensures K.Exchange(m,p,q) == K.Put(K.Put(m,p,m[q]),q,m[p])
  { reveal K.Exchange(); }
  lemma HiddenPutAt(m: map<int,int>, key: int, value: int, x: int)
    requires x in m || x == key
    ensures x in K.Put(m,key,value)
    ensures K.Put(m,key,value)[x] == (if x == key then value else m[x])
  { reveal K.Put(); }
}
'''
INVERSE_A_SIG = 'm: map<int,int>, p: int, q: int'
INVERSE_A_SPEC = '''    requires p in m && q in m && p != q
    ensures K.Exchange(m,p,q).Keys == m.Keys
    ensures forall x :: x in m ==> x in K.Exchange(m,p,q) &&
      K.Exchange(m,p,q)[x] == (if x == p then m[q] else if x == q then m[p] else m[x])
'''
INVERSE_B_SIG = 'm: map<int,int>, n: map<int,int>, p: int, q: int'
INVERSE_B_SPEC = '''    requires K.Inverse(m,n)
    requires p in m && q in m && p != q
    ensures K.Inverse(K.Exchange(m,p,q),K.Exchange(n,m[p],m[q]))
'''
INVERSE_A_PREFIX = '''    var inner := K.Put(m,p,m[q]);
    var swapped := K.Exchange(m,p,q);
    O.ExchangeShape(m,p,q);
    O.PutKeys(m,p,m[q]);
    assert inner.Keys == m.Keys;
    O.PutKeys(inner,q,m[p]);
    assert swapped.Keys == m.Keys;
'''
INVERSE_A_REF = INVERSE_A_PREFIX + '''    forall x | x in m ensures x in swapped &&
      swapped[x] == (if x == p then m[q] else if x == q then m[p] else m[x]) {
      O.PutAt(m,p,m[q],x);
      O.PutAt(inner,q,m[p],x);
    }
'''
INVERSE_A_ALT = INVERSE_A_PREFIX + '''    forall x | x in m ensures x in swapped &&
      swapped[x] == (if x == p then m[q] else if x == q then m[p] else m[x]) {
      O.PutAt(inner,q,m[p],x);
      O.PutAt(m,p,m[q],x);
      if x == q {
        assert swapped[x] == m[p];
      } else if x == p {
        assert swapped[x] == m[q];
      } else {
        assert swapped[x] == m[x];
      }
    }
'''
INVERSE_B_PREFIX = '''    var u := m[p];
    var v := m[q];
    assert u in n && v in n;
    assert n[u] == p && n[v] == q;
    assert u != v;
    H.Prove(m,p,q);
    H.Prove(n,u,v);
    var forward := K.Exchange(m,p,q);
    var backward := K.Exchange(n,u,v);
'''
INVERSE_FORWARD = '''    forall x | x in forward ensures forward[x] in backward && backward[forward[x]] == x {
      assert x in m;
      assert n[m[x]] == x;
      if x == p {
        assert forward[x] == v;
        assert backward[v] == p;
      } else if x == q {
        assert forward[x] == u;
        assert backward[u] == q;
      } else {
        assert m[x] != u && m[x] != v;
        assert forward[x] == m[x];
        assert backward[m[x]] == n[m[x]];
      }
    }
'''
INVERSE_BACKWARD = '''    forall y | y in backward ensures backward[y] in forward && forward[backward[y]] == y {
      assert y in n;
      assert m[n[y]] == y;
      if y == u {
        assert backward[y] == q;
        assert forward[q] == u;
      } else if y == v {
        assert backward[y] == p;
        assert forward[p] == v;
      } else {
        assert n[y] != p && n[y] != q;
        assert backward[y] == n[y];
        assert forward[n[y]] == m[n[y]];
      }
    }
'''
INVERSE_B_REF = INVERSE_B_PREFIX + INVERSE_FORWARD + INVERSE_BACKWARD
INVERSE_B_ALT = INVERSE_B_PREFIX.replace('    H.Prove(m,p,q);\n    H.Prove(n,u,v);\n',
    '    H.Prove(n,u,v);\n    H.Prove(m,p,q);\n') + INVERSE_BACKWARD + INVERSE_FORWARD
INVERSE_B_FAULTY = INVERSE_B_REF.replace('    H.Prove(n,u,v);\n', '    H.Prove(n,p,q);\n')

COMPOSE_KERNEL = '''module Kernel {
  export Public provides Override, Restrict, Compose
  export Internal reveals Override, Restrict, Compose
  opaque function Override(f1: map<int,int>, f2: map<int,int>): map<int,int> {
    map x | x in f1.Keys + f2.Keys :: if x in f2 then f2[x] else f1[x]
  }
  opaque function Restrict(f: map<int,int>, keep: set<int>): map<int,int> {
    map x | x in f && x in keep :: f[x]
  }
  opaque function Compose(f: map<int,int>, g: map<int,int>): map<int,int> {
    map x | x in f && f[x] in g :: g[f[x]]
  }
}
'''
COMPOSE_DOMAINS = '''include "Kernel.dfy"
module Domains {
  export Public provides K, OverrideKeys, RestrictKeys, ComposeKeys
  import K = Kernel`Internal
  lemma OverrideKeys(f1: map<int,int>, f2: map<int,int>)
    ensures K.Override(f1,f2).Keys == f1.Keys + f2.Keys
  { reveal K.Override(); }
  lemma RestrictKeys(f: map<int,int>, keep: set<int>)
    ensures K.Restrict(f,keep).Keys == f.Keys * keep
  { reveal K.Restrict(); }
  lemma ComposeKeys(f: map<int,int>, g: map<int,int>)
    ensures K.Compose(f,g).Keys == (set x | x in f && f[x] in g)
  { reveal K.Compose(); }
}
'''
COMPOSE_VALUES = '''include "Kernel.dfy"
module Values {
  export Public provides K, OverrideAt, RestrictAt, ComposeAt
  export Hidden provides K, HiddenRestrictAt
  import K = Kernel`Internal
  lemma OverrideAt(f1: map<int,int>, f2: map<int,int>, x: int)
    requires x in f1 || x in f2
    ensures x in K.Override(f1,f2)
    ensures K.Override(f1,f2)[x] == (if x in f2 then f2[x] else f1[x])
  { reveal K.Override(); }
  lemma RestrictAt(f: map<int,int>, keep: set<int>, x: int)
    requires x in f && x in keep
    ensures x in K.Restrict(f,keep)
    ensures K.Restrict(f,keep)[x] == f[x]
  { reveal K.Restrict(); }
  lemma ComposeAt(f: map<int,int>, g: map<int,int>, x: int)
    requires x in f && f[x] in g
    ensures x in K.Compose(f,g)
    ensures K.Compose(f,g)[x] == g[f[x]]
  { reveal K.Compose(); }
  lemma HiddenRestrictAt(f: map<int,int>, keep: set<int>, x: int)
    requires x in f && x in keep
    ensures x in K.Restrict(f,keep)
    ensures K.Restrict(f,keep)[x] == f[x]
  { reveal K.Restrict(); }
}
'''
COMPOSE_API = '''module Api {
  export Public provides Equal
  lemma Equal(left: map<int,int>, right: map<int,int>)
    requires left.Keys == right.Keys
    requires forall x :: x in left ==> x in right && left[x] == right[x]
    ensures left == right
  { }
}
'''
COMPOSE_SIG = 'f1: map<int,int>, f2: map<int,int>, g: map<int,int>'
COMPOSE_LEFT = 'K.Compose(K.Override(f1,f2),g)'
COMPOSE_RIGHT = 'K.Override(K.Compose(K.Restrict(f1,f1.Keys-f2.Keys),g),K.Compose(f2,g))'
COMPOSE_A_SPEC = '    ensures '+COMPOSE_LEFT+'.Keys == '+COMPOSE_RIGHT+'.Keys\n'
COMPOSE_B_SPEC = '    ensures '+COMPOSE_LEFT+' == '+COMPOSE_RIGHT+'\n'
COMPOSE_ALIASES = '''    var keep := f1.Keys-f2.Keys;
    var merged := K.Override(f1,f2);
    var trimmed := K.Restrict(f1,keep);
    var left := K.Compose(merged,g);
    var first := K.Compose(trimmed,g);
    var second := K.Compose(f2,g);
    var right := K.Override(first,second);
'''
COMPOSE_DOMAIN_CALLS = '''    D.OverrideKeys(f1,f2);
    D.RestrictKeys(f1,keep);
    D.ComposeKeys(merged,g);
    D.ComposeKeys(trimmed,g);
    D.ComposeKeys(f2,g);
    D.OverrideKeys(first,second);
'''
COMPOSE_A_PREFIX = COMPOSE_ALIASES + COMPOSE_DOMAIN_CALLS
COMPOSE_A_REF = COMPOSE_A_PREFIX + '''    assert left.Keys <= merged.Keys;
    assert right.Keys <= merged.Keys;
    forall x | x in merged ensures (x in left) == (x in right) {
      V.OverrideAt(f1,f2,x);
      if x in f2 {
        assert x !in trimmed;
      } else {
        V.RestrictAt(f1,keep,x);
      }
    }
    assert left.Keys == right.Keys;
'''
COMPOSE_A_ALT = COMPOSE_A_PREFIX + '''    forall x | x in left.Keys+right.Keys ensures (x in left) == (x in right) {
      assert x in merged;
      V.OverrideAt(f1,f2,x);
      if x !in f2 {
        V.RestrictAt(f1,keep,x);
      } else {
        assert x !in trimmed;
      }
    }
    assert left.Keys == right.Keys;
'''
COMPOSE_A_FAULTY = COMPOSE_A_REF.replace('''      if x in f2 {
        assert x !in trimmed;
      } else {
        V.RestrictAt(f1,keep,x);
      }
''', '''      if x in f1 && f1[x] in g {
        assert x in left;
      } else if x in f2 {
        assert x !in trimmed;
      } else {
        V.RestrictAt(f1,keep,x);
      }
''')
COMPOSE_B_PREFIX = '    H.Prove(f1,f2,g);\n' + COMPOSE_ALIASES + COMPOSE_DOMAIN_CALLS
COMPOSE_B_REF = COMPOSE_B_PREFIX + '''    forall x | x in left ensures x in right && left[x] == right[x] {
      V.OverrideAt(f1,f2,x);
      V.ComposeAt(merged,g,x);
      if x in f2 {
        V.ComposeAt(f2,g,x);
      } else {
        V.RestrictAt(f1,keep,x);
        V.ComposeAt(trimmed,g,x);
      }
      V.OverrideAt(first,second,x);
    }
    A.Equal(left,right);
'''
COMPOSE_B_ALT = COMPOSE_B_PREFIX + '''    forall x | x in left ensures x in right && left[x] == right[x] {
      V.OverrideAt(first,second,x);
      V.OverrideAt(f1,f2,x);
      if x in second {
        V.ComposeAt(f2,g,x);
      } else {
        V.RestrictAt(f1,keep,x);
        V.ComposeAt(trimmed,g,x);
      }
      V.ComposeAt(merged,g,x);
    }
    A.Equal(left,right);
'''


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def hashes(files):
    return {name: sha(value) for name, value in sorted(files.items())}


def body_boundary(source):
    start = source.index('  {\n', source.index('lemma {:induction false} Prove')) + 4
    end = source.rindex('  }\n}\n')
    return dict(start=len(source[:start].encode()), end=len(source[:end].encode()),
                protected_sha256=sha(source[:start]+'<EDITABLE_BODY>\n'+source[end:]))


def helper(name, signature, spec, body, includes, imports):
    return (''.join('include "'+x+'.dfy"\n' for x in includes) + 'module '+name+' {\n' +
            ''.join('  import '+alias+' = '+target+'\n' for alias,target in imports) +
            '  lemma {:induction false} Prove('+signature+')\n'+spec+'  {\n'+body+'  }\n}\n')


def inverse_clients():
    header='include "HelperB.dfy"\n'
    imports='  import K = Kernel`Public\n  import H = HelperB\n'
    a=header+'module ClientA {\n'+imports+'  lemma {:induction false} Target('+INVERSE_B_SIG+')\n'+INVERSE_B_SPEC+'  { H.Prove(m,n,p,q); }\n}\n'
    bspec=INVERSE_B_SPEC.replace('K.Inverse(K.Exchange(m,p,q),K.Exchange(n,m[p],m[q]))',
                                'K.Inverse(K.Exchange(n,m[p],m[q]),K.Exchange(m,p,q))')
    b=header+'module ClientB {\n'+imports+'  lemma {:induction false} Target('+INVERSE_B_SIG+')\n'+bspec+'''  {
    assert K.Inverse(n,m);
    assert n[m[p]] == p && n[m[q]] == q;
    assert m[p] != m[q];
    H.Prove(n,m,m[p],m[q]);
  }
}
'''
    return {'ClientA.dfy':a,'ClientB.dfy':b}


def compose_clients():
    files={}
    for name,swap in [('ClientA',False),('ClientB',True)]:
        spec=COMPOSE_B_SPEC if not swap else COMPOSE_B_SPEC.replace('f1','TEMP').replace('f2','f1').replace('TEMP','f2')
        args='f2,f1,g' if swap else 'f1,f2,g'
        files[name+'.dfy']='include "HelperB.dfy"\nmodule '+name+' {\n  import K = Kernel`Public\n  import H = HelperB\n  lemma {:induction false} Target('+COMPOSE_SIG+')\n'+spec+'  { H.Prove('+args+'); }\n}\n'
    return files


# expected diagnostic is a specific category, never an exit-code-only negative.
INVERSE_VARIANTS = {
 'reference': (INVERSE_A_REF,INVERSE_B_REF,'success','none'),
 'alternative': (INVERSE_A_ALT,INVERSE_B_ALT,'success','none'),
 'faulty': (INVERSE_A_REF,INVERSE_B_FAULTY,'proof_failure','precondition'),
 'empty': ('','','proof_failure','postcondition'),
 'only_a_repair': (INVERSE_A_REF,INVERSE_B_FAULTY,'proof_failure','precondition'),
 'only_b_repair': (INVERSE_A_REF,INVERSE_B_REF,'success','none'),
 'empty_a': ('',INVERSE_B_REF,'proof_failure','postcondition'),
 'empty_b': (INVERSE_A_REF,'','proof_failure','postcondition'),
 'missing_outer_update': (INVERSE_A_REF.replace('      O.PutAt(inner,q,m[p],x);\n',''),INVERSE_B_REF,'proof_failure','postcondition'),
 'wrong_exchange_value': (INVERSE_A_REF+'    assert swapped[p] == m[p];\n',INVERSE_B_REF,'proof_failure','assertion'),
 'missing_inverse_prerequisite': (INVERSE_A_REF,INVERSE_B_REF.replace('    H.Prove(n,u,v);\n',''),'proof_failure','assertion'),
 'wrong_inverse_direction': (INVERSE_A_REF,INVERSE_B_REF.replace('        assert backward[v] == p;','        assert backward[v] == q;'),'proof_failure','assertion'),
 'hidden_call': (INVERSE_A_REF.replace('O.PutAt(m,p,m[q],x)','O.HiddenPutAt(m,p,m[q],x)'),INVERSE_B_REF,'resolution_failure','missing export member'),
}
COMPOSE_VARIANTS = {
 'reference': (COMPOSE_A_REF,COMPOSE_B_REF,'success','none'),
 'alternative': (COMPOSE_A_ALT,COMPOSE_B_ALT,'success','none'),
 'faulty': (COMPOSE_A_FAULTY,COMPOSE_B_REF,'proof_failure','assertion'),
 'empty': ('','','proof_failure','postcondition'),
 'only_a_repair': (COMPOSE_A_REF,COMPOSE_B_REF,'success','none'),
 'only_b_repair': (COMPOSE_A_FAULTY,COMPOSE_B_REF,'proof_failure','assertion'),
 'empty_a': ('',COMPOSE_B_REF,'proof_failure','postcondition'),
 'empty_b': (COMPOSE_A_REF,'','proof_failure','postcondition'),
 'missing_override_value': (COMPOSE_A_REF.replace('      V.OverrideAt(f1,f2,x);\n',''),COMPOSE_B_REF,'proof_failure','postcondition'),
 'wrong_priority': (COMPOSE_A_REF,COMPOSE_B_REF.replace('      if x in f2 {\n','      if x in f2 {\n        if x in f1 { assert merged[x] == f1[x]; }\n'),'proof_failure','assertion'),
 'missing_compose_value': (COMPOSE_A_REF,COMPOSE_B_REF.replace('      V.ComposeAt(merged,g,x);\n',''),'proof_failure','postcondition'),
 'hidden_call': (COMPOSE_A_REF.replace('V.RestrictAt(f1,keep,x)','V.HiddenRestrictAt(f1,keep,x)'),COMPOSE_B_REF,'resolution_failure','missing export member'),
}
TASKS = ['inverse_exchange_pipeline','masked_override_composition_pipeline']


def sources(task_id, variant):
    if task_id==TASKS[0]:
        a,b,_,_=INVERSE_VARIANTS[variant]
        return {'Kernel.dfy':INVERSE_KERNEL,'Ops.dfy':INVERSE_OPS,
                'HelperA.dfy':helper('HelperA',INVERSE_A_SIG,INVERSE_A_SPEC,a,['Kernel','Ops'],[('K','Kernel`Public'),('O','Ops`Public')]),
                'HelperB.dfy':helper('HelperB',INVERSE_B_SIG,INVERSE_B_SPEC,b,['Kernel','HelperA'],[('K','Kernel`Public'),('H','HelperA')]),
                **inverse_clients(),'All.dfy':'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}
    assert task_id==TASKS[1]
    a,b,_,_=COMPOSE_VARIANTS[variant]
    common=[('K','Kernel`Public'),('D','Domains`Public'),('V','Values`Public')]
    return {'Kernel.dfy':COMPOSE_KERNEL,'Domains.dfy':COMPOSE_DOMAINS,'Values.dfy':COMPOSE_VALUES,'Api.dfy':COMPOSE_API,
            'HelperA.dfy':helper('HelperA',COMPOSE_SIG,COMPOSE_A_SPEC,a,['Kernel','Domains','Values'],common),
            'HelperB.dfy':helper('HelperB',COMPOSE_SIG,COMPOSE_B_SPEC,b,['Kernel','Domains','Values','Api','HelperA'],common+[('A','Api`Public'),('H','HelperA')]),
            **compose_clients(),'All.dfy':'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}


def rule(parameters, calls, pure):
    return dict(variables=list(parameters),calls={name:len(args) for name,args in calls.items()},
                pure={name:len(sig['arguments']) for name,sig in pure.items()},
                parameter_types=parameters,call_types=calls,pure_types=pure)


def rules():
    inverse_pure={name:dict(arguments=args,result=result) for name,args,result in [
        ('K.Put',[MAP,'int','int'],MAP),('K.Exchange',[MAP,'int','int'],MAP),('K.Inverse',[MAP,MAP],'bool')]}
    compose_pure={name:dict(arguments=args,result=MAP) for name,args in [
        ('K.Override',[MAP,MAP]),('K.Restrict',[MAP,SET]),('K.Compose',[MAP,MAP])]}
    domain_calls={'D.OverrideKeys':[MAP,MAP],'D.RestrictKeys':[MAP,SET],'D.ComposeKeys':[MAP,MAP]}
    value_calls={'V.OverrideAt':[MAP,MAP,'int'],'V.RestrictAt':[MAP,SET,'int']}
    return {
      TASKS[0]:{
        'HelperA.dfy':rule({'m':MAP,'p':'int','q':'int'},{'O.PutKeys':[MAP,'int','int'],'O.PutAt':[MAP,'int','int','int'],'O.ExchangeShape':[MAP,'int','int']},inverse_pure),
        'HelperB.dfy':rule({'m':MAP,'n':MAP,'p':'int','q':'int'},{'H.Prove':[MAP,'int','int']},inverse_pure)},
      TASKS[1]:{
        'HelperA.dfy':rule({'f1':MAP,'f2':MAP,'g':MAP},{**domain_calls,**value_calls},compose_pure),
        'HelperB.dfy':rule({'f1':MAP,'f2':MAP,'g':MAP},{**domain_calls,**value_calls,'H.Prove':[MAP,MAP,MAP],'V.ComposeAt':[MAP,MAP,'int'],'A.Equal':[MAP,MAP]},compose_pure)}}


def generate(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    tasks,cases,aliases=[],[],[]
    for tid,variants in zip(TASKS,[INVERSE_VARIANTS,COMPOSE_VARIANTS]):
        template=sources(tid,'empty');seed=sources(tid,'faulty')
        tasks.append(dict(task_id=tid,semantic_instance=tid,family='finite_map',sharing='pipeline',
          depth='two_editable_dependency_stages_not_a_minimality_claim',entry='All.dfy',
          editable_files=['HelperA.dfy','HelperB.dfy'],source_sha256=hashes(template),
          body_boundaries={name:body_boundary(template[name]) for name in ('HelperA.dfy','HelperB.dfy')},
          seed_source_sha256=hashes(seed),repair_seed='faulty',
          faulty_file='HelperB.dfy' if tid==TASKS[0] else 'HelperA.dfy',
          reference_path='fixtures/'+tid+'/reference',template_path='templates/'+tid,
          file_rules=rules()[tid],development_only=True,held_out=False,
          ancestor_group='finite_map_update_restriction_development',
          fixed_architecture=True,dependency_edges=[['HelperB.Prove','HelperA.Prove'],['ClientA.Target','HelperB.Prove'],['ClientB.Target','HelperB.Prove']],
          verification_status='not_run',guard_registry_status='pending separate per-file registration'))
        for variant,(_,_,expected,diagnostic) in variants.items():
            if variant in ('only_a_repair','only_b_repair'):
                canonical=('faulty' if variant=='only_a_repair' and tid==TASKS[0] or
                           variant=='only_b_repair' and tid==TASKS[1] else 'reference')
                assert sources(tid,variant)==sources(tid,canonical)
                aliases.append(dict(logical_case_id=tid+'-'+variant,task_id=tid,variant=variant,
                    evidence_alias_of=tid+'-'+canonical,source_path='fixtures/'+tid+'/'+canonical,
                    expected=expected,source_sha256=hashes(sources(tid,variant)),
                    new_verifier_call=False,independent_observation=False))
                continue
            files=sources(tid,variant);rel='fixtures/'+tid+'/'+variant;folder=root/rel
            folder.mkdir(parents=True,exist_ok=True)
            for name,text in files.items():(folder/name).write_text(text)
            cases.append(dict(case_id=tid+'-'+variant,task_id=tid,variant=variant,path=rel,entry='All.dfy',
              expected=expected,expected_exit={'success':0,'proof_failure':4,'resolution_failure':2}[expected],
              expected_diagnostic=diagnostic,primary_diagnostic=diagnostic,
              source_sha256=hashes(files),body_boundaries={name:body_boundary(files[name]) for name in ('HelperA.dfy','HelperB.dfy')}))
        folder=root/'templates'/tid;folder.mkdir(parents=True,exist_ok=True)
        for name,text in template.items():(folder/name).write_text(text)
    for name,data in [('tasks.json',tasks),('cases.json',cases),('file_rules.json',rules()),('control-aliases.json',aliases)]:
        (root/name).write_text(json.dumps(data,indent=2)+'\n')
    inventory={str(path.relative_to(root)):sha(path.read_bytes()) for top in ('fixtures','templates')
               for path in sorted((root/top).rglob('*.dfy'))}
    for name in ('tasks.json','cases.json','file_rules.json','control-aliases.json'):inventory[name]=sha((root/name).read_bytes())
    (root/'fixture-manifest.json').write_text(json.dumps(dict(sorted(inventory.items())),indent=2)+'\n')
    return dict(tasks=len(tasks),planned_checks=len(cases),source_files=len(inventory)-4,logical_evidence_aliases=len(aliases),
                expected_counts={status:sum(case['expected']==status for case in cases)
                                 for status in ('success','proof_failure','resolution_failure')},
                model_calls=0,verification_status='not_run')


if __name__=='__main__':
    print(json.dumps(generate(ROOT),indent=2))
