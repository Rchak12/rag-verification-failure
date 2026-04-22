"""
test_verify.py — Unit tests for src/verify.py

Tests
-----
- score_claim_support: high score when claim matches a passage sentence exactly
- score_claim_support: low score when claim has no evidence in passages
- verify_claims: marks supported=True above threshold
- verify_claims: marks supported=False below threshold
- verify_claims: empty claims list returns empty list
- verify_claims: empty passages list returns all unsupported
"""

from __future__ import annotations

import pytest

from src.verify import ClaimScore, VerifiedClaim, score_claim_support, verify_claims
from src.retrieve import RetrievedPassage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_passage(text: str, source_id: str = "S1", pid: str = "p1") -> RetrievedPassage:
    return RetrievedPassage(id=pid, text=text, score=0.9, source_id=source_id)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BIOMEDICAL_SENTENCE = (
    "The administration of aspirin significantly reduced the incidence of cardiovascular events "
    "in the treatment group compared to placebo."
)

MATCHING_CLAIM = (
    "Aspirin significantly reduced cardiovascular events compared to placebo."
)

UNRELATED_CLAIM = (
    "Quantum entanglement enables faster-than-light communication between particles."
)

FAKE_PASSAGE = make_passage(
    text=(
        f"{BIOMEDICAL_SENTENCE} "
        "Patients were followed for 12 months. "
        "No serious adverse events were reported."
    ),
    source_id="S1",
)

SECOND_PASSAGE = make_passage(
    text="The study included 500 adult participants over 18 years of age.",
    source_id="S2",
    pid="p2",
)


# ---------------------------------------------------------------------------
# Tests: score_claim_support
# ---------------------------------------------------------------------------

class TestScoreClaimSupport:

    def test_high_score_for_matching_claim(self):
        """A claim semantically close to a passage sentence should score high."""
        result: ClaimScore = score_claim_support(
            claim=MATCHING_CLAIM,
            passages=[FAKE_PASSAGE],
        )
        assert result["score"] >= 0.5, (
            f"Expected score >= 0.5 for matching claim, got {result['score']:.4f}"
        )
        assert result["best_source_id"] == "S1"
        assert len(result["best_sentence"]) > 0

    def test_lower_score_for_unrelated_claim(self):
        """A completely unrelated claim should score lower than a matching one."""
        matching = score_claim_support(
            claim=MATCHING_CLAIM,
            passages=[FAKE_PASSAGE],
        )
        unrelated = score_claim_support(
            claim=UNRELATED_CLAIM,
            passages=[FAKE_PASSAGE],
        )
        assert matching["score"] > unrelated["score"], (
            "Matching claim should score higher than unrelated claim."
        )

    def test_empty_claim_returns_zero(self):
        result = score_claim_support(claim="", passages=[FAKE_PASSAGE])
        assert result["score"] == 0.0

    def test_empty_passages_returns_zero(self):
        result = score_claim_support(claim=MATCHING_CLAIM, passages=[])
        assert result["score"] == 0.0
        assert result["best_sentence"] == ""

    def test_returns_best_source_id(self):
        """With two passages, the returned source_id should belong to the closer passage."""
        result = score_claim_support(
            claim=MATCHING_CLAIM,
            passages=[FAKE_PASSAGE, SECOND_PASSAGE],
        )
        # FAKE_PASSAGE is about aspirin / cardiovascular events — should win
        assert result["best_source_id"] == "S1"


# ---------------------------------------------------------------------------
# Tests: verify_claims
# ---------------------------------------------------------------------------

class TestVerifyClaims:

    def test_supported_true_above_threshold(self):
        """With a low threshold, the matching claim should be supported."""
        results = verify_claims(
            claims=[MATCHING_CLAIM],
            passages=[FAKE_PASSAGE],
            tau=0.3,   # deliberately low to ensure it's above threshold
        )
        assert len(results) == 1
        vc: VerifiedClaim = results[0]
        assert vc["supported"] is True
        assert vc["claim"] == MATCHING_CLAIM

    def test_unsupported_false_above_high_threshold(self):
        """With an extremely high threshold, even matching claims are unsupported."""
        results = verify_claims(
            claims=[MATCHING_CLAIM],
            passages=[FAKE_PASSAGE],
            tau=0.9999,
        )
        assert results[0]["supported"] is False

    def test_unrelated_claim_unsupported_at_default_threshold(self):
        """An unrelated claim should be unsupported at the default τ=0.55."""
        results = verify_claims(
            claims=[UNRELATED_CLAIM],
            passages=[FAKE_PASSAGE],
            tau=0.55,
        )
        assert results[0]["supported"] is False

    def test_empty_claims_list(self):
        results = verify_claims(claims=[], passages=[FAKE_PASSAGE], tau=0.55)
        assert results == []

    def test_empty_passages_all_unsupported(self):
        results = verify_claims(
            claims=[MATCHING_CLAIM, UNRELATED_CLAIM],
            passages=[],
            tau=0.55,
        )
        assert all(not r["supported"] for r in results)
        assert all(r["support_score"] == 0.0 for r in results)

    def test_output_schema_keys(self):
        """Every VerifiedClaim must have the required keys."""
        results = verify_claims(
            claims=[MATCHING_CLAIM],
            passages=[FAKE_PASSAGE],
            tau=0.55,
        )
        required_keys = {"claim", "supported", "support_score", "evidence_sentence", "evidence_source_id"}
        assert required_keys.issubset(set(results[0].keys()))

    def test_multiple_claims_independent(self):
        """Verify multiple claims independently; order matches input order."""
        claims = [MATCHING_CLAIM, UNRELATED_CLAIM]
        results = verify_claims(claims=claims, passages=[FAKE_PASSAGE], tau=0.55)
        assert len(results) == 2
        assert results[0]["claim"] == MATCHING_CLAIM
        assert results[1]["claim"] == UNRELATED_CLAIM
        # Matching claim should have a higher score
        assert results[0]["support_score"] >= results[1]["support_score"]
