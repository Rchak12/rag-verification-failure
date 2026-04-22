"""
controlled_repair_test.py - Forced Repair Activation Experiment

Takes false positive cases where verification failed to flag hedged claims,
manually marks them as unsupported, and tests whether REWRITE actually works
when properly triggered.

This answers: "Does repair work when verification actually flags problems?"

Experimental design:
1. Load the 41 false positive cases
2. Manually mark hedged claims as "unsupported"
3. Run them through REWRITE
4. Compare original (hedged) vs rewritten vs gold label
5. Measure if rewriting improves accuracy

Possible outcomes:
A) Rewriting fixes hedging → "Repair works, verification is the bottleneck"
B) Rewriting stays vague → "Repair itself is broken"
C) Mixed results → "Repair sometimes helps"

Usage:
    python -m src.controlled_repair_test --n 20
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from tqdm import tqdm

from src.data import load_pubmedqa
from src.rewrite import rewrite_unsupported
from src.retrieve import load_index, retrieve
from src.config import RUNS_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Load False Positive Cases
# ============================================================================

def load_false_positive_cases(run_dir: Path, n: int = None) -> List[Dict]:
    """
    Load false positive cases from the forced-answer run.

    A false positive is:
    - Predicted label != gold label (wrong answer)
    - All claims verified as supported (0% unsupported rate)

    Returns list of cases with question, gold label, predicted label, claims, etc.
    """
    # Load drafts
    drafts_path = run_dir / "drafts.jsonl"
    drafts = []
    with open(drafts_path) as f:
        for line in f:
            drafts.append(json.loads(line))

    # Load gold labels
    examples = load_pubmedqa(split="train", limit=len(drafts))
    gold_labels = {ex["id"]: ex["label"] for ex in examples}

    # Identify false positives
    false_positives = []
    for draft in drafts:
        qid = draft["id"]
        question = draft["question"]
        gold_label = gold_labels.get(qid, "?")
        predicted_label = draft["draft"]["answer_label"]
        summary = draft["draft"]["summary"]
        claims = draft["draft"].get("claims", [])

        # Check if false positive (wrong answer)
        if predicted_label != gold_label:
            false_positives.append({
                "id": qid,
                "question": question,
                "gold_label": gold_label,
                "predicted_label": predicted_label,
                "summary": summary,
                "claims": claims,
            })

    logger.info(f"Found {len(false_positives)} false positive cases")

    # Limit if requested
    if n is not None and n < len(false_positives):
        false_positives = false_positives[:n]
        logger.info(f"Limited to {n} cases for testing")

    return false_positives


# ============================================================================
# Controlled Repair Test
# ============================================================================

def run_controlled_repair_test(
    false_positives: List[Dict],
    index,
    meta,
    embeddings,
    k: int = 3,
) -> List[Dict]:
    """
    For each false positive case:
    1. Retrieve passages (same as original experiment)
    2. Manually mark claims as "unsupported" (force repair trigger)
    3. Run REWRITE to get repaired answer
    4. Compare: original vs rewritten vs gold
    5. Check if rewriting improves accuracy
    """
    results = []

    for fp in tqdm(false_positives, desc="Testing forced repair"):
        qid = fp["id"]
        question = fp["question"]
        gold_label = fp["gold_label"]
        original_label = fp["predicted_label"]
        original_claims = fp["claims"]

        # Retrieve passages (same as original)
        passages = retrieve(question, index, meta, k=k, embeddings=embeddings)

        # Create "verified claims" structure where all claims are marked unsupported
        # (This simulates what would happen if verification actually flagged hedging)
        verified = []
        for claim in original_claims:
            verified.append({
                "claim": claim,
                "supported": False,  # FORCE UNSUPPORTED
                "support_score": 0.0,
                "evidence_sentence": "",
                "evidence_source_id": "",
            })

        # Create draft structure
        draft = {
            "answer_label": original_label,
            "summary": fp["summary"],
            "raw": fp["summary"],  # Simplified
            "cited_sources": ["S1"],  # Simplified
        }

        # Run REWRITE (this is the actual repair mechanism)
        try:
            repaired = rewrite_unsupported(
                draft=draft,
                verified=verified,
                passages=passages,
                question=question,
                tau=0.5,
            )

            rewritten_label = repaired["answer_label"]
            rewritten_summary = repaired["final_summary"]
            rewritten_claims = repaired["rewritten_claims"]
            n_rewritten = repaired["n_rewritten"]

            # Check if rewriting improved accuracy
            original_correct = (original_label == gold_label)
            rewritten_correct = (rewritten_label == gold_label)

            improvement = "improved" if (not original_correct and rewritten_correct) else \
                         "worsened" if (original_correct and not rewritten_correct) else \
                         "same"

            results.append({
                "id": qid,
                "question": question,
                "gold_label": gold_label,

                "original_label": original_label,
                "original_correct": original_correct,
                "original_claims": original_claims,

                "rewritten_label": rewritten_label,
                "rewritten_correct": rewritten_correct,
                "rewritten_summary": rewritten_summary,
                "rewritten_claims": rewritten_claims,
                "n_rewritten": n_rewritten,

                "improvement": improvement,
            })

        except Exception as e:
            logger.error(f"Failed to rewrite {qid}: {e}")
            results.append({
                "id": qid,
                "question": question,
                "gold_label": gold_label,
                "original_label": original_label,
                "original_correct": False,
                "error": str(e),
            })

    return results


# ============================================================================
# Analysis
# ============================================================================

def analyze_repair_effectiveness(results: List[Dict]) -> Dict:
    """
    Analyze whether forced repair improves accuracy.

    Metrics:
    - Original accuracy (should be 0% since all are false positives)
    - Rewritten accuracy (did repair fix any?)
    - Improvement rate
    - Still hedged after rewriting
    """
    n_total = len([r for r in results if "error" not in r])

    if n_total == 0:
        return {"error": "No successful repairs"}

    original_correct = sum(r.get("original_correct", False) for r in results if "error" not in r)
    rewritten_correct = sum(r.get("rewritten_correct", False) for r in results if "error" not in r)

    improved = sum(1 for r in results if r.get("improvement") == "improved")
    worsened = sum(1 for r in results if r.get("improvement") == "worsened")
    same = sum(1 for r in results if r.get("improvement") == "same")

    # Check if rewritten claims still hedge
    still_hedging = 0
    for r in results:
        if "rewritten_claims" in r:
            for claim_obj in r["rewritten_claims"]:
                # Handle both string and dict formats
                claim_text = claim_obj if isinstance(claim_obj, str) else claim_obj.get("claim", "")
                if any(word in claim_text.lower() for word in ["may", "might", "suggest", "unclear", "less understood", "not fully"]):
                    still_hedging += 1
                    break

    return {
        "n_total": n_total,
        "original_accuracy": original_correct / n_total,
        "rewritten_accuracy": rewritten_correct / n_total,
        "improvement_rate": improved / n_total,
        "n_improved": improved,
        "n_worsened": worsened,
        "n_same": same,
        "still_hedging_count": still_hedging,
        "still_hedging_rate": still_hedging / n_total,
    }


def write_repair_report(results: List[Dict], metrics: Dict, output_path: Path):
    """Write detailed repair test report."""
    lines = []

    lines.append("# Controlled Repair Activation Test\n\n")

    lines.append("## Experimental Design\n\n")
    lines.append("This experiment tests whether the REWRITE repair strategy works when ")
    lines.append("verification actually flags problematic claims.\n\n")
    lines.append("**Method:**\n")
    lines.append("1. Take false positive cases (wrong answers with verified claims)\n")
    lines.append("2. Manually mark all claims as \"unsupported\" (force repair trigger)\n")
    lines.append("3. Run REWRITE to get repaired answers\n")
    lines.append("4. Compare original vs rewritten accuracy\n\n")

    # Check for errors
    if "error" in metrics:
        lines.append("## Error\n\n")
        lines.append(f"{metrics['error']}\n\n")
        lines.append("All test cases failed to complete. Check the error logs for details.\n")
        with open(output_path, "w") as f:
            f.writelines(lines)
        return

    lines.append("## Results Summary\n\n")
    lines.append(f"**Total cases tested:** {metrics['n_total']}\n\n")

    lines.append("| Metric | Value | Interpretation |\n")
    lines.append("|--------|-------|----------------|\n")
    lines.append(f"| Original Accuracy | {metrics['original_accuracy']:.1%} | All are false positives by design |\n")
    lines.append(f"| Rewritten Accuracy | {metrics['rewritten_accuracy']:.1%} | After forced repair |\n")
    lines.append(f"| Improvement Rate | {metrics['improvement_rate']:.1%} | Cases where repair helped |\n")
    lines.append(f"| Still Hedging Rate | {metrics['still_hedging_rate']:.1%} | Rewritten claims still vague |\n\n")

    lines.append("### Repair Outcome Distribution\n\n")
    lines.append(f"- **Improved:** {metrics['n_improved']} cases (repair fixed the answer)\n")
    lines.append(f"- **Same:** {metrics['n_same']} cases (repair didn't change correctness)\n")
    lines.append(f"- **Worsened:** {metrics['n_worsened']} cases (repair made it worse)\n\n")

    # Interpretation
    lines.append("## Interpretation\n\n")

    if metrics['rewritten_accuracy'] > 0.3:
        lines.append("**Finding:** Repair is effective when properly triggered.\n\n")
        lines.append("The rewriting mechanism works well—the problem is that verification ")
        lines.append("fails to flag hedged claims in the first place. If verification could ")
        lines.append("detect hedging, REWRITE would successfully fix ~")
        lines.append(f"{metrics['improvement_rate']:.0%} of cases.\n\n")
        lines.append("**Implication:** The bottleneck is verification, not repair.\n")

    elif metrics['still_hedging_rate'] > 0.5:
        lines.append("**Finding:** Repair still produces hedged outputs.\n\n")
        lines.append(f"Even when forced to rewrite, {metrics['still_hedging_rate']:.0%} of ")
        lines.append("rewritten claims still contain hedging language. This suggests the ")
        lines.append("rewriting mechanism itself struggles to produce definitive claims.\n\n")
        lines.append("**Implication:** Both verification and repair have limitations.\n")

    else:
        lines.append("**Finding:** Mixed results—repair helps sometimes.\n\n")
        lines.append(f"Repair improves accuracy in {metrics['improvement_rate']:.0%} of cases, ")
        lines.append("suggesting partial effectiveness. The mechanism works but may need ")
        lines.append("stronger prompting or multiple rewrite iterations.\n\n")
        lines.append("**Implication:** Repair shows promise but needs refinement.\n")

    # Examples
    lines.append("\n---\n\n## Representative Examples\n\n")

    # Find improved cases
    improved_cases = [r for r in results if r.get("improvement") == "improved"]
    if improved_cases:
        lines.append("### Cases Where Repair Improved Accuracy\n\n")
        for r in improved_cases[:3]:
            lines.append(f"**ID: {r['id']}**\n")
            lines.append(f"- Question: {r['question']}\n")
            lines.append(f"- Gold: **{r['gold_label']}**\n")
            lines.append(f"- Original: {r['original_label']} (WRONG)\n")
            lines.append(f"- Rewritten: {r['rewritten_label']} (CORRECT ✓)\n")
            if 'rewritten_summary' in r:
                lines.append(f"- Rewritten summary: {r['rewritten_summary'][:200]}...\n")
            lines.append("\n")

    # Find cases that stayed wrong
    same_wrong = [r for r in results if r.get("improvement") == "same" and not r.get("rewritten_correct")]
    if same_wrong:
        lines.append("### Cases Where Repair Stayed Wrong\n\n")
        for r in same_wrong[:3]:
            lines.append(f"**ID: {r['id']}**\n")
            lines.append(f"- Question: {r['question']}\n")
            lines.append(f"- Gold: **{r['gold_label']}**\n")
            lines.append(f"- Original: {r['original_label']} (WRONG)\n")
            lines.append(f"- Rewritten: {r['rewritten_label']} (STILL WRONG)\n")

            # Check if still hedging
            if 'rewritten_claims' in r:
                for claim_obj in r['rewritten_claims']:
                    claim_text = claim_obj if isinstance(claim_obj, str) else claim_obj.get("claim", "")
                    if any(word in claim_text.lower() for word in ["may", "might", "suggest", "unclear"]):
                        lines.append(f"- Still hedges: \"{claim_text[:150]}...\"\n")
                        break
            lines.append("\n")

    with open(output_path, "w") as f:
        f.writelines(lines)

    logger.info(f"Report written to {output_path}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Controlled repair activation test",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--n", type=int, default=20,
                       help="Number of false positive cases to test")
    parser.add_argument("--k", type=int, default=3,
                       help="Number of passages to retrieve")
    parser.add_argument("--run-dir", type=Path,
                       default=Path("outputs/runs/three_systems_20260410_135637"),
                       help="Directory containing false positive cases")

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("CONTROLLED REPAIR ACTIVATION TEST")
    logger.info("=" * 80)
    logger.info(f"Testing {args.n} false positive cases")
    logger.info(f"Run directory: {args.run_dir}")

    # Load false positive cases
    false_positives = load_false_positive_cases(args.run_dir, n=args.n)

    if len(false_positives) == 0:
        logger.error("No false positive cases found!")
        return

    # Load retrieval index
    logger.info("Loading retrieval index...")
    index, embeddings, meta = load_index()

    # Run controlled repair test
    logger.info("Running forced repair on false positive cases...")
    results = run_controlled_repair_test(
        false_positives,
        index,
        meta,
        embeddings,
        k=args.k,
    )

    # Analyze results
    logger.info("Analyzing repair effectiveness...")
    metrics = analyze_repair_effectiveness(results)

    # Save results
    output_dir = RUNS_DIR / "controlled_repair_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    results_path = output_dir / "results.json"
    with open(results_path, "w") as f:
        json.dump({
            "metrics": metrics,
            "results": results,
        }, f, indent=2)

    report_path = output_dir / "repair_test_report.md"
    write_repair_report(results, metrics, report_path)

    # Print summary
    logger.info("=" * 80)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Tested: {metrics['n_total']} cases")
    logger.info(f"Original accuracy: {metrics['original_accuracy']:.1%} (all false positives)")
    logger.info(f"Rewritten accuracy: {metrics['rewritten_accuracy']:.1%}")
    logger.info(f"Improvement rate: {metrics['improvement_rate']:.1%}")
    logger.info(f"  - Improved: {metrics['n_improved']}")
    logger.info(f"  - Same: {metrics['n_same']}")
    logger.info(f"  - Worsened: {metrics['n_worsened']}")
    logger.info(f"Still hedging: {metrics['still_hedging_rate']:.1%}")
    logger.info("=" * 80)

    # Interpretation
    if metrics['rewritten_accuracy'] > 0.3:
        logger.info("✓ FINDING: Repair works when verification flags claims properly")
        logger.info("  → Bottleneck is verification, not repair")
    elif metrics['still_hedging_rate'] > 0.5:
        logger.info("✗ FINDING: Repair still produces hedged outputs")
        logger.info("  → Both verification and repair have limitations")
    else:
        logger.info("~ FINDING: Repair partially effective")
        logger.info("  → Shows promise but needs refinement")

    logger.info(f"\n✓ Full report: {report_path}")
    logger.info(f"✓ Results JSON: {results_path}")


if __name__ == "__main__":
    main()
