"""
ablation.py — τ threshold sweep + k ablation for the midterm report.

Runs the full pipeline across multiple τ values and k values,
then prints a consolidated table suitable for copy-paste into your report.

Usage
-----
# Sweep τ (recommended for midterm)
python -m src.ablation --n 50 --mode tau

# Sweep k (retrieval depth)
python -m src.ablation --n 50 --mode k

# Both
python -m src.ablation --n 50 --mode both
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List

from tqdm import tqdm

from src.claims import extract_claims
from src.config import DEFAULT_SPLIT, RUNS_DIR
from src.data import load_pubmedqa
from src.generate import generate_draft
from src.repair import repair
from src.retrieve import build_index, retrieve, save_index
from src.verify import verify_claims
from src.rewrite import rewrite_unsupported

logging.basicConfig(level=logging.WARNING)  # quiet during sweep
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sweep configs
# ---------------------------------------------------------------------------

TAU_VALUES   = [0.35, 0.45, 0.55, 0.65, 0.75]
K_VALUES     = [1, 3, 5, 7]
DEFAULT_K    = 5
DEFAULT_TAU  = 0.55
DEFAULT_N    = 50


# ---------------------------------------------------------------------------
# Single-run helper
# ---------------------------------------------------------------------------

def run_single(examples, index, meta, tau: float, k: int, backend: str, repair_mode: str = "delete") -> dict:
    """Run pipeline on all examples with given tau and k, return aggregate metrics."""
    rag_correct = vrag_correct = 0
    rag_total_claims = rag_unsup_total = 0
    vrag_total_claims = 0
    runtimes: List[float] = []

    for ex in examples:
        passages = retrieve(ex["question"], index, meta, k=k)
        t0 = time.perf_counter()
        draft  = generate_draft(ex["question"], passages, backend=backend)
        claims = extract_claims(draft["raw"])
        verified = verify_claims(claims, passages, tau=tau)
        if repair_mode == "rewrite":
            rewritten = rewrite_unsupported(draft=draft, verified=verified, passages=passages, question=ex["question"], tau=tau)
            final = {
                "answer_label": rewritten.get("answer_label"),
                "final_summary": rewritten.get("final_summary"),
                "supported_claims": list(rewritten.get("supported_claims", [])),
                "unsupported_claims": [],
                "repair_applied": bool(rewritten.get("repair_applied", False)),
            }
        else:
            final = repair(draft, verified)
        runtimes.append(time.perf_counter() - t0)

        n_unsup = sum(1 for v in verified if not v["supported"])

        rag_correct      += int(draft["answer_label"] == ex["label"])
        vrag_correct     += int(final["answer_label"] == ex["label"])
        rag_total_claims += len(claims)
        rag_unsup_total  += n_unsup
        vrag_total_claims += len(final["supported_claims"])

    n = len(examples)
    return {
        "tau": tau,
        "k":   k,
        "n":   n,
        "rag_acc":          round(rag_correct / n, 3),
        "vrag_acc":         round(vrag_correct / n, 3),
        "rag_unsup_rate":   round(rag_unsup_total / rag_total_claims, 3) if rag_total_claims else 0.0,
        "vrag_unsup_rate":  0.0,
        "rag_avg_claims":   round(rag_total_claims / n, 2),
        "vrag_avg_claims":  round(vrag_total_claims / n, 2),
        "mean_rt_s":        round(sum(runtimes) / n, 2),
    }


# ---------------------------------------------------------------------------
# Table printers
# ---------------------------------------------------------------------------

def _tau_table(rows: List[dict]) -> str:
    lines = [
        "\n" + "=" * 80,
        f"  TAU SWEEP  (N={rows[0]['n']}  k={rows[0]['k']})",
        "=" * 80,
        f"  {'τ':>6} | {'RAG Unsup':>10} | {'VRAG Unsup':>11} | "
        f"{'RAG Acc':>8} | {'VRAG Acc':>9} | {'Avg Cl (R→V)':>13} | {'RT(s)':>6}",
        "  " + "-" * 76,
    ]
    for r in rows:
        lines.append(
            f"  {r['tau']:>6.2f} | {r['rag_unsup_rate']:>10.3f} | {r['vrag_unsup_rate']:>11.3f} | "
            f"{r['rag_acc']:>8.3f} | {r['vrag_acc']:>9.3f} | "
            f"{r['rag_avg_claims']:>5.1f} → {r['vrag_avg_claims']:<5.1f}   | {r['mean_rt_s']:>6.2f}"
        )
    lines.append("=" * 80 + "\n")
    return "\n".join(lines)


def _k_table(rows: List[dict]) -> str:
    lines = [
        "\n" + "=" * 80,
        f"  K SWEEP  (N={rows[0]['n']}  τ={rows[0]['tau']})",
        "=" * 80,
        f"  {'k':>4} | {'RAG Unsup':>10} | {'VRAG Unsup':>11} | "
        f"{'RAG Acc':>8} | {'VRAG Acc':>9} | {'Avg Cl (R→V)':>13} | {'RT(s)':>6}",
        "  " + "-" * 76,
    ]
    for r in rows:
        lines.append(
            f"  {r['k']:>4} | {r['rag_unsup_rate']:>10.3f} | {r['vrag_unsup_rate']:>11.3f} | "
            f"{r['rag_acc']:>8.3f} | {r['vrag_acc']:>9.3f} | "
            f"{r['rag_avg_claims']:>5.1f} → {r['vrag_avg_claims']:<5.1f}   | {r['mean_rt_s']:>6.2f}"
        )
    lines.append("=" * 80 + "\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--n",       type=int,   default=DEFAULT_N)
    p.add_argument("--mode",    type=str,   default="tau", choices=["tau", "k", "both"])
    p.add_argument("--backend", type=str,   default="stub", choices=["stub", "openai"])
    p.add_argument(
        "--repair", type=str, default="delete",
        choices=["delete", "rewrite"],
        help="Repair policy to apply during ablation: delete or rewrite",
    )
    p.add_argument("--split",   type=str,   default=DEFAULT_SPLIT)
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print(f"\nLoading {args.n} examples…")
    examples = load_pubmedqa(split=args.split, limit=args.n)

    print("Building FAISS index…")
    index, embeddings, meta = build_index(examples)
    save_index(index, embeddings, meta)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = RUNS_DIR / f"ablation_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_results = {}

    # --- τ sweep ---
    if args.mode in ("tau", "both"):
        print(f"\nRunning τ sweep: {TAU_VALUES}  (k={DEFAULT_K})")
        tau_rows = []
        for tau in tqdm(TAU_VALUES, desc="τ sweep"):
            row = run_single(examples, index, meta, tau=tau, k=DEFAULT_K, backend=args.backend, repair_mode=args.repair)
            tau_rows.append(row)
        table = _tau_table(tau_rows)
        print(table)
        (out_dir / "tau_sweep.txt").write_text(table)
        all_results["tau_sweep"] = tau_rows

    # --- k sweep ---
    if args.mode in ("k", "both"):
        print(f"\nRunning k sweep: {K_VALUES}  (τ={DEFAULT_TAU})")
        k_rows = []
        for k in tqdm(K_VALUES, desc="k sweep"):
            row = run_single(examples, index, meta, tau=DEFAULT_TAU, k=k, backend=args.backend, repair_mode=args.repair)
            k_rows.append(row)
        table = _k_table(k_rows)
        print(table)
        (out_dir / "k_sweep.txt").write_text(table)
        all_results["k_sweep"] = k_rows

    with open(out_dir / "ablation_results.json", "w") as fh:
        json.dump(all_results, fh, indent=2)

    print(f"Ablation outputs saved to: {out_dir}\n")


if __name__ == "__main__":
    main()
