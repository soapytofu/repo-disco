"""Offset-preserving declaration scanner copied from the published preparation.

Only lex, line_number and declaration_headers are included; no prompt builder,
provider transport or source mutation code is imported. See copy-provenance.json.
"""
import re
from review_native import require

DECLARATIONS = {"function", "method", "lemma", "predicate", "constructor", "iterator"}
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")


def lex(text):
    """Offset-preserving source scan for declaration and dependency inventories."""
    tokens = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
        elif text.startswith("//", i):
            stop = text.find("\n", i)
            i = len(text) if stop < 0 else stop + 1
        elif text.startswith("/*", i):
            depth = 1
            i += 2
            while i < len(text) and depth:
                if text.startswith("/*", i): depth += 1; i += 2
                elif text.startswith("*/", i): depth -= 1; i += 2
                else: i += 1
            require(depth == 0, "Unclosed source comment")
        elif text.startswith('@"', i):
            start = i
            i += 2
            while i < len(text):
                if text.startswith('""', i): i += 2
                elif text[i] == '"': i += 1; break
                else: i += 1
            else: raise ValueError("Unclosed verbatim source string")
            tokens.append(("literal", text[start:i], start, i))
        elif text[i] in {'"', "'"}:
            start, quote = i, text[i]
            i += 1
            while i < len(text):
                if text[i] == "\\": i += 2
                elif text[i] == quote: i += 1; break
                else: i += 1
            else: raise ValueError("Unclosed source literal")
            tokens.append(("literal", text[start:i], start, i))
        else:
            match = IDENTIFIER.match(text, i)
            start = i
            if match:
                i += len(match.group())
                tokens.append(("identifier", match.group(), start, i))
            else:
                i += 1
                tokens.append(("punctuation", text[start:i], start, i))
    return tokens


def line_number(text, position):
    return text.count("\n", 0, position) + 1


def declaration_headers(text):
    tokens = lex(text)
    result = []
    for index, token in enumerate(tokens):
        if token[0] != "identifier" or token[1] not in DECLARATIONS:
            continue
        if token[1] == "method" and index and tokens[index-1][1] in {"function", "predicate"}:
            continue
        cursor = index + 1
        if cursor < len(tokens) and tokens[cursor][1] == "method":
            cursor += 1
        attributes = []
        while cursor + 1 < len(tokens) and tokens[cursor][1] == "{" and tokens[cursor+1][1] == ":":
            start = cursor
            cursor += 2
            while cursor < len(tokens) and tokens[cursor][1] != "}": cursor += 1
            require(cursor < len(tokens), "Unclosed declaration attribute")
            attributes.append(text[tokens[start][2]:tokens[cursor][3]])
            cursor += 1
        if cursor < len(tokens) and tokens[cursor][0] == "identifier":
            result.append(dict(kind=token[1], name=tokens[cursor][1], start=token[2],
                               name_start=tokens[cursor][2], name_end=tokens[cursor][3],
                               line=line_number(text, token[2]), attributes=attributes))
    return result
