#!/bin/bash
#SBATCH --job-name=diverse-extract-core
#SBATCH --partition=test
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco/outputs/diverse-repair-extraction-diagnostic-001
#SBATCH --output=/n/home13/sophiezeng/formal-disco/outputs/diverse-repair-extraction-diagnostic-001/verify-%j.log
#SBATCH --error=/n/home13/sophiezeng/formal-disco/outputs/diverse-repair-extraction-diagnostic-001/verify-%j.err
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export CONDA_PREFIX=/n/home13/sophiezeng/.conda/envs/repodisco
export PATH="$CONDA_PREFIX/bin:$PATH"
exec "$CONDA_PREFIX/bin/python" -B -u preflight.py --output verification-001
