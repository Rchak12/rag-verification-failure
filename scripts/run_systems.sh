#!/bin/bash
# Run full system experiments: Baseline (A), DELETE repair (B), REWRITE repair (C)
# Usage: bash scripts/run_systems.sh [n_samples] [backend]
# Example: bash scripts/run_systems.sh 50 stub

set -e

N=${1:-50}
BACKEND=${2:-stub}
REPO_ROOT=$(pwd)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "======================================"
echo "System Tests: A (Baseline), B (DELETE), C (REWRITE)"
echo "N: $N | Backend: $BACKEND"
echo "======================================"

# System A: RAG Baseline (no repair)
echo -e "\n[1/3] System A: RAG Baseline (no verification/repair)..."
python -m src.run_experiment \
  --n "$N" \
  --k 3 \
  --tau 0.55 \
  --backend "$BACKEND" \
  --no_verify \
  --final

# System B: Verified RAG with DELETE
echo -e "\n[2/3] System B: Verified RAG + DELETE unsupported..."
python -m src.run_experiment \
  --n "$N" \
  --k 3 \
  --tau 0.55 \
  --backend "$BACKEND" \
  --repair delete \
  --final

# System C: Verified RAG with REWRITE (if using openai backend)
if [[ "$BACKEND" == "openai" ]]; then
  echo -e "\n[3/3] System C: Verified RAG + REWRITE unsupported..."
  python -m src.run_experiment \
    --n "$N" \
    --k 3 \
    --tau 0.55 \
    --backend "$BACKEND" \
    --repair rewrite \
    --final
else
  echo -e "\n[3/3] Skipping System C (REWRITE requires openai backend)."
fi

echo -e "\n======================================"
echo "System tests complete!"
echo "Outputs in: outputs/runs/*/"
echo "======================================"
