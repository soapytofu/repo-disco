"""Deliberately narrow edit policy for this arithmetic fixture, not a Dafny parser."""
import re


def validate_candidate(candidate):
    pattern = (r'\s*module\s+Arithmetic\s*\{\s*'
               r'method\s+Increment\s*\(\s*x\s*:\s*int\s*\)\s*'
               r'returns\s*\(\s*y\s*:\s*int\s*\)\s*'
               r'ensures\s+y\s*==\s*x\s*\+\s*1\s*\{\s*'
               r'y\s*:=\s*(?P<expression>[x0-9+*/%()\s-]+);\s*\}\s*\}\s*')
    match = re.fullmatch(pattern, candidate)
    if not match or any(marker in match['expression'] for marker in ('//', '/*', '*/')):
        raise ValueError('Edit rejected: preserve the exact module, method signature, and contract; body must be one arithmetic assignment to y using x and integer literals. No extra declarations, statements, comments, or attributes.')
    return True
