#!/bin/bash
#SBATCH --job-name=growth-controls-dafny
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=01:30:00
#SBATCH --no-requeue
#SBATCH --output=dafny-vmc-%j.log
#SBATCH --error=dafny-vmc-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PYTHONDONTWRITEBYTECODE=1
exec /n/home13/sophiezeng/.conda/envs/repodisco/bin/python -B verify_controls.py dafny-vmc
