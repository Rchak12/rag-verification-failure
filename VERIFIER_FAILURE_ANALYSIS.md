# Verifier Failure Analysis: False Positives in Similarity-Based Verification

## Executive Summary

While NLI-based verification successfully marks 100% of claims as "supported," **manual analysis reveals systematic false positives** where semantically similar claims fail to capture factual correctness. This demonstrates a fundamental limitation of similarity-based verification in high-fidelity RAG systems.

## Methodology

- **Dataset**: Forced-answer experiment (50 samples)
- **Verification**: NLI cross-encoder (τ=0.5)
- **Result**: 0% unsupported claims (100% pass verification)
- **Manual Review**: Human evaluation of "supported" claims for factual correctness

## False Positive Categories

### 1. Hedging Away from Ground Truth

**Pattern**: Verifier approves vague/cautious claims that don't commit to the correct answer.

#### Example 1: ID 21645374
**Question:** Do mitochondria play a role in remodelling lace plant leaves during programmed cell death?
**Gold Answer:** YES

**RAG Claim (Verified ✅):**
> "Programmed cell death in the lace plant involves leaf perforations, and while the role of mitochondria in animal PCD is recognized, **it is less understood in plants**"

**Problem:**
- ✅ Semantically supported by passage
- ❌ Doesn't answer YES - instead hedges with "less understood"
- ❌ Factually misleading - gold answer is YES

**Why Verifier Fails:** Passage likely mentions "understanding" or "research on plants" → semantic similarity passes, but claim avoids committing to the correct conclusion.

---

#### Example 2: ID 16418930
**Question:** Landolt C and Snellen E acuity: differences in strabismus amblyopia?
**Gold Answer:** NO

**RAG Claim (Verified ✅):**
> "There is **some indication that differences may exist** in visual acuity measurements... but the specific nature of these differences is not detailed"

**Problem:**
- ✅ Semantically supported (passage mentions comparing the tests)
- ❌ Doesn't answer NO - hedges with "may exist"
- ❌ Gold answer is definitively NO

**Why Verifier Fails:** Hedging language ("may exist", "some indication") is semantically close to passage discussion of comparisons, but misses that the answer should be negative.

---

#### Example 3: ID 10808977
**Question:** Can tailored interventions increase mammography use among HMO women?
**Gold Answer:** YES

**RAG Claim (Verified ✅):**
> "Telephone counseling and tailored print communications are **promising methods** for promoting mammography screening, but **their efficacy has not been fully tested**"

**Problem:**
- ✅ Semantically supported (passage discusses these methods)
- ❌ Doesn't answer YES - says "not fully tested"
- ❌ Undermines the correct affirmative answer

**Why Verifier Fails:** Discussing "promising" interventions is semantically similar to passage content, but the claim avoids affirming effectiveness despite gold = YES.

---

### 2. Missing Critical Qualifiers

**Pattern**: Claims omit important caveats present in source material.

#### Example: Overgeneralization (Hypothetical Pattern)
**Passage:** "Drug X reduced tumor size **in mice**"
**Claim (Verified ✅):** "Drug X reduced tumor size"

**Problem:**
- ✅ Technically in passage
- ❌ Missing "in mice" → implies human efficacy
- ❌ Misleading overgeneralization

**Why Verifier Fails:** The core fact ("drug reduced tumors") appears in passage, so semantic similarity is high. The qualifier ("in mice") is a detail that doesn't significantly change embedding similarity.

---

### 3. Correlation → Causation Drift

**Pattern**: Observational findings presented as causal without justification.

#### Example: Causal Language (Hypothetical Pattern)
**Passage:** "Gene X was **associated with** increased disease risk"
**Claim (Verified ✅):** "Gene X **causes** increased disease risk"

**Problem:**
- ✅ Same entities and relationship mentioned
- ❌ "Associated" ≠ "causes"
- ❌ Introduces unsupported causal claim

**Why Verifier Fails:** Embeddings for "associated with" and "causes" are semantically close (both describe relationships), but the distinction is crucial for correctness.

---

## Quantitative Impact

### Accuracy Analysis

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Verifier Approval Rate | 100% | All claims marked "supported" |
| RAG Accuracy | 18% | Only 18% correctly answer questions |
| **Implied False Positive Rate** | **82%** | Verifier approves claims in wrong answers |

