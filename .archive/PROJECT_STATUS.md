# PROJECT STATUS — CS592 Verified RAG

**Date:** April 10, 2026  
**Current Phase:** System validation & experiment execution  
**Overall Progress:** 60% (implementation complete, experiments pending)

---

## 🎯 CORE OBJECTIVE

Evaluate whether a verification layer (with REWRITE option) improves factual reliability of RAG systems, and determine **when it is actually necessary** (especially under imperfect retrieval).

**Key Research Question:**  
Does verification (remove vs rewrite) reduce hallucinations while preserving answer quality? How does usefulness depend on retrieval conditions?

---

## ✅ WHAT'S IMPLEMENTED

### Core Pipeline (100% complete)
- [x] **Retrieval** — FAISS + sentence-transformers (all-MiniLM-L6-v2)
- [x] **Generation** — stub backend (offline) + OpenAI (GPT-4o)
- [x] **Claim Extraction** — atomic claim splitting
- [x] **Verification** — cosine similarity (baseline) + NLI cross-encoder (recommended)
- [x] **Repair** — System B (DELETE unsupported) and System C (REWRITE unsupported)

### System Runners (100% complete)
- [x] `src/run_experiment.py` — main runner (supports `--repair delete|rewrite`)
- [x] `src/ablation.py` — τ & k sweeps
- [x] `src/run_three_systems.py` — explicit 3-system comparison (A/B/C)
- [x] `tools/run_one_example.py` — single-example debugger

### Report Infrastructure (70% complete)
- [x] `midterm_report.md` — template with figures
- [x] Figures: `pipeline_diagram.png`, `results_comparison.png`, `verification_example.png`
- [x] `experiment_summary/` — aggregated midterm outputs
- [x] `repro/README.md` — reproducibility instructions
- [x] `scripts/run_systems.sh` — orchestration for system runs
- [x] `scripts/run_ablations.sh` — orchestration for ablations
- [ ] Results tables & failure analysis (pending experiment runs)

### Test Suite
- [x] `tests/test_claims.py`, `test_data.py`, `test_verify.py`, `test_retrieve.py`
- [x] Unit tests for claim extraction, verification (cosine & NLI), retrieval indexing

---

## 🚨 WHAT'S LEFT TO DO

### **PHASE 1: System Validation** (Current)
**Status:** Blocked on environment issues; conda env set up but not yet tested end-to-end

1. **Environment validation** (estimated 10 min)
   - Activate conda env: `conda activate cs592`
   - Quick test: `python -m src.run_experiment --n 5 --backend stub --repair delete`
   - Verify no segfaults, outputs written to `outputs/runs/<timestamp>/`

2. **System tests (N=50, stub backend)** (estimated 30 min)
   ```bash
   python -m src.run_experiment --n 50 --backend stub --repair delete
   python -m src.run_experiment --n 50 --backend stub --repair rewrite
   ```
   Expected outputs:
   - `outputs/runs/<timestamp>/results.csv`
   - `outputs/runs/<timestamp>/metrics.json`
   - `outputs/runs/<timestamp>/qual_examples.md`
   - `outputs/runs/<timestamp>/failure_analysis.md`

---

### **PHASE 2: Ablation Sweeps** (After Phase 1)
**Status:** Code ready, waiting for Phase 1 to complete

1. **Threshold sweep (τ)** — 4 values × 2 repair modes × 50 samples (estimated 2 hours)
   ```bash
   python -m src.ablation --mode tau --n 50 --backend stub --repair delete
   python -m src.ablation --mode tau --n 50 --backend stub --repair rewrite
   ```
   τ ∈ {0.35, 0.45, 0.55, 0.65, 0.75}

2. **Retrieval depth sweep (k)** — 4 values × 2 repair modes × 50 samples (estimated 2 hours)
   ```bash
   python -m src.ablation --mode k --n 50 --backend stub --repair delete
   python -m src.ablation --mode k --n 50 --backend stub --repair rewrite
   ```
   k ∈ {1, 3, 5, 7}

Outputs: `outputs/ablation_tau_*.csv`, `outputs/ablation_k_*.csv`

---

### **PHASE 3: Stress Testing** (After Phase 2)
**Status:** Requires implementation

1. **Low retrieval (k=1)**
   ```bash
   python -m src.run_experiment --n 50 --k 1 --backend stub --repair delete
   python -m src.run_experiment --n 50 --k 1 --backend stub --repair rewrite
   ```

2. **Conflicting evidence injection** (NEW requirement from Final_Steps.md)
   - Retrieve top-10 candidates
   - Use [relevant doc, conflicting doc] (instead of full top-k)
   - Expected: rewrite > delete under conflict

3. **Measurement**
   - Accuracy, hallucination rate, completeness
   - Expected: rewrite preserves more quality under stress

---

### **PHASE 4: Analysis & Report** (After Phases 1–3)
**Status:** Analysis code partially ready; report template exists

1. **Failure case collection** (estimated 1 hour)
   - Aggregate ≥10 failure cases from `outputs/runs/*/failure_analysis.md`
   - Categorize: (1) retrieval miss, (2) partial evidence, (3) rewrite error, (4) paraphrase mismatch, (5) conflict resolution
   - Output: `outputs/failure_cases.md`

