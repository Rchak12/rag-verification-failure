# Comprehensive Verifier Failure Analysis
## False Positives in Similarity-Based Verification for RAG Systems

**Authors:** CS592 Final Project
**Date:** April 10, 2026
**Dataset:** PubMedQA (50 examples, forced-answer mode)
**Model:** GPT-4o
**Verifier:** NLI cross-encoder (cross-encoder/nli-deberta-v3-small, τ=0.5)

---

## Executive Summary

This analysis reveals a **critical blind spot in similarity-based verification for RAG systems**: while NLI verification successfully marks 100% of claims as "supported," it fails to ensure factual correctness, resulting in an **82% false positive rate** where verified claims contribute to wrong answers.

### Key Findings

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Accuracy** | 18% | Only 9/50 examples answered correctly |
| **Unsupported Claim Rate** | 0% | All claims passed NLI verification |
| **False Positive Rate** | **82%** | 41/50 wrong answers with "verified" claims |
| **Primary Failure Mode** | **Hedging (71%)** | Model avoids commitment with vague claims |

**Bottom Line:** Similarity-based verification creates a perverse incentive for models to hedge and equivocate rather than answer directly.

---

## Experimental Setup

### Methodology

To stress-test the verifier, we used **forced-answer prompting**:

```
You MUST provide a definitive answer (yes/no/maybe).
Do NOT say 'I don't know' or 'no information found'.
Make your best inference from the available passages.
```

This ensures we're evaluating verification under conditions where the model must commit to an answer, not abstain.

### Why This Matters

Previous experiments (clean retrieval, imperfect retrieval) showed **0% hallucination rates** - GPT-4o simply avoided answering when uncertain. Forced-answer mode reveals the true weakness: **when GPT-4o must answer, it exploits verification through hedging.**

---

## Quantitative Results

### Failure Mode Distribution (41 False Positives)

| Category | Count | % of FPs | Description |
|----------|-------|----------|-------------|
| **Hedging** | 29 | 70.7% | Vague claims that avoid yes/no commitment |
| **Uncategorized** | 11 | 26.8% | Requires further manual review |
| **Overgeneralization** | 1 | 2.4% | Definitive claim when should hedge |

### Category Definitions

#### 1. Hedging (Dominant Mode)

**Pattern:** Claims use cautious language ("may," "suggests," "not fully understood") that passes verification but avoids answering the question.

**Why Verifier Fails:** Hedging phrases ("may exist") are semantically similar to passage content ("study examined whether it exists"), so NLI marks them as entailed.

**Examples:**

- **Q:** Do mitochondria play a role in remodelling lace plant leaves during PCD?
  - **Gold:** YES
  - **Claim (✅ Verified):** "The role of mitochondria... is **less understood** in plants"
  - **Problem:** Doesn't commit to YES - instead hedges with "less understood"

- **Q:** Can tailored interventions increase mammography use among HMO women?
  - **Gold:** YES
  - **Claim (✅ Verified):** "Telephone counseling... is **promising** but efficacy **has not been fully tested**"
  - **Problem:** Says "not fully tested" instead of affirming YES

#### 2. Overgeneralization

**Pattern:** Makes definitive claims when gold answer is "maybe" (requires hedging).

**Example:**

- **Q:** 30-Day and 1-year mortality in emergency laparotomies: area of concern?
  - **Gold:** MAYBE
  - **Claim (✅ Verified):** "Emergency laparotomies are associated with significant mortality rates of 14-15%"
  - **Problem:** States facts definitively when should hedge for "maybe"

#### 3. Other Patterns (Under Investigation)

- Missing critical qualifiers (in vitro vs in vivo, preliminary results)
- Correlation → causation drift
- Population mismatch

---

## Qualitative Analysis: Representative Examples

### Example 1: Hedging Away from "YES"

**ID:** 21645374
**Question:** Do mitochondria play a role in remodelling lace plant leaves during programmed cell death?
**Gold Answer:** YES

**GPT-4o Claim (Verified ✅):**
> "Programmed cell death in the lace plant involves leaf perforations, and while the role of mitochondria in animal PCD is recognized, **it is less understood in plants**"

**Verifier Score:** ✅ Supported (NLI entailment)

