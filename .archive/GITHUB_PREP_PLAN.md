# Professional GitHub Repository Structure & Plan

## Current State Assessment
✅ Strong research contribution (82% false positive analysis)
✅ Well-documented experiments and findings
✅ Good codebase structure with modular design
❌ Too many intermediate markdown files (clutters repo)
❌ Results/figures mixed into root
❌ Missing professional documentation
❌ No clear entry point for reproducibility

---

## PROPOSED FINAL STRUCTURE

```
rag-verification-failure/
├── README.md                          # Main entry point (professional, recruiter-friendly)
├── LICENSE                             # MIT or Apache 2.0
├── .gitignore                          # Exclude venv, .env, cache, large data
├── .env.example                        # Template for required env vars
├── requirements.txt                    # Python dependencies
├── environment.yml                     # Conda environment (optional)
│
├── setup.py                            # Optional: for pip install
│
├── docs/
│   ├── RESEARCH_FINDINGS.md           # Detailed 82% false positive analysis
│   ├── METHODOLOGY.md                 # Experimental setup and design
│   ├── FAILURE_MODES.md               # Hedging and exploitation patterns
│   └── ARCHITECTURE.md                # System design overview
│
├── src/
│   ├── __init__.py
│   ├── config.py                       # Constants, hyperparameters
│   ├── data.py                         # PubMedQA loading
│   ├── retrieve.py                     # FAISS retrieval
│   ├── generate.py                     # Draft generation
│   ├── claims.py                       # Claim extraction
│   ├── verify.py                       # Verification (NLI + cosine)
│   ├── repair.py                       # Repair policies
│   ├── rewrite.py                      # Rewrite module (GPT-4o)
│   └── eval.py                         # Evaluation metrics
│
├── scripts/
│   ├── run_experiment.py              # Main experimental runner
│   ├── run_ablations.sh                # Ablation sweep orchestration
│   └── reproduce_results.sh            # One-command reproducibility
│
├── notebooks/
│   ├── 01_data_exploration.ipynb       # PubMedQA analysis
│   ├── 02_verification_analysis.ipynb  # False positive breakdown
│   └── 03_failure_modes.ipynb          # Hedging patterns
│
├── results/
│   ├── .gitkeep
│   ├── figures/
│   │   ├── figure1_pipeline.png
│   │   ├── figure2_main_results.png
│   │   ├── figure7_false_positive_breakdown.png
│   │   └── ...
│   ├── tables/
│   │   ├── results_summary.csv
│   │   └── failure_case_analysis.csv
│   └── paper/
│       └── FINAL_REPORT.pdf            # Research paper (if available)
│
├── data/
│   └── .gitkeep                        # Placeholder (no data in repo, auto-download)
│
├── tests/
│   ├── __init__.py
│   ├── test_claims.py
│   ├── test_data.py
│   ├── test_retrieve.py
│   ├── test_verify.py
│   └── conftest.py
│
├── .github/
│   ├── workflows/
│   │   ├── tests.yml                   # CI/CD for automated testing
│   │   └── lint.yml                    # Code style checks
│   └── ISSUE_TEMPLATE/
│       └── bug_report.md
│
└── pytest.ini
```

---

## FILES TO CREATE / UPDATE

### 1. **README.md** (New Professional Version)
   - Clear project title & one-liner
   - Executive summary of 82% false positive finding
   - System architecture diagram (ASCII or link)
   - Installation instructions
   - Quick-start example
   - Main results with figures
   - Paper link
   - Limitations & future work

### 2. **.gitignore** (Enhanced)
   - Exclude: .venv/, .env, __pycache__/, *.pyc
   - Exclude: outputs/, results/ (generated, not source)
   - Exclude: .DS_Store, .claude/
   - Exclude: large data files, indices

### 3. **LICENSE** (New)
   - MIT or Apache 2.0 (your choice)

### 4. **docs/RESEARCH_FINDINGS.md**
   - Comprehensive 82% false positive analysis
   - Failure mode taxonomy
   - Manual case studies
   - Recommendations

