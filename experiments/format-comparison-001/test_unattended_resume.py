"""Offline safety tests: no SDK imports, credentials, network, or verifier calls."""
import ast
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from types import SimpleNamespace

SOURCE = Path(__file__).with_name('run_comparison_unattended.py').resolve()
TREE = ast.parse(SOURCE.read_text())
FUNCTIONS = ast.Module(body=[n for n in TREE.body if isinstance(n, ast.FunctionDef)], type_ignores=[])


def exercise(count, interrupted=False, error=False):
    with tempfile.TemporaryDirectory() as temp:
        suite = Path(temp)
        run = suite / 'run'
        run.mkdir()
        cases = ['a', 'b', 'c', 'd', 'e']
        baseline = []
        for case in cases:
            folder = suite / 'cases' / case
            folder.mkdir(parents=True)
            (folder / 'broken.dfy').write_text('broken')
            (folder / 'broken-stdout.txt').write_text('error')
            baseline.append(dict(case=case, reference=dict(status=0,outcome='SUCCESS'),broken=dict(status=4)))
        (suite / 'baseline-validation.json').write_text(json.dumps(baseline))
        plan = []
        for repeat in range(5):
            for i, case in enumerate(cases):
                modes = ['diff','full_program'] if (repeat+i)%2==0 else ['full_program','diff']
                plan.extend(dict(case=case,repeat=repeat+1,mode=mode) for mode in modes)
        (run / 'plan.json').write_text(json.dumps(plan))
        (run / 'protocol.json').write_text(json.dumps(dict(max_calls=50,source_revision='same',case_input_hashes={c:hashlib.sha256(b'broken').hexdigest() for c in cases})))
        records = [dict(p,sequence=i+1,outcome='SUCCESS') for i,p in enumerate(plan[:count])]
        current = records.pop() if interrupted else None
        if current:
            (run / f"{count:03d}-{current['case']}-{current['mode']}-r{current['repeat']}").mkdir()
        (run / 'ledger.json').write_text(json.dumps(dict(calls_dispatched=count,max_calls=50,completed=records,current=current)))
        dispatched=[]
        def invoke(messages):
            saved=json.loads((run/'ledger.json').read_text())
            dispatched.append(saved['calls_dispatched'])
            assert saved['current']['sequence']==saved['calls_dispatched']
            if error:
                raise RuntimeError('simulated provider failure')
            return SimpleNamespace(content='invalid patch',usage_metadata={},response_metadata={})
        def patch(*args):
            raise ValueError('simulated patch rejection')
        ns=dict(globals(),__file__=str(SOURCE),ROOT=suite,
                subprocess=SimpleNamespace(check_output=lambda *a,**k:'same'),
                consume_key=lambda p:None,
                ChatBedrockConverse=lambda **k:SimpleNamespace(invoke=invoke),
                Config=lambda **k:None, SystemMessage=lambda **k:k,HumanMessage=lambda **k:k,
                CodeOutputParser=lambda:SimpleNamespace(invoke=lambda r:''),apply_text_diff=patch,
                TEXT_BEFORE_EXAMPLE='',TEXT_DIFF_EXAMPLE='',TEXT_AFTER_EXAMPLE='')
        exec(compile(FUNCTIONS,str(SOURCE),'exec'),ns)
        old=sys.argv
        try:
            sys.argv=['runner','--suite',str(suite),'--resume',str(run),'--max-calls','50']
            ns['main']()
        finally:
            sys.argv=old
        ledger=json.loads((run/'ledger.json').read_text())
        expected=[count+1] if error else list(range(count+1,51))
        assert dispatched==expected,(dispatched,expected)
        assert ledger['calls_dispatched']==(count+1 if error else 50)
        assert ledger['current'] is None
        if interrupted:
            assert ledger['completed'][count-1]['outcome']=='INTERRUPTED_UNKNOWN'

if __name__=='__main__':
    exercise(5)
    exercise(5,interrupted=True)
    exercise(50)
    exercise(5,error=True)
    print('PASS: resume, interrupted-call accounting, exhausted budget, provider-error stop')
