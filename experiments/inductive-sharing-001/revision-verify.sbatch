#!/bin/bash
#SBATCH --job-name=inductive-sharing
#SBATCH --partition=shared,sapphire
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco
#SBATCH --output=outputs/inductive-sharing-001/revision-verify-%j.log
#SBATCH --error=outputs/inductive-sharing-001/revision-verify-%j.err
set -euo pipefail
module load python
exec mamba run -n repodisco python -u outputs/inductive-sharing-001/revision-002/run_verification.py --output outputs/inductive-sharing-001/revision-002/verification-001
