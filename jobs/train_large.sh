#!/bin/bash
#Set job requirements
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=36
#SBATCH --gpus=2
#SBATCH --partition=gpu
#SBATCH --time=120:00:00

# Set environment variables
export HF_DATASETS_CACHE="/projects/0/einf2504/cache/"
export TRANSFORMERS_CACHE="/projects/0/einf2504/cache/"

# Load modules required for processing
module load 2021
module load FFmpeg/4.3.2-GCCcore-10.3.0
module load Python/3.9.5-GCCcore-10.3.0

# Install packages
python -m pip install torch==1.11.0+cu113 torchvision==0.12.0+cu113 torchaudio==0.11.0+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html
#python -m pip install --upgrade pip wandb pandas numpy sklearn transformers datasets ipywidgets matplotlib jiwer seaborn unidecode librosa soundfile tqdm torch_audiomentations
python -m pip install pip wandb pandas numpy sklearn transformers datasets ipywidgets matplotlib jiwer seaborn unidecode librosa soundfile tqdm torch_audiomentations

# Browse to the right folder
cd /projects/0/einf2504/ || exit

# Execute training script
python ./train_hubert_mcv-interview.py || exit