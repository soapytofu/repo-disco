#!/bin/bash
#SBATCH --job-name=repodisco-window
#SBATCH --partition=shared,sapphire
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=24:00:00
#SBATCH --no-requeue
#SBATCH --output=session-%j.log
#SBATCH --error=session-%j.err
set -euo pipefail
cd -- "$SLURM_SUBMIT_DIR"
export PYTHONDONTWRITEBYTECODE=1
export CONDA_PREFIX=/n/home13/sophiezeng/.conda/envs/repodisco
export PATH="$CONDA_PREFIX/bin:$PATH"
exec "$CONDA_PREFIX/bin/python" -B -u execution-runtime/session_driver.py \
  --work-root "$SLURM_SUBMIT_DIR" \
  --scope-sha256 a649bcfca3be0b1120f8c7810778a344dd6fbf395dbeb6b6e362a20c5541ed01 \
  --execution-freeze-sha256 ca24194ab90c932e0c514c1b390a80dd999645ccf07a9c937ea176f82b701b44 \
  --key-handoff /n/home13/sophiezeng/.repodisco-bedrock-handoff
