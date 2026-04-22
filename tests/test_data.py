"""
test_data.py — Unit tests for src/data.py

Tests
-----
- load_pubmedqa returns at least the requested number of examples
- All examples have non-empty 'question' and 'context' fields
- All label values are in {"yes", "no", "maybe"}
- Example TypedDict has all required keys
"""

from __future__ import annotations

import pytest

from src.data import load_pubmedqa, Example


REQUIRED_KEYS = {"id", "question", "context", "label", "long_answer"}
VALID_LABELS = {"yes", "no", "maybe"}
N_TEST = 5


@pytest.fixture(scope="module")
def examples():
    """Load a small slice of PubMedQA once for all tests in this module."""
    return load_pubmedqa(split="train", limit=N_TEST)


class TestLoadPubmedQA:

    def test_returns_list(self, examples):
        assert isinstance(examples, list)

    def test_correct_length(self, examples):
        assert len(examples) == N_TEST

    def test_all_have_required_keys(self, examples):
        for ex in examples:
            assert REQUIRED_KEYS.issubset(ex.keys()), (
                f"Missing keys in example {ex.get('id')}: "
                f"{REQUIRED_KEYS - set(ex.keys())}"
            )

    def test_non_empty_question(self, examples):
        for ex in examples:
            assert ex["question"].strip(), f"Empty question in example {ex['id']}"

    def test_non_empty_context(self, examples):
        for ex in examples:
            assert ex["context"].strip(), f"Empty context in example {ex['id']}"

    def test_valid_labels(self, examples):
        for ex in examples:
            assert ex["label"] in VALID_LABELS, (
                f"Invalid label '{ex['label']}' in example {ex['id']}"
            )

    def test_ids_are_strings(self, examples):
        for ex in examples:
            assert isinstance(ex["id"], str) and ex["id"], (
                f"Invalid id in example: {ex}"
            )
