"""Bounded method-body policy; this is not the older lemma-repair adapter ABI.

Only registered body spans can change. Parsing is a syntactic/type-role gate;
Dafny still decides assignment coverage, well-formedness and mathematical truth.
"""
from collections import Counter
from pathlib import Path
import hashlib
import importlib.util
import json
import re

VERSION = POLICY_ID = 'internal-contract-method-bodies-v1-development'
ROOT = Path(__file__).resolve().parent
TYPED_SHA256 = 'c1a235b61fad50606a4cc0c54ac315cc7badb296b2a90a11ab7bddb185b73460'
REGISTRY_SHA256 = 'baab39cddd7b46ac4c641abd6c06475c221485ce4c5e88281eb3bab35fba8883'
FILES = ['All.dfy', 'Client.dfy', 'Helper.dfy', 'Kernel.dfy']
EDITABLE_FILES = ['Helper.dfy', 'Client.dfy']
TYPES = {'int', 'bool', 'map<int,int>', 'set<int>'}
BINDING_KEYS = (
    'task_id', 'semantic_instance', 'entry', 'files', 'editable_files',
    'internal_api_version', 'source_sha256', 'template_sha256',
    'body_boundaries', 'public_contract_sha256', 'public_contract_prefix',
    'fixed_helper_prefix', 'fixed_helper_prefix_sha256', 'file_rules',
)
EXTRA_RESERVED = set('''abstract array as by case char class constructor datatype
    export extends extern false fresh greatest H Helper Client Kernel Transfer
    Target int bool is iterator least let modify multiset nat newtype null object
    old older print real refines return seq set static string this trait true
    twostate type unchanged var where yield yields'''.split())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(text):
    return sha(text.encode('utf-8'))


def hashes(files):
    return {name: digest(source) for name, source in sorted(files.items())}


