"""
generate.py — Draft answer generation from retrieved passages.

Public API
----------
generate_draft(question, passages) -> DraftAnswer

DraftAnswer (TypedDict)
-----------------------
{
    "answer_label":  str,         # "yes" | "no" | "maybe"
    "summary":       str,         # 1–2 sentence summary
    "claims":        List[str],   # bullet claim sentences
    "cited_sources": List[str],   # e.g. ["S1", "S3"]
    "raw":           str,         # full raw model output
}

Backends
--------
- "stub"   : rule-based stub (default; no API key required)
- "openai" : GPT via OpenAI Chat API (requires OPENAI_API_KEY in .env)
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List, TypedDict

from src.config import (
    GENERATION_BACKEND,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)
from src.retrieve import RetrievedPassage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class DraftAnswer(TypedDict):
    answer_label: str
    summary: str
    claims: List[str]
    cited_sources: List[str]
    raw: str


# ---------------------------------------------------------------------------
# Prompt builder (shared by all backends)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an expert biomedical question-answering assistant. "
    "Answer questions using ONLY the provided evidence passages from PubMed abstracts. "
    "Each claim you make must be directly supported by the evidence. "
    "Be precise, concise, and cite sources using [S1], [S2] notation. "
    "Choose yes/no/maybe based on the strength of evidence in the passages."
)

FORCED_ANSWER_PROMPT = (
    "You are an expert biomedical question-answering assistant. "
    "Answer questions using the provided evidence passages from PubMed abstracts. "
    "You MUST provide a definitive answer (yes/no/maybe). "
    "Do NOT say 'I don't know' or 'no information found'. "
    "Make your best inference from the available passages, even if they are not perfectly relevant. "
    "Cite sources using [S1], [S2] notation for any claims you make."
)

ANSWER_FORMAT = """
Answer the question below using the provided passages.

Output format (follow exactly):
Label: <yes|no|maybe>
Summary: <1-2 sentences with inline citations like [S1]>
Claims:
- <claim 1> (Sources: S1)
- <claim 2> (Sources: S2,S3)
...

Question: {question}

