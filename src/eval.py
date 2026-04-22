"""
eval.py — Evaluation metrics for Verified RAG on PubMedQA.

Public API
----------
compute_metrics(records)   -> MetricsSummary
write_results_csv(records, path)
write_qual_examples(records, path, n)

MetricsSummary (TypedDict)
--------------------------
{
    "n_examples":              int,
    "accuracy":                float,   # yes/no/maybe label accuracy
    "unsupported_claim_rate":  float,   # fraction of claims flagged unsupported
    "citation_precision":      float,   # % claims whose evidence_source_id is in cited_sources
    "mean_runtime_s":          float,   # avg seconds per example
}
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, TypedDict

from src.config import N_QUAL_EXAMPLES, QUAL_EXAMPLES_NAME, RESULTS_CSV_NAME

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class MetricsSummary(TypedDict):
    n_examples: int
    accuracy: float
    unsupported_claim_rate: float
    citation_precision: float
    mean_runtime_s: float


# Record schema (one per example, produced by run_experiment.py)
# Required keys: id, question, gold_label, predicted_label,
#                n_claims, n_unsupported, cited_sources (list), verified_claims (list of dicts),
#                runtime_s
ExperimentRecord = Dict[str, Any]


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def compute_metrics(records: List[ExperimentRecord]) -> MetricsSummary:
    """
    Aggregate per-example records into dataset-level metrics.

    Parameters
    ----------
    records:
        List of dicts produced during the experiment loop in run_experiment.py.

    Returns
    -------
    MetricsSummary with accuracy, unsupported claim rate, citation precision,
    and mean runtime.
    """
    if not records:
        return MetricsSummary(
            n_examples=0,
            accuracy=0.0,
            unsupported_claim_rate=0.0,
            citation_precision=0.0,
            mean_runtime_s=0.0,
        )

    n = len(records)

    # --- accuracy ---
    correct = sum(
        1 for r in records if r.get("predicted_label") == r.get("gold_label")
    )
    accuracy = correct / n

    # --- unsupported claim rate ---
    total_claims = sum(r.get("n_claims", 0) for r in records)
    total_unsupported = sum(r.get("n_unsupported", 0) for r in records)
    unsupported_rate = (
        total_unsupported / total_claims if total_claims > 0 else 0.0
    )

    # --- citation precision ---
    # For each claim that HAS an evidence_source_id, check if that source_id
    # is in the cited_sources list the generator produced.
    n_cited_checked = 0
    n_cited_correct = 0
    for r in records:
        cited_sources: List[str] = r.get("cited_sources", [])
        for vc in r.get("verified_claims", []):
            evi_src = vc.get("evidence_source_id", "")
            if not evi_src:
                continue
            n_cited_checked += 1
            if evi_src in cited_sources:
                n_cited_correct += 1
    citation_prec = n_cited_correct / n_cited_checked if n_cited_checked > 0 else 0.0

    # --- runtime ---
    runtimes = [r.get("runtime_s", 0.0) for r in records]
    mean_runtime = sum(runtimes) / n

    summary = MetricsSummary(
        n_examples=n,
        accuracy=accuracy,
        unsupported_claim_rate=unsupported_rate,
        citation_precision=citation_prec,
        mean_runtime_s=mean_runtime,
    )

    logger.info(
        "Metrics — N=%d  acc=%.3f  unsupported_rate=%.3f  cite_prec=%.3f  rt=%.2fs",
        n, accuracy, unsupported_rate, citation_prec, mean_runtime,
    )
    return summary


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------

_CSV_FIELDS = [
    "id", "question", "gold_label",
    # RAG baseline
    "rag_prediction", "rag_correct", "rag_n_claims", "rag_n_unsupported",
    "rag_unsup_rate", "rag_runtime_s",
    # Verified RAG
    "vrag_prediction", "vrag_correct", "vrag_n_claims", "vrag_n_unsupported",
    "vrag_unsup_rate", "vrag_runtime_s", "repair_applied",
]


def write_results_csv(
    records: List[ExperimentRecord],
    path: Path,
) -> None:
    """
    Write per-example results to a CSV file.

    Parameters
    ----------
    records: List of experiment records.
    path:    Output file path (parent directories created automatically).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=_CSV_FIELDS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(records)
    logger.info("Wrote results CSV → %s", path)


# ---------------------------------------------------------------------------
# Qualitative examples writer
# ---------------------------------------------------------------------------

