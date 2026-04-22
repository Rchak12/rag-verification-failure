"""
test_retrieve.py — Unit tests for src/retrieve.py

Tests
-----
- build_index creates an index with correct number of vectors
- retrieve returns exactly k passages
- retrieve results are sorted descending by score
- save_index / load_index round-trip works
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.retrieve import (
    PassageMeta,
    RetrievedPassage,
    build_index,
    load_index,
    retrieve,
    save_index,
)
from src.data import Example


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_example(uid: str, text: str, label: str = "yes") -> Example:
    return Example(
        id=uid,
        question="What is the effect?",
        context=text,
        label=label,
        long_answer="",
    )


SAMPLE_EXAMPLES = [
    make_example("1", "Aspirin reduces the risk of heart attack in high-risk patients."),
    make_example("2", "Beta-blockers are commonly used to treat hypertension and heart failure."),
    make_example("3", "Statins lower LDL cholesterol and reduce cardiovascular mortality."),
    make_example("4", "ACE inhibitors are prescribed for diabetes-related kidney disease."),
    make_example("5", "Metformin is the first-line treatment for type 2 diabetes."),
]

SAMPLE_QUESTION = "What medications are used to treat cardiovascular disease?"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def built_index():
    """Build a FAISS index from SAMPLE_EXAMPLES once."""
    return build_index(SAMPLE_EXAMPLES)


# ---------------------------------------------------------------------------
# Tests: build_index
# ---------------------------------------------------------------------------

class TestBuildIndex:

    def test_index_ntotal_matches_corpus(self, built_index):
        index, embeddings, meta = built_index
        assert index.ntotal == len(SAMPLE_EXAMPLES)

    def test_embeddings_shape(self, built_index):
        _, embeddings, _ = built_index
        assert embeddings.ndim == 2
        assert embeddings.shape[0] == len(SAMPLE_EXAMPLES)

    def test_meta_length(self, built_index):
        _, _, meta = built_index
        assert len(meta) == len(SAMPLE_EXAMPLES)

    def test_meta_ids_match(self, built_index):
        _, _, meta = built_index
        expected_ids = {ex["id"] for ex in SAMPLE_EXAMPLES}
        actual_ids = {m["id"] for m in meta}
        assert expected_ids == actual_ids


# ---------------------------------------------------------------------------
# Tests: retrieve
# ---------------------------------------------------------------------------

class TestRetrieve:

    @pytest.mark.parametrize("k", [1, 3, 5])
    def test_returns_exactly_k_passages(self, built_index, k):
        index, _, meta = built_index
        passages = retrieve(SAMPLE_QUESTION, index, meta, k=k)
        assert len(passages) == k

    def test_passages_sorted_descending_by_score(self, built_index):
        index, _, meta = built_index
        passages = retrieve(SAMPLE_QUESTION, index, meta, k=3)
        scores = [p["score"] for p in passages]
        assert scores == sorted(scores, reverse=True)

    def test_passages_have_required_keys(self, built_index):
        index, _, meta = built_index
        passages = retrieve(SAMPLE_QUESTION, index, meta, k=2)
        for p in passages:
            assert set(p.keys()) >= {"id", "text", "score", "source_id"}

    def test_source_ids_are_sequential(self, built_index):
        index, _, meta = built_index
        passages = retrieve(SAMPLE_QUESTION, index, meta, k=3)
        expected = ["S1", "S2", "S3"]
        assert [p["source_id"] for p in passages] == expected

    def test_k_capped_at_corpus_size(self, built_index):
        """Requesting more than corpus size should not raise — returns all."""
        index, _, meta = built_index
        passages = retrieve(SAMPLE_QUESTION, index, meta, k=999)
        assert len(passages) == len(SAMPLE_EXAMPLES)


# ---------------------------------------------------------------------------
# Tests: save_index / load_index
# ---------------------------------------------------------------------------

class TestIndexPersistence:

    def test_save_and_load_roundtrip(self, built_index):
        index, embeddings, meta = built_index
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            save_index(index, embeddings, meta, index_dir=tmp_path)
            loaded_index, loaded_emb, loaded_meta = load_index(index_dir=tmp_path)

        assert loaded_index.ntotal == index.ntotal
        assert np.allclose(loaded_emb, embeddings)
        assert len(loaded_meta) == len(meta)

    def test_load_raises_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                load_index(index_dir=Path(tmpdir))