Passages:
{passages_text}
""".strip()


def _build_passages_text(passages: List[RetrievedPassage]) -> str:
    """Format passages as numbered blocks for the prompt."""
    blocks = []
    for p in passages:
        snippet = p["text"][:600].replace("\n", " ")
        blocks.append(f"[{p['source_id']}] {snippet}")
    return "\n\n".join(blocks)


def _build_prompt(question: str, passages: List[RetrievedPassage]) -> str:
    return ANSWER_FORMAT.format(
        question=question,
        passages_text=_build_passages_text(passages),
    )


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_raw(raw: str) -> DraftAnswer:
    """
    Parse the structured LLM output into a DraftAnswer.
    Tolerates minor formatting variations.
    """
    raw_clean = raw.strip()

    # --- label ---
    label_match = re.search(r"Label\s*:\s*(yes|no|maybe)", raw_clean, re.IGNORECASE)
    answer_label = label_match.group(1).lower() if label_match else "maybe"

    # --- summary ---
    summary_match = re.search(
        r"Summary\s*:\s*(.+?)(?:\nClaims\s*:|\Z)", raw_clean, re.IGNORECASE | re.DOTALL
    )
    summary = summary_match.group(1).strip() if summary_match else ""

    # --- claims ---
    claims_block_match = re.search(
        r"Claims\s*:\s*\n(.*)", raw_clean, re.IGNORECASE | re.DOTALL
    )
    claims: List[str] = []
    cited_sources: List[str] = []

    if claims_block_match:
        block = claims_block_match.group(1)
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            # strip leading bullets / numbers
            line = re.sub(r"^[-*•\d]+[.)]\s*", "", line)
            if not line:
                continue
            # extract sources
            src_match = re.search(r"\(Sources\s*:\s*([^)]+)\)", line, re.IGNORECASE)
            if src_match:
                srcs = [s.strip() for s in src_match.group(1).split(",")]
                cited_sources.extend(srcs)
                line = line[: src_match.start()].strip()
            if line:
                claims.append(line)

    cited_sources = list(dict.fromkeys(cited_sources))   # deduplicate, preserve order

    return DraftAnswer(
        answer_label=answer_label,
        summary=summary,
        claims=claims,
        cited_sources=cited_sources,
        raw=raw_clean,
    )


# ---------------------------------------------------------------------------
# Stub backend (no LLM — evidence-grounded, offline)
# ---------------------------------------------------------------------------

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences_stub(text: str) -> List[str]:
    """Split text into sentences, return non-trivial ones (>= 20 chars)."""
    return [s.strip() for s in _SENTENCE_RE.split(text.strip()) if len(s.strip()) >= 20]


def _stub_generate(question: str, passages: List[RetrievedPassage]) -> str:
    """
    Evidence-grounded stub generator.

    Produces a structured answer whose claims are REAL sentences extracted
    from the top retrieved passages.  This makes the verification layer
    non-trivial: evidence-sourced claims score high (supported), while the
    one injected off-topic claim scores low (unsupported), demonstrating the
    verifier's discriminative power.

    Claim composition (3 claims per answer):
      Claim 1 — lead sentence from top passage            (should be SUPPORTED)
      Claim 2 — second sentence from top passage          (should be SUPPORTED)
      Claim 3 — generic off-topic claim injected as noise (should be UNSUPPORTED)
    """
    label = "maybe"

    # --- Label heuristic based on top passage keywords ---
    if passages:
        top_text = passages[0]["text"].lower()
        no_words  = ["no significant", "not associated", "failed", "ineffective",
                     "no difference", "no effect", "no association"]
        yes_words = ["significant", "effective", "associated", "positive", "benefit",
                     "improved", "reduced", "increased", "demonstrated"]
        if any(w in top_text for w in no_words):
            label = "no"
        elif any(w in top_text for w in yes_words):
            label = "yes"

    # --- Extract real evidence sentences ---
    evidence_claims: List[tuple[str, str]] = []   # (claim_text, source_id)
    for passage in passages:
        sents = _split_sentences_stub(passage["text"])
        for s in sents[:2]:   # at most 2 sentences per passage
            evidence_claims.append((s, passage["source_id"]))
        if len(evidence_claims) >= 2:
            break

    # Pad if passage was very short
    while len(evidence_claims) < 2 and passages:
        fallback = passages[0]["text"][:150].replace("\n", " ").strip()
        evidence_claims.append((fallback, passages[0]["source_id"]))

    # --- Injected off-topic claim (noise — should be flagged unsupported) ---
    off_topic = (
        "Further longitudinal studies with larger sample sizes are needed "
        "to establish definitive causal relationships in this domain."
    )
    noise_src = passages[-1]["source_id"] if passages else "S1"

    # --- Build structured raw output ---
    c1_text, c1_src = evidence_claims[0]
    c2_text, c2_src = evidence_claims[1] if len(evidence_claims) > 1 else evidence_claims[0]

    summary = f"{c1_text[:120]} [{c1_src}]"

    raw = (
        f"Label: {label}\n"
        f"Summary: {summary}\n"
        f"Claims:\n"
        f"- {c1_text} (Sources: {c1_src})\n"
        f"- {c2_text} (Sources: {c2_src})\n"
        f"- {off_topic} (Sources: {noise_src})\n"
    )
    return raw


# ---------------------------------------------------------------------------
# OpenAI backend
# ---------------------------------------------------------------------------

def _openai_generate(question: str, passages: List[RetrievedPassage], force_answer: bool = False) -> str:
    """
    Call OpenAI Chat API with GPT-4o for biomedical QA generation.

    Uses low temperature (0.2) for factual consistency and limits tokens
    to encourage concise, evidence-grounded answers.
    """
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        raise ImportError("Install openai: pip install openai>=1.0.0")

    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is not set in .env file. "
            "Please add your API key to use GPT-4o generation."
        )

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = _build_prompt(question, passages)

    # Use forced-answer prompt if requested
    system_prompt = FORCED_ANSWER_PROMPT if force_answer else SYSTEM_PROMPT

    logger.debug("Calling OpenAI API with model=%s, force_answer=%s", OPENAI_MODEL, force_answer)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,        # Low temp for factual accuracy
        max_tokens=400,         # Concise answers, cost-effective
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
    )

    content = response.choices[0].message.content or ""
    logger.debug("Generated %d chars", len(content))
    return content


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_draft(
    question: str,
    passages: List[RetrievedPassage],
    backend: str = GENERATION_BACKEND,
    force_answer: bool = False,
) -> DraftAnswer:
    """
    Generate a draft answer to *question* grounded in *passages*.

    Parameters
    ----------
    question: The biomedical question to answer.
    passages: Top-k retrieved passages from retrieve.retrieve().
    backend:  "stub" (default, offline) or "openai".
    force_answer: If True, disallow abstention - model must provide answer.

    Returns
    -------
    DraftAnswer with label, summary, claims, cited sources, and raw text.
    """
    if backend == "openai":
        raw = _openai_generate(question, passages, force_answer=force_answer)
    else:
        raw = _stub_generate(question, passages)

    draft = _parse_raw(raw)
    logger.debug("Generated draft: label=%s, #claims=%d", draft["answer_label"], len(draft["claims"]))
    return draft


def save_drafts(drafts: List[dict], output_path: Path) -> None:
    """Append draft records to a JSONL file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        for record in drafts:
            fh.write(json.dumps(record) + "\n")
    logger.info("Saved %d draft records to %s", len(drafts), output_path)
