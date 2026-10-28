#!/bin/bash
#SBATCH --job-name=baseline-preflight
#SBATCH --partition=shared,sapphire
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --no-requeue
#SBATCH --chdir=/n/home13/sophiezeng/formal-disco
#SBATCH --output=outputs/baseline-reproduction-001/preflight-%j.log
#SBATCH --error=outputs/baseline-reproduction-001/preflight-%j.err
set -euo pipefail
module load python
exec mamba run -n repodisco python experiments/baseline-reproduction-001/preflight.py --dataset inputs/DafnyBench --output outputs/baseline-reproduction-001/preflight-001
