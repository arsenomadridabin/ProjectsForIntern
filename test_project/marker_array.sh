#!/bin/bash
#SBATCH --job-name=marker
#SBATCH --partition=RM-512
#SBATCH --output=marker_%A_%a.out
#SBATCH --error=marker_%A_%a.err
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --array=0-3%2   # <-- 4 PDFs, max 2 running at once

module load anaconda3
conda activate marker

export OMP_NUM_THREADS=2

FILE=$(sed -n "$((SLURM_ARRAY_TASK_ID+1))p" pdf_list.txt)

mkdir -p output

marker_single "$FILE" \
  --output_dir "output/${FILE%.pdf}" \
  --disable_ocr
