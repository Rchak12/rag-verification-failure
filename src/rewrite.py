"""
rewrite.py — Claim rewriting module using GPT-4o.

This is the MAIN CONTRIBUTION of the Verified RAG project.

Instead of deleting unsupported claims (repair.py), this module uses GPT-4o
to REWRITE unsupported claims to be factually grounded in the retrieved evidence.

Public API
----------
rewrite_claim(claim, evidence, question, ...) -> RewrittenClaim
rewrite_unsupported(draft, verified, passages, ...) -> RewrittenAnswer

Algorithm
---------
1. For each unsupported claim (support_score < τ):
   - Extract the best available evidence sentences from retrieved passages
   - Prompt GPT-4o to rewrite the claim to align with the evidence
   - Preserve the original intent while ensuring factual grounding

2. Combine original supported claims + rewritten claims → final answer

RewrittenClaim (TypedDict)
--------------------------
{
    "original_claim":    str,
    "rewritten_claim":   str,
    "evidence_used":     str,
    "was_rewritten":     bool,
    "original_support":  float,
}

RewrittenAnswer (TypedDict)
---------------------------
{
    "answer_label":       str,      # may be adjusted if many claims rewritten
    "final_summary":      str,
    "supported_claims":   List[str],
    "rewritten_claims":   List[RewrittenClaim],
    "repair_applied":     bool,
    "n_rewritten":        int,
}
"""

from __future__ import annotations

import logging
from typing import List, TypedDict

from src.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    REWRITE_MAX_TOKENS,
    REWRITE_TEMPERATURE,
)
from src.generate import DraftAnswer
from src.retrieve import RetrievedPassage
from src.verify import VerifiedClaim

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class RewrittenClaim(TypedDict):
    original_claim: str
    rewritten_claim: str
    evidence_used: str
    was_rewritten: bool
    original_support: float


class RewrittenAnswer(TypedDict):
    answer_label: str
    final_summary: str
    supported_claims: List[str]
    rewritten_claims: List[RewrittenClaim]
    repair_applied: bool
    n_rewritten: int


# ---------------------------------------------------------------------------
# GPT-4o rewriting
# ---------------------------------------------------------------------------

REWRITE_SYSTEM_PROMPT = (
    "You are an expert biomedical fact-checker and editor. "
    "Your task is to rewrite claims to be factually accurate and supported by evidence. "
    "Preserve the original intent and stay relevant to the question, but ensure "
    "the rewritten claim is directly grounded in the provided evidence."
)

REWRITE_USER_PROMPT = """Question: {question}

Original claim (unsupported): {claim}

Available evidence from retrieved passages:
{evidence}

Task: Rewrite the claim to be factually supported by the evidence above.

Requirements:
- Keep it concise (1-2 sentences max)
- Stay relevant to the original question
- Use ONLY information present in the evidence
- If the evidence contradicts the claim, correct it
- If the evidence is insufficient, write a more conservative/qualified statement

Rewritten claim:"""


def rewrite_claim(
    claim: str,
    evidence_sentences: List[str],
    question: str,
    model: str = OPENAI_MODEL,
) -> str:
    """
    Use GPT-4o to rewrite an unsupported claim to be grounded in evidence.

    Parameters
    ----------
    claim:              The original unsupported claim.
    evidence_sentences: List of relevant evidence sentences from retrieved passages.
    question:           The original question (for context).
    model:              OpenAI model to use (default: GPT-4o).

    Returns
    -------
    str: The rewritten, evidence-grounded claim.
    """
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        raise ImportError("Install openai: pip install openai>=1.0.0")

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY required for claim rewriting")

    # Format evidence
    evidence_text = "\n".join(f"- {sent}" for sent in evidence_sentences[:5])  # top 5 sentences

    prompt = REWRITE_USER_PROMPT.format(
        question=question,
        claim=claim,
        evidence=evidence_text,
    )

    client = OpenAI(api_key=OPENAI_API_KEY)

    logger.debug("Rewriting claim with %s: %s", model, claim[:60])

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=REWRITE_TEMPERATURE,
        max_tokens=REWRITE_MAX_TOKENS,
        top_p=1.0,
    )

    rewritten = response.choices[0].message.content or ""
    rewritten = rewritten.strip()

    logger.debug("Rewritten to: %s", rewritten[:60])

    return rewritten


