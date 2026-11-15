"""Reviewed session integration. Importing this file never reads a key or sends.

Only main()/execute_session() can enter the live path. Tests inject a fake key
consumer, transport, environment probe and verifier. Admission files are data;
only the fixed repair-v1 handler below can execute them.
"""
import argparse
import hashlib
import importlib.util
from importlib.metadata import version
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import socket
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
WINDOW_ID = 'repodisco-research-20261114'
DEADLINE = 1794801912.0
SESSION_NAME = 'session-001'
HANDLER_ID = 'repair-v1'
ENVIRONMENT = dict(dafny='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2',
                   z3='Z3 version 4.12.1 - 64 bit', boto3='1.43.115', botocore='1.43.115')
for folder in (ROOT, ROOT.parent/'runtime', ROOT.parent/'session-runtime-002'):
    sys.path.insert(0, str(folder))
import window_budget as w
import coordinator as coordination

def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

batch = _module('window_session_run_batch', ROOT/'run_batch.py')


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    raw = path.read_bytes()
    require(len(raw) <= 16*1024*1024, 'Metadata too large')
    def reject(value):raise ValueError('Nonstandard JSON')
    return json.loads(raw, object_pairs_hook=w.unique_pairs, parse_constant=reject)


def relative(value):
    require(isinstance(value, str) and value and '\\' not in value, 'Relative POSIX path required')
    p=PurePosixPath(value)
    require(not p.is_absolute() and all(x not in ('', '.', '..') for x in value.split('/')), 'Unsafe relative path')
    return p


def regular(root, name):
    path=root
    for component in relative(name).parts:
        path=path/component
        require(not path.is_symlink(), 'Symlink forbidden')
    require(path.is_file(), 'Regular file required')
    return path


def inventory(root):
    require(root.is_dir() and not root.is_symlink(), 'Regular directory required')
    result={}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink() and (path.is_file() or path.is_dir()), 'Nonregular artifact')
        if path.is_file():result[path.relative_to(root).as_posix()]=sha(path)
    return result


def model_settings():
    return dict(model_id=batch.ALLOWED_MODEL, region=batch.ALLOWED_REGION,
                inference_config=batch.ALLOWED_INFERENCE.copy())


def validate_execution(work_root, scope_sha256, execution_freeze_sha256):
    work_root=Path(work_root).resolve(strict=True)
    require(ROOT.parent.resolve()==work_root, 'Execution root differs from this fixed runner')
    scope_path=regular(work_root,'scope.json')
    require(sha(scope_path)==scope_sha256, 'Scope hash differs')
    scope=w._scope(read_json(scope_path))
    require(scope['window_id']==WINDOW_ID and scope['deadline_epoch']==DEADLINE and scope['max_calls']==128,
            'Window identity, deadline or aggregate cap differs')
    require(scope.get('automatic_resume') is False and scope.get('automatic_retries') is False,
            'No resume/retry scope required')
    require(Path(scope['central_ledger_path']).is_absolute() and Path(scope['central_ledger_path'])==work_root/'budget',
            'Mandatory canonical budget path differs; no fallback')
    freeze_path=regular(ROOT,'runtime-freeze.json')
    require(sha(freeze_path)==execution_freeze_sha256,'Execution freeze hash differs')
    freeze=read_json(freeze_path)
    require(freeze['schema']=='repodisco-session-execution-v1' and freeze['scope_sha256']==scope_sha256
            and freeze['window_id']==WINDOW_ID and freeze['deadline_epoch']==DEADLINE,
            'Execution freeze scope differs')
    require(freeze['automatic_retries'] is False and freeze['sdk_total_max_attempts']==1
            and type(freeze['sdk_total_max_attempts']) is int and freeze['handler_id']==HANDLER_ID,
            'Execution policy differs')
    require(freeze['model_settings']==model_settings() and freeze['environment_versions']==ENVIRONMENT,
            'Pinned model or toolchain differs')
    pins=freeze['runtime_sha256']
    require(isinstance(pins,dict) and pins and inventory(ROOT)==dict(pins,**{'runtime-freeze.json':execution_freeze_sha256}),
            'Execution code inventory/hash differs')
    dependencies=freeze['dependencies_sha256']
    required={'../runtime/window_budget.py','../runtime/manifest.json',
              '../session-runtime-002/coordinator.py','../session-runtime-002/manifest.json'}
    require(isinstance(dependencies,dict) and required<=set(dependencies), 'Pinned gate/session dependencies required')
    for path,h in dependencies.items():
        require(path.startswith(('../runtime/','../session-runtime-002/')), 'Unapproved runtime dependency')
        remainder=path.removeprefix('../')
        require(sha(regular(work_root,remainder))==h,'Runtime dependency changed')
    return scope,freeze


