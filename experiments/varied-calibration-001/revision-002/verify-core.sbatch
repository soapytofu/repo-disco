#!/bin/bash
#SBATCH --job-name=varied2-core
#SBATCH --partition=test
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco/outputs/varied-calibration-001/revision-002
#SBATCH --output=/n/home13/sophiezeng/formal-disco/outputs/varied-calibration-001/revision-002/verify-%j.log
#SBATCH --error=/n/home13/sophiezeng/formal-disco/outputs/varied-calibration-001/revision-002/verify-%j.err
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
module load python
exec mamba run -n repodisco python -B -u preflight.py --phase core --output verification-001
