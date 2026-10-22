#!/bin/bash -l
#SBATCH --job-name=repodisco-context
#SBATCH --partition=test
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco
#SBATCH --output=outputs/context-pilot-001/pilot-%j.log
#SBATCH --error=outputs/context-pilot-001/pilot-%j.err
set -euo pipefail
umask 077
module load python
exec mamba run -n repodisco python -u outputs/context-pilot-001/run_pilot.py --output outputs/context-pilot-001/pilot-001
