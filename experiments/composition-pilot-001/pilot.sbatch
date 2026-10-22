#!/bin/bash -l
#SBATCH --job-name=repodisco-composition
#SBATCH --partition=shared
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:45:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco
#SBATCH --output=outputs/composition-pilot-001/pilot-%j.log
#SBATCH --error=outputs/composition-pilot-001/pilot-%j.err
set -euo pipefail
umask 077
module load python
exec mamba run -n repodisco python -u outputs/composition-pilot-001/run_pilot.py --output outputs/composition-pilot-001/pilot-001
