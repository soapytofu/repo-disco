"""Only fake-process offline tests and shell syntax; safe on login/Mac."""
import json
import subprocess
import sys

import common as c


def main():
    c.validate_package()
    for name in ('verify-dafny-vmc.sbatch', 'verify-vest.sbatch'):
        subprocess.run(['bash', '-n', str(c.ROOT / name)], check=True, timeout=5)
    p = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(c.ROOT),
                        '-p', 'test_*.py', '-v'], cwd=c.ROOT, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=50)
    print(json.dumps(dict(returncode=p.returncode, log=p.stdout.decode(), python=sys.version,
                         model_calls=0, verifier_calls=0,
                         runtime_sha256=c.sha(c.ROOT / 'runtime-freeze.json'))))
    sys.exit(p.returncode)


if __name__ == '__main__':
    main()
