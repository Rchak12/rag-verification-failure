"""
run_three_systems.py — 3-System Comparison: RAG vs REMOVE vs REWRITE

This is the MAIN EXPERIMENT for the final project.

System A — RAG BASELINE
    retrieve → GPT-4o generate → evaluate
    (no verification, no repair)

System B — REMOVE (delete unsupported claims)
    retrieve → GPT-4o generate → verify → DELETE unsupported → evaluate

System C — REWRITE (rewrite unsupported claims) ⭐ MAIN CONTRIBUTION
    retrieve → GPT-4o generate → verify → REWRITE unsupported → evaluate

All systems use:
✅ GPT-4o for generation
✅ Same retrieval (FAISS, same k)
✅ Same verification (NLI entailment)
✅ Same dataset samples

Only difference: repair strategy (NONE vs DELETE vs REWRITE)

Usage
-----
# Production run with NLI verification
python -m src.run_three_systems --n 100 --k 3 --verification nli

# Quick test with 10 samples
python -m src.run_three_systems --n 10 --k 3

# With final report outputs
python -m src.run_three_systems --n 100 --k 3 --final

Output
------
outputs/runs/<timestamp>/
    three_system_results.csv
    comparison_table.txt
    qualitative_examples.md
    failure_analysis.md
    metrics.json
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from src.claims import extract_claims
from src.config import (
    DEFAULT_SPLIT,
    NLI_THRESHOLD,
    RUNS_DIR,
    SIMILARITY_THRESHOLD,
)
from src.data import load_pubmedqa
from src.eval import compute_metrics, write_failure_analysis, write_qual_examples, write_results_csv
from src.generate import generate_draft, save_drafts
from src.repair import repair
from src.retrieve import build_index, load_index, retrieve, save_index
from src.rewrite import rewrite_unsupported
from src.verify import verify_claims

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
        description="3-System Comparison: RAG vs REMOVE vs REWRITE",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--n", type=int, default=100,
                        help="Number of examples to evaluate")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    parser.add_argument("--split", type=str, default=DEFAULT_SPLIT,
                        help="Dataset split")
    parser.add_argument("--k", type=int, default=3,
                        help="Number of passages to retrieve")
    parser.add_argument("--verification", type=str, default="nli",
                        choices=["nli", "cosine"],
                        help="Verification method (NLI recommended)")
    parser.add_argument("--tau", type=float, default=None,
                        help="Verification threshold (auto-selected if not set)")
    parser.add_argument("--noise-ratio", type=float, default=0.0,
                        help="Fraction of retrieved passages to replace with noise (0.0-1.0). "
                             "Use 0.33 for imperfect retrieval experiments.")
    parser.add_argument("--force-answer", action="store_true",
                        help="Force model to answer (disallow abstention). "
                             "Use to test verification under forced-decision conditions.")
    parser.add_argument("--rebuild-index", action="store_true",
                        help="Force rebuild FAISS index")
    parser.add_argument("--final", action="store_true",
                        help="Copy outputs to outputs/ root for report")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    # Reproducibility
    random.seed(args.seed)
    logger.info("Random seed: %d", args.seed)

    # Auto-select threshold
    if args.tau is None:
        args.tau = NLI_THRESHOLD if args.verification == "nli" else SIMILARITY_THRESHOLD

    logger.info("Verification: %s (τ=%.2f)", args.verification, args.tau)

    if args.noise_ratio > 0:
        logger.info("🔊 IMPERFECT RETRIEVAL MODE: %.0f%% noise injection", args.noise_ratio * 100)
    else:
        logger.info("✅ IDEAL RETRIEVAL MODE: No noise injection")

    # Output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / f"three_systems_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Run directory: %s", run_dir)

    # Load dataset
    logger.info("Loading %d examples from PubMedQA...", args.n)
    examples = load_pubmedqa(split=args.split, limit=args.n)
    logger.info("Loaded %d examples", len(examples))

    # Build/load retrieval index
    from src.config import INDEX_DIR
    index_exists = (INDEX_DIR / "pubmedqa_index.faiss").exists()

    if args.rebuild_index or not index_exists:
        logger.info("Building FAISS index...")
        index, embeddings, meta = build_index(examples)
        save_index(index, embeddings, meta)
    else:
        logger.info("Loading existing FAISS index...")
        index, embeddings, meta = load_index()

    # Experiment loop
    records = []
    draft_records = []

    for ex in tqdm(examples, desc="Evaluating 3 systems", unit="example"):
        qid = ex["id"]
        question = ex["question"]
        gold_label = ex["label"]

        # ========== STEP 1: RETRIEVE (shared by all systems) ==========
        passages = retrieve(question, index, meta, k=args.k, noise_ratio=args.noise_ratio, seed=args.seed, embeddings=embeddings)

        # ========== STEP 2: GENERATE (shared by all systems) ==========
        t_gen_start = time.perf_counter()
        draft = generate_draft(question, passages, backend="openai", force_answer=args.force_answer)  # GPT-4o
        claims = extract_claims(draft["raw"])
        t_gen = time.perf_counter() - t_gen_start

        draft_records.append({
            "id": qid,
            "question": question,
            "draft": dict(draft),
        })

        # ========== SYSTEM A: RAG BASELINE (no verification) ==========
        system_a_label = draft["answer_label"]
        system_a_claims = claims
        system_a_n_claims = len(claims)
        system_a_runtime = t_gen

        # For analysis: verify claims but DON'T apply any repair
        verified_for_analysis = verify_claims(
            claims, passages, tau=args.tau, method=args.verification
        )
        system_a_n_unsupported = sum(1 for vc in verified_for_analysis if not vc["supported"])
        system_a_unsup_rate = system_a_n_unsupported / system_a_n_claims if system_a_n_claims else 0

        # ========== SYSTEM B: REMOVE (verify + delete) ==========
        t_remove_start = time.perf_counter()
        verified_b = verify_claims(
            claims, passages, tau=args.tau, method=args.verification
        )
        final_b = repair(draft, verified_b)
        t_remove = time.perf_counter() - t_remove_start

        system_b_label = final_b["answer_label"]
        system_b_n_claims = len(final_b["supported_claims"])
        system_b_n_unsupported = 0  # deleted
        system_b_unsup_rate = 0.0
        system_b_runtime = t_gen + t_remove

        # ========== SYSTEM C: REWRITE (verify + rewrite) ⭐ ==========
        t_rewrite_start = time.perf_counter()
        verified_c = verify_claims(
            claims, passages, tau=args.tau, method=args.verification
        )
        final_c = rewrite_unsupported(
            draft, verified_c, passages, question, tau=args.tau
        )
        t_rewrite = time.perf_counter() - t_rewrite_start

        system_c_label = final_c["answer_label"]
        system_c_n_claims = len(final_c["supported_claims"])
        system_c_n_rewritten = final_c["n_rewritten"]
        system_c_n_unsupported = 0  # rewritten
        system_c_unsup_rate = 0.0
        system_c_runtime = t_gen + t_rewrite

        # ========== RECORD ==========
        record = {
            # Identifiers
            "id": qid,
            "question": question,
            "gold_label": gold_label,

            # System A — RAG Baseline
            "system_a_label": system_a_label,
            "system_a_correct": int(system_a_label == gold_label),
            "system_a_n_claims": system_a_n_claims,
            "system_a_n_unsupported": system_a_n_unsupported,
            "system_a_unsup_rate": round(system_a_unsup_rate, 4),
            "system_a_runtime": round(system_a_runtime, 4),

            # System B — REMOVE
            "system_b_label": system_b_label,
            "system_b_correct": int(system_b_label == gold_label),
            "system_b_n_claims": system_b_n_claims,
            "system_b_n_unsupported": system_b_n_unsupported,
            "system_b_unsup_rate": round(system_b_unsup_rate, 4),
            "system_b_runtime": round(system_b_runtime, 4),

            # System C — REWRITE
            "system_c_label": system_c_label,
            "system_c_correct": int(system_c_label == gold_label),
            "system_c_n_claims": system_c_n_claims,
            "system_c_n_rewritten": system_c_n_rewritten,
            "system_c_n_unsupported": system_c_n_unsupported,
            "system_c_unsup_rate": round(system_c_unsup_rate, 4),
            "system_c_runtime": round(system_c_runtime, 4),

            # For qualitative analysis
            "draft_summary": draft["summary"],
            "system_b_summary": final_b["final_summary"],
            "system_c_summary": final_c["final_summary"],
            "verified_claims": [dict(vc) for vc in verified_for_analysis],
            "rewritten_claims": final_c["rewritten_claims"],
        }
        records.append(record)

    # ========== SAVE OUTPUTS ==========
    save_drafts(draft_records, run_dir / "drafts.jsonl")
    write_results_csv(records, run_dir / "three_system_results.csv")
    write_qual_examples(records, run_dir / "qualitative_examples.md")
    write_failure_analysis(records, run_dir / "failure_analysis.md")

    # ========== COMPUTE AGGREGATE METRICS ==========
    n = len(records)

    metrics = {
        "experimental_setup": {
            "n_examples": n,
            "k_retrieval": args.k,
            "verification_method": args.verification,
            "tau_threshold": args.tau,
            "seed": args.seed,
            "model": "gpt-4o",
        },
        "system_a_rag": {
            "accuracy": round(sum(r["system_a_correct"] for r in records) / n, 4),
            "unsupported_rate": round(sum(r["system_a_unsup_rate"] for r in records) / n, 4),
            "avg_claims": round(sum(r["system_a_n_claims"] for r in records) / n, 2),
            "mean_runtime_s": round(sum(r["system_a_runtime"] for r in records) / n, 4),
        },
        "system_b_remove": {
            "accuracy": round(sum(r["system_b_correct"] for r in records) / n, 4),
            "unsupported_rate": round(sum(r["system_b_unsup_rate"] for r in records) / n, 4),
            "avg_claims": round(sum(r["system_b_n_claims"] for r in records) / n, 2),
            "mean_runtime_s": round(sum(r["system_b_runtime"] for r in records) / n, 4),
        },
        "system_c_rewrite": {
            "accuracy": round(sum(r["system_c_correct"] for r in records) / n, 4),
            "unsupported_rate": round(sum(r["system_c_unsup_rate"] for r in records) / n, 4),
            "avg_claims": round(sum(r["system_c_n_claims"] for r in records) / n, 2),
            "avg_rewritten": round(sum(r["system_c_n_rewritten"] for r in records) / n, 2),
            "mean_runtime_s": round(sum(r["system_c_runtime"] for r in records) / n, 4),
        },
    }

    with open(run_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # ========== COMPARISON TABLE ==========
    table = _build_comparison_table(metrics)
    (run_dir / "comparison_table.txt").write_text(table)
    print(table)

    # ========== FINAL OUTPUTS ==========
    if args.final:
        from src.config import OUTPUTS_DIR
        import shutil
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(run_dir / "three_system_results.csv", OUTPUTS_DIR / "results.csv")
        shutil.copy(run_dir / "qualitative_examples.md", OUTPUTS_DIR / "qualitative_examples.md")
        with open(OUTPUTS_DIR / "summary_metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        logger.info("✅ Final outputs copied to %s", OUTPUTS_DIR)

    print(f"\n✅ 3-System comparison complete!")
    print(f"  Run dir: {run_dir}")
    print(f"  Outputs: three_system_results.csv, metrics.json, comparison_table.txt\n")


def _build_comparison_table(m: dict) -> str:
    """Format 3-system comparison table."""
    a = m["system_a_rag"]
    b = m["system_b_remove"]
    c = m["system_c_rewrite"]

    lines = [
        "\n" + "=" * 90,
        f"  3-SYSTEM COMPARISON  (N={m['experimental_setup']['n_examples']}  "
        f"verification={m['experimental_setup']['verification_method']}  "
        f"τ={m['experimental_setup']['tau_threshold']})",
        "=" * 90,
        f"  {'Metric':<30} {'RAG':>12} {'REMOVE':>12} {'REWRITE':>12}",
        "  " + "-" * 86,
        f"  {'Accuracy':<30} {a['accuracy']:>12.3f} {b['accuracy']:>12.3f} {c['accuracy']:>12.3f}",
        f"  {'Unsupported Claim Rate':<30} {a['unsupported_rate']:>12.3f} {b['unsupported_rate']:>12.3f} {c['unsupported_rate']:>12.3f}",
        f"  {'Avg Claims Per Answer':<30} {a['avg_claims']:>12.2f} {b['avg_claims']:>12.2f} {c['avg_claims']:>12.2f}",
        f"  {'Mean Runtime (s)':<30} {a['mean_runtime_s']:>12.2f} {b['mean_runtime_s']:>12.2f} {c['mean_runtime_s']:>12.2f}",
    ]
    if "avg_rewritten" in c:
        lines.append(f"  {'Avg Claims Rewritten':<30} {'-':>12} {'-':>12} {c['avg_rewritten']:>12.2f}")
    lines.append("=" * 90 + "\n")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
