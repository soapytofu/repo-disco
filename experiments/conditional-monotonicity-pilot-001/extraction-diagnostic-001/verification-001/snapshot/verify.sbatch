#!/bin/bash
#SBATCH --job-name=monotone-extraction
#SBATCH --partition=test
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco/outputs/conditional-monotonicity-pilot-001/extraction-diagnostic-001
#SBATCH --output=/n/home13/sophiezeng/formal-disco/outputs/conditional-monotonicity-pilot-001/extraction-diagnostic-001/verify-%j.log
#SBATCH --error=/n/home13/sophiezeng/formal-disco/outputs/conditional-monotonicity-pilot-001/extraction-diagnostic-001/verify-%j.err
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
module load python
exec mamba run -n repodisco python -B -u verify.py verification-001
