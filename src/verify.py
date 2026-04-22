"""
verify.py — Verification layer: NLI-based and cosine-similarity evidence matching.

Public API
----------
score_claim_support(claim, passages, method, ...) -> ClaimScore
verify_claims(claims, passages, tau, method, ...)  -> List[VerifiedClaim]

Algorithms
----------
METHOD 1: Cosine Similarity (baseline, deprecated)
1. For each claim, split every retrieved passage into sentences.
2. Embed the claim and all passage sentences with sentence-transformers.
3. Compute cosine similarity (vectors are already L2-normalised).
4. The support score = max similarity across all sentences.
5. The claim is *supported* iff score ≥ τ (threshold).

METHOD 2: NLI Entailment (recommended, better for paraphrases)
1. For each claim, split every retrieved passage into sentences.
2. Use a cross-encoder NLI model to score entailment (premise=evidence, hypothesis=claim).
3. The support score = max entailment score across all sentences.
4. The claim is *supported* iff entailment_score ≥ τ.

VerifiedClaim (TypedDict)
-------------------------
{
    "claim":             str,
    "supported":         bool,
    "support_score":     float,
    "evidence_sentence": str,
    "evidence_source_id":str,
}
"""

from __future__ import annotations

import logging
import re
from typing import List, Tuple, TypedDict

import numpy as np

from src.config import (
    EMBED_MODEL,
    MAX_EVIDENCE_SENTENCES,
    NLI_MODEL,
    NLI_THRESHOLD,
    SIMILARITY_THRESHOLD,
    VERIFICATION_METHOD,
)
from src.retrieve import RetrievedPassage, embed_texts

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class ClaimScore(TypedDict):
    score: float
    best_source_id: str
    best_sentence: str


class VerifiedClaim(TypedDict):
    claim: str
    supported: bool
    support_score: float
    evidence_sentence: str
    evidence_source_id: str


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str, max_sentences: int = MAX_EVIDENCE_SENTENCES) -> List[str]:
    """
    Split *text* into sentences (naïve regex splitter).
    Returns at most *max_sentences* non-empty sentences.
    """
    raw = _SENT_SPLIT_RE.split(text.strip())
    sentences = [s.strip() for s in raw if len(s.strip()) >= 8]
    return sentences[:max_sentences]


# ---------------------------------------------------------------------------
# Core scoring — NLI-based entailment
# ---------------------------------------------------------------------------

_NLI_MODEL_CACHE = None  # Lazy-loaded cross-encoder

def _get_nli_model():
    """Lazy-load the NLI cross-encoder model."""
    global _NLI_MODEL_CACHE
    if _NLI_MODEL_CACHE is None:
        from sentence_transformers import CrossEncoder  # type: ignore
        logger.info("Loading NLI model: %s", NLI_MODEL)
        _NLI_MODEL_CACHE = CrossEncoder(NLI_MODEL)
    return _NLI_MODEL_CACHE


def score_claim_support_nli(
    claim: str,
    passages: List[RetrievedPassage],
    nli_model_name: str = NLI_MODEL,
) -> ClaimScore:
    """
    Compute claim support using NLI entailment scoring.

    Uses a cross-encoder NLI model to determine if evidence sentences
    entail the claim. This is better than cosine similarity for handling
    paraphrases and semantic equivalence.

    Parameters
    ----------
    claim:          A single factual claim string.
    passages:       Retrieved passages (from retrieve.retrieve()).
    nli_model_name: Cross-encoder NLI model name.

    Returns
    -------
    ClaimScore with (score, best_source_id, best_sentence).
    Score is the entailment probability (0-1).
    """
    if not claim.strip():
        return ClaimScore(score=0.0, best_source_id="", best_sentence="")

    # Collect all (source_id, sentence) pairs
    sentence_pairs: List[Tuple[str, str]] = []
    for passage in passages:
        sents = _split_sentences(passage["text"])
        for sent in sents:
            sentence_pairs.append((passage["source_id"], sent))

    if not sentence_pairs:
        return ClaimScore(score=0.0, best_source_id="", best_sentence="")

    # Load NLI model
    nli_model = _get_nli_model()

    # Format as (premise, hypothesis) pairs
    # Premise = evidence sentence, Hypothesis = claim
    nli_pairs = [(sent, claim) for _, sent in sentence_pairs]

    # Predict entailment scores
    # Output: [contradiction, neutral, entailment] logits
    scores = nli_model.predict(nli_pairs, convert_to_numpy=True)

    # Extract entailment score (index 2 in 3-class NLI)
    # Shape: (N, 3) → take column 2 (entailment)
    entailment_scores = scores[:, 2] if len(scores.shape) > 1 else scores

    # Find best entailment score
    best_idx = int(np.argmax(entailment_scores))
    best_score = float(entailment_scores[best_idx])
    best_source_id, best_sentence = sentence_pairs[best_idx]

    return ClaimScore(
        score=best_score,
        best_source_id=best_source_id,
        best_sentence=best_sentence,
    )


