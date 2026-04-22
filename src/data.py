"""
data.py — PubMedQA dataset loading and normalisation.

Public API
----------
load_pubmedqa(split, limit) -> List[Example]

Example (TypedDict)
-------------------
{
    "id":          str,
    "question":    str,
    "context":     str,   # concatenated abstract sentences
    "label":       str,   # "yes" | "no" | "maybe"
    "long_answer": str,   # expert long-form answer (may be empty)
}
"""

from __future__ import annotations

import logging
from typing import List, TypedDict

from datasets import load_dataset  # type: ignore

from src.config import (
    DEFAULT_N_EXAMPLES,
    DEFAULT_SPLIT,
    PUBMEDQA_DATASET_NAME,
    PUBMEDQA_SUBSET,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class Example(TypedDict):
    id: str
    question: str
    context: str          # flattened abstract text
    label: str            # yes / no / maybe
    long_answer: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _flatten_context(raw_ctx: dict | list | str) -> str:
    """
    PubMedQA contexts are stored as a dict with 'contexts' (list of strings)
    and 'labels'/'meshes' keys, or occasionally as a plain string.
    Return a single whitespace-separated string of all sentences.
    """
    if isinstance(raw_ctx, str):
        return raw_ctx.strip()

    if isinstance(raw_ctx, list):
        return " ".join(s.strip() for s in raw_ctx if s)

    if isinstance(raw_ctx, dict):
        # HF schema: {"contexts": [...], "labels": [...], "meshes": [...]}
        sentences: list[str] = raw_ctx.get("contexts", [])
        return " ".join(s.strip() for s in sentences if s)

    return ""


def _normalise_label(raw_label: str) -> str:
    """Lower-case and strip; keep only yes/no/maybe."""
    label = str(raw_label).strip().lower()
    if label not in {"yes", "no", "maybe"}:
        logger.warning("Unexpected label %r — defaulting to 'maybe'", raw_label)
        return "maybe"
    return label


def _row_to_example(row: dict) -> Example:
    """Convert a raw HuggingFace row to our canonical Example schema."""
    # The pqa_labeled subset uses key 'pubid' as the unique identifier
    uid = str(row.get("pubid", row.get("id", "")))

    question: str = row.get("question", "").strip()

    context: str = _flatten_context(row.get("context", ""))

    # Final decision label
    raw_label = row.get("final_decision", row.get("label", "maybe"))
    label = _normalise_label(raw_label)

    long_answer: str = row.get("long_answer", "").strip()

    return Example(
        id=uid,
        question=question,
        context=context,
        label=label,
        long_answer=long_answer,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_pubmedqa(
    split: str = DEFAULT_SPLIT,
    limit: int = DEFAULT_N_EXAMPLES,
) -> List[Example]:
    """
    Load PubMedQA examples from HuggingFace and return them as a list of
    ``Example`` dicts.

    Parameters
    ----------
    split:
        Dataset split to use — typically ``"train"``.  PubMedQA (pqa_labeled)
        only ships a train split; test/validation splits are available in the
        pqa_unlabeled subset.
    limit:
        Maximum number of examples to return.  ``-1`` returns all.

    Returns
    -------
    List[Example]
        Normalised examples with keys id, question, context, label, long_answer.
    """
    logger.info(
        "Loading %s / %s  split=%s  limit=%s",
        PUBMEDQA_DATASET_NAME,
        PUBMEDQA_SUBSET,
        split,
        limit,
    )

    ds = load_dataset(PUBMEDQA_DATASET_NAME, PUBMEDQA_SUBSET, split=split, trust_remote_code=True)

    if limit and limit > 0:
        ds = ds.select(range(min(limit, len(ds))))

    examples: List[Example] = [_row_to_example(row) for row in ds]

    logger.info("Loaded %d examples.", len(examples))
    return examples
