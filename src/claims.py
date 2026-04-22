"""
claims.py — Factual claim extraction from draft answer text.

Public API
----------
extract_claims(draft_text: str) -> List[str]

Strategy (in order of precedence)
----------------------------------
1. If the text contains a "Claims:" section with bullet / numbered items,
   parse those items directly.
2. Otherwise fall back to sentence splitting on the full text.

Each returned claim is a single, non-empty string stripped of bullet markers,
source annotations like "(Sources: S1)", and leading/trailing whitespace.
"""

from __future__ import annotations

import re
from typing import List


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Regex for common bullet / ordered-list prefixes:  "- ", "* ", "• ", "1. ", "2) "
_BULLET_RE = re.compile(r"^[-*•]\s+|^\d+[.)]\s+")

# "Claims:" section header (case-insensitive)
_CLAIMS_HEADER_RE = re.compile(r"claims\s*:", re.IGNORECASE)

# Source citation annotations appended to claims: "(Sources: S1,S2)"
_SOURCE_ANNOTATION_RE = re.compile(r"\(\s*[Ss]ources?\s*:[^)]*\)", re.IGNORECASE)

# Sentence boundary: ends with . ! ?  (not inside abbreviations — heuristic)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _strip_claim(text: str) -> str:
    """Remove bullet markers, source annotations, and extra whitespace."""
    text = _BULLET_RE.sub("", text.strip())
    text = _SOURCE_ANNOTATION_RE.sub("", text)
    return text.strip()


def _parse_bullet_block(block: str) -> List[str]:
    """
    Extract claim strings from a bullet / numbered list block.
    Lines that don't start with a bullet marker are also kept if non-empty
    (handles plain-sentence lists).
    """
    claims: List[str] = []
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        claim = _strip_claim(line)
        if claim:
            claims.append(claim)
    return claims


def _sentence_split(text: str) -> List[str]:
    """
    Naïve sentence splitter.  Splits on . ! ? followed by whitespace.
    Filters very short fragments (< 10 chars).
    """
    sentences = _SENTENCE_SPLIT_RE.split(text.strip())
    return [s.strip() for s in sentences if len(s.strip()) >= 10]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_claims(draft_text: str) -> List[str]:
    """
    Extract a list of atomic factual claim strings from *draft_text*.

    The function first looks for an explicit ``Claims:`` section.  If found,
    it parses that block; otherwise it falls back to sentence splitting the
    entire text.

    Parameters
    ----------
    draft_text:
        Raw text output from the generation stage.  May contain a structured
        ``Label / Summary / Claims:`` format or free-form prose.

    Returns
    -------
    List[str]
        Non-empty claim strings, each representing one atomic assertion.
    """
    if not draft_text or not draft_text.strip():
        return []

    # --- Try structured "Claims:" section first ---
    match = _CLAIMS_HEADER_RE.search(draft_text)
    if match:
        block = draft_text[match.end():]   # everything after "Claims:"
        claims = _parse_bullet_block(block)
        if claims:
            return claims

    # --- Fallback: sentence-split the Summary line (or whole text) ---
    # Prefer to split just the Summary section if it exists
    summary_match = re.search(
        r"Summary\s*:\s*(.+?)(?:\nClaims\s*:|\nLabel\s*:|\Z)",
        draft_text,
        re.IGNORECASE | re.DOTALL,
    )
    if summary_match:
        summary_text = summary_match.group(1).strip()
        sentences = _sentence_split(summary_text)
        if sentences:
            return sentences

    # --- Last resort: split entire text ---
    return _sentence_split(draft_text)