# ---------------------------------------------------------------------------
# Core scoring — Cosine similarity (baseline)
# ---------------------------------------------------------------------------

def score_claim_support_cosine(
    claim: str,
    passages: List[RetrievedPassage],
    model_name: str = EMBED_MODEL,
) -> ClaimScore:
    """
    Compute the maximum cosine-similarity between *claim* and every
    sentence in *passages* (BASELINE method, deprecated).

    Parameters
    ----------
    claim:      A single factual claim string.
    passages:   Retrieved passages (from retrieve.retrieve()).
    model_name: Sentence-transformer model used for embedding.

    Returns
    -------
    ClaimScore with (score, best_source_id, best_sentence).
    """
    if not claim.strip():
        return ClaimScore(score=0.0, best_source_id="", best_sentence="")

    # Collect all (source_id, sentence) pairs
    sentence_pairs: List[Tuple[str, str]] = []
    for passage in passages:
        sents = _split_sentences(passage["text"])
        for sent in sents:
            sentence_pairs.append((passage["source_id"], sent))

    if not sentence_pairs:
        return ClaimScore(score=0.0, best_source_id="", best_sentence="")

    texts_to_embed = [claim] + [sp[1] for sp in sentence_pairs]
    embeddings = embed_texts(texts_to_embed, model_name)   # already L2-normalised

    claim_emb = embeddings[0:1]          # shape (1, D)
    passage_embs = embeddings[1:]        # shape (N, D)

    # cosine similarity = dot product (vectors are L2-normalised)
    similarities: np.ndarray = (passage_embs @ claim_emb.T).squeeze(axis=1)  # (N,)

    best_idx = int(np.argmax(similarities))
    best_score = float(similarities[best_idx])
    best_source_id, best_sentence = sentence_pairs[best_idx]

    return ClaimScore(
        score=best_score,
        best_source_id=best_source_id,
        best_sentence=best_sentence,
    )


# ---------------------------------------------------------------------------
# Unified scoring API
# ---------------------------------------------------------------------------

def score_claim_support(
    claim: str,
    passages: List[RetrievedPassage],
    method: str = VERIFICATION_METHOD,
    model_name: str = EMBED_MODEL,
    nli_model_name: str = NLI_MODEL,
) -> ClaimScore:
    """
    Score claim support using the specified verification method.

    Parameters
    ----------
    claim:          Claim to verify.
    passages:       Retrieved passages.
    method:         "nli" (recommended) or "cosine" (baseline).
    model_name:     Sentence-transformer model for cosine method.
    nli_model_name: Cross-encoder NLI model for NLI method.

    Returns
    -------
    ClaimScore with support score and best evidence.
    """
    if method == "nli":
        return score_claim_support_nli(claim, passages, nli_model_name)
    elif method == "cosine":
        return score_claim_support_cosine(claim, passages, model_name)
    else:
        raise ValueError(f"Unknown verification method: {method}. Use 'nli' or 'cosine'.")


# ---------------------------------------------------------------------------
# Batch verification
# ---------------------------------------------------------------------------

def verify_claims(
    claims: List[str],
    passages: List[RetrievedPassage],
    tau: float = None,
    method: str = VERIFICATION_METHOD,
    model_name: str = EMBED_MODEL,
    nli_model_name: str = NLI_MODEL,
) -> List[VerifiedClaim]:
    """
    Verify each claim in *claims* against the retrieved *passages*.

    Parameters
    ----------
    claims:         List of claim strings (from claims.extract_claims()).
    passages:       Retrieved passages for the question.
    tau:            Verification threshold. If None, uses NLI_THRESHOLD for "nli"
                    or SIMILARITY_THRESHOLD for "cosine".
    method:         "nli" (recommended) or "cosine" (baseline).
    model_name:     Embedding model for cosine method.
    nli_model_name: Cross-encoder NLI model for NLI method.

    Returns
    -------
    List[VerifiedClaim] — one entry per input claim, in the same order.
    """
    # Auto-select threshold based on method
    if tau is None:
        tau = NLI_THRESHOLD if method == "nli" else SIMILARITY_THRESHOLD

    results: List[VerifiedClaim] = []
    for claim in claims:
        cs = score_claim_support(claim, passages, method, model_name, nli_model_name)
        results.append(
            VerifiedClaim(
                claim=claim,
                supported=cs["score"] >= tau,
                support_score=cs["score"],
                evidence_sentence=cs["best_sentence"],
                evidence_source_id=cs["best_source_id"],
            )
        )
    logger.debug(
        "Verified %d claims (%s): %d supported, %d unsupported (τ=%.2f)",
        len(results),
        method,
        sum(1 for r in results if r["supported"]),
        sum(1 for r in results if not r["supported"]),
        tau,
    )
    return results
