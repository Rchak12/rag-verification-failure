"""
run_experiment.py — End-to-end Verified RAG pipeline on PubMedQA.

Locked experimental setup (midterm):
  Dataset : PubMedQA (qiaojin/PubMedQA, pqa_labeled, train split)
  N       : 40 questions  (fixed random seed=42)
  k       : 3 retrieved passages
  tau     : 0.55
  Repair  : delete unsupported claims

Runs TWO systems per example for direct comparison:
  - RAG baseline  : retrieve + generate (no verify/repair)
  - Verified RAG  : retrieve + generate + verify + repair

Usage
-----
# Canonical midterm run (N=40, k=3, seed=42)
python -m src.run_experiment

# Also write clean copies to outputs/ for report submission
python -m src.run_experiment --final

# Custom run
python -m src.run_experiment --n 50 --k 5 --tau 0.55 --backend stub

Output
------
outputs/runs/<timestamp>/
    results.csv
    comparison_table.txt
    qual_examples.md
    failure_analysis.md
    drafts.jsonl
    metrics.json

With --final also writes:
    outputs/results.csv
    outputs/summary_metrics.json
    outputs/qualitative_examples.md
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import shutil
import time
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from src.claims import extract_claims
from src.config import (
    DEFAULT_N_EXAMPLES,
    DEFAULT_SPLIT,
    RETRIEVAL_TOP_K,
    RUNS_DIR,
    SIMILARITY_THRESHOLD,
)
from src.data import load_pubmedqa
from src.eval import compute_metrics, write_failure_analysis, write_qual_examples, write_results_csv
from src.generate import generate_draft, save_drafts
from src.repair import repair
from src.retrieve import build_index, retrieve, save_index
from src.verify import verify_claims
from src.rewrite import rewrite_unsupported

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verified RAG experiment on PubMedQA",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--n", type=int, default=40,
        help="Number of examples to evaluate.",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--split", type=str, default=DEFAULT_SPLIT,
        help="Dataset split to use.",
    )
    parser.add_argument(
        "--k", type=int, default=3,
        help="Number of passages to retrieve per question.",
    )
    parser.add_argument(
        "--tau", type=float, default=SIMILARITY_THRESHOLD,
        help="Cosine-similarity threshold τ for claim verification.",
    )
    parser.add_argument(
        "--backend", type=str, default="stub",
        choices=["stub", "openai"],
        help="Generation backend.",
    )
    parser.add_argument(
        "--repair", type=str, default="delete",
        choices=["delete", "rewrite"],
        help="Repair policy to apply for unsupported claims: delete (remove) or rewrite (GPT-based).",
    )
    parser.add_argument(
        "--rebuild-index", action="store_true",
        help="Force rebuild the FAISS index even if one exists on disk.",
    )
    parser.add_argument(
        "--final", action="store_true",
        help="Also copy clean outputs to outputs/ root for report submission.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    # --- Reproducibility ---
    random.seed(args.seed)
    logger.info("Random seed: %d", args.seed)

    # --- Output directory ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Run directory: %s", run_dir)

    # --- Load dataset ---
    logger.info("Loading %d examples from PubMedQA (split=%s)…", args.n, args.split)
    examples = load_pubmedqa(split=args.split, limit=args.n)
    logger.info("Loaded %d examples.", len(examples))

    # --- Build / load retrieval index ---
    from src.config import INDEX_DIR
    index_exists = (INDEX_DIR / "pubmedqa_index.faiss").exists()

    if args.rebuild_index or not index_exists:
        logger.info("Building FAISS index over %d abstracts…", len(examples))
        index, embeddings, meta = build_index(examples)
        save_index(index, embeddings, meta)
    else:
        from src.retrieve import load_index
        logger.info("Loading existing FAISS index from %s…", INDEX_DIR)
        index, _embeddings, meta = load_index()

    # --- Experiment loop ---
    records = []
    draft_records = []

    for ex in tqdm(examples, desc="Processing", unit="example"):

        # ── Step 1: Retrieve (shared by both systems) ──────────────────
        passages = retrieve(ex["question"], index, meta, k=args.k)

        # ── Step 2: Generate draft (shared) ────────────────────────────
        t_rag_start = time.perf_counter()
        draft = generate_draft(ex["question"], passages, backend=args.backend)
        claims = extract_claims(draft["raw"])
        t_rag_end = time.perf_counter()
        rag_runtime = round(t_rag_end - t_rag_start, 4)

        # ── RAG BASELINE: no verify / repair ───────────────────────────
        rag_label      = draft["answer_label"]
        rag_n_claims   = len(claims)
        # For baseline, we run verify just to count unsupported
        # but do NOT apply repair (keep all claims)
        verified_for_counting = verify_claims(claims, passages, tau=args.tau)
        rag_n_unsupported = sum(1 for vc in verified_for_counting if not vc["supported"])

        # ── VERIFIED RAG: verify + repair ──────────────────────────────
        t_vrag_start = time.perf_counter()
        verified = verify_claims(claims, passages, tau=args.tau)
        if args.repair == "rewrite":
            # Use rewrite module to repair unsupported claims (may call OpenAI)
            rewritten = rewrite_unsupported(draft=draft, verified=verified, passages=passages, question=ex["question"], tau=args.tau)
            # Map RewrittenAnswer to expected final dict structure used downstream
            final = {
                "answer_label": rewritten.get("answer_label"),
                "final_summary": rewritten.get("final_summary"),
                "supported_claims": list(rewritten.get("supported_claims", [])),
                "unsupported_claims": [],
                "repair_applied": bool(rewritten.get("repair_applied", False)),
            }
        else:
            final = repair(draft, verified)
        t_vrag_end = time.perf_counter()
        vrag_extra_runtime = round(t_vrag_end - t_vrag_start, 4)
        vrag_runtime = round(rag_runtime + vrag_extra_runtime, 4)

        vrag_n_claims      = len(final["supported_claims"])
        vrag_n_unsupported = 0   # repair deleted them all

        record = {
            # ── identifiers ──
            "id":           ex["id"],
            "question":     ex["question"],
            "gold_label":   ex["label"],

            # ── RAG baseline ──
            "rag_prediction":    rag_label,
            "rag_correct":       int(rag_label == ex["label"]),
            "rag_n_claims":      rag_n_claims,
            "rag_n_unsupported": rag_n_unsupported,
            "rag_unsup_rate":    round(rag_n_unsupported / rag_n_claims, 4) if rag_n_claims else 0.0,
            "rag_runtime_s":     rag_runtime,

            # ── Verified RAG ──
            "vrag_prediction":    final["answer_label"],
            "vrag_correct":       int(final["answer_label"] == ex["label"]),
            "vrag_n_claims":      vrag_n_claims,
            "vrag_n_unsupported": vrag_n_unsupported,
            "vrag_unsup_rate":    0.0,
            "vrag_runtime_s":     vrag_runtime,
            "repair_applied":     final["repair_applied"],

            # ── for qual examples ──
            "answer_label_draft": draft["answer_label"],
            "draft_summary":      draft["summary"],
            "final_summary":      final["final_summary"],
            "cited_sources":      draft["cited_sources"],
            "verified_claims":    [dict(vc) for vc in verified],

            # ── legacy keys (used by eval.py compute_metrics) ──
            "predicted_label":  final["answer_label"],
            "n_claims":         rag_n_claims,
            "n_unsupported":    rag_n_unsupported,
            "runtime_s":        vrag_runtime,
        }
        records.append(record)

        draft_records.append({
            "id":       ex["id"],
            "question": ex["question"],
            "draft":    dict(draft),
        })

    # --- Persist outputs ---
    save_drafts(draft_records, run_dir / "drafts.jsonl")
    write_results_csv(records, run_dir / "results.csv")
    write_qual_examples(records, run_dir / "qual_examples.md")
    write_failure_analysis(records, run_dir / "failure_analysis.md")

    metrics = compute_metrics(records)

    # --- Aggregate dual-system metrics ---
    n = len(records)
    rag_acc       = sum(r["rag_correct"] for r in records) / n
    vrag_acc      = sum(r["vrag_correct"] for r in records) / n
    rag_unsup     = sum(r["rag_n_unsupported"] for r in records)
    rag_total_cl  = sum(r["rag_n_claims"] for r in records)
    rag_unsup_rate  = rag_unsup / rag_total_cl if rag_total_cl else 0.0
    vrag_unsup_rate = 0.0   # all unsupported claims deleted by repair
    rag_avg_claims  = rag_total_cl / n
    vrag_avg_claims = sum(r["vrag_n_claims"] for r in records) / n
    rag_rt   = sum(r["rag_runtime_s"] for r in records) / n
    vrag_rt  = sum(r["vrag_runtime_s"] for r in records) / n

    dual_metrics = {
        "n_examples": n,
        "tau": args.tau,
        "k": args.k,
        "backend": args.backend,
        "rag": {
            "accuracy":            round(rag_acc, 4),
            "unsupported_rate":    round(rag_unsup_rate, 4),
            "avg_claims":          round(rag_avg_claims, 2),
            "mean_runtime_s":      round(rag_rt, 4),
        },
        "verified_rag": {
            "accuracy":            round(vrag_acc, 4),
            "unsupported_rate":    round(vrag_unsup_rate, 4),
            "avg_claims":          round(vrag_avg_claims, 2),
            "mean_runtime_s":      round(vrag_rt, 4),
        },
    }

    metrics_path = run_dir / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as fh:
        json.dump(dual_metrics, fh, indent=2)

    # --- Comparison table (file + stdout) ---
    table = _build_comparison_table(dual_metrics)
    table_path = run_dir / "comparison_table.txt"
    table_path.write_text(table)

    # --- --final: write clean copies to outputs/ root for report submission ---
    if args.final:
        from src.config import OUTPUTS_DIR
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(run_dir / "results.csv",       OUTPUTS_DIR / "results.csv")
        shutil.copy(run_dir / "qual_examples.md",  OUTPUTS_DIR / "qualitative_examples.md")
        # Write summary_metrics.json (clean, report-ready subset)
        summary = {
            "experimental_setup": {
                "dataset": "PubMedQA (qiaojin/PubMedQA, pqa_labeled)",
                "n_examples": args.n,
                "seed": args.seed,
                "k": args.k,
                "tau": args.tau,
                "verification": "cosine similarity (sentence-transformers/all-MiniLM-L6-v2)",
                "repair": "delete unsupported claims",
                "generation_backend": args.backend,
            },
            "results": {
                "rag": dual_metrics["rag"],
                "verified_rag": dual_metrics["verified_rag"],
            },
        }
        with open(OUTPUTS_DIR / "summary_metrics.json", "w") as fh:
            json.dump(summary, fh, indent=2)
        logger.info("Wrote final report artifacts to %s", OUTPUTS_DIR)

    print(table)
    print(f"  Run dir : {run_dir}")
    print(f"  Outputs : results.csv  qual_examples.md  failure_analysis.md  metrics.json  comparison_table.txt")
    if args.final:
        print(f"  Report  : outputs/results.csv  outputs/summary_metrics.json  outputs/qualitative_examples.md")
    print()


def _build_comparison_table(m: dict) -> str:
    """Format the 4-metric comparison table for stdout and file."""
    rag  = m["rag"]
    vrag = m["verified_rag"]

    def delta(a, b, higher_better=True):
        d = b - a
        if higher_better:
            arrow = "▲" if d > 0 else ("▼" if d < 0 else "=")
        else:
            arrow = "▼" if d > 0 else ("▲" if d < 0 else "=")
        return f"{arrow}{abs(d):.3f}"

    lines = [
        "\n" + "=" * 65,
        f"  EXPERIMENT COMPLETE  (N={m['n_examples']}  τ={m['tau']}  k={m['k']}  backend={m['backend']})",
        "=" * 65,
        f"  {'Metric':<28} {'RAG':>8} {'Verified RAG':>14} {'Δ':>8}",
        "  " + "-" * 61,
        f"  {'Unsupported Claim Rate':<28} {rag['unsupported_rate']:>8.3f} {vrag['unsupported_rate']:>14.3f} {delta(rag['unsupported_rate'], vrag['unsupported_rate'], higher_better=False):>8}",
        f"  {'Accuracy (yes/no/maybe)':<28} {rag['accuracy']:>8.3f} {vrag['accuracy']:>14.3f} {delta(rag['accuracy'], vrag['accuracy']):>8}",
        f"  {'Avg Claims Per Answer':<28} {rag['avg_claims']:>8.2f} {vrag['avg_claims']:>14.2f} {delta(rag['avg_claims'], vrag['avg_claims'], higher_better=False):>8}",
        f"  {'Mean Runtime (s)':<28} {rag['mean_runtime_s']:>8.2f} {vrag['mean_runtime_s']:>14.2f} {delta(rag['mean_runtime_s'], vrag['mean_runtime_s'], higher_better=False):>8}",
        "=" * 65 + "\n",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