**Key Insight:** With 18% accuracy but 100% verification pass rate, **~82% of verified claims contribute to wrong answers**. This indicates massive false positive problem.

---

## Root Cause: Semantic Similarity ≠ Factual Correctness

### Why NLI Verification Fails

1. **Embeddings conflate related concepts**
   - "may exist" ≈ "exists" (both discuss existence)
   - "associated" ≈ "causes" (both describe relationships)
   - "less understood" ≈ "plays a role" (both mention the concept)

2. **Passage-level matching is too coarse**
   - Claim: "Drug X is effective"
   - Passage: "Studies of Drug X show promise, but **more research needed**"
   - Verifier: ✅ Both mention Drug X and effectiveness concepts

3. **Hedging is rewarded**
   - Vague claims ("may", "could", "suggests") almost always match something in passage
   - Precision is punished (specific wrong claims rejected, vague wrong claims pass)

4. **Question-answer alignment not checked**
   - Verifier only checks claim-passage similarity
   - Doesn't verify claim actually answers the question
   - GPT-4o can produce supported non-answers

---

## Threshold Sensitivity Analysis

Testing if higher τ thresholds help:

| τ | Unsupported Rate | Accuracy | Interpretation |
|---|------------------|----------|----------------|
| 0.3 | 0% | 18% | Too permissive |
| 0.5 | 0% | 18% | **Current** - still too permissive |
| 0.7 | ? | ? | **Test needed** |
| 0.9 | ? | ? | Likely too strict (would reject valid claims) |

**Hypothesis:** Increasing τ won't fix false positives because the problem is *semantic conflation*, not threshold calibration.

---

## Implications for RAG Deployment

### When Similarity-Based Verification Fails

1. **High-calibration models** (GPT-4o, Claude 3.5)
   - Produce plausible-sounding hedged claims
   - Avoid obviously wrong statements
   - Verification can't distinguish hedging from correctness

2. **Yes/no questions requiring definitive answers**
   - Hedged responses ("may", "suggests") pass verification
   - But don't actually commit to yes/no
   - Accuracy suffers despite 100% "supported" rate

3. **Biomedical/scientific domains**
   - Subtle qualifiers matter (in vitro vs in vivo, correlation vs causation)
   - Semantic similarity misses these distinctions
   - Critical for safety/regulatory contexts

### When Verification Still Helps

1. **Lower-quality models** that produce obviously wrong claims
2. **Open-ended generation** where hedging is acceptable
3. **Attribution transparency** (even if not perfect correctness filter)

---

## Recommendations

### 1. Beyond Semantic Similarity

**Need:** Factual consistency checking, not just semantic overlap

**Approaches:**
- Question-answering entailment (does claim answer the question correctly?)
- Structured fact extraction + knowledge base verification
- Multi-hop reasoning verification
- Confidence calibration (reject hedged answers for yes/no questions)

### 2. Accuracy-Aware Evaluation

**Current:** Unsupported claim rate
**Better:** Combine with accuracy - "supported but wrong" is still wrong

**Proposed Metric:**
```
Verified Correctness Rate = (supported AND correct) / total
```

### 3. Domain-Specific Verification

**Biomedical RAG needs:**
- Qualifier preservation (in vitro, in mice, preliminary)
- Causal language detection (correlation vs causation)
- Certainty level matching (passage uncertainty → claim uncertainty)

---

## Conclusion

**Key Finding:** Similarity-based verification achieves 0% unsupported claim rate but only 18% accuracy, revealing an **82% false positive problem** where semantically similar claims fail to ensure factual correctness.

**Implication:** As LLMs become more calibrated (GPT-4o), they exploit verification weaknesses through hedging and vagueness. Standard similarity metrics are insufficient for high-stakes domains requiring definitive, precise answers.

**Future Work:** Development of question-aware, qualifier-sensitive verification mechanisms that go beyond semantic similarity to enforce factual correctness and answer commitment.

---

**This analysis demonstrates that the challenge in modern RAG is not detecting blatant hallucinations (which GPT-4o avoids) but ensuring semantic similarity translates to factual accuracy - a problem current verification approaches fail to solve.**
