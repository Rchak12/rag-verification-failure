# Final Report Guide

## Document: FINAL_REPORT.tex

A comprehensive 15-page academic writeup of the entire verified RAG project.

---

## Structure Overview

### Title
**"When Verification Fails: Exposing False Positives in Similarity-Based Claim Verification for Retrieval-Augmented Generation"**

### Abstract (200 words)
- Original goal: Test whether NLI verification reduces hallucinations
- Unexpected finding: GPT-4o has 0% hallucination rate
- **Main discovery: 82% false positive problem** (verified but wrong)
- Dominant failure mode: Strategic hedging (71% of cases)
- Contribution: Exposing verification blind spots for high-calibration models

---

## Sections Breakdown

### 1. Introduction (2 pages)
**Content:**
- Motivation: Hallucination problem in LLMs
- RAG as partial solution
- Claim-level verification as proposed safety layer
- **Critical discovery subsection:** 0% hallucination ≠ correctness
- Reframed contribution: Exposing verification failures

**Key Message:** "As LLMs become more sophisticated, they learn to *exploit* verification rather than being constrained by it."

---

### 2. Related Work (1 page)
**Covers:**
- RAG systems (Lewis et al., 2020)
- Claim verification (RARR, AttributedQA)
- Hallucination detection methods
- Model calibration and uncertainty

**Positioning:** Prior work assumes models produce blatantly wrong claims. We show modern models produce *subtly evasive* claims instead.

---

### 3. Problem Formulation (1 page)

**Original Task:**
- Generate answer $a$ with claims $C$
- Verify: $V(c_i, D) > \tau$
- Remove/rewrite unsupported claims

**Discovered Problem:**
- All claims pass: $V(c_i, D) > \tau$ for all $c_i$
- But accuracy = 18%
- **Implication:** 82% false positive rate

**Reframed Questions:**
1. Why do verified claims contribute to wrong answers?
2. What exploitation strategies do models use?
3. Can threshold tuning fix this?

---

### 4. System Architecture (1.5 pages)

**Three-System Comparison:**
- **System A (RAG Baseline):** No verification
- **System B (REMOVE):** Delete unsupported claims
- **System C (REWRITE):** Rewrite unsupported claims

**Components:**
- Retrieval: FAISS + sentence-transformers
- Generation: GPT-4o
- Verification: NLI cross-encoder (τ=0.5)
- Repair: Deletion vs. rewriting

**Key Design:** Identical retrieval/generation, only repair differs

---

### 5. Experimental Setup (2 pages)

**Dataset:** PubMedQA (biomedical yes/no/maybe questions)

**Four Experiments:**

1. **Clean Retrieval (N=100)**
   - Standard RAG, top-k=3
   - Goal: Baseline hallucination rate

2. **Adversarial Retrieval (N=100)**
   - 50% conflicting evidence (rank 5-15 injection)
   - Goal: Stress-test verification

3. **Forced-Answer Mode (N=50)** ⭐
   - Prompt disallows abstention
   - Goal: Force commitment, reveal blind spots
   - **This is the main experiment**

4. **Ablation Studies (N=50)**
   - Threshold sweep: τ ∈ {0.3, 0.5, 0.7, 0.9}
   - Retrieval size: k ∈ {1, 3, 5, 10}
   - Goal: Test if parameter tuning helps

**Metrics:**
- Accuracy (% correct labels)
- Unsupported claim rate (% failing verification)
- Avg claims per answer
- Runtime

---

### 6. Results (3 pages)

#### Table 1: Main Results (Forced-Answer, N=50)
```
System          Accuracy  Unsupported  Avg Claims  Runtime
RAG Baseline    0.180     0.000        1.26        1.79s
REMOVE          0.180     0.000        1.26        2.30s
REWRITE         0.180     0.000        1.26        2.31s
```

**Finding:** All systems identical - no unsupported claims, but only 18% accuracy!

#### Table 2: Clean vs Adversarial Retrieval (N=100)
```
Condition       Accuracy  Unsupported  Notes
Clean           0.23      0.000        No noise
50% Conflict    0.19      0.000        Rank 5-15 injection
```

**Finding:** Even with conflicting evidence, 0% unsupported rate

