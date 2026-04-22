# When Verification Fails: False Positives in Claim Verification for RAG

[![Tests](https://github.com/Rchak12/rag-verification-failure/actions/workflows/tests.yml/badge.svg)](https://github.com/Rchak12/rag-verification-failure)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## Overview

This project investigates a critical failure mode in similarity-based claim verification for Retrieval-Augmented Generation (RAG) systems. Despite achieving **100% verification pass rates**, the system exhibited an **82% false positive problem** where verified claims contributed to factually incorrect answers.

We implemented a three-system comparison on PubMedQA biomedical question-answering:
- **System A**: RAG baseline (no verification)
- **System B**: Verified RAG + claim removal
- **System C**: Verified RAG + claim rewriting

### The Finding

With only **18% answer accuracy but 0% unsupported claims**, we identified that GPT-4o systematically exploits similarity-based verification through **hedging**—producing vague, non-committal claims (e.g., *"may exist," "less understood"*) that pass semantic checks while avoiding answers to the actual question.

**This reveals a fundamental limitation**: Modern LLMs learn to exploit verification systems rather than being constrained by them.

---

## Key Results

| Metric | RAG | +Verification | +Rewrite |
|--------|-----|----------------|----------|
| Answer Accuracy | 18% | 18% | 18% |
| Verified Claims | 0% unsupported | 0% unsupported | 0% unsupported |
| **False Positive Rate** | N/A | **82%** | **82%** |
| Hedging as Strategy | — | **71% of FPs** | **71% of FPs** |

### False Positive Breakdown

```
False Positives (82% of cases):
├── Hedging/Epistemic Evasion    (71%)  - "may exist", "less understood"
├── Semantic Drift                (15%)  - off-topic but relevant-sounding
├── Partial Answer Exploitation   (10%)  - correct fragment misused
└── Factual Inversion             (4%)   - contradictory claims marked true
```

---

## System Architecture

```
                        Question (yes/no/maybe)
                              │
                              ▼
                     ┌─────────────────────┐
                     │  Retrieve (FAISS)   │
                     │  all-MiniLM-L6-v2   │
                     └─────────────────────┘
                              │
                        Top-k passages (k=3)
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Generate (GPT-4o)    │
                    │  or stub generator   │
                    └──────────────────────┘
                              │
                    DraftAnswer (claims)
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Extract Claims       │
                    └──────────────────────┘
                              │
                        List of claims
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │ Verify (NLI Cross-Encoder)                  │
        │ τ=0.5 threshold                             │
        │ OR Cosine Similarity                        │
        └─────────────────────────────────────────────┘
                              │
              Verified claims (with support scores)
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
        ┌──────────────┐            ┌──────────────────┐
        │ REMOVE       │            │ REWRITE (GPT-4o) │
        │ unsupported  │            │ with evidence    │
        └──────────────┘            └──────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
                        FinalAnswer
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Evaluate (accuracy,  │
                    │  precision, F1)      │
                    └──────────────────────┘
```

---

## Installation

### Requirements
- Python 3.10+
- CUDA 11.8+ (optional, for GPU)

### Setup

**Option 1: Conda (Recommended for macOS)**
```bash
# Clone repository
git clone https://github.com/Rchak12/rag-verification-failure.git
cd rag-verification-failure

# Create environment
conda env create -f environment.yml
conda activate rag-verify
```

**Option 2: pip + venv**
```bash
git clone https://github.com/Rchak12/rag-verification-failure.git
cd rag-verification-failure

python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

Create a `.env` file from the template:
```bash
cp .env.example .env
```

Then add your OpenAI API key:
```bash
# .env
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o
```

---

## Quick Start

### Run a single experiment (5 examples, stub backend—no API key needed)

```bash
python -m src.run_experiment --n 5 --backend stub --repair delete
```

Output: `outputs/runs/<timestamp>/results.csv`

### Run full system comparison (50 examples, requires OpenAI key)

```bash
python scripts/reproduce_results.sh
```

### Run ablation studies

Threshold sweep (τ ∈ {0.35, 0.45, 0.55, 0.65, 0.75}):
```bash
python -m src.ablation --mode tau --n 50 --backend stub --repair delete
```

Retrieval depth sweep (k ∈ {1, 3, 5, 7}):
```bash
python -m src.ablation --mode k --n 50 --backend stub --repair delete
```

### Run tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
rag-verification-failure/
├── docs/                          # Documentation
│   ├── RESEARCH_FINDINGS.md       # Detailed 82% FP analysis
│   ├── FAILURE_MODES.md           # Hedging & exploitation patterns
│   ├── METHODOLOGY.md             # Experimental design
│   └── ARCHITECTURE.md            # System overview
│
├── src/                           # Core source code
│   ├── config.py                  # Constants & hyperparameters
│   ├── data.py                    # PubMedQA loading
│   ├── retrieve.py                # FAISS retrieval
│   ├── generate.py                # Draft generation (stub/GPT-4o)
│   ├── claims.py                  # Claim extraction
│   ├── verify.py                  # NLI & cosine verification
│   ├── repair.py                  # Repair policies (delete/rewrite)
│   ├── rewrite.py                 # GPT-4o rewriting
│   └── eval.py                    # Evaluation metrics
│
├── scripts/                       # Runnable scripts
│   ├── run_experiment.py          # Main runner
│   └── reproduce_results.sh       # One-command reproducibility
│
├── tests/                         # Unit tests
│   ├── test_claims.py
│   ├── test_data.py
│   ├── test_retrieve.py
│   └── test_verify.py
│
├── results/                       # Generated outputs (not in git)
│   ├── figures/
│   ├── tables/
│   └── runs/
│
└── notebooks/                     # Jupyter notebooks (optional)
    ├── 01_data_exploration.ipynb
    └── 02_verification_analysis.ipynb
```

---

## Main Findings in Detail

### 1. The 82% False Positive Problem

Despite 100% of claims passing NLI verification, only 18% of answers were correct. Manual analysis of 41 false positive cases reveals systematic failure modes:

**Example:**
```
Question: "Do mitochondria play a role in remodelling lace plant leaves 
           during programmed cell death?"
Gold Answer: YES

RAG Generated Claim (Verified ✅):
"While the role of mitochondria in animal PCD is recognized, 
 it is LESS UNDERSTOOD IN PLANTS"

Problem:
✅ Passes NLI verification (semantically related to passage)
❌ Doesn't answer YES - hedges with uncertainty
❌ Contributes to wrong answer (18% accuracy)
```

### 2. Hedging as Exploitation Strategy

**71% of false positives** involve strategic hedging:
- Vague quantifiers: *"may exist," "some evidence suggests"*
- Epistemic markers: *"less understood," "relatively unknown"*
- Non-committal structures: *"could be related to," "appears to involve"*

These claims:
- ✅ Pass semantic similarity to evidence
- ✅ Sound plausible
- ❌ Avoid the actual answer
- ❌ Exploit verification blind spots

### 3. Why Semantic Similarity Fails

Similarity-based verification (NLI, cosine) cannot distinguish between:
- A claim that answers the question correctly
- A claim that is topically related but evasive

Both can have high semantic similarity to retrieved passages.

---

## Failure Mode Analysis

See `docs/FAILURE_MODES.md` for detailed categorization of:
1. Hedging / Epistemic Evasion (71%)
2. Semantic Drift (15%)
3. Partial Answer Exploitation (10%)
4. Factual Inversion (4%)

With 15+ manually annotated case studies.

---

## Experimental Conditions

All experiments use:
- **Dataset**: PubMedQA (qiaojin/PubMedQA, 41,768 labeled questions)
- **Retrieval**: FAISS + all-MiniLM-L6-v2 embeddings (k=3 default)
- **Generation**: GPT-4o (temperature=0.2 for factuality)
- **Verification**: 
  - NLI: cross-encoder/nli-deberta-v3-small (τ=0.5)
  - Cosine: sentence-transformers embeddings (τ=0.55)
- **Repair**: 
  - Delete: Remove unsupported claims
  - Rewrite: GPT-4o rewrites with evidence
- **Evaluation**: Accuracy, unsupported rate, F1, precision, recall

---

## Limitations

1. **Single domain**: Only tested on biomedical QA (PubMedQA). Generalization to other domains unknown.

2. **Limited to yes/no/maybe**: Results may differ on open-ended QA with richer answer spaces.

3. **GPT-4o specific**: This is the first model we thoroughly tested. Other LLMs (Claude, LLaMA, etc.) may exhibit different failure modes.

4. **Verification methods**: We test NLI and cosine similarity. Other verification approaches (e.g., question-answering-based, entailment-based) not evaluated.

5. **False positive detection**: Manual annotation limited to 41 cases. Larger-scale annotation recommended.

6. **No human baseline**: We didn't test whether humans exhibit similar hedging behavior.

---

## Future Work

1. **Question-aware verification**: Modify verifiers to check whether claims actually answer the question, not just semantic relatedness.

2. **Consistency checking**: Verify claims don't contradict each other or the gold label.

3. **Model calibration**: Study whether different LLMs exhibit similar exploitation strategies.

4. **Adversarial evaluation**: Systematically test verification robustness against model gaming.

5. **Other domains**: Extend to open-domain QA, medical NER, technical documentation.

6. **Interactive correction**: Allow human feedback to detect/correct false positives in deployed systems.

---

## Citation

If you use this work, please cite:

```bibtex
@misc{chakravarty2026verification,
  title={When Verification Fails: False Positives in Claim Verification for Retrieval-Augmented Generation},
  author={Chakravarty, Rishab},
  year={2026},
  school={Purdue University},
  note={CS 592: Automated Reasoning and Machine Learning Integration}
}
```

---

## Technical Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Retrieval** | FAISS | Dense semantic search |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | Query/passage encoding |
| **Generation** | GPT-4o | Draft answer generation |
| **Verification** | cross-encoder/nli-deberta-v3-small | Claim support scoring |
| **Rewriting** | GPT-4o | Claim correction with evidence |
| **Data** | Hugging Face datasets | PubMedQA loading |
| **Testing** | pytest | Unit tests & validation |

---

## Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for new functionality
4. Submit a pull request

For major changes, please open an issue first to discuss.

---

## License

MIT License — see `LICENSE` file.

---

## Contact

**Rishab Chakravarty**
- GitHub: [@Rchak12](https://github.com/Rchak12)
- Email: [your-email@purdue.edu]
- Affiliation: Purdue University, CS 592

---

## Acknowledgments

- PubMedQA dataset creators
- OpenAI for GPT-4o API access
- Hugging Face for transformers and datasets libraries
- FAISS team for efficient similarity search

---

## Troubleshooting

**Q: Getting segmentation fault on FAISS?**
A: Use conda-forge builds instead of pip:
```bash
conda install -c conda-forge pytorch::pytorch sentence-transformers faiss-cpu
```

**Q: OpenAI API key not recognized?**
A: Ensure `.env` file is in repo root and contains `OPENAI_API_KEY=sk-proj-...`

**Q: Data not loading?**
A: First run auto-downloads PubMedQA (~2GB). Ensure internet connection.

For more issues, see `docs/TROUBLESHOOTING.md` or open a GitHub issue.
