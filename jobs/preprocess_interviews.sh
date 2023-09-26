#!/bin/bash
#Set job requirements
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --partition=thin
#SBATCH --time=02:00:00

export OMP_NUM_THREADS=64

# Load modules required for processing
module load 2021
module load FFmpeg/4.3.2-GCCcore-10.3.0
module load Python/3.9.5-GCCcore-10.3.0

# Browse to the right folder
cd /projects/0/einf2504/data_preperation || exit

# Execute splitting script
python ./prepare_from_json.py