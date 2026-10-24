#!/bin/bash -l
#SBATCH --job-name=sharing-eight-calls
#SBATCH --partition=shared,sapphire
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco
#SBATCH --output=outputs/sharing-model-pilot-001/model-%j.log
#SBATCH --error=outputs/sharing-model-pilot-001/model-%j.err
set -euo pipefail
umask 077
module load python
exec mamba run -n repodisco python -u outputs/sharing-model-pilot-001/dispatch.py