# ---------------------------------------------------------------------------
# Batch rewriting for full answer
# ---------------------------------------------------------------------------

def rewrite_unsupported(
    draft: DraftAnswer,
    verified: List[VerifiedClaim],
    passages: List[RetrievedPassage],
    question: str,
    tau: float = 0.55,
) -> RewrittenAnswer:
    """
    Rewrite all unsupported claims in the draft answer using GPT-4o.

    This is the core of the REWRITE system (System C in your experiments).

    Parameters
    ----------
    draft:     Original draft answer from generate.py
    verified:  Verification results from verify.py
    passages:  Retrieved passages (for extracting evidence sentences)
    question:  Original question
    tau:       Support threshold (claims with score < tau are rewritten)

    Returns
    -------
    RewrittenAnswer with rewritten claims and adjusted metadata.
    """
    supported: List[str] = []
    rewritten_claims: List[RewrittenClaim] = []

    # Extract all passage sentences for evidence pool
    evidence_pool: List[str] = []
    for passage in passages:
        # Simple sentence split
        import re
        sents = re.split(r'(?<=[.!?])\s+', passage["text"])
        evidence_pool.extend(s.strip() for s in sents if len(s.strip()) >= 20)

    n_rewritten = 0

    for vc in verified:
        claim_text = vc["claim"]
        is_supported = vc["supported"]
        support_score = vc["support_score"]

        if is_supported:
            # Keep as-is
            supported.append(claim_text)
            rewritten_claims.append(
                RewrittenClaim(
                    original_claim=claim_text,
                    rewritten_claim=claim_text,  # unchanged
                    evidence_used=vc["evidence_sentence"],
                    was_rewritten=False,
                    original_support=support_score,
                )
            )
        else:
            # Rewrite using GPT-4o
            try:
                new_claim = rewrite_claim(
                    claim=claim_text,
                    evidence_sentences=evidence_pool,
                    question=question,
                )
                supported.append(new_claim)
                rewritten_claims.append(
                    RewrittenClaim(
                        original_claim=claim_text,
                        rewritten_claim=new_claim,
                        evidence_used=vc["evidence_sentence"],
                        was_rewritten=True,
                        original_support=support_score,
                    )
                )
                n_rewritten += 1
                logger.info("Rewrote unsupported claim: %s → %s", claim_text[:50], new_claim[:50])

            except Exception as e:
                logger.error("Failed to rewrite claim: %s — %s", claim_text[:50], e)
                # Fallback: keep original (or could delete it)
                supported.append(claim_text)
                rewritten_claims.append(
                    RewrittenClaim(
                        original_claim=claim_text,
                        rewritten_claim=claim_text,
                        evidence_used="",
                        was_rewritten=False,
                        original_support=support_score,
                    )
                )

    # Adjust label if many claims were rewritten (uncertainty indicator)
    original_label = draft["answer_label"]
    rewrite_rate = n_rewritten / len(verified) if verified else 0

    if rewrite_rate > 0.5 and original_label in ("yes", "no"):
        # High rewrite rate → downgrade confidence to "maybe"
        adjusted_label = "maybe"
        logger.info("Adjusted label %s → %s (rewrite_rate=%.2f)", original_label, adjusted_label, rewrite_rate)
    else:
        adjusted_label = original_label

    # Build final summary (concatenate first 2 claims)
    final_summary = " ".join(supported[:2]) if len(supported) >= 2 else (supported[0] if supported else "")

    return RewrittenAnswer(
        answer_label=adjusted_label,
        final_summary=final_summary,
        supported_claims=supported,
        rewritten_claims=rewritten_claims,
        repair_applied=(n_rewritten > 0),
        n_rewritten=n_rewritten,
    )
