#!/bin/bash
#SBATCH --job-name=repodisco-harness-001
#SBATCH --partition=test
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
#SBATCH --output=verify-%j.log
#SBATCH --error=verify-%j.err
set -euo pipefail
cd -- "$SLURM_SUBMIT_DIR"
export CONDA_PREFIX=/n/home13/sophiezeng/.conda/envs/repodisco
export PATH="$CONDA_PREFIX/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
exec "$CONDA_PREFIX/bin/python" -B -u verify_controls.py verification-001
