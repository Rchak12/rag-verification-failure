"""
config.py — Central configuration for Verified RAG.

All tuneable hyper-parameters and path constants live here.
Import this module in every other src/ module instead of scattering
magic numbers throughout the code-base.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env (silently ignored if file is absent)
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
ROOT_DIR: Path = Path(__file__).resolve().parent.parent          # repo root
OUTPUTS_DIR: Path = ROOT_DIR / "outputs"
INDEX_DIR: Path = OUTPUTS_DIR / "index"
RUNS_DIR: Path = OUTPUTS_DIR / "runs"

# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
PUBMEDQA_DATASET_NAME: str = "qiaojin/PubMedQA"
PUBMEDQA_SUBSET: str = "pqa_labeled"          # labelled split (yes/no/maybe)
DEFAULT_SPLIT: str = "train"
DEFAULT_N_EXAMPLES: int = 10

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
EMBED_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
RETRIEVAL_TOP_K: int = 5
FAISS_INDEX_FILENAME: str = "pubmedqa_index.faiss"
FAISS_META_FILENAME: str = "pubmedqa_meta.pkl"

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
VERIFICATION_METHOD: str = os.getenv("VERIFICATION_METHOD", "nli")  # "cosine" or "nli"
SIMILARITY_THRESHOLD: float = 0.55            # τ for cosine similarity (deprecated, use NLI)
NLI_THRESHOLD: float = 0.5                     # τ for NLI entailment score
NLI_MODEL: str = "cross-encoder/nli-deberta-v3-small"  # or "cross-encoder/nli-deberta-v3-base"
MAX_EVIDENCE_SENTENCES: int = 10              # max sentences per passage chunk

# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
RESULTS_CSV_NAME: str = "results.csv"
QUAL_EXAMPLES_NAME: str = "qual_examples.md"
N_QUAL_EXAMPLES: int = 5

# ---------------------------------------------------------------------------
# Generation (LLM back-end — GPT-4o for production, stub for testing)
# ---------------------------------------------------------------------------
GENERATION_BACKEND: str = os.getenv("GENERATION_BACKEND", "openai")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# Rewrite module settings
REWRITE_MAX_TOKENS: int = 150
REWRITE_TEMPERATURE: float = 0.3

# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------
DEVICE: str = os.getenv("DEVICE", "cpu")
