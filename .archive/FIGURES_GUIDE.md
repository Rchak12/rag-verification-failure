# Figures for Final Report - Complete Guide

## ✅ What Was Created

All 7 publication-quality figures for your final report, generated in both PDF (for LaTeX) and PNG (for previewing).

---

## 📊 Figure Summary

### Figure 1: Pipeline Diagram
**File:** `figure1_pipeline.pdf`
**Location in report:** After Section 4 (System Architecture)
**What it shows:**
- Vertical flow: Question → Retrieval → Generation → Verification → Three Systems
- Visual split showing RAG Baseline, REMOVE, and REWRITE
- Emphasizes that all systems share retrieval/generation backbone
- Shows that systems differ only in post-verification repair

**Key message:** "Three systems, same inputs, different repair strategies"

---

### Figure 2: Main Results - The False Positive Problem ⭐
**File:** `figure2_main_results.pdf`
**Location in report:** Right after Table 1 in Section 6 (Results)
**What it shows:**
- Grouped bar chart with 3 bars per system
- Accuracy: 0.18 (blue)
- Unsupported rate: 0.00 (red)
- False positive rate: 0.82 (orange)
- Red annotation pointing to the contradiction

**Key message:** "Perfect verification, terrible accuracy = 82% false positives"

**This is your most important figure** - it visualizes the entire thesis.

---

### Figure 3: Clean vs Adversarial Retrieval
**File:** `figure3_retrieval_comparison.pdf`
**Location in report:** Right after Table 2 in Section 6.2
**What it shows:**
- Two conditions: Clean vs 50% Conflicting
- Metrics: Accuracy, Unsupported Rate, Avg Claims
- Shows accuracy drops (0.23 → 0.19) but unsupported stays 0%

**Key message:** "Even adversarial retrieval doesn't trigger verifier"

---

### Figure 4: Threshold Ablation
**File:** `figure4_threshold_ablation.pdf`
**Location in report:** Right after Table 3 in Section 6.3.1
**What it shows:**
- Line plot: τ on x-axis, accuracy/unsupported on y-axis
- Two lines: Accuracy (blue circles), Unsupported (red squares)
- Annotations highlighting τ=0.5 (current) and τ=0.9 issues

**Key message:** "Threshold tuning doesn't fix the problem"

---

### Figure 5: Retrieval Size Ablation
**File:** `figure5_retrieval_size_ablation.pdf`
**Location in report:** Right after Table 4 in Section 6.3.2
**What it shows:**
- Line plot: k on x-axis, metrics on y-axis
- Three lines: Accuracy, Unsupported, Avg Claims
- Vertical dashed line at k=3 (used in experiments)

**Key message:** "More passages help slightly, but unsupported stays zero"

---

### Figure 6: Failure Mode Distribution
**File:** `figure6_failure_modes.pdf`
**Location in report:** Right after Table 5 in Section 7 (Failure Analysis)
**What it shows:**
- Pie chart with 3 slices
- Strategic Hedging: 71% (purple, exploded)
- Overgeneralization: 2% (orange)
- Other: 27% (gray)

**Key message:** "Hedging is the dominant failure mode"

---

### Figure 7: False Positive Breakdown
**File:** `figure7_false_positive_breakdown.pdf`
**Location in report:** Near end of Section 6 or beginning of Section 7
**What it shows:**
- Horizontal stacked bar (N=50)
- Green: Correct & Verified (9, 18%)
- Red: Incorrect & Verified (41, 82%)
- Gray: Unsupported (0, 0%)

**Key message:** "82% of outputs are false positives"

---

## 🔧 How to Add to Your LaTeX Report

### Step 1: Copy Figure Files

All PDF files are already in your project root:
```bash
/Users/rishabchakravarty/CS592 project/cs592-verified-rag/figure*.pdf
```

They're in the same directory as `FINAL_REPORT.tex`, so LaTeX will find them automatically.

### Step 2: Add to LaTeX Document

Open `FINAL_REPORT.tex` and insert the figure code blocks from `FIGURES_LATEX_GUIDE.tex` at the appropriate locations.

**Quick insertion guide:**

1. **After System Architecture section (around line 200):**
   ```latex
   \begin{figure}[htbp]
   \centering
   \includegraphics[width=0.75\textwidth]{figure1_pipeline.pdf}
   \caption{Overview of the three-system experimental architecture...}
   \label{fig:pipeline}
   \end{figure}
   ```

2. **Right after Table 1 in Results section:**
   ```latex
   \begin{figure}[htbp]
   \centering
   \includegraphics[width=0.85\textwidth]{figure2_main_results.pdf}
   \caption{Despite perfect verification pass rates...}
   \label{fig:main_results}
   \end{figure}
   ```

3. **Continue similarly for Figures 3-7** (see `FIGURES_LATEX_GUIDE.tex` for exact code)

