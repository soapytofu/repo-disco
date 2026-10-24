#!/bin/bash -l
#SBATCH --job-name=sharing-extraction
#SBATCH --partition=shared,sapphire
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco
#SBATCH --output=outputs/sharing-extraction-diagnostic-001/verify-%j.log
#SBATCH --error=outputs/sharing-extraction-diagnostic-001/verify-%j.err
set -euo pipefail
module load python
exec mamba run -n repodisco python -u outputs/sharing-extraction-diagnostic-001/verify.py --output outputs/sharing-extraction-diagnostic-001/verification-001
