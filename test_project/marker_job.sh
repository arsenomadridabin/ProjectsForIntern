#!/bin/bash
#SBATCH --job-name=marker
#SBATCH --partition=RM-512
#SBATCH --output=marker_%j.out
#SBATCH --error=marker_%j.err
#SBATCH --time=04:00:00

#SBATCH --cpus-per-task=2
#SBATCH --mem=16G

module load anaconda3
conda activate marker

export OMP_NUM_THREADS=2

marker_single 2005-SLB.pdf --output_dir output --disable_ocr