def _inherited():
    path = ROOT / 'inherited' / 'typed_guard.py'
    if sha(path.read_bytes()) != TYPED_SHA256:
        raise ValueError('Inherited typed parser changed')
    spec = importlib.util.spec_from_file_location('method_guard_inherited_types', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inherited = _inherited()
syntax = inherited.syntax
MAX_RESPONSE = syntax.MAX_RESPONSE
MAX_BODY = syntax.MAX_BODY
MAX_TOKENS = syntax.MAX_TOKENS
MAX_STATEMENTS = syntax.MAX_STATEMENTS
MAX_MAP_ENTRIES = 32
unique = syntax.unique
reject_constant = syntax.reject_constant


def validate_rules(rules, filename):
    required = {'variables', 'parameter_types', 'output_types', 'pure',
                'pure_types', 'calls', 'call_types', 'call_returns'}
    if not isinstance(rules, dict) or set(rules) != required:
        raise ValueError('Exact method rule schema required')
    variables = rules['variables']
    if (not isinstance(variables, list) or not variables
            or not all(isinstance(n, str) for n in variables)
            or len(set(variables)) != len(variables)
            or not isinstance(rules['parameter_types'], dict)
            or list(rules['parameter_types']) != variables):
        raise ValueError('Ordered typed input parameters required')
    for field in ('parameter_types', 'output_types'):
        env = rules[field]
        if (not isinstance(env, dict) or not env
                or any(not isinstance(n, str) or not re.fullmatch(r'[a-z][A-Za-z0-9_]*', n)
                       or n in syntax.RESERVED | EXTRA_RESERVED for n in env)
                or any(t not in TYPES for t in env.values())):
            raise ValueError('Typed input/output role environment required')
    if set(rules['parameter_types']) & set(rules['output_types']):
        raise ValueError('Input and output names overlap')
    if len(rules['output_types']) > 2:
        raise ValueError('At most two fixed method outputs')
    for field, typed_field in (('pure', 'pure_types'), ('calls', 'call_types')):
        names, signatures = rules[field], rules[typed_field]
        if not isinstance(names, dict) or not isinstance(signatures, dict) or set(names) != set(signatures):
            raise ValueError('Exact callable signatures required')
        for name, arity in names.items():
            if (not isinstance(name, str) or not re.fullmatch(r'[KH]\.[A-Z][A-Za-z0-9_]*', name)
                    or type(arity) is not int or not 0 <= arity <= 12):
                raise ValueError('Qualified, bounded callable required')
            types = signatures[name]
            if field == 'pure':
                if (not name.startswith('K.') or not isinstance(types, dict)
                        or set(types) != {'arguments', 'result'} or types['result'] not in TYPES):
                    raise ValueError('Registered Kernel pure functions only')
                types = types['arguments']
            if not isinstance(types, list) or len(types) != arity or any(t not in TYPES for t in types):
                raise ValueError('Typed argument signature mismatch')
    if set(rules['calls']) & set(rules['pure']):
        raise ValueError('Pure functions and methods overlap')
    if not isinstance(rules['call_returns'], dict) or set(rules['call_returns']) != set(rules['calls']):
        raise ValueError('Returning method signatures required')
    if any(t not in TYPES for t in rules['call_returns'].values()):
        raise ValueError('Single typed method return required')
    if filename == 'Helper.dfy':
        if rules['calls']:
            raise ValueError('Helper body cannot call methods')
    elif filename == 'Client.dfy':
        if set(rules['calls']) != {'H.Transfer'}:
            raise ValueError('Client may expose only the fixed helper method')
    else:
        raise ValueError('Unknown editable method')
    return rules


def registry():
    raw = (ROOT / 'registry.json').read_bytes()
    if sha(raw) != REGISTRY_SHA256:
        raise ValueError('Pinned method registry changed')
    data = json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)
    if data.get('policy_id') != POLICY_ID or data.get('schema') != 'repodisco-method-body-registry-v1':
        raise ValueError('Method registry identity changed')
    entries = data['tasks']
    if not isinstance(entries, dict) or len(entries) != 2:
        raise ValueError('Exact two registered tasks required')
    for task_id, entry in entries.items():
        task = entry['binding']
        if (set(task) != set(BINDING_KEYS) or task['task_id'] != task_id
                or task['files'] != FILES or task['editable_files'] != EDITABLE_FILES
                or task['entry'] != 'All.dfy' or task['internal_api_version'] != 'new_fixed_before_repair'
                or set(task['file_rules']) != set(EDITABLE_FILES)
                or set(entry['boundaries']) != set(EDITABLE_FILES)
                or set(task['source_sha256']) != set(FILES)
                or task['template_sha256'] != task['source_sha256']):
            raise ValueError('Method registry scope changed')
        for name in EDITABLE_FILES:
            validate_rules(task['file_rules'][name], name)
        helper, client = (task['file_rules'][name] for name in EDITABLE_FILES)
        if (len(helper['output_types']) != 1
                or client['call_types']['H.Transfer'] != [helper['parameter_types'][n] for n in helper['variables']]
                or client['call_returns']['H.Transfer'] != next(iter(helper['output_types'].values()))):
            raise ValueError('Client method signature differs from Helper.Transfer')
    return entries


def task_entry(task):
    if not isinstance(task, dict):
        raise ValueError('Trusted task metadata required')
    entry = registry().get(task.get('task_id'))
    if entry is None:
        raise ValueError('Unknown method task')
    for key in BINDING_KEYS:
        if task.get(key) != entry['binding'][key]:
            raise ValueError('Task binding changed: ' + key)
    if any(key in task for key in ('params', 'calls', 'pure')):
        raise ValueError('Task-wide rules cannot replace per-file rules')
    return entry


def split_seed(source, boundary):
    if not isinstance(source, str):
        raise ValueError('Trusted source must be text')
    raw = source.encode('utf-8')
    start, end = boundary['start'], boundary['end']
    if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(raw):
        raise ValueError('Invalid pinned byte span')
    prefix, body, suffix = raw[:start], raw[start:end], raw[end:]
    if (not prefix.endswith(b'  {\n') or suffix != b'  }\n}\n'
            or sha(prefix) != boundary['prefix_sha256']
            or sha(body) != boundary['body_sha256']
            or sha(suffix) != boundary['suffix_sha256']
            or sha(prefix + b'<BODY>\n' + suffix) != boundary['protected_sha256']):
        raise ValueError('Pinned method body span changed')
    return prefix.decode('utf-8'), body.decode('utf-8'), suffix.decode('utf-8')


