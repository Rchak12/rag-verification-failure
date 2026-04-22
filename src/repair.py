"""
repair.py — Repair policy: delete unsupported claims, regenerate final answer.

Public API
----------
repair(draft, verified_claims) -> FinalAnswer

Repair Rule (MVP — delete)
--------------------------
1. Keep only claims marked ``supported=True``.
2. Re-derive the answer label from the fraction of supported claims:
   - All supported                     → keep original label
   - Majority unsupported (> 50 %)     → "maybe"
   - No supported claims at all        → "maybe"
3. Synthesise a short final answer from the retained claims.

FinalAnswer (TypedDict)
-----------------------
{
    "answer_label":        str,
    "final_summary":       str,
    "supported_claims":    List[str],
    "unsupported_claims":  List[str],
    "repair_applied":      bool,
}
"""

from __future__ import annotations

import logging
from typing import List, TypedDict

from src.generate import DraftAnswer
from src.verify import VerifiedClaim

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class FinalAnswer(TypedDict):
    answer_label: str
    final_summary: str
    supported_claims: List[str]
    unsupported_claims: List[str]
    repair_applied: bool


# ---------------------------------------------------------------------------
# Label re-derivation helper
# ---------------------------------------------------------------------------

def _derive_label(
    original_label: str,
    n_supported: int,
    n_total: int,
) -> str:
    """
    Re-derive an answer label after repair.

    Rules
    -----
    - 0 supported claims             → "maybe"
    - > 50 % claims unsupported      → "maybe"
    - Otherwise                      → keep original label
    """
    if n_total == 0 or n_supported == 0:
        return "maybe"
    unsupported_frac = (n_total - n_supported) / n_total
    if unsupported_frac > 0.5:
        return "maybe"
    return original_label


# ---------------------------------------------------------------------------
# Summary synthesis helper
# ---------------------------------------------------------------------------

def _synthesise_summary(
    label: str,
    supported_claims: List[str],
    original_summary: str,
) -> str:
    """
    Build a concise final summary from retained claims.
    Falls back to the original summary if no claims remain.
    """
    if not supported_claims:
        return f"[Repaired] Insufficient evidence to confirm. Original: {original_summary}"

    claim_text = " ".join(supported_claims)
    return f"[{label.upper()}] {claim_text}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def repair(
    draft: DraftAnswer,
    verified_claims: List[VerifiedClaim],
) -> FinalAnswer:
    """
    Apply the delete-unsupported-claims repair policy.

    Parameters
    ----------
    draft:            The original DraftAnswer from generate.generate_draft().
    verified_claims:  Verification results from verify.verify_claims().

    Returns
    -------
    FinalAnswer with repaired label, summary, and claim lists.
    """
    supported: List[str] = []
    unsupported: List[str] = []

    for vc in verified_claims:
        if vc["supported"]:
            supported.append(vc["claim"])
        else:
            unsupported.append(vc["claim"])

    repair_applied = len(unsupported) > 0

    new_label = _derive_label(
        original_label=draft["answer_label"],
        n_supported=len(supported),
        n_total=len(verified_claims),
    )

    final_summary = _synthesise_summary(
        label=new_label,
        supported_claims=supported,
        original_summary=draft["summary"],
    )

    if repair_applied:
        logger.info(
            "Repair: deleted %d / %d claims; label %s → %s",
            len(unsupported),
            len(verified_claims),
            draft["answer_label"],
            new_label,
        )
    else:
        logger.debug("Repair: no changes needed (all claims supported).")

    return FinalAnswer(
        answer_label=new_label,
        final_summary=final_summary,
        supported_claims=supported,
        unsupported_claims=unsupported,
        repair_applied=repair_applied,
    )