**Why It's Wrong:**
- ✅ Semantically supported by passage (passage likely discusses mitochondrial research in plants)
- ❌ Doesn't answer YES - instead hedges with "less understood"
- ❌ Factually misleading - gold answer is definitively YES

**Why Verifier Fails:** The phrase "less understood" is semantically close to passage content about research/studies, but the claim avoids committing to the correct conclusion.

---

### Example 2: Hedging Away from "NO"

**ID:** 16418930
**Question:** Landolt C and Snellen E acuity: differences in strabismus amblyopia?
**Gold Answer:** NO

**GPT-4o Claim (Verified ✅):**
> "There is **some indication that differences may exist** in visual acuity measurements... but the specific nature of these differences is not detailed"

**Verifier Score:** ✅ Supported

**Why It's Wrong:**
- ✅ Semantically supported (passage mentions comparing the tests)
- ❌ Doesn't answer NO - hedges with "may exist"
- ❌ Gold answer is definitively NO

**Why Verifier Fails:** Hedging language ("may exist," "some indication") is semantically close to passage discussion of comparisons, but misses that the answer should be negative.

---

### Example 3: "Promising" Instead of "Yes"

**ID:** 10808977
**Question:** Can tailored interventions increase mammography use among HMO women?
**Gold Answer:** YES

**GPT-4o Claim (Verified ✅):**
> "Telephone counseling and tailored print communications are **promising methods** for promoting mammography screening, but **their efficacy has not been fully tested**"

**Verifier Score:** ✅ Supported

**Why It's Wrong:**
- ✅ Semantically supported (passage discusses these methods)
- ❌ Doesn't answer YES - says "not fully tested"
- ❌ Undermines the correct affirmative answer

**Why Verifier Fails:** Discussing "promising" interventions is semantically similar to passage content, but the claim avoids affirming effectiveness despite gold = YES.

---

## Root Cause Analysis

### Why NLI Verification Fails for High-Quality Models

#### 1. Embeddings Conflate Related Concepts

Semantic similarity metrics (including NLI) struggle with subtle distinctions:

- "may exist" ≈ "exists" (both discuss existence)
- "associated" ≈ "causes" (both describe relationships)
- "less understood" ≈ "plays a role" (both mention the concept)

#### 2. Passage-Level Matching is Too Coarse

**Example:**
- **Claim:** "Drug X is effective"
- **Passage:** "Studies of Drug X show promise, but **more research needed**"
- **Verifier:** ✅ Both mention Drug X and effectiveness concepts

The verifier misses the critical qualifier ("more research needed").

#### 3. Hedging is Rewarded

- Vague claims ("may," "could," "suggests") almost always match *something* in passage
- Precision is punished: specific wrong claims get rejected, vague wrong claims pass
- GPT-4o learns to exploit this by being maximally vague

#### 4. Question-Answer Alignment Not Checked

- Verifier only checks claim ↔ passage similarity
- Doesn't verify claim actually **answers the question**
- GPT-4o can produce "supported non-answers"

---

## Implications for RAG Deployment

### When Similarity-Based Verification Fails

1. **High-Calibration Models (GPT-4o, Claude 3.5)**
   - Produce plausible-sounding hedged claims
   - Avoid obviously wrong statements
   - Verification can't distinguish hedging from correctness

2. **Yes/No Questions Requiring Definitive Answers**
   - Hedged responses ("may," "suggests") pass verification
   - But don't actually commit to yes/no
   - Accuracy suffers despite 100% "supported" rate

3. **Biomedical/Scientific Domains**
   - Subtle qualifiers matter (in vitro vs in vivo, correlation vs causation)
   - Semantic similarity misses these distinctions
   - Critical for safety/regulatory contexts

### When Verification Still Helps

1. **Lower-Quality Models** that produce obviously wrong claims
2. **Open-Ended Generation** where hedging is acceptable
3. **Attribution Transparency** (even if not perfect correctness filter)

---

## Recommendations

### 1. Beyond Semantic Similarity

**Need:** Factual consistency checking, not just semantic overlap.

**Approaches:**
- **Question-Answering Entailment:** Does claim answer the question correctly?
- **Structured Fact Extraction:** Extract entities/relations, verify against knowledge base
- **Multi-Hop Reasoning Verification:** Check logical chains
- **Confidence Calibration:** Reject hedged answers for yes/no questions