### Step 3: Reference Figures in Text

Example references to add in your text:

```latex
As shown in Figure~\ref{fig:main_results}, despite achieving a 0\% unsupported
claim rate, system accuracy remains at only 18\%, revealing an 82\% false
positive problem.

The pipeline architecture (Figure~\ref{fig:pipeline}) shows that all three
systems share identical retrieval and generation components...

Figure~\ref{fig:failure_modes} shows that strategic hedging dominates the
failure modes, accounting for 71\% of false positive cases.
```

### Step 4: Compile

```bash
cd "/Users/rishabchakravarty/CS592 project/cs592-verified-rag"
pdflatex FINAL_REPORT.tex
pdflatex FINAL_REPORT.tex  # Run twice for references
```

---

## 📐 Figure Specifications

All figures designed with:
- **Style:** Publication-quality (serif fonts, clean layout)
- **Size:** Optimized for single-column LaTeX (8" wide)
- **Format:** PDF (vector graphics, scales perfectly)
- **Colors:** Consistent palette across all figures
  - Blue: Accuracy metrics
  - Red: Unsupported/error metrics
  - Orange: False positives
  - Purple: Hedging
  - Green: Correct/REWRITE system

---

## 🎨 Customization (Optional)

If you want to modify the figures, edit `create_figures.py` and re-run:

```bash
python create_figures.py
```

Common customizations:
- **Change colors:** Modify `COLOR_*` variables at top
- **Adjust sizes:** Change `figsize=(8, 5)` parameters
- **Modify labels:** Edit `ax.set_xlabel()` / `ax.set_ylabel()` calls
- **Update data:** Change the data arrays (e.g., `accuracy = [0.18, 0.18, 0.18]`)

---

## 📊 Quick Preview (PNG Files)

To preview figures without compiling LaTeX:

```bash
# On macOS
open figure2_main_results.png
open figure6_failure_modes.png
open figure7_false_positive_breakdown.png

# Or view all at once
open figure*.png
```

---

## ✅ Checklist for Final Report

- [ ] All 7 PDF figures generated
- [ ] Figures added to FINAL_REPORT.tex at correct locations
- [ ] Captions updated with your specific interpretation
- [ ] Figure references (`\ref{fig:...}`) added in text
- [ ] LaTeX compiles without errors
- [ ] All figures appear in correct order
- [ ] Figure numbers match table numbers in same sections

---

## 🎯 Strategic Placement

The figures are strategically designed to support your narrative:

**Introduction → Problem:**
- *No figures needed* (text sets up motivation)

**System Architecture:**
- **Figure 1** establishes the experimental setup

**Results:**
- **Figure 2** (main finding) - "Here's the problem"
- **Figure 3** (adversarial) - "Problem persists under stress"
- **Figures 4-5** (ablations) - "Tuning doesn't fix it"
- **Figure 7** (breakdown) - "82% false positives visualized"

**Failure Analysis:**
- **Figure 6** (failure modes) - "Hedging is why"

This creates a logical flow:
1. Show the system (Fig 1)
2. Show the main problem (Fig 2)
3. Show it's robust/systematic (Figs 3-5, 7)
4. Explain why it happens (Fig 6)

---

## 📝 Caption Writing Tips

Good captions have three parts:

1. **What:** "Grouped bar chart showing..."
2. **Finding:** "Despite 0% unsupported rate, accuracy is only 18%..."
3. **Implication:** "...revealing an 82% false positive problem"

**Example:**
```latex
\caption{Distribution of failure modes among 41 false positive cases
from the forced-answer experiment (what). Strategic hedging dominates
at 71\% (finding), where the model produces vague claims that pass NLI
verification but avoid commitment (implication).}
```

---

## 🚀 Final Check

After adding all figures to your LaTeX document:

1. **Compile twice:**
   ```bash
   pdflatex FINAL_REPORT.tex
   pdflatex FINAL_REPORT.tex
   ```

2. **Check for issues:**
   - Look for "Overfull hbox" warnings (figures too wide)
   - Verify all `\ref{fig:...}` resolve correctly
   - Ensure figures appear on correct pages

3. **If figures appear in wrong spots:**
   - Try `\usepackage{float}` and use `[H]` instead of `[htbp]`
   - Or manually adjust with `\clearpage` before/after figures

4. **Final verification:**
   - Open the PDF
   - Verify all 7 figures appear
   - Check that figure numbers match references in text
   - Ensure captions are complete and informative

---

## 🎓 You Now Have

✅ **7 publication-quality figures** ready for your final report
✅ **LaTeX code** to insert them at the right locations
✅ **Proper captions** that explain each figure's significance
✅ **Consistent visual style** across all figures
✅ **Strategic placement** that supports your narrative

Your final report now has professional visualizations that make the 82% false positive problem impossible to miss!
