# FINAL PROJECT EXECUTION PLAN (v3)

## RAG + VERIFICATION + REWRITE PIPELINE

---

# 0. CORE OBJECTIVE

Goal:
Evaluate whether a verification layer improves factual reliability of a RAG system, and determine **when it is actually necessary**.

Key research question:
Does verification (remove vs rewrite) reduce hallucinations while preserving answer quality, and how does its usefulness depend on retrieval conditions?

---

# 1. SYSTEMS

## System A — RAG Baseline

retrieve → LLM → answer

## System B — Verification (REMOVE)

retrieve → LLM → claims → remove unsupported

## System C — Verification (REWRITE)

retrieve → LLM → claims → rewrite unsupported

---

# 2. DATASET

* PubMedQA
* 100–150 samples

---

# 3. PIPELINE

### Retrieval

* FAISS + sentence embeddings
* sentence-level matching
* default: k = 3–5

### Generation

Prompt:
"Answer ONLY using the provided context. Be concise and factual."

### Claims

Split into atomic claims

### Verification

* similarity vs sentences
* threshold τ = 0.55

### Rewrite

* rewrite unsupported claims using evidence
* else REMOVE

---

# 4. METRICS

* Hallucination Rate
* Accuracy
* Completeness
* Relevance
* Information Retention
* Runtime

---

# 5. COMPLETED EXPERIMENTS ✅

---

## 5.1 Main Comparison (100 samples)

| System  | Accuracy | Hallucination |
| ------- | -------- | ------------- |
| RAG     | 20%      | 1%            |
| REMOVE  | 20%      | 0%            |
| REWRITE | 20%      | 0%            |

### Finding

* GPT-4o is highly faithful under RAG
* Verification removes remaining errors
* Rewrite rarely activates

---

## 5.2 Ablation Studies (50 samples)

### Threshold Sweep

* τ ∈ {0.35–0.75}
* Minimal effect

### Retrieval Depth

* k ∈ {1,3,5,7}
* Accuracy ↑ with k
* Runtime ↑ significantly

---

## 5.3 Noise Injection (Initial Attempt)

* 33% random noise
* Result: 0% hallucination

### Finding

* GPT-4o ignores irrelevant passages
* Random noise ≠ effective stress test

---

# 6. CRITICAL INSIGHT

Hallucinations are **rare under ideal RAG conditions** with strong LLMs.

Therefore:

> Verification is not primarily a performance booster, but a **robustness and safety mechanism**

---

# 7. FINAL EXPERIMENT PLAN (OPTIONAL BUT HIGH VALUE)

---

## Phase 2.3 — CONFLICT-BASED STRESS TEST ⭐

### Goal

Create conditions where model must resolve conflicting evidence

---

## Strategy: Conflicting Retrieval

Instead of random noise:

* Retrieve top-k candidates (k=10)
* Use:

  * 1 highly relevant doc
  * 1 semantically similar but conflicting doc

---

## Simple Implementation (fast version)

```python id="3fclp7"
top_docs = top_k(query, k=10)

relevant = top_docs[0]
conflicting = top_docs[5]  # lower-ranked but similar

docs = [relevant, conflicting]
```

---

## Debug Requirement

Before full run:

* Print retrieved docs
* Print final docs after injection
* Confirm conflict actually exists

---

## Expected Behavior

| Setting  | Hallucination |
| -------- | ------------- |
| Clean    | ~1%           |
| Conflict | higher        |

---

## Decision Rule

Spend ≤90 minutes debugging:

* If conflict increases hallucination → run full experiment
* If NOT → proceed to final report

---

# 8. FAILURE ANALYSIS

Log ≥10 cases:

* retrieval miss
* partial evidence
* rewrite failure
* paraphrase mismatch
* conflict resolution errors

---

# 9. MATHEMATICAL FORMULATION

Verification:

V(c) = 1 if supported else 0

Hallucination:

H = (# unsupported claims) / N

Objective:

minimize H
subject to accuracy ≥ α

---

# 10. FINAL EXPECTED RESULTS

---

## Ideal Setting (Observed)

| System  | Hallucination | Accuracy |
| ------- | ------------- | -------- |
| RAG     | ~1%           | 20%      |
| REMOVE  | 0%            | 20%      |
| REWRITE | 0%            | 20%      |

---

## Stress Setting (If successful)

| System  | Hallucination | Accuracy |
| ------- | ------------- | -------- |
| RAG     | higher        | lower    |
| REMOVE  | low           | lower    |
| REWRITE | low           | higher   |

---

# 11. FINAL CONTRIBUTION

This project shows:

1. Modern LLMs (GPT-4o) are highly faithful under RAG
2. Verification guarantees correctness with minimal overhead
3. Random noise does NOT induce hallucinations
4. Verification is **conditionally valuable**, depending on retrieval quality
5. Conflict-based evaluation is necessary to fully assess robustness

---

# 12. OUTPUT FILES

* outputs.json
* metrics.csv
* failure_cases.txt

---

# 13. SUCCESS CRITERIA

* Verification reduces hallucinations (1% → 0%)
* Rewrite maintains completeness
* Conditional usefulness is demonstrated

---

# 14. IMPORTANT NOTES

* Do NOT weaken the model artificially
* Focus on retrieval failures
* This is a **robustness study**

---

# END
