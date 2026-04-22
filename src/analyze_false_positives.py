"""
analyze_false_positives.py — Systematic Verifier Failure Analysis

Analyzes RAG baseline outputs to identify and categorize false positives where:
- Claims are marked "supported" by NLI verifier
- But the final answer is WRONG (doesn't match gold label)

This reveals the 82% false positive problem: 100% verification pass + 18% accuracy.

Failure Categories:
1. Hedging/Abstention - Vague claims that avoid committing to yes/no
2. Missing Qualifiers - Omits critical context (e.g., "in mice", "preliminary")
3. Correlation→Causation - Upgrades association to causal language
4. Overgeneralization - Removes important scope restrictions
5. Paraphrase Drift - Semantically similar but factually different
6. Population Mismatch - Wrong demographic or condition scope

Usage:
    python -m src.analyze_false_positives \
        --run-dir outputs/runs/three_systems_20260410_135637 \
        --n 50
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd


# Failure category taxonomy
FAILURE_CATEGORIES = [
    "hedging",  # Vague claims avoiding commitment
    "missing_qualifiers",  # Omits critical context
    "correlation_to_causation",  # Association → causes
    "overgeneralization",  # Removes scope restrictions
    "paraphrase_drift",  # Semantically close but factually wrong
    "population_mismatch",  # Wrong demographic/condition
]


def load_run_data(run_dir: Path) -> tuple[List[Dict], pd.DataFrame]:
    """Load drafts.jsonl and three_system_results.csv."""
    # Load drafts
    drafts_path = run_dir / "drafts.jsonl"
    drafts = []
    with open(drafts_path) as f:
        for line in f:
            drafts.append(json.loads(line))

    # Load results CSV
    results_path = run_dir / "three_system_results.csv"
    results_df = pd.read_csv(results_path)

    return drafts, results_df


def extract_false_positives(drafts: List[Dict], results_df: pd.DataFrame) -> List[Dict]:
    """
    Extract examples where:
    - All claims verified as supported (system_a_unsup_rate = 0)
    - But answer is WRONG (system_a_correct = 0)

    These are the 82% false positives.
    """
    false_positives = []

    for draft in drafts:
        qid = draft["id"]

        # Find corresponding result row
        row = results_df[results_df["id"] == qid]
        if row.empty:
            continue

        row = row.iloc[0]

        # Check if this is a false positive case
        # (wrong answer but all claims verified)
        if row["system_a_correct"] == 0 and row["system_a_unsup_rate"] == 0:
            false_positives.append({
                "id": qid,
                "question": row["question"],
                "gold_label": row["gold_label"],
                "predicted_label": row["system_a_label"],
                "draft_summary": draft["draft"]["summary"],
                "claims": draft["draft"].get("claims", []),
                "n_claims": row["system_a_n_claims"],
            })

    return false_positives


def manual_categorization_template(false_positives: List[Dict], output_path: Path) -> None:
    """
    Generate a CSV template for manual categorization of failure types.

    Analyst should review each claim and assign failure category.
    """
    rows = []

    for fp in false_positives:
        for i, claim in enumerate(fp["claims"]):
            rows.append({
                "id": fp["id"],
                "question": fp["question"],
                "gold_label": fp["gold_label"],
                "predicted_label": fp["predicted_label"],
                "claim_index": i,
                "claim_text": claim,
                "failure_category": "",  # TO BE FILLED MANUALLY
                "notes": "",  # Optional analyst notes
            })

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    print(f"✅ Manual categorization template saved: {output_path}")
    print(f"   {len(rows)} claims from {len(false_positives)} false positive examples")
    print(f"\n📝 Next step: Open this CSV and manually fill the 'failure_category' column")
    print(f"   Categories: {', '.join(FAILURE_CATEGORIES)}")


def analyze_categorized_data(categorized_path: Path, output_dir: Path) -> None:
    """
    After manual categorization, analyze results and generate:
    - Summary table of failure counts by category
    - Top examples for each category
    - Written analysis
    """
    df = pd.read_csv(categorized_path)

    # Filter to only categorized rows
    df_categorized = df[df["failure_category"].notna() & (df["failure_category"] != "")]

    if df_categorized.empty:
        print("⚠️  No categorized failures found. Please fill the 'failure_category' column first.")
        return

    # Category counts
    category_counts = df_categorized["failure_category"].value_counts()

    # Summary table
    summary = []
    summary.append("# Verifier Failure Analysis: False Positive Categorization\n")
    summary.append("## Failure Category Counts\n")
    summary.append(f"**Total False Positive Claims:** {len(df_categorized)}\n")
    summary.append(f"**From Examples:** {df_categorized['id'].nunique()}\n\n")
    summary.append("| Category | Count | % of Total |\n")
    summary.append("|----------|-------|------------|\n")

    for cat, count in category_counts.items():
        pct = 100 * count / len(df_categorized)
        summary.append(f"| {cat} | {count} | {pct:.1f}% |\n")

    summary.append("\n---\n\n")

    # Top examples per category
    summary.append("## Representative Examples by Category\n\n")

    for cat in FAILURE_CATEGORIES:
        cat_examples = df_categorized[df_categorized["failure_category"] == cat]
        if cat_examples.empty:
            continue

        summary.append(f"### {cat.replace('_', ' ').title()}\n\n")

        # Show up to 3 examples
        for _, row in cat_examples.head(3).iterrows():
            summary.append(f"**ID {row['id']}**\n")
            summary.append(f"- Question: {row['question']}\n")
            summary.append(f"- Gold: {row['gold_label']} | Predicted: {row['predicted_label']}\n")
            summary.append(f"- Claim (Verified ✅): \"{row['claim_text']}\"\n")
            if pd.notna(row["notes"]) and row["notes"]:
                summary.append(f"- Notes: {row['notes']}\n")
            summary.append("\n")

        summary.append("---\n\n")

    # Write summary
    summary_path = output_dir / "false_positive_analysis.md"
    summary_path.write_text("".join(summary))

    print(f"✅ False positive analysis complete!")
    print(f"   Summary: {summary_path}")
    print(f"\n📊 Category Distribution:")
    print(category_counts)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze false positives in verified RAG outputs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="Path to run directory (e.g., outputs/runs/three_systems_20260410_135637)",
    )
    parser.add_argument(
        "--categorized",
        type=Path,
        help="Path to manually categorized CSV (for analysis step)",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=50,
        help="Expected number of examples in run",
    )

    args = parser.parse_args()

    # Step 1: Extract false positives and generate template
    if not args.categorized:
        print("🔍 Step 1: Extracting false positives from run data...")
        drafts, results_df = load_run_data(args.run_dir)

        print(f"   Loaded {len(drafts)} drafts and {len(results_df)} results")

        false_positives = extract_false_positives(drafts, results_df)

        print(f"\n📊 Found {len(false_positives)} false positive examples")
        print(f"   (Wrong answer but all claims verified)")

        # Generate manual categorization template
        template_path = args.run_dir / "false_positive_categorization_template.csv"
        manual_categorization_template(false_positives, template_path)

        print(f"\n⏭️  Next: Manually categorize failures in {template_path}")
        print(f"   Then run: python -m src.analyze_false_positives \\")
        print(f"              --run-dir {args.run_dir} \\")
        print(f"              --categorized {template_path}")

    # Step 2: Analyze categorized data
    else:
        print("📊 Step 2: Analyzing categorized false positives...")
        analyze_categorized_data(args.categorized, args.run_dir)


if __name__ == "__main__":
    main()