def live_environment():
    require(os.environ.get('SLURM_JOB_ID','').isdigit() and 'login' not in socket.gethostname().lower(),
            'Slurm non-login compute node required')
    require(os.environ.get('SLURM_JOB_PARTITION') in ('test','shared','sapphire'), 'Reviewed partition required')
    require(os.environ.get('SLURM_RESTART_COUNT','0')=='0', 'Requeued execution forbidden')
    versions={name:version(name) for name in ('boto3','botocore')}
    for tool in ('dafny','z3'):
        command=[tool,'--version']
        versions[tool]=subprocess.run(command,capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    require(versions==ENVIRONMENT,'Installed toolchain/SDK differs from pinned versions')
    return dict(job_id=os.environ['SLURM_JOB_ID'],partition=os.environ['SLURM_JOB_PARTITION'],
                host=socket.gethostname(),python=sys.version,versions=versions,
                requeue=False,model_connectivity_calls=0)


class ManagedTransport:
    def __init__(self, settings, *, client_factory=None, config_factory=None):
        self.client=None
        self.invoke=None
        def capture(*args,**kwargs):
            require(self.client is None,'Only one provider client may be created')
            if client_factory is None:
                import boto3
                self.client=boto3.client(*args,**kwargs)
            else:self.client=client_factory(*args,**kwargs)
            return self.client
        self.invoke=batch.bedrock_transport(settings,client_factory=capture,config_factory=config_factory)

    def __call__(self,payload):
        require(self.invoke is not None,'Transport disposed')
        return self.invoke(payload)

    def close(self):
        client=self.client
        self.client=None
        self.invoke=None
        if client is not None:client.close()


class RepairIntegration:
    """Fixed callback registry; never imports an admission-specified handler."""
    def __init__(self,work_root,scope,freeze,environment,*,verifier=None,clock=time.time):
        self.root=Path(work_root)
        self.scope=w.cloned(scope)
        self.freeze=w.cloned(freeze)
        self.execution_freeze_sha256=sha(ROOT/'runtime-freeze.json')
        self.environment=w.cloned(environment)
        self.verifier=verifier or batch.verify_logged
        self.clock=clock
        self.admissions={}

    @property
    def code_pins(self):
        return w.cloned(self.freeze['runtime_sha256'])

    def check_admissions(self):
        root=self.root/'admissions'
        require(root.is_dir() and not root.is_symlink(),'Atomic admissions directory required')
        names=[]
        for path in root.iterdir():
            require(path.is_file() and not path.is_symlink(),'Admission must be a regular data file')
            if re.fullmatch(r'[0-9]{6}\.json',path.name):names.append(path.name)
            else:require(re.fullmatch(r'[0-9]{6}\.tmp',path.name),'Unknown admission entry')
        require(sorted(names)==[f'{i:06}.json' for i in range(1,len(names)+1)],'Out-of-order admission publication')
        for sequence,h in self.admissions.items():
            require(sha(root/f'{sequence:06}.json')==h,'Consumed admission changed or disappeared')
        return names

    def supply(self,sequence,previous_hash):
        names=self.check_admissions()
        name=f'{sequence:06}.json'
        if name not in names:return None
        path=self.root/'admissions'/name
        raw=path.read_bytes();value=read_json(path)
        require(path.read_bytes()==raw,'Admission changed during read')
        require(value.get('sequence')==sequence and value.get('previous_descriptor_sha256')==previous_hash,
                'Admission order/hash chain differs')
        self.admissions[sequence]=w.digest(raw)
        self.validate(value,self.root/'batches'/value['batch_id'])
        return value

    def validate(self,descriptor,root):
        validate_execution(self.root,self.freeze['scope_sha256'],self.execution_freeze_sha256)
        self.check_admissions()
        sequence=descriptor['sequence']
        require(sequence in self.admissions,'Unadmitted descriptor')
        require(read_json(self.root/'admissions'/f'{sequence:06}.json')==descriptor,'Admission/descriptor differs')
        require(w.IDENTIFIER.fullmatch(descriptor['batch_id']) and root==self.root/'batches'/descriptor['batch_id'],
                'Batch directory binding differs')
        binding=read_json(regular(root,'batch-binding.json'))
        required={'window_id','batch_id','max_calls','proposal_freeze_sha256','runtime_freeze_sha256',
                  'authorized','automatic_retries','max_calls_per_trial','model_settings'}
        require(set(binding)==required and binding['window_id']==WINDOW_ID and binding['batch_id']==descriptor['batch_id']
                and binding['authorized'] is True and binding['automatic_retries'] is False
                and binding['max_calls_per_trial']==1 and type(binding['max_calls_per_trial']) is int,
                'Explicit batch binding differs')
        require(binding['model_settings']==model_settings(),'Batch approved model/settings differs')
        require(binding['runtime_freeze_sha256']==sha(ROOT/'runtime-freeze.json')==sha(regular(root,'runtime-freeze.json')),
                'Copied execution freeze differs')
        plan,parents,trials=batch.validate_bundle(root)
        batch.validate_runtime(root)
        require(binding['max_calls']==len(trials) and type(binding['max_calls']) is int and plan['study']==binding['batch_id'],
                'Batch fixed call limit/identity differs')
        for trial in trials:
            request=read_json(regular(root/'frozen-001',trial['request_path']))
            require(set(request)=={'modelId','system','messages','inferenceConfig'}
                    and request['modelId']==batch.ALLOWED_MODEL and request['inferenceConfig']==batch.ALLOWED_INFERENCE,
                    'Frozen request/model/settings differs')
            require(isinstance(request['system'],list) and isinstance(request['messages'],list),'Request messages malformed')
        expected=dict(schema=coordination.SCHEMA,sequence=sequence,
            previous_descriptor_sha256=descriptor['previous_descriptor_sha256'],batch_id=binding['batch_id'],handler_id=HANDLER_ID,
            handler_binding_sha256=w.digest(w.canonical(self.code_pins)),artifact_directory=binding['batch_id'],
            freeze_path='frozen-001/freeze.json',freeze_sha256=binding['proposal_freeze_sha256'],
            runtime_path='runtime-freeze.json',runtime_sha256=binding['runtime_freeze_sha256'],input_sha256=inventory(root),
            slots=[dict(trial_id=t['trial_id'],request_path='frozen-001/'+t['request_path'],request_sha256=t['request_sha256']) for t in trials],
            max_calls=len(trials),sdk_total_max_attempts=1)
        require(descriptor==expected,'Descriptor does not bind exact reviewed inputs/order/runtime')
        return True

    def execute(self,descriptor,context):
        root=context.input_directory;out=context.output_directory
        self.validate(descriptor,root)
        plan,parents,trials=batch.validate_bundle(root)
        batch.archive_runtime(root,out)
        for name in ('runtime','session-runtime-002'):
            # Keep the globally reviewed window/session code separately from the
            # per-batch execution archive named runtime.
            source=self.root/name
            destination=out/('window-runtime' if name=='runtime' else 'session-runtime')
            shutil.copytree(source,destination)
        shutil.copy2(self.root/'scope.json',out/'scope.json')
        shutil.copy2(self.root/'admissions'/f"{descriptor['sequence']:06}.json",out/'admission.json')
        batch.durable_json(out/'environment.json',self.environment)
        index=0
        def only_via_window(payload):
            nonlocal index
            require(index<len(trials),'Per-batch request exceeded frozen order')
            trial=trials[index]
            expected=read_json(root/'frozen-001'/trial['request_path'])
            require(w.canonical(payload)==w.canonical(expected),'Per-batch transport payload drift')
            result=context.invoke(trial['trial_id'])
            index+=1
            return result
        rows=batch.collect(out,only_via_window,self.verifier,self.scope['deadline_epoch'],root=root,clock=self.clock)
        require(index==len(trials) and len(rows)==len(trials)
                and [r['trial_id'] for r in rows]==list(context.trial_ids)
                and all(r['outcome'] in batch.NORMAL_OUTCOMES and r['stop'] is False for r in rows),
                'Incomplete or infrastructure-stopped batch; no next batch')
        summary=read_json(out/'summary.json');ledger=read_json(out/'requests/ledger.json')
        require(summary['all_trials_processed'] is True and summary['reserved_calls']==len(trials)
                and summary['completed_responses']==len(trials) and summary['fatal_error_type'] is None,
                'Per-batch summary mismatch')
        require(ledger['closed'] is True and ledger['closed_reason']=='finished'
                and len(ledger['reservations'])==len(trials)
                and all(r['status']=='COMPLETED' for r in ledger['reservations']), 'Per-batch ledger incomplete')
        self.validate(descriptor,root)
        return dict(completed_trials=list(context.trial_ids),evidence_sha256=inventory(out))


def execute_session(work_root,scope_sha256,execution_freeze_sha256,*,handoff_path,
                    environment_probe=live_environment,key_consumer=batch.consume_key,
                    transport_factory=ManagedTransport,verifier=None,clock=time.time,sleep=time.sleep):
    """One process, one key consumption, one client and one canonical ledger."""
    work_root=Path(work_root).resolve(strict=True)
    scope,freeze=validate_execution(work_root,scope_sha256,execution_freeze_sha256)
    require(clock()<DEADLINE,'Window already ended')
    budget_path=Path(scope['central_ledger_path']);session_path=work_root/SESSION_NAME
    require(not budget_path.exists() and not budget_path.is_symlink()
            and not session_path.exists() and not session_path.is_symlink(),'Preexisting budget/session forbidden')
    environment=environment_probe()
    require(environment.get('versions')==ENVIRONMENT and environment.get('model_connectivity_calls')==0,
            'Environment preflight differs')
    integration=RepairIntegration(work_root,scope,freeze,environment,verifier=verifier,clock=clock)
    first=integration.supply(1,coordination.ZERO)
    require(first is not None,'A first reviewed frozen admission is required before consuming credentials')
    gate=None;session=None;transport=None
    try:
        gate=w.WindowBudget.create(budget_path,scope,clock=clock)
        key_consumer(handoff_path)
        transport=transport_factory(model_settings())
        handler=coordination.ReviewedHandler(integration.validate,integration.execute,integration.code_pins)
        session=coordination.ResearchSession.create(session_path,budget=gate,transport=transport,
            handlers={HANDLER_ID:handler},artifact_root=work_root/'batches',code_root=ROOT,clock=clock,sleep=sleep)
        session.publish(first)
        return session.run(supply=integration.supply,poll_interval=30)
    finally:
        os.environ.pop('AWS_BEARER_TOKEN_BEDROCK',None)
        try:
            if transport is not None:transport.close()
        finally:
            if gate is not None and not gate.poisoned and not gate.closed:
                try:gate.finish()
                except BaseException:pass


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-root',type=Path,required=True)
    parser.add_argument('--scope-sha256',required=True)
    parser.add_argument('--execution-freeze-sha256',required=True)
    parser.add_argument('--key-handoff',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=execute_session(args.work_root,args.scope_sha256,args.execution_freeze_sha256,handoff_path=args.key_handoff)
        print('Session '+result,flush=True)
        return 0 if result=='closed' else 1
    except BaseException as error:
        os.environ.pop('AWS_BEARER_TOKEN_BEDROCK',None)
        print('Session stopped: '+type(error).__name__,file=sys.stderr,flush=True)
        return 1


if __name__=='__main__':raise SystemExit(main())
