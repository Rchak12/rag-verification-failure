#!/usr/bin/env bash
# setup_conda.sh — Create a conda environment with compatible builds for FAISS, PyTorch, sentence-transformers, and datasets.
# Usage: bash setup_conda.sh

set -euo pipefail
ENV_NAME=cs592
PY_VER=3.10
CHANNEL=conda-forge

echo "Creating conda environment '$ENV_NAME' (python=$PY_VER)..."
conda create -n "$ENV_NAME" python=$PY_VER -y

echo "Activating environment..."
# Note: user should run `conda activate cs592` after this script completes

echo "Installing core packages from conda-forge (faiss-cpu, pytorch, sentence-transformers, datasets)..."
conda install -n "$ENV_NAME" -c "$CHANNEL" faiss-cpu sentence-transformers datasets pytorch -y

echo "Activating the new environment and installing remaining Python deps via pip..."
# Activate and run pip install -r requirements.txt inside the environment
# On macOS the recommended command is below (user should run it interactively):
# conda activate cs592
# pip install -r requirements.txt --no-deps

cat <<'EOF'

DONE.
Next steps (run these in a new shell):

conda activate cs592
# Install Python-only requirements but avoid reinstalling core conda packages
pip install -r requirements.txt --no-deps

# Optional: set HF_TOKEN environment var for faster HF dataset downloads
# export HF_TOKEN=hf_.....

# Run tests
python -m pytest -q

EOF
