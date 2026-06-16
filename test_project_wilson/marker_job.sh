#!/bin/bash
#SBATCH --job-name=marker
#SBATCH --output=marker_%j.out
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32GB
#SBATCH --time=02:00:00
#SBATCH --partition=RM
#SBATCH --account=dmr180040p

module load anaconda3
conda activate myenv

marker_single research_papers/2011-SLB.pdf --output_dir ./output
