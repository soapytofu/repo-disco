"""Identical proof edit policy; map adds structural import information only."""
import re,json
from pathlib import Path
SYSTEM=('Repair the missing proof in Client.dfy using the complete repository source below. '
        'Return only the COMPLETE Client.dfy source, optionally in a dafny code fence. '
        'All provider files are immutable. Preserve every byte outside the final client lemma body, '
        'including its imports, parameters, preconditions, and postcondition. '
        'The proof body may contain only qualified calls Alias.Lemma(arguments); with whitespace. '
        'Arguments may use existing parameter names, integer literals, commas, parentheses, plus, and minus. '
        'Do not add comments, assumptions, attributes, assertions, declarations, or other statements. '
        'Use the existing provider contracts to satisfy required preconditions and prove the target. '
        'The same edit policy and verifier apply to both context conditions.')


def load_task(folder):
    folder=Path(folder)
    sources={p.name:p.read_text() for p in sorted((folder/'fixtures/missing').glob('*.dfy'))}
    mapping=json.loads((folder/'dependency-map.json').read_text())
    return sources,mapping


def validate(candidate,original):
    prefix=original[:-6] if original.endswith('  }\n}\n') else None
    if prefix is None or not candidate.startswith(prefix) or not candidate.endswith('  }\n}\n'):
        raise ValueError('Protected client bytes outside proof body changed')
    body=candidate[len(prefix):-6]
    call=r'[A-Za-z_][A-Za-z_0-9]*\.[A-Za-z_][A-Za-z_0-9]*\s*\([A-Za-z_0-9,()\s+\-]*\)\s*;'
    if not re.fullmatch(r'\s*(?:'+call+r'\s*)*',body):
        raise ValueError('Proof body violates shared lemma-call-only policy')
    return body


def make_prompt(condition,sources,mapping,feedback):
    user='Complete repository source (provider implementations included):\n'
    for name,text in sorted(sources.items()):user+=f'\nFILE {name}\n{text}'
    user+='\nOriginal whole-repository verifier feedback:\n'+feedback
    if condition=='with_map':user+='\n\nStructural dependency map (duplicates source import information; no proof steps):\n'+json.dumps(mapping,sort_keys=True,indent=2)
    elif condition!='full_context':raise ValueError(condition)
    return [dict(role='system',content=SYSTEM),dict(role='user',content=user)]
