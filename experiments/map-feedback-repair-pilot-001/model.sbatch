#!/bin/bash
#SBATCH --job-name=map-repair8
#SBATCH --partition=test
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco/outputs/map-feedback-repair-pilot-001/runtime-002
#SBATCH --output=/n/home13/sophiezeng/formal-disco/outputs/map-feedback-repair-pilot-001/runtime-002/model-%j.log
#SBATCH --error=/n/home13/sophiezeng/formal-disco/outputs/map-feedback-repair-pilot-001/runtime-002/model-%j.err
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export CONDA_PREFIX=/n/home13/sophiezeng/.conda/envs/repodisco
export PATH="$CONDA_PREFIX/bin:$PATH"
exec "$CONDA_PREFIX/bin/python" -B -u run_pilot.py run
