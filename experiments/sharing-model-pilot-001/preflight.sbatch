#!/bin/bash -l
#SBATCH --job-name=sharing-pilot-preflight
#SBATCH --partition=shared,sapphire
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco
#SBATCH --output=outputs/sharing-model-pilot-001/preflight-%j.log
#SBATCH --error=outputs/sharing-model-pilot-001/preflight-%j.err
set -euo pipefail
module load python
exec mamba run -n repodisco python -u outputs/sharing-model-pilot-001/preflight.py --output outputs/sharing-model-pilot-001/preflight-001