def validate_template(seeds, task):
    entry = task_entry(task)
    if (not isinstance(seeds, dict) or set(seeds) != set(FILES)
            or not all(isinstance(v, str) for v in seeds.values())):
        raise ValueError('Exact four-file source template required')
    try:
        if hashes(seeds) != entry['binding']['source_sha256']:
            raise ValueError('Template file or byte drift')
        for name in EDITABLE_FILES:
            split_seed(seeds[name], entry['boundaries'][name])
    except UnicodeError as error:
        raise ValueError('Invalid template UTF-8') from error
    return entry


class Grammar(inherited.Grammar):
    """Add returning calls, assignments and map displays to the pinned AST grammar."""
    def __init__(self, body, rules):
        super().__init__(body, rules)
        self.scopes[0].update(rules['output_types'])

    def declare(self, name):
        if (not re.fullmatch(r'[a-z][A-Za-z0-9_]*', name)
                or name in EXTRA_RESERVED):
            raise ValueError('Reserved or invalid local/binder name')
        super().declare(name)

    def atom(self, depth):
        if self.peek() != 'map' or self.i + 1 >= len(self.tokens) or self.tokens[self.i + 1] != '[':
            return super().atom(depth)
        if depth > 32:
            raise ValueError('Expression nesting')
        self.take('map'); self.take('[')
        pairs = []
        if self.peek() != ']':
            while True:
                key = self.expr(depth + 1); self.take(':='); value = self.expr(depth + 1)
                pairs.append([key, value])
                if len(pairs) > MAX_MAP_ENTRIES:
                    raise ValueError('Map display entry count')
                if self.peek() != ',':
                    break
                self.take(',')
        self.take(']')
        node = ['map_display', pairs]
        count = 0
        while self.peek() in ('[', '.'):
            count += 1
            if count > 32:
                raise ValueError('Postfix nesting')
            if self.peek() == '.':
                self.take('.'); self.take('Keys'); node = ['keys', node]
            else:
                self.take('['); key = self.expr(depth + 1)
                if self.peek() == ':=':
                    self.take(':='); node = ['functional_update', node, key, self.expr(depth + 1)]
                else:
                    node = ['index', node, key]
                self.take(']')
        return node

    def rhs(self):
        if self.i + 2 < len(self.tokens) and self.tokens[self.i + 1] == '.':
            name = self.tokens[self.i] + '.' + self.tokens[self.i + 2]
            if name in self.rules['calls']:
                self.qualified(); args = self.arguments(0)
                if len(args) != self.rules['calls'][name]:
                    raise ValueError('Method argument count')
                return ['method_call', name, args]
        return self.expr()

    def statement(self, depth):
        if depth > 24:
            raise ValueError('Statement nesting')
        self.statements += 1
        if self.statements > MAX_STATEMENTS:
            raise ValueError('Statement count')
        token = self.peek()
        if token == 'if':
            self.take('if'); condition = self.expr(); yes = self.block(depth + 1); no = []
            if self.peek() == 'else':
                self.take('else')
                no = [self.statement(depth + 1)] if self.peek() == 'if' else self.block(depth + 1)
            return ['if_statement', condition, yes, no]
        if token == 'var':
            self.take('var'); name = self.identifier(); self.take(':='); value = self.rhs(); self.take(';')
            self.declare(name)
            return ['local', name, value]
        if token == 'assert':
            self.take('assert'); expression = self.expr(); self.take(';')
            return ['assert', expression]
        name = self.identifier()
        if not self.bound(name) or name in self.rules['parameter_types']:
            raise ValueError('Assignment target must be a return variable or existing local')
        self.take(':='); value = self.rhs(); self.take(';')
        return ['assignment', name, value]


