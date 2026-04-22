"""
retrieve.py — FAISS-based dense retrieval over PubMedQA abstracts.

Public API
----------
build_index(examples)  -> (FaissIndex, np.ndarray, List[PassageMeta])
retrieve(question, index, embeddings, meta, k) -> List[RetrievedPassage]
save_index(index, embeddings, meta)
load_index() -> (FaissIndex, np.ndarray, List[PassageMeta])

RetrievedPassage (TypedDict)
----------------------------
{
    "id":     str,   # passage / document id
    "text":   str,   # full abstract text
    "score":  float, # cosine similarity to query
    "source_id": str # human-readable citation label e.g. "S1"
}
"""

from __future__ import annotations

import logging
import pickle
import random
from pathlib import Path
from typing import Dict, List, Tuple, TypedDict, Optional

import numpy as np
from tqdm import tqdm  # type: ignore

# Import faiss and sentence-transformers
import faiss  # type: ignore
from sentence_transformers import SentenceTransformer  # type: ignore

from src.config import (
    DEVICE,
    EMBED_MODEL,
    FAISS_INDEX_FILENAME,
    FAISS_META_FILENAME,
    INDEX_DIR,
    RETRIEVAL_TOP_K,
)
from src.data import Example

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class PassageMeta(TypedDict):
    id: str
    text: str


class RetrievedPassage(TypedDict):
    id: str
    text: str
    score: float
    source_id: str   # e.g. "S1", "S2" — used as citation anchor


# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------

_model_cache: Dict[str, SentenceTransformer] = {}


def _get_model(model_name: str = EMBED_MODEL) -> SentenceTransformer:
    """Return (and cache) a SentenceTransformer model."""
    if model_name not in _model_cache:
        logger.info("Loading embedding model: %s", model_name)
        _model_cache[model_name] = SentenceTransformer(model_name, device=DEVICE)
    return _model_cache[model_name]


def embed_texts(texts: List[str], model_name: str = EMBED_MODEL) -> np.ndarray:
    """
    Encode a list of texts into L2-normalised embeddings.

    Parameters
    ----------
    texts:      Texts to encode.
    model_name: SentenceTransformer model identifier.

    Returns
    -------
    np.ndarray of shape (N, D), dtype float32, L2-normalised.
    """
    model = _get_model(model_name)
    logger.info("Encoding %d texts…", len(texts))
    embeddings = model.encode(
        texts,
        show_progress_bar=len(texts) > 50,
        convert_to_numpy=True,
        normalize_embeddings=True,   # cosine sim = dot product after L2-norm
    ).astype(np.float32)
    return embeddings


# ---------------------------------------------------------------------------
# Index construction
# ---------------------------------------------------------------------------

FaissIndex = faiss.IndexFlatIP  # inner-product (= cosine sim with L2 norm)


def build_index(
    examples: List[Example],
    model_name: str = EMBED_MODEL,
) -> Tuple[FaissIndex, np.ndarray, List[PassageMeta]]:
    """
    Build a FAISS inner-product index from a list of Examples.

    Parameters
    ----------
    examples:   Corpus of PubMedQA examples whose contexts become passages.
    model_name: Embedding model to use.

    Returns
    -------
    (index, embeddings, meta)
        index:      faiss.IndexFlatIP — ready for search.
        embeddings: (N, D) float32 array.
        meta:       List[PassageMeta] aligned with index rows.
    """
    texts: List[str] = [ex["context"] for ex in examples]
    meta: List[PassageMeta] = [
        PassageMeta(id=ex["id"], text=ex["context"]) for ex in examples
    ]

    embeddings = embed_texts(texts, model_name)

    dim = embeddings.shape[1]
    index: FaissIndex = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    logger.info("Built FAISS index with %d vectors (dim=%d).", index.ntotal, dim)
    return index, embeddings, meta


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_index(
    index: FaissIndex,
    embeddings: np.ndarray,
    meta: List[PassageMeta],
    index_dir: Path = INDEX_DIR,
) -> None:
    """Persist FAISS index, raw embeddings, and metadata to disk."""
    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_dir / FAISS_INDEX_FILENAME))
    with open(index_dir / FAISS_META_FILENAME, "wb") as fh:
        pickle.dump({"embeddings": embeddings, "meta": meta}, fh)
    logger.info("Saved index to %s", index_dir)


