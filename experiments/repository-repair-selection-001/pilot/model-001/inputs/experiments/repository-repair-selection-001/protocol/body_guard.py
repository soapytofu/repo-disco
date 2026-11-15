"""Prospective, per-file proof-body policy for a fixed HelperA -> HelperB pipeline.

The inherited VERSION is the existing repair adapter ABI, not this policy's
identity. POLICY_ID and registry/source hashes identify this new policy. The
frozen parser, envelope and repair adapter are copied without modification.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

VERSION = 'repair-diversity-bodies-v1-development'
POLICY_ID = 'repository-repair-selection-bodies-v1-development'
ROOT = Path(__file__).resolve().parent
SYNTAX_SHA256 = '877f898f695ac88b0af1c377d5a1859de544dbb7cc7a1585e6b09d2eecd02fe9'
# Draft value is populated by build_registry.py after fixture construction.
REGISTRY_SHA256 = '7810e1fc3e7ac0558106ae5ab3f3a42253b6533acf301d3059615518e2f04c98'
EDITABLE_FILES = ['HelperA.dfy', 'HelperB.dfy']
TYPES = {'int', 'bool', 'map<int,int>', 'set<int>'}


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def hashes(files):
    return {name: digest(source) for name, source in sorted(files.items())}


def _syntax():
    path = ROOT / 'syntax_guard.py'
    if hashlib.sha256(path.read_bytes()).hexdigest() != SYNTAX_SHA256:
        raise ValueError('Inherited syntax dependency changed')
    spec = importlib.util.spec_from_file_location('repository_selection_syntax', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


syntax = _syntax()
MAX_RESPONSE = syntax.MAX_RESPONSE
MAX_BODY = syntax.MAX_BODY
MAX_TOKENS = syntax.MAX_TOKENS
MAX_STATEMENTS = syntax.MAX_STATEMENTS
TOKEN = syntax.TOKEN
PRECEDENCE = syntax.PRECEDENCE
split_seed = syntax.split_seed
unique = syntax.unique
reject_constant = syntax.reject_constant


def validate_rules(rules, filename):
    required = {'variables', 'calls', 'pure', 'parameter_types', 'call_types', 'pure_types'}
    if not isinstance(rules, dict) or set(rules) != required:
        raise ValueError('Exact per-file rule schema required')
    variables = rules['variables']
    if (not isinstance(variables, list) or len(variables) != len(set(variables))
            or not all(isinstance(name, str) and re.fullmatch(r'[a-z][a-zA-Z0-9_]*', name) for name in variables)
            or not isinstance(rules['parameter_types'], dict)
            or set(variables) != set(rules['parameter_types'])
            or any(t not in TYPES for t in rules['parameter_types'].values())):
        raise ValueError('Typed parameter environment required')
    for key, types_key in (('calls', 'call_types'), ('pure', 'pure_types')):
        names, typed = rules[key], rules[types_key]
        if not isinstance(names, dict) or not isinstance(typed, dict) or set(names) != set(typed):
            raise ValueError('Typed callable environment required')
        for name, arity in names.items():
            if (not isinstance(name, str) or not re.fullmatch(r'[A-Z][A-Za-z0-9_]*\.[A-Z][A-Za-z0-9_]*', name)
                    or type(arity) is not int or not 0 <= arity <= 12):
                raise ValueError('Qualified callable signature required')
            signature = typed[name]
            if key == 'pure':
                if not isinstance(signature, dict) or set(signature) != {'arguments', 'result'} or signature['result'] not in TYPES:
                    raise ValueError('Typed pure result required')
                signature = signature['arguments']
            if not isinstance(signature, list) or len(signature) != arity or any(t not in TYPES for t in signature):
                raise ValueError('Typed callable arity mismatch')
    if set(rules['calls']) & set(rules['pure']):
        raise ValueError('Lemma and pure environments overlap')
    aliases = {name.split('.')[0] for name in [*rules['calls'], *rules['pure']]}
    if aliases - {'K', 'O', 'A', 'D', 'V', 'H'}:
        raise ValueError('Unreviewed provider alias')
    if any(name.endswith('.Prove') and name != 'H.Prove' for name in [*rules['calls'], *rules['pure']]):
        raise ValueError('Unreviewed helper call')
    if any(name.startswith('H.') and (name != 'H.Prove' or key != 'calls')
           for key in ('calls', 'pure') for name in rules[key]):
        raise ValueError('Helper alias only permits its lemma')
    if filename == 'HelperA.dfy' and 'H' in aliases:
        raise ValueError('HelperA cannot depend on another helper')
    if filename == 'HelperB.dfy' and 'H.Prove' not in rules['calls']:
        raise ValueError('HelperB must expose the pinned HelperA contract')
    return rules


def registry():
    raw = (ROOT / 'registry.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != REGISTRY_SHA256:
        raise ValueError('Pinned registry changed')
    data = json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)
    if data.get('policy_id') != POLICY_ID or data.get('adapter_abi') != VERSION:
        raise ValueError('Registry policy identity changed')
    entries = data['tasks']
    for task_id, entry in entries.items():
        if (entry['task_id'] != task_id or entry['editable_files'] != EDITABLE_FILES
                or set(entry['file_rules']) != set(EDITABLE_FILES)
                or set(entry['body_boundaries']) != set(EDITABLE_FILES)
                or not set(EDITABLE_FILES).issubset(entry['source_sha256'])
                or entry['entry'] != 'All.dfy'):
            raise ValueError('Unsupported pipeline edit scope')
        for filename in EDITABLE_FILES:
            validate_rules(entry['file_rules'][filename], filename)
        a_rules = entry['file_rules']['HelperA.dfy']
        if entry['file_rules']['HelperB.dfy']['call_types']['H.Prove'] != [a_rules['parameter_types'][name] for name in a_rules['variables']]:
            raise ValueError('HelperB call does not match HelperA parameter signature')
    return entries


def task_entry(task):
    if not isinstance(task, dict):
        raise ValueError('Trusted task object required')
    entry = registry().get(task.get('task_id'))
    if entry is None:
        raise ValueError('Unsupported task identifier')
    for key in ('task_id', 'semantic_instance', 'sharing', 'depth', 'entry', 'editable_files', 'source_sha256', 'file_rules'):
        if task.get(key) != entry[key]:
            raise ValueError('Task binding changed: ' + key)
    if any(key in task for key in ('params', 'calls', 'pure')):
        raise ValueError('Task-wide rules cannot replace per-file rules')
    if 'body_boundaries' in task:
        if set(task['body_boundaries']) != set(EDITABLE_FILES):
            raise ValueError('Task boundary file set')
        for name, boundary in task['body_boundaries'].items():
            saved = entry['body_boundaries'][name]
            if (boundary.get('start') != saved['start_utf8_byte'] or boundary.get('end') != saved['end_utf8_byte']
                    or boundary.get('protected_sha256') != saved['protected_sha256']):
                raise ValueError('Task boundary changed')
    return entry


class Grammar(syntax.Grammar):
    """The inherited statement/expression parser with a per-file environment."""
    def __init__(self, body, rules):
        if not isinstance(body, str):
            raise ValueError('Body type')
        try:
            encoded = body.encode('utf-8')
        except UnicodeError as error:
            raise ValueError('Unpaired body surrogate') from error
        if len(encoded) > MAX_BODY:
            raise ValueError('Body size')
        self.tokens = []
        position = 0
        while position < len(body):
            if not body[position:].strip():
                break
            match = TOKEN.match(body, position)
            if not match:
                raise ValueError('Forbidden token, comment, string, or attribute')
            self.tokens.append(match[1])
            position = match.end()
            if len(self.tokens) > MAX_TOKENS:
                raise ValueError('Token count')
        self.i = 0
        self.statements = 0
        self.rules = rules
        self.scopes = [set(rules['variables'])]


class Types:
    """Small signature checker; Dafny still owns complete typing and proof checks.

    As in the inherited syntax tree, grouping parentheses are not retained.
    Comparison chains are checked by adjacent operand types. This can admit an
    invalid parenthesized comparison that Dafny subsequently rejects; it cannot
    add a callable, alter a protected byte, or bypass semantic verification.
    """
    COMPARISONS = {'==', '!=', '<', '<=', '>', '>='}

    def __init__(self, rules):
        self.rules = rules

    def require(self, actual, expected):
        if actual != expected:
            raise ValueError('Expression type differs from pinned signature')

    def expression(self, node, env):
        kind = node[0]
        if kind in ('integer', 'boolean'):
            return 'int' if kind == 'integer' else 'bool'
        if kind == 'variable':
            return env[node[1]]
        if kind == 'unary':
            want = 'bool' if node[1] == '!' else 'int'
            self.require(self.expression(node[2], env), want)
            return want
        if kind == 'if_expression':
            self.require(self.expression(node[1], env), 'bool')
            yes, no = self.expression(node[2], env), self.expression(node[3], env)
            self.require(yes, no)
            return yes
        if kind == 'pure':
            signature = self.rules['pure_types'][node[1]]
            self.arguments(node[2], signature['arguments'], env)
            return signature['result']
        if kind == 'set_literal':
            for child in node[1]:
                self.require(self.expression(child, env), 'int')
            return 'set<int>'
        if kind == 'map_comprehension':
            scope = dict(env, **{node[1]: 'int'})
            self.require(self.expression(node[2], scope), 'bool')
            self.require(self.expression(node[3], scope), 'int')
            return 'map<int,int>'
        if kind == 'keys':
            self.require(self.expression(node[1], env), 'map<int,int>')
            return 'set<int>'
        if kind == 'index':
            self.require(self.expression(node[1], env), 'map<int,int>')
            self.require(self.expression(node[2], env), 'int')
            return 'int'
        if kind == 'functional_update':
            self.require(self.expression(node[1], env), 'map<int,int>')
            self.require(self.expression(node[2], env), 'int')
            self.require(self.expression(node[3], env), 'int')
            return 'map<int,int>'
        if kind == 'cardinality':
            if self.expression(node[1], env) not in {'map<int,int>', 'set<int>'}:
                raise ValueError('Finite map/set cardinality required')
            return 'int'
        if kind == 'forall_expression':
            scope = dict(env, **{node[1]: 'int'})
            if node[2] is not None:
                self.require(self.expression(node[2], scope), 'bool')
            self.require(self.expression(node[3], scope), 'bool')
            return 'bool'
        if kind == 'infix_syntax':
            operator, left, right = node[1:]
            if operator in self.COMPARISONS:
                operands, operators = self.comparison_chain(node)
                types = [self.expression(child, env) for child in operands]
                for i, op in enumerate(operators):
                    self.require(types[i], types[i + 1])
                    if op not in {'==', '!='} and types[i] not in {'int', 'set<int>'}:
                        raise ValueError('Ordering requires integers or finite integer sets')
                return 'bool'
            a, b = self.expression(left, env), self.expression(right, env)
            if operator in {'&&', '||', '==>'}:
                self.require(a, 'bool'); self.require(b, 'bool')
                return 'bool'
            if operator in {'in', '!in'}:
                self.require(a, 'int')
                if b not in {'map<int,int>', 'set<int>'}:
                    raise ValueError('Integer membership requires map or set')
                return 'bool'
            if operator in {'+', '-'} and a == b and a in {'int', 'set<int>'}:
                return a
            raise ValueError('Unsupported typed operator')
        raise ValueError('Expression outside this task type policy')

    def comparison_chain(self, node):
        if node[0] == 'infix_syntax' and node[1] in self.COMPARISONS:
            operands, operators = self.comparison_chain(node[2])
            return operands + [node[3]], operators + [node[1]]
        return [node], []

    def arguments(self, args, expected, env):
        if len(args) != len(expected):
            raise ValueError('Typed argument arity')
        for arg, want in zip(args, expected):
            self.require(self.expression(arg, env), want)

    def statements(self, nodes, env=None):
        env = dict(self.rules['parameter_types'] if env is None else env)
        for node in nodes:
            kind = node[0]
            if kind == 'local':
                env[node[1]] = self.expression(node[2], env)
            elif kind == 'assert':
                self.require(self.expression(node[1], env), 'bool')
            elif kind == 'call':
                self.arguments(node[2], self.rules['call_types'][node[1]], env)
            elif kind == 'if_statement':
                self.require(self.expression(node[1], env), 'bool')
                self.statements(node[2], env); self.statements(node[3], env)
            elif kind == 'forall_proof':
                scope = dict(env, **{node[1]: 'int'})
                self.require(self.expression(node[2], scope), 'bool')
                self.require(self.expression(node[3], scope), 'bool')
                self.statements(node[4], scope)
            else:
                raise ValueError('Statement outside this task policy')


def validate_template(seeds, task):
    entry = task_entry(task)
    if not isinstance(seeds, dict) or not all(isinstance(n, str) and isinstance(s, str) for n, s in seeds.items()):
        raise ValueError('Trusted source types')
    try:
        actual = hashes(seeds)
    except UnicodeError as error:
        raise ValueError('Template Unicode') from error
    if actual != entry['source_sha256']:
        raise ValueError('Seed byte/file drift')
    for name, boundary in entry['body_boundaries'].items():
        prefix, suffix = split_seed(seeds[name])
        if (len(prefix.encode()) != boundary['start_utf8_byte']
                or boundary['end_utf8_byte'] != boundary['start_utf8_byte']
                or digest(prefix) != boundary['prefix_sha256'] or digest(suffix) != boundary['suffix_sha256']
                or digest(prefix + '<EDITABLE_BODY>\n' + suffix) != boundary['protected_sha256']):
            raise ValueError('Pinned body boundary drift')
    return entry


def parse_response(payload, seeds, task):
    if not isinstance(payload, str):
        raise ValueError('Payload type')
    try:
        encoded = payload.encode('utf-8')
    except UnicodeError as error:
        raise ValueError('Payload Unicode') from error
    if len(encoded) > MAX_RESPONSE:
        raise ValueError('Payload size')
    entry = validate_template(seeds, task)
    try:
        bodies = json.loads(payload, object_pairs_hook=unique, parse_constant=reject_constant)
    except (ValueError, RecursionError) as error:
        raise ValueError('Invalid body JSON') from error
    if not isinstance(bodies, dict) or set(bodies) != set(EDITABLE_FILES) or not all(isinstance(b, str) for b in bodies.values()):
        raise ValueError('Exact eligible filename/body-string set required')
    candidate = dict(seeds)
    decisions = {}
    for name in EDITABLE_FILES:
        body, rules = bodies[name], entry['file_rules'][name]
        grammar = Grammar(body, rules)
        tree = grammar.sequence()
        if grammar.peek() is not None:
            raise ValueError('Trailing body tokens')
        Types(rules).statements(tree)
        prefix, suffix = split_seed(seeds[name])
        candidate[name] = prefix + body + suffix
        decisions[name] = dict(**entry['body_boundaries'][name], body_sha256=digest(body),
            rules_sha256=digest(json.dumps(rules, sort_keys=True, separators=(',', ':'))),
            syntax=tree, tokens=len(grammar.tokens), statements=grammar.statements)
    return candidate, dict(version=VERSION, policy_id=POLICY_ID, registry_sha256=REGISTRY_SHA256,
        syntax_sha256=SYNTAX_SHA256, task_id=entry['task_id'], parent_sha256=entry['source_sha256'],
        candidate_sha256=hashes(candidate), bodies=decisions, semantic_verification_performed=False)
