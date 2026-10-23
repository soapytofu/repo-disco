#!/bin/bash -l
#SBATCH --job-name=repodisco-control
#SBATCH --partition=shared
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco
#SBATCH --output=outputs/sharing-control-001/verify-%j.log
#SBATCH --error=outputs/sharing-control-001/verify-%j.err
set -euo pipefail
module load python
exec mamba run -n repodisco python -u outputs/sharing-control-001/run_verification.py --output outputs/sharing-control-001/verification-002