2. **LLM-as-judge evaluation** (estimated 2 hours, requires OpenAI API)
   - Implement: `tools/judge.py` — score each answer (correctness/completeness/usefulness 1–5)
   - Collect judgments for all 3 systems
   - Compute mean ± std per system
   - Output: `outputs/judge_scores.json`

3. **Statistical significance tests** (estimated 1 hour)
   - Paired bootstrap or McNemar test
   - Generate plots: bar chart (accuracy, hallucination, completeness), ablation curves
   - Output: `outputs/figures/` (ablation_tau.png, ablation_k.png, comparison.png)

4. **Report finalization** (estimated 2 hours)
   - Update `midterm_report.md` with Results section
   - Embed figures (ablation plots, failure table)
   - Write Discussion (ideal vs imperfect retrieval insights)
   - Optional: render PDF

---

## 📊 EXPECTED RESULTS

### **Ideal Setting (Strong Retrieval)**
| System  | Hallucination | Accuracy | Completeness |
|---------|---------------|----------|--------------|
| RAG     | ~1%           | 20–30%   | High         |
| REMOVE  | 0%            | 20–30%   | Lower        |
| REWRITE | 0%            | 20–30%   | High         |

**Finding:** Verification is a safety guarantee, not a performance booster.

### **Stress Setting (Poor/Conflicting Retrieval)**
| System  | Hallucination | Accuracy | Completeness |
|---------|---------------|----------|--------------|
| RAG     | Higher        | Lower    | High         |
| REMOVE  | Low           | Lower    | Lower        |
| REWRITE | Low           | Higher   | Higher       |

**Finding:** Rewrite > Delete under imperfect retrieval (preserves answer quality).

---

## 📁 KEY FILES & THEIR STATUS

| File | Status | Notes |
|------|--------|-------|
| `src/run_experiment.py` | ✅ Ready | Supports `--repair delete\|rewrite` |
| `src/ablation.py` | ✅ Ready | τ & k sweeps implemented |
| `src/rewrite.py` | ✅ Ready | GPT-4o rewrite (requires OPENAI_API_KEY) |
| `src/verify.py` | ✅ Ready | NLI & cosine methods |
| `src/repair.py` | ✅ Ready | DELETE unsupported claims |
| `scripts/run_systems.sh` | ✅ Ready | Orchestration script |
| `scripts/run_ablations.sh` | ✅ Ready | Ablation orchestration |
| `tools/run_one_example.py` | ✅ Ready | Single-example debugger |
| `tools/judge.py` | ❌ Not started | LLM-as-judge scorer (needed for Phase 4) |
| `outputs/failure_cases.md` | ❌ Not started | Aggregated failure analysis (Phase 4) |
| `midterm_report.md` | 🟡 Partial | Has template + figures; needs Results section |

---

## ⏱️ TIME ESTIMATES

| Phase | Task | Duration | Blocker |
|-------|------|----------|---------|
| 1 | Environment validation | 10 min | None |
| 1 | System tests (N=50) | 30 min | Phase 1 validation |
| 2 | Ablation sweeps (τ & k) | 4 hours | Phase 1 complete |
| 3 | Stress tests (k=1, conflict) | 2 hours | Phase 2 complete |
| 4 | Failure analysis | 1 hour | Phase 3 complete |
| 4 | LLM-as-judge | 2 hours | Phase 3 complete (+ OpenAI key) |
| 4 | Statistical tests & plots | 1 hour | Phase 3 complete |
| 4 | Report finalization | 2 hours | Phase 4 analysis complete |
| **Total** | | **~12 hours** | Start with Phase 1 |

---

## 🔑 CRITICAL DEPENDENCIES

1. **conda env must work** — needs to run without segfaults
2. **OpenAI API key** — required for System C (REWRITE) and LLM-judge; add to `.env`
3. **PubMedQA dataset** — auto-downloaded via HuggingFace `datasets` library on first run
4. **FAISS index** — built on first retrieval call, cached in `outputs/index/`

---

## ✨ SUCCESS CRITERIA (From Final_Steps.md)

1. ✅ Verification eliminates hallucinations (1% → 0%)
2. ✅ Rewrite maintains/improves completeness vs Delete
3. ✅ Conditional usefulness demonstrated (more valuable under poor retrieval)
4. ✅ ≥10 failure cases categorized and analyzed
5. ✅ Report includes tables, figures, and discussion

---

## 🚀 NEXT IMMEDIATE ACTION

**Run Phase 1 validation:**

```bash
conda activate cs592
python -m src.run_experiment --n 5 --backend stub --repair delete --final
```

**Expected output:**
- Prints progress (retrieve → generate → verify → repair)
- Creates `outputs/runs/<TIMESTAMP>/results.csv` (5 rows)
- Creates `outputs/runs/<TIMESTAMP>/metrics.json` (aggregate stats)
- Creates `outputs/runs/<TIMESTAMP>/qual_examples.md` (3 examples)
- **No errors or segfaults**

If successful → proceed to Phase 1 full run (N=50).  
If failed → debug environment issues.

---

## 📝 NOTES

- Stub backend (rule-based) doesn't require OpenAI API key; useful for testing pipeline
- Full experiments can use OpenAI backend when ready
- All ablations/sweeps designed to be parallelizable (can batch or run sequentially)
- Report should emphasize **conditional value of verification** as main finding
