#!/bin/bash
# Reproduce main results from the paper
# Usage: bash scripts/reproduce_results.sh

set -e  # Exit on error

echo "========================================"
echo "RAG Verification Failure Reproduction"
echo "========================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
N_SAMPLES=50
BACKEND="stub"  # Use "openai" if you have OPENAI_API_KEY set
K_VALUES=(1 3 5 7)
TAU_VALUES=(0.35 0.45 0.55 0.65 0.75)

# Check environment
echo -e "${YELLOW}[1/7] Checking environment...${NC}"
if ! command -v python &> /dev/null; then
    echo -e "${RED}✗ Python not found${NC}"
    exit 1
fi
python --version

# Check .env file
if [ ! -f .env ] && [ "$BACKEND" = "openai" ]; then
    echo -e "${YELLOW}⚠ .env not found. Copy .env.example:${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please add your OPENAI_API_KEY to .env${NC}"
fi

# Create output directories
echo -e "${YELLOW}[2/7] Setting up directories...${NC}"
mkdir -p results/figures results/tables results/runs

# Main System Comparison (N=50)
echo -e "${YELLOW}[3/7] Running main system comparison (N=${N_SAMPLES})...${NC}"
echo "System A: RAG Baseline"
python -m src.run_experiment \
    --n $N_SAMPLES \
    --k 3 \
    --tau 0.55 \
    --backend $BACKEND \
    --repair delete \
    --final

echo -e "${GREEN}✓ System A complete${NC}"

# Threshold ablation (τ sweep)
echo -e "${YELLOW}[4/7] Running threshold ablation (τ sweep)...${NC}"
python -m src.ablation \
    --mode tau \
    --n $N_SAMPLES \
    --backend $BACKEND \
    --repair delete \
    --output results/tables/ablation_tau_delete.csv

echo -e "${GREEN}✓ Threshold ablation complete${NC}"

# Retrieval depth ablation (k sweep)
echo -e "${YELLOW}[5/7] Running retrieval depth ablation (k sweep)...${NC}"
python -m src.ablation \
    --mode k \
    --n $N_SAMPLES \
    --backend $BACKEND \
    --repair delete \
    --output results/tables/ablation_k_delete.csv

echo -e "${GREEN}✓ Retrieval depth ablation complete${NC}"

# Analysis (if notebooks available)
echo -e "${YELLOW}[6/7] Summarizing results...${NC}"
python -c "
import json
import glob
from pathlib import Path

# Find latest run
runs = sorted(glob.glob('outputs/runs/*/metrics.json'))
if runs:
    with open(runs[-1]) as f:
        metrics = json.load(f)
    
    print('\n' + '='*50)
    print('SUMMARY RESULTS')
    print('='*50)
    print(f'Answer Accuracy: {metrics.get(\"accuracy\", 0):.1%}')
    print(f'Unsupported Rate: {metrics.get(\"unsupported_rate\", 0):.1%}')
    print(f'Mean Runtime: {metrics.get(\"mean_runtime_s\", 0):.2f}s')
    print('='*50 + '\n')
else:
    print('No results found')
" || echo "Results summary not available"

echo -e "${GREEN}✓ Reproduction complete${NC}"

echo -e "${YELLOW}[7/7] Output locations:${NC}"
echo "  Main results: outputs/runs/*/"
echo "  Ablations: results/tables/"
echo "  Figures: results/figures/"
echo ""
echo -e "${GREEN}✅ Reproduction complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review results/tables/ablation_*.csv"
echo "  2. Check outputs/runs/*/failure_analysis.md for false positive examples"
echo "  3. See docs/RESEARCH_FINDINGS.md for detailed analysis"
