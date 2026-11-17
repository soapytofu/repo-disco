#!/bin/bash
#SBATCH --job-name=real-repo-repair-controls
#SBATCH --partition=shared
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:15:00
#SBATCH --no-requeue
#SBATCH --output=controls-%j.log
#SBATCH --error=controls-%j.err
set -euo pipefail
cd -- "$SLURM_SUBMIT_DIR"
export PYTHONDONTWRITEBYTECODE=1
exec /n/home13/sophiezeng/.conda/envs/repodisco/bin/python -B -u run_controls.py
