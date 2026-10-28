#!/bin/bash
#SBATCH --job-name=repository-extension-pilot
#SBATCH --partition=test
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco/outputs/repository-extension-001
#SBATCH --output=/n/home13/sophiezeng/formal-disco/outputs/repository-extension-001/model-%j.log
#SBATCH --error=/n/home13/sophiezeng/formal-disco/outputs/repository-extension-001/model-%j.err
set -euo pipefail
module load python
exec mamba run -n repodisco python -u run_pilot.py run
