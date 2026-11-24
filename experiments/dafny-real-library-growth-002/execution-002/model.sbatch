#!/bin/bash
#SBATCH --job-name=dafny-varied-growth-8-002
#SBATCH --partition=test
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=03:00:00
#SBATCH --no-requeue
#SBATCH --output=library-growth-%j.log
#SBATCH --error=library-growth-%j.err
set -euo pipefail
test "$#" -eq 2
execution_root=/n/home13/sophiezeng/formal-disco/outputs/dafny-real-library-growth-002/execution-002
package_root="$execution_root/package"
cd "$execution_root"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
exec /n/home13/sophiezeng/.conda/envs/repodisco/bin/python -B \
  "$package_root/execution-002/run_pilot.py" \
  --scope "$1" --expected-runtime-sha "$2" \
  --runtime-freeze "$package_root/execution-002/runtime-freeze.json" \
  --authorization "$execution_root/authorization.json" \
  --output "$execution_root/model-001" \
  --private-handoff "$HOME/.repodisco-bedrock-handoff"