class Types(inherited.Types):
    def expression(self, node, env):
        if node[0] == 'map_display':
            for key, value in node[1]:
                self.require(self.expression(key, env), 'int')
                self.require(self.expression(value, env), 'int')
            return 'map<int,int>'
        return super().expression(node, env)

    def rhs(self, node, env):
        if node[0] == 'method_call':
            self.arguments(node[2], self.rules['call_types'][node[1]], env)
            return self.rules['call_returns'][node[1]]
        return self.expression(node, env)

    def statements(self, nodes, env=None):
        env = dict({**self.rules['parameter_types'], **self.rules['output_types']} if env is None else env)
        for node in nodes:
            kind = node[0]
            if kind == 'local':
                if node[1] in env:
                    raise ValueError('Shadowed typed local')
                env[node[1]] = self.rhs(node[2], env)
            elif kind == 'assignment':
                if node[1] in self.rules['parameter_types'] or node[1] not in env:
                    raise ValueError('Invalid typed assignment role')
                self.require(self.rhs(node[2], env), env[node[1]])
            elif kind == 'assert':
                self.require(self.expression(node[1], env), 'bool')
            elif kind == 'if_statement':
                self.require(self.expression(node[1], env), 'bool')
                self.statements(node[2], env); self.statements(node[3], env)
            else:
                raise ValueError('Statement outside method-body policy')


def call_inventory(tree):
    counts = {'method': Counter(), 'pure': Counter()}
    def walk(node):
        if not isinstance(node, list):
            return
        if node and node[0] in ('method_call', 'pure'):
            counts['method' if node[0] == 'method_call' else 'pure'][node[1]] += 1
        for child in node:
            if isinstance(child, list):
                walk(child)
    walk(tree)
    return {kind: dict(sorted(counter.items())) for kind, counter in counts.items()}


def parse_response(payload, seeds, task):
    """Strict flat JSON only; use the unchanged separate extractor for envelopes."""
    if not isinstance(payload, str):
        raise ValueError('Payload must be text')
    try:
        if len(payload.encode('utf-8')) > MAX_RESPONSE:
            raise ValueError('Response size')
    except UnicodeError as error:
        raise ValueError('Response Unicode') from error
    entry = validate_template(seeds, task)
    try:
        bodies = json.loads(payload, object_pairs_hook=unique, parse_constant=reject_constant)
    except (ValueError, RecursionError) as error:
        raise ValueError('Invalid body JSON') from error
    if (not isinstance(bodies, dict) or set(bodies) != set(EDITABLE_FILES)
            or not all(isinstance(body, str) for body in bodies.values())):
        raise ValueError('Exactly Helper.dfy and Client.dfy body strings required')
    candidate = dict(seeds); decisions = {}
    for name in EDITABLE_FILES:
        rules, body = entry['binding']['file_rules'][name], bodies[name]
        try:
            grammar = Grammar(body, rules); tree = grammar.sequence()
            if grammar.peek() is not None:
                raise ValueError('Trailing body tokens')
            Types(rules).statements(tree)
        except (RecursionError, KeyError) as error:
            raise ValueError('Body outside bounded typed syntax') from error
        prefix, _, suffix = split_seed(seeds[name], entry['boundaries'][name])
        candidate[name] = prefix + body + suffix
        decisions[name] = {
            'template_boundary': entry['boundaries'][name], 'body_sha256': digest(body),
            'rules_sha256': digest(json.dumps(rules, sort_keys=True, separators=(',', ':'))),
            'syntax': tree, 'call_inventory': call_inventory(tree),
            'tokens': len(grammar.tokens), 'statements': grammar.statements,
        }
    return candidate, {
        'version': VERSION, 'policy_id': POLICY_ID, 'registry_sha256': REGISTRY_SHA256,
        'policy_code_sha256': sha((ROOT / 'body_guard.py').read_bytes()),
        'typed_dependency_sha256': TYPED_SHA256, 'syntax_dependency_sha256': inherited.SYNTAX_SHA256,
        'task_id': task['task_id'], 'parent_sha256': entry['binding']['source_sha256'],
        'candidate_sha256': hashes(candidate), 'bodies': decisions,
        'call_inventory_is_syntactic': True, 'helper_call_required': False,
        'semantic_verification_performed': False,
    }
