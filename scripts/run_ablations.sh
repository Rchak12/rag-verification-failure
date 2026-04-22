#!/bin/bash
# Run ablation sweeps and collect results for Systems A, B, C
# Usage: bash scripts/run_ablations.sh [stub|openai] [n_samples]
# Example: bash scripts/run_ablations.sh stub 50

set -e

BACKEND=${1:-stub}
N=${2:-50}
REPO_ROOT=$(pwd)

echo "======================================"
echo "Ablation Test Suite"
echo "Backend: $BACKEND | N: $N"
echo "======================================"

# TAU SWEEP
echo -e "\n[1/4] Running tau sweep (threshold sensitivity)..."
python -m src.ablation \
  --mode tau \
  --n "$N" \
  --backend "$BACKEND" \
  --repair delete \
  --output "$REPO_ROOT/outputs/ablation_tau_delete.csv"

if [[ "$BACKEND" == "openai" ]]; then
  python -m src.ablation \
    --mode tau \
    --n "$N" \
    --backend "$BACKEND" \
    --repair rewrite \
    --output "$REPO_ROOT/outputs/ablation_tau_rewrite.csv"
fi

# K SWEEP
echo -e "\n[2/4] Running k sweep (retrieval depth sensitivity)..."
python -m src.ablation \
  --mode k \
  --n "$N" \
  --backend "$BACKEND" \
  --repair delete \
  --output "$REPO_ROOT/outputs/ablation_k_delete.csv"

if [[ "$BACKEND" == "openai" ]]; then
  python -m src.ablation \
    --mode k \
    --n "$N" \
    --backend "$BACKEND" \
    --repair rewrite \
    --output "$REPO_ROOT/outputs/ablation_k_rewrite.csv"
fi

echo -e "\n======================================"
echo "Ablation tests complete!"
echo "Outputs saved to outputs/ablation_*.csv"
echo "======================================"
