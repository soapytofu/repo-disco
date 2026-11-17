"""Offline imports, fake transport tests and resource syntax; never creates a client."""
import importlib.metadata
import json
import subprocess
import sys
import common as c

def main():
    c.validate_package()
    import boto3,botocore  # imports only; no clients, credentials or requests
    for name in ['collect.sbatch','verify-dafny-vmc.sbatch','verify-vest.sbatch']:
        subprocess.run(['bash','-n',str(c.ROOT/name)],check=True,timeout=5)
    p=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(c.ROOT),'-p','test_execution.py','-v'],
                     cwd=c.ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=50)
    print(json.dumps(dict(returncode=p.returncode,log=p.stdout.decode(),python=sys.version,
                         packages={n:importlib.metadata.version(n) for n in ['boto3','botocore']},
                         model_calls=0,verifier_calls=0,runtime_sha256=c.sha(c.ROOT/'runtime-freeze.json'))))
    sys.exit(p.returncode)

if __name__=='__main__':main()
