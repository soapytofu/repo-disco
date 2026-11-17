#!/bin/bash
#SBATCH --job-name=guard-diagnostic-vest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --no-requeue
#SBATCH --output=vest-%j.log
#SBATCH --error=vest-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PYTHONDONTWRITEBYTECODE=1
exec /n/home13/sophiezeng/.conda/envs/repodisco/bin/python -B verify_candidates.py vest
