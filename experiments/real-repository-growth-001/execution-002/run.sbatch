#!/bin/bash
#SBATCH --job-name=growth-model-8-002
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --no-requeue
#SBATCH --output=growth-%j.log
#SBATCH --error=growth-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PYTHONDONTWRITEBYTECODE=1
export CARGO_BUILD_JOBS=1
exec /n/home13/sophiezeng/.conda/envs/repodisco/bin/python -B \
  repo/experiments/real-repository-growth-001/execution-002/run_pilot.py \
  --repo "$PWD/repo" --output "$PWD/model-001" \
  --authorization "$PWD/authorization.json" --handoff "$HOME/.repodisco-bedrock-handoff"
