#!/bin/bash
#SBATCH --job-name=monorepo-syntax-smoke
#SBATCH --partition=test
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco/outputs/monorepo-syntax-smoke-001
#SBATCH --output=/n/home13/sophiezeng/formal-disco/outputs/monorepo-syntax-smoke-001/model-%j.log
#SBATCH --error=/n/home13/sophiezeng/formal-disco/outputs/monorepo-syntax-smoke-001/model-%j.err
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
module load python
exec mamba run -n repodisco python -B -u run_pilot.py run
