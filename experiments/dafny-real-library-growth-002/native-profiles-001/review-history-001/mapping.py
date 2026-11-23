"""Reviewed declaration/unit ownership adapted from prior native profile builders.

This maps the pinned module families, not arbitrary Dafny programs. New CSV
labels must match real declarations. Unlogged definitions are never passes.
"""
from collections import Counter
import re

import review_native as native
import source_scan as scanner


MODULE_FILES = {
    'Std.BoundedInts': 'Source/DafnyStandardLibraries/src/Std/BoundedInts.dfy',
    'Std.Wrappers': 'Source/DafnyStandardLibraries/src/Std/Wrappers.dfy',
    'Std.DynamicArray': 'Source/DafnyStandardLibraries/src/Std/DynamicArray.dfy',
    'RepoDiscoStdAppend': 'growth/AppendAll.dfy',
    'RepoDiscoStableFilter': 'growth/StableFilterBelow.dfy',
    'RepoDiscoSplice': 'growth/SpliceRange.dfy',
    'StandardLibrary.UInt': 'StandardLibrary/src/UInt.dfy',
    'BoundedInts': 'libraries/src/BoundedInts.dfy',
    'Wrappers': 'libraries/src/Wrappers.dfy',
    'RepoDiscoU16Frame': 'StandardLibrary/src/RepoDiscoU16Frame.dfy',
    'RepoDiscoFramePair': 'StandardLibrary/src/RepoDiscoFramePair.dfy',
    'RepoDiscoFrameBatch': 'StandardLibrary/src/RepoDiscoFrameBatch.dfy',
    'RepoDiscoTaggedFramePair': 'StandardLibrary/src/RepoDiscoTaggedFramePair.dfy',
}


def module_name(file, text):
    matches = re.findall(r'^module\s+(?:\{:[^\n]*?\}\s*)*([A-Za-z_][A-Za-z0-9_.]*)\s*\{', text, re.M)
    native.require(len(matches) == 1 and MODULE_FILES.get(matches[0]) == file,
                   'Module/source ownership is outside reviewed scope: ' + file)
    return matches[0]


def stdlib_declarations(sources):
    """Prior indentation-aware mapping, with explicit class/datatype/field rows."""
    found = []
    for file, raw in sorted(sources.items()):
        text = raw.decode()
        module = module_name(file, text)
        container = None
        for number, line in enumerate(text.splitlines(), 1):
            named_container = re.match(r'^  (class|datatype) ([A-Za-z_][A-Za-z0-9_\']*)', line)
            if named_container:
                kind, container = named_container.groups()
                found.append(dict(name=module + '.' + container, kind=kind, file=file, line=number,
                    source_line=line, source_sha256=native.sha(raw)))
            if line == '  }':
                container = None
            declaration = re.match(r'^(  |    )(?:(?:ghost|static) )?(const|newtype|type|function|predicate|method|lemma)\s+([A-Za-z_][A-Za-z0-9_\'?]*)', line)
            constructor = re.match(r'^    constructor\(', line)
            field = re.match(r'^    (?:ghost )?var\s+([A-Za-z_][A-Za-z0-9_\']*)\s*:', line)
            if declaration:
                indent, kind, name = declaration.groups()
                owner = module + ('.' + container if indent == '    ' and container else '')
            elif constructor:
                native.require(container is not None, 'Constructor has no reviewed owner')
                owner, kind, name = module + '.' + container, 'constructor', '_ctor'
            elif field and container:
                owner, kind, name = module + '.' + container, 'field', field.group(1)
            else:
                continue
            found.append(dict(name=owner + '.' + name, kind=kind, file=file, line=number,
                              source_line=line, source_sha256=native.sha(raw)))
    return found


def aws_declarations(sources):
    """Prior token scanner retains legacy callable syntax and attributes."""
    found = []
    for file, raw in sorted(sources.items()):
        text = raw.decode()
        module = module_name(file, text)
        by_line, container = {}, None
        for number, line in enumerate(text.splitlines(), 1):
            datatype = re.match(r'^  datatype\s+([A-Za-z_][A-Za-z0-9_\']*)', line)
            if datatype:
                container = datatype.group(1)
            by_line[number] = container
            if line == '  }':
                container = None
            simple = re.match(r'^  (const|newtype|type|datatype)\s+([A-Za-z_][A-Za-z0-9_\']*)', line)
            if simple:
                kind, name = simple.groups()
                found.append(dict(name=module + '.' + name, kind=kind, file=file, line=number,
                                  source_line=line, source_sha256=native.sha(raw)))
        for declaration in scanner.declaration_headers(text):
            number = declaration['line']
            line = text.splitlines()[number - 1]
            indent = len(line) - len(line.lstrip())
            native.require(indent in {2, 4}, 'Unknown declaration indentation requires review')
            owner = module
            if indent == 4:
                native.require(by_line[number] is not None, 'Nested callable has no reviewed datatype owner')
                owner += '.' + by_line[number]
            found.append(dict(name=owner + '.' + declaration['name'], kind=declaration['kind'],
                file=file, line=number, source_line=line, source_sha256=native.sha(raw),
                attributes=declaration['attributes']))
    return found


def inventory(family, sources, raw, inherited):
    native.require(family in {'stdlib', 'aws'}, 'Unknown reviewed family')
    native_rows = native._csv(inherited, raw)
    native.require(native_rows, 'No actual native units')
    native.require(all(row['outcome'] == 'Passed' for row in native_rows),
                   'Failed rows cannot define a positive profile')
    definitions = stdlib_declarations(sources) if family == 'stdlib' else aws_declarations(sources)
    native.require(len({row['name'] for row in definitions}) == len(definitions),
                   'Duplicate declaration identity')
    by_name = {row['name']: row for row in definitions}
    rows = []
    for row in native_rows:
        label = row['name']
        owners = [module for module in MODULE_FILES if label.startswith(module + '.')]
        native.require(len(owners) == 1, 'Ambiguous native module ownership: ' + label)
        file = MODULE_FILES[owners[0]]
        declaration = label.split(' (')[0]
        native.require(file in sources and declaration in by_name and by_name[declaration]['file'] == file,
                       'Native label lacks an exact reviewed source declaration: ' + label)
        rows.append(dict(label=label, file=file, csv=row['csv'], row=row['row'], fields=row['fields']))
    counts = Counter(row['label'] for row in rows)
    native.require(all(n == 1 for n in counts.values()), 'Duplicate actual native unit')
    native.require({row['file'] for row in rows} == set(sources),
                   'A source file lacks actual logged obligations')
    unlogged = []
    for definition in definitions:
        definition['logged_units'] = [row['label'] for row in rows
                                     if row['label'].split(' (')[0] == definition['name']]
        definition['has_logged_units'] = bool(definition['logged_units'])
        if not definition['logged_units']:
            unlogged.append(dict(name=definition['name'], file=definition['file'],
                source_sha256=definition['source_sha256'], counted_as_pass=False,
                kind=definition['kind'], line=definition['line'], source_line=definition['source_line'],
                reason='No named CSV unit in this exact complete-scope observation; explicitly not a logged proof pass.'))
    return rows, sorted(definitions, key=lambda d: (d['file'], d['line'], d['name'])), unlogged, dict(sorted(counts.items()))