### 5. **setup.py** (Optional but Professional)
   - Allows `pip install -e .` installation

### 6. **scripts/reproduce_results.sh**
   - One-command entry point to regenerate results

### 7. **Cleanup existing files**
   - Move: `FINAL_REPORT.tex` → `docs/paper/` (or `.pdf` only)
   - Move: All `ANALYSIS_*.md` → `docs/`
   - Move: All figures → `results/figures/`
   - Delete: Intermediate files (PROJECT_STATUS.md, FINAL_STEPS.md, etc.)

---

## FILES TO DELETE (or .gitignore)

```
❌ .venv/
❌ __pycache__/
❌ .pytest_cache/
❌ .claude/
❌ .DS_Store
❌ .env (keep .env.example)
❌ outputs/ (generated during runs)
❌ *.pyc
❌ INSTALL_FIX.md
❌ PROJECT_STATUS.md
❌ FINAL_STEPS.md
❌ IMPLEMENTATION_SUMMARY.md
❌ All intermediate analysis docs (keep only key ones in docs/)
```

---

## SUGGESTED REPO NAMES

1. **rag-verification-failure** (descriptive, honest, research-focused)
2. **llm-verification-false-positives** (broader scope)
3. **semantic-verification-blindspots** (technical focus)
4. **hedging-in-verified-rag** (failure mode specific)
5. **gpt4-verification-exploitation** (direct, attention-grabbing)

**Recommendation:** `rag-verification-failure` — clear, explains the key finding, professional.

---

## COMMIT SEQUENCE (after cleanup)

```bash
# 1. Initial cleanup
git add --all
git commit -m "feat: organize project structure for publication"

# 2. Documentation
git commit -m "docs: add comprehensive README and research findings"

# 3. Code organization
git commit -m "refactor: move figures, results, and analysis to docs/"

# 4. License & config
git commit -m "chore: add LICENSE, updated .gitignore, setup.py"

# 5. Reproducibility
git commit -m "scripts: add reproduction workflow"

# 6. Final polish
git commit -m "chore: remove intermediate/generated files"
```

---

## CODE CLEANUP CHECKLIST

- [ ] Add docstrings to all public functions in `src/`
- [ ] Remove debug print statements
- [ ] Consistent naming: `tau` vs `threshold` (pick one)
- [ ] Type hints on all function signatures
- [ ] Move all constants to `config.py`
- [ ] Add inline comments only for non-obvious logic
- [ ] Verify tests pass: `pytest tests/`
- [ ] Check for unused imports: `python -m pip install autoflake` + `autoflake --remove-all-unused-imports -r src/`

---

## README OUTLINE (Draft)

```markdown
# When Verification Fails: False Positives in RAG Claim Verification

**An analysis of failure modes in similarity-based claim verification for LLM-augmented generation.**

## Overview
This project investigates claim-level verification in RAG systems using GPT-4o and 
NLI-based verification. We discovered an **82% false positive rate** where verified 
claims pass semantic checks but contribute to factually incorrect answers.

## Main Finding
While verification marked 100% of claims as "supported," only 18% of answers were 
correct. Analysis reveals GPT-4o exploits verification through **hedging**—producing 
vague claims that pass similarity checks without committing to correct answers.

## Key Results
- 82% false positive rate in semantic verification
- 71% of false positives driven by hedging/epistemic evasion
- Verification passes for claims that don't answer the question
- Modern LLMs learn to exploit semantic similarity

## Architecture
[ASCII diagram here]

## Installation
## Quick Start
## Results
## Failure Modes
## Limitations
## Future Work
## Citation
## Contact
```

---

## NEXT STEPS (Execution Order)

1. ✅ Create professional README (I'll draft)
2. ✅ Create .gitignore
3. ✅ Create LICENSE
4. ✅ Create docs/ structure
5. ✅ Move/delete files
6. ✅ Add setup.py
7. ✅ Add reproduce_results.sh
8. ✅ Verify all tests pass
9. ✅ Make first professional commit

---

**Ready to execute? I'll start with files 1-4 below.**
