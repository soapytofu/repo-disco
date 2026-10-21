#!/bin/bash -l
#SBATCH --job-name=repodisco-50
#SBATCH --partition=test
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco
#SBATCH --output=/n/home13/sophiezeng/formal-disco/outputs/format-comparison-001/run-20261020T231743-605946Z/batch-%j.log
#SBATCH --error=/n/home13/sophiezeng/formal-disco/outputs/format-comparison-001/run-20261020T231743-605946Z/batch-%j.err
set -euo pipefail
umask 077
module load python
exec mamba run -n repodisco python -u outputs/format-comparison-001/run_comparison_unattended.py \
  --suite outputs/format-comparison-001 \
  --resume outputs/format-comparison-001/run-20261020T231743-605946Z \
  --max-calls 50
