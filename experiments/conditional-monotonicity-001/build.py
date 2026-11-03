"""Deterministic development fixtures for guarded clamp monotonicity; zero model calls."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

KERNEL = '''module Kernel {
  export Public provides Lower, Upper, Clamp
  export Internal reveals Lower, Upper, Clamp
  opaque function Lower(x: int, l: int): int { if x < l then l else x }
  opaque function Upper(x: int, h: int): int { if x > h then h else x }
  opaque function Clamp(x: int, l: int, h: int): int { Upper(Lower(x,l),h) }
}
'''
OPS1 = '''include "Kernel.dfy"
module Ops1 {
  export Hidden provides K
  export Public provides K, Below, Within, Above
  import K = Kernel`Internal
  lemma Below(x: int, l: int, h: int)
    requires l <= h && x < l
    ensures K.Lower(x,l) == l
  { reveal K.Lower(); }
  lemma Within(x: int, l: int, h: int)
    requires l <= x <= h
    ensures K.Lower(x,l) == x
  { reveal K.Lower(); }
  lemma Above(x: int, l: int, h: int)
    requires l <= h && h < x
    ensures K.Lower(x,l) == x
  { reveal K.Lower(); }
}
'''
OPS2 = '''include "Kernel.dfy"
module Ops2 {
  export Hidden provides K
  export Public provides K, Below, Within, Above
  import K = Kernel`Internal
  lemma Below(l: int, h: int)
    requires l <= h
    ensures K.Upper(l,h) == l
  { reveal K.Upper(); }
  lemma Within(x: int, l: int, h: int)
    requires l <= x <= h
    ensures K.Upper(x,h) == x
  { reveal K.Upper(); }
  lemma Above(x: int, h: int)
    requires h < x
    ensures K.Upper(x,h) == h
  { reveal K.Upper(); }
}
'''
API = '''include "Kernel.dfy"
module Api {
  export Shallow provides K, Below, Within, Above
  export Deep provides K, Assemble
  import K = Kernel`Internal
  lemma Below(x: int, l: int, h: int)
    requires l <= h && x < l
    ensures K.Clamp(x,l,h) == l
  { reveal K.Clamp(); reveal K.Lower(); reveal K.Upper(); }
  lemma Within(x: int, l: int, h: int)
    requires l <= x <= h
    ensures K.Clamp(x,l,h) == x
  { reveal K.Clamp(); reveal K.Lower(); reveal K.Upper(); }
  lemma Above(x: int, l: int, h: int)
    requires l <= h && h < x
    ensures K.Clamp(x,l,h) == h
  { reveal K.Clamp(); reveal K.Lower(); reveal K.Upper(); }
  lemma Assemble(x: int, l: int, h: int, lower: int, result: int)
    requires K.Lower(x,l) == lower && K.Upper(lower,h) == result
    ensures K.Clamp(x,l,h) == result
  { reveal K.Clamp(); }
}
'''
SIGNATURE = '''  lemma {:induction false} Prove(x: int, y: int, l: int, h: int)
    requires x <= y && l <= h
    ensures K.Clamp(x,l,h) <= K.Clamp(y,l,h)
'''
PROVIDERS = {'Kernel.dfy': KERNEL, 'Ops1.dfy': OPS1, 'Ops2.dfy': OPS2, 'Api.dfy': API}
VARIANTS = ['reference', 'empty', 'only_first', 'wrong_region', 'boundary', 'missing_stage', 'wrong_upper', 'hidden_shortcut']


def hashes(files): return {name: hashlib.sha256(text.encode()).hexdigest() for name, text in sorted(files.items())}


def observation(variable, depth):
    if depth == 'shallow':
        steps = [f'A.Below({variable},l,h);', f'A.Within({variable},l,h);', f'A.Above({variable},l,h);']
    else:
        steps = [f'O1.Below({variable},l,h); O2.Below(l,h); A.Assemble({variable},l,h,l,l);',
                 f'O1.Within({variable},l,h); O2.Within({variable},l,h); A.Assemble({variable},l,h,{variable},{variable});',
                 f'O1.Above({variable},l,h); O2.Above({variable},h); A.Assemble({variable},l,h,{variable},h);']
    return f'    if {variable} < l {{\n      {steps[0]}\n    }} else if {variable} <= h {{\n      {steps[1]}\n    }} else {{\n      {steps[2]}\n    }}\n'


def proof(depth, variant):
    if variant == 'empty': return ''
    if variant == 'hidden_shortcut':
        return '    A.Assemble(x,l,h,x,x);\n' if depth == 'shallow' else '    A.Below(x,l,h);\n'
    first = observation('x', depth)
    second = observation('y', depth)
    if variant == 'only_first': return first
    if variant == 'wrong_region':
        old = 'A.Below(x,l,h);' if depth == 'shallow' else 'O1.Below(x,l,h);'
        first = first.replace(old, old.replace('Below', 'Above'))
    elif variant == 'boundary': first = first.replace('if x < l', 'if x <= l', 1)
    elif variant == 'missing_stage':
        missing = 'A.Within(x,l,h);' if depth == 'shallow' else 'O1.Within(x,l,h);'
        first = first.replace(missing, '', 1)
    elif variant == 'wrong_upper':
        old, new = (('A.Above(x,l,h);', 'A.Above(x,l,l);') if depth == 'shallow' else
                    ('O2.Above(x,h);', 'O2.Above(x,l);'))
        first = first.replace(old, new, 1)
    elif variant != 'reference': raise ValueError(variant)
    return first + second


def helper(name, depth, body, forward=False):
    if forward:
        return ('include "Kernel.dfy"\ninclude "HelperA.dfy"\nmodule HelperB {\n'
                '  import K = Kernel`Public\n  import H = HelperA\n' + SIGNATURE +
                '  {\n    H.Prove(x,y,l,h);\n  }\n}\n')
    view = 'Public' if depth == 'deep' else 'Hidden'
    api_view = 'Deep' if depth == 'deep' else 'Shallow'
    return ('include "Kernel.dfy"\ninclude "Ops1.dfy"\ninclude "Ops2.dfy"\ninclude "Api.dfy"\n'
            + f'module {name} {{\n  import K = Kernel`Public\n  import A = Api`{api_view}\n'
            + f'  import O1 = Ops1`{view}\n  import O2 = Ops2`{view}\n'
            + SIGNATURE + '  {\n' + body + '  }\n}\n')


def client(letter):
    post = 'K.Clamp(x,l,h) <= K.Clamp(y,l,h)' if letter == 'A' else '0 <= K.Clamp(y,l,h) - K.Clamp(x,l,h)'
    return (f'include "Kernel.dfy"\ninclude "Helper{letter}.dfy"\nmodule Client{letter} {{\n'
            + f'  import K = Kernel`Public\n  import H = Helper{letter}\n'
            + f'  lemma Target(x: int, y: int, l: int, h: int)\n    requires x <= y && l <= h\n    ensures {post}\n'
            + '  { H.Prove(x,y,l,h); }\n}\n')


def sources(depth, sharing, variant):
    body = proof(depth, variant)
    return {**PROVIDERS, 'HelperA.dfy': helper('HelperA', depth, body),
            'HelperB.dfy': helper('HelperB', depth, body, forward=sharing == 'shared'),
            'ClientA.dfy': client('A'), 'ClientB.dfy': client('B'),
            'All.dfy': 'include "ClientA.dfy"\ninclude "ClientB.dfy"\n'}


def build():
    tasks = []; checks = []
    for depth in ('shallow', 'deep'):
        for sharing in ('shared', 'separate'):
            task_id = f'clamp_monotone-{depth}-{sharing}'
            seed = sources(depth, sharing, 'empty')
            tasks.append(dict(task_id=task_id, family='conditional', semantic_instance='clamp_monotone',
                              depth=depth, sharing=sharing, entry='All.dfy', source_sha256=hashes(seed),
                              editable_files=['HelperA.dfy'] if sharing == 'shared' else ['HelperA.dfy', 'HelperB.dfy'],
                              development_only=True, model_calls=0))
            for variant in VARIANTS:
                snapshot = sources(depth, sharing, variant)
                rel = f'fixtures/{task_id}/{variant}'
                folder = ROOT / rel
                folder.mkdir(parents=True, exist_ok=False)
                for name, text in snapshot.items(): (folder / name).write_text(text)
                expected = 'success' if variant == 'reference' else ('resolution_failure' if variant == 'hidden_shortcut' else 'proof_failure')
                checks.append(dict(task_id=task_id, variant=variant, path=rel, expected=expected, source_sha256=hashes(snapshot)))
    for name, data in [('tasks.json', tasks), ('checks.json', checks)]:
        with (ROOT / name).open('x') as handle: handle.write(json.dumps(data, indent=2) + '\n')
    print(json.dumps(dict(tasks=len(tasks), checks=len(checks), source_files=len(checks)*9, model_calls=0)))


if __name__ == '__main__': build()
