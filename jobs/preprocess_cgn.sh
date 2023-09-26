#!/bin/bash
#Set job requirements
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --partition=thin
#SBATCH --time=02:00:00

# Load modules required for processing
module load 2021
module load FFmpeg/4.3.2-GCCcore-10.3.0
module load Python/3.9.5-GCCcore-10.3.0

# Browse to the right folder
cd /projects/0/einf2504/CGN/CGN/Spltting/ || exit

python -m pip install pandas || exit
python -m pip install soundfile || exit

# Execute splitting script
python ./split_cgn.py ../CGN_2.0.3 || exit

# Execute import script
python ./import_cgn.py ../CGN_2.0.3 || exit

# Execute clean script
python ./clean_data.py ../CGN_2.0.3 || exit