def write_qual_examples(
    records: List[ExperimentRecord],
    path: Path,
    n: int = N_QUAL_EXAMPLES,
) -> None:
    """
    Write a Markdown file with side-by-side RAG vs Verified RAG examples.

    Parameters
    ----------
    records: Full list of experiment records.
    path:    Output .md file path.
    n:       Number of examples to include.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    sample = records[:n]

    lines = ["# Qualitative Examples: RAG vs Verified RAG\n"]
    for i, r in enumerate(sample, 1):
        lines.append(f"## Example {i} — ID: {r.get('id', '?')}\n")
        lines.append(f"**Question:** {r.get('question', '')}\n")
        lines.append(f"**Gold label:** `{r.get('gold_label', '')}`\n\n")

        lines.append("### RAG Draft\n")
        lines.append(f"- **Label:** `{r.get('answer_label_draft', '')}`\n")
        lines.append(f"- **Summary:** {r.get('draft_summary', '')}\n")
        claims_all = [vc.get('claim', '') for vc in r.get('verified_claims', [])]
        if claims_all:
            lines.append("- **Claims:**\n")
            for c in claims_all:
                lines.append(f"  - {c}\n")
        lines.append("\n")

        lines.append("### Verified RAG (after repair)\n")
        lines.append(f"- **Label:** `{r.get('predicted_label', '')}`\n")
        lines.append(f"- **Final summary:** {r.get('final_summary', '')}\n")
        sup = [vc.get('claim', '') for vc in r.get('verified_claims', []) if vc.get('supported')]
        unsup = [vc.get('claim', '') for vc in r.get('verified_claims', []) if not vc.get('supported')]
        if sup:
            lines.append("- **Supported claims (kept):**\n")
            for c in sup:
                lines.append(f"  - ✅ {c}\n")
        if unsup:
            lines.append("- **Unsupported claims (deleted):**\n")
            for c in unsup:
                lines.append(f"  - ❌ {c}\n")
        lines.append(f"- **Repair applied:** {r.get('repair_applied', False)}\n")
        lines.append(f"- **Runtime:** {r.get('runtime_s', 0.0):.2f}s\n")
        lines.append("\n---\n\n")

    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    logger.info("Wrote qualitative examples → %s", path)


# ---------------------------------------------------------------------------
# Failure analysis
# ---------------------------------------------------------------------------

def write_failure_analysis(
    records: List[ExperimentRecord],
    path: Path,
) -> None:
    """
    Categorise every verified claim into one of four failure/success modes
    and write a Markdown report.

    Categories (per claim)
    ----------------------
    ✅  Correct & Supported    — claim grounded in evidence, answer label correct
    ⚠️  Correct & Unsupported  — label correct but verifier flagged claim (false negative)
    🔶  Incorrect & Supported  — claim passes verifier but answer label wrong
    ❌  Incorrect & Unsupported — both wrong (verifier correctly rejects)
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    counts = {
        "correct_supported":    0,
        "correct_unsupported":  0,
        "incorrect_supported":  0,
        "incorrect_unsupported":0,
    }

    examples_by_category: dict = {k: [] for k in counts}

    for r in records:
        answer_correct = (r.get("vrag_prediction") == r.get("gold_label"))
        for vc in r.get("verified_claims", []):
            supported = vc.get("supported", False)
            if answer_correct and supported:
                key = "correct_supported"
            elif answer_correct and not supported:
                key = "correct_unsupported"
            elif not answer_correct and supported:
                key = "incorrect_supported"
            else:
                key = "incorrect_unsupported"
            counts[key] += 1
            if len(examples_by_category[key]) < 3:   # keep up to 3 examples per category
                examples_by_category[key].append({
                    "id": r.get("id"),
                    "question": r.get("question", "")[:100],
                    "gold": r.get("gold_label"),
                    "pred": r.get("vrag_prediction"),
                    "claim": vc.get("claim", "")[:120],
                    "score": round(vc.get("support_score", 0.0), 3),
                    "evidence": vc.get("evidence_sentence", "")[:120],
                })

    total = sum(counts.values()) or 1

    lines = ["# Failure Analysis\n\n"]
    lines.append("## Summary\n\n")
    lines.append("| Category | Count | % of Claims |\n")
    lines.append("|---|---|---|\n")

    labels = {
        "correct_supported":    "✅ Correct & Supported",
        "correct_unsupported":  "⚠️  Correct & Unsupported (false negative)",
        "incorrect_supported":  "🔶 Incorrect & Supported (verifier missed it)",
        "incorrect_unsupported":"❌ Incorrect & Unsupported",
    }
    for key, label in labels.items():
        pct = 100 * counts[key] / total
        lines.append(f"| {label} | {counts[key]} | {pct:.1f}% |\n")
    lines.append("\n")

    lines.append("## Failure Mode Descriptions\n\n")
    lines.append(
        "1. **⚠️ False Negative (Correct but Unsupported)** — The verifier deleted a claim "
        "whose underlying answer was correct. Caused by paraphrase mismatch: the claim "
        "expresses the same idea as a passage sentence but with different wording, so "
        "cosine similarity falls below τ. *Fix: lower τ or use NLI entailment.*\n\n"
    )
    lines.append(
        "2. **🔶 False Positive (Incorrect but Supported)** — The verifier kept a claim "
        "even though the final answer label was wrong. Happens when the retrieved passage "
        "is topically similar but does not actually support the specific claim. "
        "*Fix: sentence-level NLI rather than embedding similarity.*\n\n"
    )
    lines.append(
        "3. **❌ Correctly Rejected** — Claim was both wrong and unsupported. This is "
        "the ideal case: verification catches hallucinated claims.\n\n"
    )
    lines.append(
        "4. **Retrieval misses** — If the key evidence passage is not in top-k, "
        "verification fails even for true claims. Not directly visible in claim categories "
        "but visible as low support scores across all claims for an example.\n\n"
    )

    lines.append("## Example Instances\n\n")
    for key, label in labels.items():
        egs = examples_by_category[key]
        if not egs:
            continue
        lines.append(f"### {label}\n\n")
        for eg in egs:
            lines.append(f"**Q:** {eg['question']}  \n")
            lines.append(f"**Gold:** `{eg['gold']}` | **Pred:** `{eg['pred']}`  \n")
            lines.append(f"**Claim:** {eg['claim']}  \n")
            lines.append(f"**Support score:** {eg['score']} | **Best evidence:** {eg['evidence']}  \n\n")

    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    logger.info("Wrote failure analysis → %s", path)
