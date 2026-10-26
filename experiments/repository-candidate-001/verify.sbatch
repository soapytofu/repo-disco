#!/bin/bash
#SBATCH --job-name=repository-candidate
#SBATCH --partition=shared,sapphire
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco
#SBATCH --output=outputs/repository-candidate-001/verify-%j.log
#SBATCH --error=outputs/repository-candidate-001/verify-%j.err
set -euo pipefail
module load python
exec mamba run -n repodisco python -u outputs/repository-candidate-001/run_integration.py
