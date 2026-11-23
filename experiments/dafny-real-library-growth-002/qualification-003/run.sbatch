#!/bin/bash
#SBATCH --job-name=dafny-growth-002-references
#SBATCH --partition=test
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --no-requeue
#SBATCH --output=qualification-%j.log
#SBATCH --error=qualification-%j.err
set -euo pipefail
cd -- "${REPODISCO_EXECUTION_ROOT:?Missing authoritative execution directory}"
export CONDA_PREFIX=/n/home13/sophiezeng/.conda/envs/repodisco
export PATH="$CONDA_PREFIX/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1
exec "$CONDA_PREFIX/bin/python" -B -u qualification-003/collect.py \
  "qualification-003/configs/$1.json" "qualification-003/output-$1" \
  --expected-freeze-sha "${REPODISCO_FREEZE_SHA:?Missing pinned runtime hash}"