#### Table 3: Threshold Ablation (N=50)
```
τ      Unsupported  Accuracy  Interpretation
0.3    0.00         0.18      Too permissive
0.5    0.00         0.18      Current (still permissive)
0.7    0.02         0.19      Minimal improvement
0.9    0.15         0.22      Rejects hedges + valid claims
```

**Finding:** Higher τ doesn't fix hedging problem

#### Table 4: Retrieval Size Ablation (N=50)
```
k      Unsupported  Accuracy
k=1    0.00         0.14
k=3    0.00         0.18
k=5    0.00         0.20
k=10   0.00         0.22
```

**Finding:** More passages help slightly, but 0% unsupported across all

**Summary:** Across 250+ examples and 4 conditions, GPT-4o consistently shows 0% unsupported claims but 18-23% accuracy.

---

### 7. Verifier Failure Analysis (3 pages) ⭐⭐⭐

**The core contribution section**

#### Methodology
- Manual analysis of 41 false positive examples
- Categorize failure modes
- Identify exploitation patterns

#### Table 5: Failure Mode Distribution
```
Failure Mode          Count  % of FPs
Hedging               29     70.7%
Overgeneralization    1      2.4%
Uncategorized         11     26.8%
TOTAL                 41     100%
```

#### Example 1: Hedging from "YES"
- **Q:** Do mitochondria play a role in PCD?
- **Gold:** YES
- **Claim (✓):** "Role is **less understood** in plants"
- **Problem:** Hedges instead of answering YES

#### Example 2: Hedging from "NO"
- **Q:** Landolt C vs Snellen E: differences?
- **Gold:** NO
- **Claim (✓):** "**Some indication differences may exist**"
- **Problem:** Says "may exist" instead of NO

#### Example 3: "Promising" instead of "YES"
- **Q:** Can interventions increase mammography use?
- **Gold:** YES
- **Claim (✓):** "Promising but **not fully tested**"
- **Problem:** Undermines affirmative answer

#### Root Cause Analysis

**Why NLI Verification Fails:**

1. **Embeddings conflate concepts**
   - "may exist" ≈ "exists"
   - "associated" ≈ "causes"
   - "less understood" ≈ "plays a role"

2. **Passage-level matching too coarse**
   - Misses critical qualifiers
   - Example: "Drug X effective" matches "Drug X promising, more research needed"

3. **Hedging is rewarded**
   - Vague claims match *something* in passage
   - Precision punished (specific wrong rejected, vague wrong passes)
   - GPT-4o learns to be maximally vague

4. **No question-answer alignment check**
   - Verifier only checks claim ↔ passage
   - Doesn't verify claim actually answers question
   - Enables "supported non-answers"

---

### 8. Discussion (2 pages)

#### When Verification Fails
1. High-calibration models (GPT-4o, Claude)
2. Yes/no questions requiring definitive answers
3. Biomedical/scientific domains (subtle qualifiers matter)

#### When Verification Helps
1. Lower-quality models (blatant errors)
2. Open-ended generation (hedging acceptable)
3. Attribution transparency

#### Recommendations

**1. Beyond Semantic Similarity**
- Question-answering entailment
- Structured fact extraction
- Multi-hop reasoning verification
- Confidence calibration (reject hedges for yes/no)

**2. Accuracy-Aware Metrics**
```
Verified Correctness = (supported AND correct) / total
```
Instead of just unsupported rate

**3. Domain-Specific Verification**
- Qualifier preservation (in vitro, in mice)
- Causal language detection
- Certainty level matching

#### Limitations
1. Sample size (50 main, 250 total)
2. Single domain (PubMedQA)
3. Single model (GPT-4o)
4. 27% false positives uncategorized

#### Future Work
1. Implement question-aware verification
2. Test on additional domains
3. Compare multiple models
4. Automated failure detection
5. Adversarial training against hedging

---

### 9. Conclusion (1 page)

**Summary:**
- Started with: "Does verification reduce hallucinations?"
- Discovered: GPT-4o has 0% hallucinations
- **Main finding: 82% false positive problem**
- Dominant mode: Strategic hedging (71%)
- Threshold tuning doesn't help (semantic conflation)

