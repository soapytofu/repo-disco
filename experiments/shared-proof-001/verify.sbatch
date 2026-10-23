#!/bin/bash -l
#SBATCH --job-name=repodisco-sharing
#SBATCH --partition=serial_requeue
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco
#SBATCH --output=outputs/shared-proof-001/verify-%j.log
#SBATCH --error=outputs/shared-proof-001/verify-%j.err
set -euo pipefail
module load python
exec mamba run -n repodisco python -u outputs/shared-proof-001/run_verification.py --output outputs/shared-proof-001/verification-001
