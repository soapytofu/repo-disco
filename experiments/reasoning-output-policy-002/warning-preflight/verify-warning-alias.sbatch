#!/bin/bash
#SBATCH --job-name=reasoning-warning-alias
#SBATCH --partition=test
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco/outputs/reasoning-output-policy-002/warning-preflight
#SBATCH --output=/n/home13/sophiezeng/formal-disco/outputs/reasoning-output-policy-002/warning-preflight/verify-%j.log
#SBATCH --error=/n/home13/sophiezeng/formal-disco/outputs/reasoning-output-policy-002/warning-preflight/verify-%j.err
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
module load python
exec mamba run -n repodisco python -B -u verify.py verification-001
