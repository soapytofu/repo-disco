"""Shared prompt and protected proof-body policy for the two context conditions."""
import re

PREFIX = '''include "MagnitudeFacts.dfy"

module Client {
  import F = MagnitudeFacts

  lemma ClientNonnegative(x: int)
    ensures F.Magnitude(x) >= 0
  {
'''
SUFFIX = '  }\n}\n'
SYSTEM = ('Complete the missing proof in this two-module Dafny repository. '
          'Return only the COMPLETE Client.dfy source, optionally in one dafny code fence. '
          'Preserve every byte outside the body of ClientNonnegative, including its contract and imports. '
          'The provider is immutable. The allowed proof body is zero or more calls of the form F.Identifier(x); '
          'and/or assert F.Magnitude(x) >= 0; with whitespace. No comments, assumptions, attributes, '
          'new declarations, or other statements. Both conditions use this same edit policy. '
          'Provide your best repair using the information supplied.')
API_CONTEXT = '''Dependency map: Client imports MagnitudeFacts as F.
Exported provider API (provides only; implementation bodies are hidden):
  opaque function Magnitude(x: int): int
    // No postcondition is exported for this function.
  lemma EstablishLowerBound(x: int)
    ensures Magnitude(x) >= 0
'''


def validate(candidate):
    if not candidate.startswith(PREFIX) or not candidate.endswith(SUFFIX):
        raise ValueError('Protected bytes outside the proof body changed')
    body=candidate[len(PREFIX):-len(SUFFIX)]
    statement=r'(?:F\.[A-Za-z_][A-Za-z_0-9]*\s*\(\s*x\s*\)\s*;|assert\s+F\.Magnitude\s*\(\s*x\s*\)\s*>=\s*0\s*;)'
    if not re.fullmatch(r'\s*(?:'+statement+r'\s*)*',body):
        raise ValueError('Body violates the shared proof-statement allowlist')
    return body


def prompt(condition,client,feedback):
    user=f'Editable Client.dfy:\n{client}\nOriginal whole-repository verifier feedback:\n{feedback}'
    if condition=='api_context':user+='\n\n'+API_CONTEXT
    elif condition!='local_only':raise ValueError(condition)
    return [dict(role='system',content=SYSTEM),dict(role='user',content=user)]
