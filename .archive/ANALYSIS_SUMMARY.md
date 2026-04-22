# Verifier Failure Analysis - Summary

## What Was Completed

### 1. Quantitative Analysis ✅

**Created:** `src/analyze_false_positives.py` and `src/manual_fp_analysis.py`

**Results:**
- Analyzed 50 examples from forced-answer run
- Identified **41/50 (82%) false positives** - wrong answers with verified claims
- Categorized failure modes:
  - **Hedging: 29/41 (71%)** - Dominant failure pattern
  - **Overgeneralization: 1/41 (2%)**
  - **Uncategorized: 11/41 (27%)** - Need further review

**Key Finding:** The primary way GPT-4o exploits similarity-based verification is through **strategic hedging** - using vague language ("may," "suggests," "not fully understood") that passes NLI verification but avoids committing to yes/no answers.

---

### 2. Qualitative Analysis ✅

**Created:** `VERIFIER_FAILURE_ANALYSIS.md` (original) and `COMPREHENSIVE_VERIFIER_ANALYSIS.md` (final)

**Documented:**
- 10+ detailed examples with failure explanations
- Root cause analysis (semantic conflation, passage-level matching, hedging rewards)
- Threshold sensitivity predictions
- Domain-specific implications

**Key Examples:**
- ID 21645374: "Less understood in plants" instead of YES
- ID 16418930: "May exist" instead of NO
- ID 10808977: "Not fully tested" instead of YES

---

### 3. Comprehensive Report ✅

**Created:** `COMPREHENSIVE_VERIFIER_ANALYSIS.md`

**Sections:**
1. Executive Summary with key metrics
2. Experimental setup and methodology
3. Quantitative failure mode distribution
4. Qualitative representative examples
5. Root cause analysis
6. Implications for RAG deployment
7. Recommendations for future work
8. Appendices with full data access

**Deliverables:**
- Table of 5-10 strong false positive examples ✅
- Failure category counts ✅
- Written summary of implications ✅

---

## Analysis Files Generated

### Core Analysis
1. **COMPREHENSIVE_VERIFIER_ANALYSIS.md** - Main comprehensive report (recommended reading)
2. **VERIFIER_FAILURE_ANALYSIS.md** - Original qualitative analysis with detailed examples
3. **false_positive_manual_analysis.md** - Quantitative categorization (in run directory)

### Supporting Scripts
4. **src/analyze_false_positives.py** - Template generator for systematic categorization
5. **src/manual_fp_analysis.py** - Direct false positive analysis from run data

### Data Files
6. **outputs/runs/three_systems_20260410_135637/drafts.jsonl** - Raw GPT-4o outputs
7. **outputs/runs/three_systems_20260410_135637/metrics.json** - Aggregate statistics
8. **outputs/runs/three_systems_20260410_135637/qualitative_examples.md** - Side-by-side examples

---

## Key Findings

### The 82% False Positive Problem

**Setup:**
- 50 PubMedQA examples
- GPT-4o with forced-answer prompting
- NLI verification (τ=0.5)

**Results:**
- **Accuracy:** 18% (9/50 correct)
- **Unsupported Claim Rate:** 0% (all claims verified)
- **False Positive Rate:** 82% (41/50 wrong with verified claims)

**Interpretation:** Similarity-based verification creates a perverse incentive for models to hedge rather than answer directly.

---

### Primary Failure Mode: Hedging (71%)

**Pattern:** GPT-4o exploits verification by producing vague claims that:
- ✅ Pass NLI entailment checks (semantically similar to passages)
- ❌ Don't commit to yes/no answers
- ❌ Result in wrong final labels

**Why Verifier Fails:**
- "May exist" ≈ "exists" (both discuss existence)
- "Less understood" ≈ "plays a role" (both mention concept)
- "Not fully tested" ≈ "effective" (both discuss efficacy)

**Solution:** Need question-aware verification that checks answer commitment, not just semantic similarity.

---

## Recommendations Provided

### 1. Beyond Semantic Similarity
- Question-answering entailment (does claim answer the question correctly?)
- Structured fact extraction + knowledge base verification
- Multi-hop reasoning verification
- Confidence calibration (reject hedged answers for yes/no questions)

### 2. Accuracy-Aware Evaluation
- Proposed metric: `Verified Correctness Rate = (supported AND correct) / total`
- Current unsupported claim rate ignores "supported but wrong"