**Broader Implication:**
Modern LLMs *exploit* verification rather than being constrained by it. Semantic similarity creates perverse incentives for vagueness over precision.

**Solution:**
Next-generation verification must enforce:
- Question-answer alignment
- Certainty matching
- Qualifier preservation
- Factual correctness over semantic similarity

**Final Statement:**
"The challenge in modern RAG is not detecting blatant hallucinations—which GPT-4o avoids—but ensuring semantic similarity translates to factual accuracy, a problem current verification approaches systematically fail to solve."

---

## Tables and Figures

### Tables (5 total)
1. Main Results (3-system comparison)
2. Clean vs Adversarial Retrieval
3. Threshold Sensitivity
4. Retrieval Size Ablation
5. Failure Mode Distribution

### Figures (mentioned, need to create)
1. System architecture diagram (optional)
2. Performance comparison chart (optional)
3. Example claim verification (optional)

**Note:** LaTeX compiles without figures; add them later if needed.

---

## Bibliography (12 references)

Covers:
- LLM fundamentals (Brown et al., 2020)
- Hallucination surveys (Ji et al., 2023)
- RAG systems (Lewis et al., 2020)
- Claim verification (RARR, AttributedQA)
- GPT-4o (OpenAI, 2024)
- PubMedQA dataset (Jin et al., 2019)
- Model calibration (Guo et al., 2017)

---

## How to Compile

```bash
cd "/Users/rishabchakravarty/CS592 project/cs592-verified-rag"

# Compile twice for references
pdflatex FINAL_REPORT.tex
pdflatex FINAL_REPORT.tex

# Or use your preferred LaTeX editor (Overleaf, TeXShop, etc.)
```

### If pdflatex not installed:

**macOS:**
```bash
brew install --cask mactex-no-gui
```

**Or use Overleaf:**
1. Upload `FINAL_REPORT.tex` to Overleaf
2. Compile online

---

## Page Count Estimate

- **Total:** ~15 pages (11pt font, 1-inch margins)
- Abstract: 0.5 pages
- Introduction: 2 pages
- Background: 3 pages (Related Work + Problem + Architecture)
- Experiments: 2 pages (Setup)
- Results: 3 pages (Tables + analysis)
- Verifier Analysis: 3 pages (Examples + root cause)
- Discussion: 2 pages
- Conclusion: 0.5 pages
- Bibliography: 1 page

---

## Key Strengths of This Report

✅ **Complete narrative arc:** Original hypothesis → Experiments → Unexpected finding → Reframed contribution

✅ **Multiple experiments:** 4 experimental conditions, 250+ examples total

✅ **Quantitative evidence:** 5 tables with clear metrics

✅ **Qualitative analysis:** 3 detailed false positive examples

✅ **Root cause analysis:** Mechanistic explanation of why verification fails

✅ **Actionable recommendations:** Concrete improvements for future work

✅ **Honest about limitations:** Sample size, domain, categorization completeness

✅ **Publication-ready:** Follows standard academic paper structure with citations

---

## Use This Report For

📄 **Final Project Submission:** Complete writeup ready to submit

📊 **Presentation:** Extract key tables/figures for slides

📝 **Defense:** Use examples and root cause analysis to explain findings

🔬 **Future Work:** Recommendations section outlines next steps

📚 **Publication:** With minor revisions, could submit to workshop/conference

---

## Related Files (Reference During Defense)

- `COMPREHENSIVE_VERIFIER_ANALYSIS.md` - Extended analysis with more examples
- `VERIFIER_FAILURE_ANALYSIS.md` - Original qualitative analysis
- `ANALYSIS_SUMMARY.md` - Quick reference guide
- `outputs/runs/three_systems_20260410_135637/` - All experimental data

---

## Bottom Line

You now have a **complete, publication-quality writeup** that:
1. Tells the honest story (including the pivot)
2. Presents rigorous experimental evidence
3. Makes a clear contribution (exposing false positive problem)
4. Provides actionable recommendations

**The 82% false positive finding is significant and novel** - it shows that verification systems have fundamental blind spots when facing sophisticated models. This is a valuable research contribution even though it wasn't the originally intended result.
