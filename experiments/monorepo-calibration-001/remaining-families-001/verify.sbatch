#!/bin/bash
#SBATCH --job-name=calibration-remaining
#SBATCH --partition=test
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco/outputs/monorepo-calibration-001/remaining-families-001
#SBATCH --output=/n/home13/sophiezeng/formal-disco/outputs/monorepo-calibration-001/remaining-families-001/verify-%j.log
#SBATCH --error=/n/home13/sophiezeng/formal-disco/outputs/monorepo-calibration-001/remaining-families-001/verify-%j.err
set -euo pipefail
module load python
exec mamba run -n repodisco python -u preflight.py
