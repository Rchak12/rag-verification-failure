"""
test_claims.py — Unit tests for src/claims.py

Tests
-----
- Structured "Claims:" section parsing (bullets)
- Numbered list parsing
- Fallback to sentence splitting when no Claims section
- Source annotation stripping
- Empty / edge-case inputs
"""

from __future__ import annotations

import pytest

from src.claims import extract_claims


# ---------------------------------------------------------------------------
# Fixtures / sample texts
# ---------------------------------------------------------------------------

STRUCTURED_DRAFT = """\
Label: yes
Summary: The study shows significant improvement. [S1]
Claims:
- Patients receiving treatment showed a 30% reduction in symptoms. (Sources: S1)
- The control group showed no significant change. (Sources: S2)
- Side effects were minimal and transient. (Sources: S1,S2)
"""

NUMBERED_DRAFT = """\
Label: no
Summary: No evidence of benefit was found.
Claims:
1. The intervention did not improve outcomes. (Sources: S1)
2. Placebo-controlled trials yielded negative results. (Sources: S3)
"""

NO_CLAIMS_SECTION = """\
The treatment was effective. Multiple studies confirmed this result.
Further research is needed.
"""

ONLY_SUMMARY = """\
Label: maybe
Summary: Evidence is mixed. Some trials show benefit while others do not.
"""

EMPTY_DRAFT = ""
WHITESPACE_DRAFT = "   \n\n   "


# ---------------------------------------------------------------------------
# Tests: structured Claims: section
# ---------------------------------------------------------------------------

class TestStructuredClaims:

    def test_extracts_correct_count(self):
        claims = extract_claims(STRUCTURED_DRAFT)
        assert len(claims) == 3

    def test_exact_claim_strings(self):
        claims = extract_claims(STRUCTURED_DRAFT)
        assert "Patients receiving treatment showed a 30% reduction in symptoms" in claims[0]
        assert "The control group showed no significant change" in claims[1]
        assert "Side effects were minimal and transient" in claims[2]

    def test_source_annotations_removed(self):
        claims = extract_claims(STRUCTURED_DRAFT)
        for claim in claims:
            assert "Sources:" not in claim
            assert "(S1)" not in claim


class TestNumberedClaims:

    def test_extracts_correct_count(self):
        claims = extract_claims(NUMBERED_DRAFT)
        assert len(claims) == 2

    def test_numbers_stripped_from_claim(self):
        claims = extract_claims(NUMBERED_DRAFT)
        # Should not start with a digit
        for claim in claims:
            assert not claim[0].isdigit()

    def test_exact_strings(self):
        claims = extract_claims(NUMBERED_DRAFT)
        assert "The intervention did not improve outcomes" in claims[0]
        assert "Placebo-controlled trials yielded negative results" in claims[1]


# ---------------------------------------------------------------------------
# Tests: fallback sentence splitting
# ---------------------------------------------------------------------------

class TestFallbackSentenceSplitting:

    def test_falls_back_when_no_claims_section(self):
        claims = extract_claims(NO_CLAIMS_SECTION)
        assert len(claims) >= 1

    def test_all_returned_are_non_empty(self):
        claims = extract_claims(NO_CLAIMS_SECTION)
        for c in claims:
            assert len(c.strip()) > 0

    def test_summary_section_split(self):
        claims = extract_claims(ONLY_SUMMARY)
        assert len(claims) >= 1


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_string_returns_empty_list(self):
        assert extract_claims(EMPTY_DRAFT) == []

    def test_whitespace_only_returns_empty_list(self):
        assert extract_claims(WHITESPACE_DRAFT) == []

    def test_single_claim_bullet(self):
        text = "Claims:\n- The drug is effective. (Sources: S1)\n"
        claims = extract_claims(text)
        assert len(claims) == 1
        assert "Sources:" not in claims[0]

    def test_claims_with_no_source_annotation(self):
        text = "Claims:\n- First claim without source.\n- Second claim without source.\n"
        claims = extract_claims(text)
        assert len(claims) == 2
        assert "First claim without source" in claims[0]
        assert "Second claim without source" in claims[1]
