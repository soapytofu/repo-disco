#!/bin/bash
#SBATCH --job-name=sharing-branches
#SBATCH --partition=shared,sapphire
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco
#SBATCH --output=outputs/sharing-branching-001/guard-verify-%j.log
#SBATCH --error=outputs/sharing-branching-001/guard-verify-%j.err
set -euo pipefail
module load python
exec mamba run -n repodisco python -u outputs/sharing-branching-001/guard-preflight/run_verification.py --output outputs/sharing-branching-001/guard-preflight/verification-001