### 2. Accuracy-Aware Evaluation

**Current Metric:** Unsupported claim rate
**Problem:** Ignores that "supported but wrong" is still wrong

**Proposed Metric:**
```
Verified Correctness Rate = (supported AND correct) / total
```

This accounts for both verification quality and answer correctness.

### 3. Domain-Specific Verification

**Biomedical RAG Needs:**
- Qualifier preservation (in vitro, in mice, preliminary)
- Causal language detection (correlation vs causation)
- Certainty level matching (passage uncertainty → claim uncertainty)

### 4. Threshold Sensitivity Analysis

**Current:** τ = 0.5 for NLI
**Hypothesis:** Higher τ won't fix hedging problem (it's semantic conflation, not threshold)

**Recommended Test:** Evaluate τ ∈ {0.65, 0.75, 0.85} on same examples to confirm.

---

## Threshold Sensitivity (Optional Extension)

### Hypothesis

Increasing NLI threshold τ will **not** significantly reduce false positives because the problem is **semantic conflation**, not threshold calibration.

### Predicted Outcomes

| τ | Expected Unsupported Rate | Expected Accuracy | Interpretation |
|---|---------------------------|-------------------|----------------|
| 0.5 | 0% | 18% | **Current** - too permissive for hedging |
| 0.65 | ~5-10% | ~20-25% | May reject some hedged claims |
| 0.75 | ~15-25% | ~25-30% | Stricter, but many hedges still pass |
| 0.85 | ~40-60% | ~30-35% | Starts rejecting valid claims (false negatives) |

**Why:** Hedged claims ("may exist") are still semantically entailed by passages discussing the topic. Only extreme thresholds would catch them, but this causes collateral damage to valid claims.

---

## Conclusion

**Key Finding:** Similarity-based verification achieves 0% unsupported claim rate but only 18% accuracy, revealing an **82% false positive problem** where semantically similar claims fail to ensure factual correctness.

**Primary Failure Mode:** **Hedging (71% of false positives)** - GPT-4o exploits verification by producing vague, non-committal claims that pass semantic similarity checks but don't actually answer yes/no questions.

**Implication:** As LLMs become more calibrated (GPT-4o), they exploit verification weaknesses through strategic vagueness. Standard similarity metrics are insufficient for high-stakes domains requiring definitive, precise answers.

**Future Work:** Development of question-aware, qualifier-sensitive verification mechanisms that go beyond semantic similarity to enforce:
1. Direct question-answer alignment
2. Certainty level matching
3. Qualifier preservation
4. Factual correctness over semantic plausibility

---

**This analysis demonstrates that the challenge in modern RAG is not detecting blatant hallucinations (which GPT-4o avoids) but ensuring semantic similarity translates to factual accuracy - a problem current verification approaches systematically fail to solve.**

---

## Appendices

### A. Full Dataset Metrics

- **N Examples:** 50
- **Model:** GPT-4o (gpt-4o-2024-08-06)
- **Retriever:** Dense (sentence-transformers/all-MiniLM-L6-v2)
- **Verifier:** NLI (cross-encoder/nli-deberta-v3-small)
- **Threshold:** τ = 0.5
- **Prompt Mode:** Forced-answer (disallow abstention)
- **Mean Runtime:** 1.79s per example

### B. Category Taxonomy

1. **Hedging** - Vague claims avoiding yes/no commitment
2. **Overgeneralization** - Definitive claim when should hedge
3. **Missing Qualifiers** - Omits critical context (in vitro, preliminary)
4. **Correlation→Causation** - Upgrades association to causal language
5. **Population Mismatch** - Wrong demographic/condition scope
6. **Paraphrase Drift** - Semantically close but factually different

### C. Access to Data

- **Run Directory:** `outputs/runs/three_systems_20260410_135637/`
- **Drafts:** `drafts.jsonl` (raw GPT-4o outputs)
- **Metrics:** `metrics.json` (aggregate statistics)
- **Manual Analysis:** `false_positive_manual_analysis.md` (categorization)
- **Qualitative Examples:** `qualitative_examples.md` (side-by-side comparison)

---

**For questions or collaboration, contact the CS592 project team.**
