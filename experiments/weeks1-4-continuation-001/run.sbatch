#!/bin/bash
#SBATCH --job-name=weeks14-continuation
#SBATCH --partition=shared,sapphire
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco/outputs/weeks1-4-runtime-001
#SBATCH --output=/n/home13/sophiezeng/formal-disco/outputs/weeks1-4-runtime-001/continuation-%j.log
#SBATCH --error=/n/home13/sophiezeng/formal-disco/outputs/weeks1-4-runtime-001/continuation-%j.err
set -euo pipefail
module load python
exec mamba run -n repodisco python -u weeks14_continuation.py
