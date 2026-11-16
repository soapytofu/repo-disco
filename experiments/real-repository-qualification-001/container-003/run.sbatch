#!/bin/bash
#SBATCH --job-name=qual-vmc-container-003
#SBATCH --partition=shared
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH --no-requeue
#SBATCH --output=container-%j.log
#SBATCH --error=container-%j.err
set -euo pipefail
cd -- "$SLURM_SUBMIT_DIR"
export PYTHONDONTWRITEBYTECODE=1
exec /n/home13/sophiezeng/.conda/envs/repodisco/bin/python -B -u run.py