def load_index(
    index_dir: Path = INDEX_DIR,
) -> Tuple[FaissIndex, np.ndarray, List[PassageMeta]]:
    """
    Load a previously saved FAISS index from disk.

    Raises
    ------
    FileNotFoundError if the index files are absent.
    """
    idx_path = index_dir / FAISS_INDEX_FILENAME
    meta_path = index_dir / FAISS_META_FILENAME
    if not idx_path.exists() or not meta_path.exists():
        raise FileNotFoundError(
            f"Index not found at {index_dir}. Run build_index() first."
        )
    index = faiss.read_index(str(idx_path))
    with open(meta_path, "rb") as fh:
        payload = pickle.load(fh)
    logger.info("Loaded index with %d vectors from %s.", index.ntotal, index_dir)
    return index, payload["embeddings"], payload["meta"]


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve(
    question: str,
    index: FaissIndex,
    meta: List[PassageMeta],
    k: int = RETRIEVAL_TOP_K,
    model_name: str = EMBED_MODEL,
    noise_ratio: float = 0.0,
    seed: Optional[int] = None,
    embeddings: Optional[np.ndarray] = None,
) -> List[RetrievedPassage]:
    """
    Retrieve the top-k passages most relevant to *question*.

    Parameters
    ----------
    question:    Natural-language query string.
    index:       Populated FAISS index.
    meta:        Passage metadata aligned with the index.
    k:           Number of passages to return.
    model_name:  Embedding model (must match the one used for build_index).
    noise_ratio: Fraction of passages to replace with random (off-topic) documents.
                 0.0 = perfect retrieval, 0.33 = 1/3 noisy, 1.0 = all random.
    seed:        Random seed for reproducible noise injection.

    Returns
    -------
    List[RetrievedPassage] sorted descending by cosine similarity score.
    """
    if seed is not None:
        random.seed(seed)

    q_emb = embed_texts([question], model_name)   # shape (1, D)
    scores, indices = index.search(q_emb, min(k, index.ntotal))

    passages: List[RetrievedPassage] = []
    for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
        if idx < 0:
            continue   # FAISS pads with -1 when ntotal < k
        passage_meta = meta[int(idx)]
        passages.append(
            RetrievedPassage(
                id=passage_meta["id"],
                text=passage_meta["text"],
                score=float(score),
                source_id=f"S{rank + 1}",
            )
        )

    # Inject conflicts: replace a fraction of passages with semi-relevant conflicting documents
    if noise_ratio > 0.0 and len(passages) > 0:
        logger.info("🔥 FORCING CONFLICT INJECTION - noise_ratio=%.2f, n_passages=%d", noise_ratio, len(passages))
        logger.info("📋 Embeddings provided: %s", embeddings is not None)

        if embeddings is not None:
            logger.info("🎯 Original docs (top 3): %s", [p["id"][:8] for p in passages[:3]])
            passages = inject_noise(passages, meta, noise_ratio, index, embeddings)
            logger.info("✅ After injection (top 3): %s", [p["id"][:8] for p in passages[:3]])
        else:
            logger.warning("⚠️  Conflict injection requires embeddings - skipping noise injection")

    return passages


def inject_noise(
    passages: List[RetrievedPassage],
    meta: List[PassageMeta],
    noise_ratio: float,
    index: FaissIndex,
    embeddings: np.ndarray,
) -> List[RetrievedPassage]:
    """
    SIMPLIFIED: Replace passages with lower-ranked candidates to force conflicts.

    Strategy: Take top-1 best passage + replace others with rank 5-15 passages.
    This guarantees topically-similar but potentially conflicting evidence.
    """
    n_passages = len(passages)
    # Use ceiling to ensure at least 1 conflict when noise_ratio > 0
    import math
    n_conflict = max(1, math.ceil(n_passages * noise_ratio)) if noise_ratio > 0 else 0

    logger.info(f"🎯 inject_noise called: n_passages={n_passages}, noise_ratio={noise_ratio:.2f}, n_conflict={n_conflict}")

    if n_conflict == 0:
        logger.info("⚠️  No conflicts to inject (n_conflict=0)")
        return passages

    # SIMPLE APPROACH: Use first passage embedding to find top-20, then swap
    # Get index of first passage in meta
    first_passage_id = passages[0]["id"]
    query_idx = None
    for idx, m in enumerate(meta):
        if m["id"] == first_passage_id:
            query_idx = idx
            break

    if query_idx is None:
        logger.warning("❌ Could not find first passage in meta - skipping injection")
        return passages

    # Search for top-20 candidates using first passage as query
    query_emb = embeddings[query_idx:query_idx+1]
    top_k_expanded = min(20, len(meta))
    scores, indices = index.search(query_emb, top_k_expanded)

    logger.info(f"📊 Top-20 search results: {indices[0][:10]}")

    # Get IDs of currently retrieved passages
    retrieved_ids = {p["id"] for p in passages}

    # Find candidates in rank 5-15 (semi-relevant but potentially conflicting)
    conflict_pool = []
    for rank, idx in enumerate(indices[0]):
        if idx < 0:
            continue
        candidate_id = meta[int(idx)]["id"]
        if candidate_id not in retrieved_ids and 5 <= rank < 15:
            conflict_pool.append(int(idx))

    logger.info(f"🎲 Conflict pool (rank 5-15): {len(conflict_pool)} candidates")

    if len(conflict_pool) == 0:
        logger.warning("❌ No conflict candidates found in rank 5-15 - using random fallback")
        # Random fallback
        available_docs = [m for m in meta if m["id"] not in retrieved_ids]
        if len(available_docs) >= n_conflict:
            noise_docs = random.sample(available_docs, n_conflict)
            result = passages.copy()
            replace_indices = random.sample(range(n_passages), n_conflict)
            for i, noise_doc in zip(replace_indices, noise_docs):
                result[i] = RetrievedPassage(
                    id=noise_doc["id"],
                    text=noise_doc["text"],
                    score=-1.0,
                    source_id=result[i]["source_id"],
                )
            logger.info(f"🔥 Injected {n_conflict} RANDOM conflicting passages")
            return result
        return passages

    # Replace passages with conflicts from pool
    n_conflict = min(n_conflict, len(conflict_pool))
    replace_indices = random.sample(range(n_passages), n_conflict)
    conflict_indices = random.sample(conflict_pool, n_conflict)

    result = passages.copy()
    for i, conflict_idx in zip(replace_indices, conflict_indices):
        conflict_meta = meta[conflict_idx]
        logger.info(f"   Replacing passage {i} ({result[i]['id'][:12]}) with conflict ({conflict_meta['id'][:12]})")
        result[i] = RetrievedPassage(
            id=conflict_meta["id"],
            text=conflict_meta["text"],
            score=-1.0,  # Mark as conflict
            source_id=result[i]["source_id"],
        )

    logger.info(f"🔥 Successfully injected {n_conflict} CONFLICTING passages from rank 5-15")
    return result