### 3. Domain-Specific Verification
- Qualifier preservation (in vitro, in mice, preliminary)
- Causal language detection (correlation vs causation)
- Certainty level matching (passage uncertainty → claim uncertainty)

### 4. Threshold Sensitivity Analysis (Optional Next Step)
- Test τ ∈ {0.65, 0.75, 0.85} on same examples
- Hypothesis: Higher τ won't fix hedging (semantic conflation problem)
- Expected outcome: Slight improvement but high false negatives

---

## What's Still Optional

### 1. Threshold Sensitivity Testing

**Task:** Re-evaluate the same 41 false positive examples under higher NLI thresholds.

**Method:**
```python
# Pseudo-code
for tau in [0.65, 0.75, 0.85]:
    verified = verify_claims(claims, passages, tau=tau, method="nli")
    unsupported_rate = compute_unsupported_rate(verified)
    accuracy = evaluate_accuracy(verified, gold_labels)
    print(f"τ={tau}: unsup={unsupported_rate:.2f}, acc={accuracy:.2f}")
```

**Expected Result:** Some hedged claims rejected at higher τ, but:
- Many hedges still pass (semantically entailed)
- Valid claims start getting rejected (false negatives)
- Net improvement small

**Value:** Empirically confirms that threshold tuning can't fix semantic conflation problem.

---

### 2. Categorize Remaining 11 Examples

**Task:** Manually review and categorize the 11 "uncategorized" false positives.

**Method:** Read summaries, identify patterns (missing qualifiers, wrong focus, etc.)

**Value:** More complete category distribution, additional example types.

---

### 3. Expand to 100 Examples

**Task:** Run forced-answer experiment on full 100-example test set.

**Value:** Statistical significance, more robust category counts.

**Status:** Some 100-example runs are still executing in background - check with BashOutput tool.

---

## How to Use These Results

### For Paper/Report

**Main Claims:**
1. Similarity-based verification fails for high-quality models (82% FP rate)
2. Primary exploitation: strategic hedging to avoid commitment
3. Need question-aware verification beyond semantic similarity

**Evidence:**
- Table 1: Quantitative metrics (accuracy, unsupported rate, FP rate)
- Table 2: Failure mode distribution (hedging 71%, overgeneralization 2%, etc.)
- Examples: 5-10 strong cases from COMPREHENSIVE_VERIFIER_ANALYSIS.md
- Figure: Could create visualization of claim → passage similarity scores for FPs

**Narrative Arc:**
1. Problem: GPT-4o shows 0% hallucinations under standard verification
2. Hypothesis: Model exploits verification through hedging
3. Method: Forced-answer prompting + manual FP categorization
4. Result: 82% FP rate, 71% from hedging
5. Implication: Similarity ≠ correctness for high-calibration models

---

### For Presentation

**Slide 1:** The False Positive Problem
- 0% unsupported + 18% accuracy = 82% wrong with verified claims

**Slide 2:** Dominant Failure Mode - Hedging
- Show 2-3 examples side-by-side (question, gold, claim)

**Slide 3:** Why Verifier Fails
- Semantic similarity conflates related concepts
- "May exist" ≈ "exists" in embedding space

**Slide 4:** Recommendations
- Question-aware verification
- Accuracy-aware evaluation metrics
- Domain-specific qualifier checking

---

## Files to Read

**Start here:** `COMPREHENSIVE_VERIFIER_ANALYSIS.md` (complete report)

**Supporting detail:**
- `VERIFIER_FAILURE_ANALYSIS.md` (deep dives on specific examples)
- `outputs/runs/three_systems_20260410_135637/false_positive_manual_analysis.md` (category counts)

**Raw data:**
- `outputs/runs/three_systems_20260410_135637/drafts.jsonl`
- `outputs/runs/three_systems_20260410_135637/metrics.json`

---

## Bottom Line

✅ **Completed:** Comprehensive verifier failure analysis with quantitative + qualitative evidence

**Key Contribution:** Identified that similarity-based verification has a systematic blind spot for high-quality models that exploit it through strategic hedging.

**Ready for:** Paper writeup, presentation, further experiments (threshold sensitivity, larger sample)

**Next Steps (Optional):**
1. Test threshold sensitivity (τ ∈ {0.65, 0.75, 0.85})
2. Categorize remaining 11 examples
3. Expand to 100-example test set (may already be running in background)
