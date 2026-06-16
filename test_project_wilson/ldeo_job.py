#!/bin/bash
#SBATCH -p RM-shared
#SBATCH -t 48:00:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=1
set -x

module load python
python3 hello_world.py
