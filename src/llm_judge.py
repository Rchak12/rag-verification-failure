"""
llm_judge.py — LLM-as-Judge evaluation for answer quality.

This module uses GPT-4o to score answer quality along multiple dimensions:
- Correctness: Does the answer match the evidence?
- Completeness: Does it fully address the question?
- Faithfulness: Are all claims grounded in evidence?

This provides richer evaluation than simple accuracy metrics.

Public API
----------
judge_answer(question, answer, passages, gold_label) -> JudgeScore

JudgeScore (TypedDict)
----------------------
{
    "correctness":   int,   # 0-10
    "completeness":  int,   # 0-10
    "faithfulness":  int,   # 0-10
    "overall":       int,   # 0-10
    "explanation":   str,   # Judge's reasoning
}

Usage
-----
from src.llm_judge import judge_answer

score = judge_answer(
    question="Does aspirin reduce heart attack risk?",
    answer="Yes. Aspirin reduces platelet aggregation.",
    passages=[...],
    gold_label="yes"
)

print(f"Correctness: {score['correctness']}/10")
"""

from __future__ import annotations

import json
import logging
from typing import List, TypedDict

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.retrieve import RetrievedPassage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class JudgeScore(TypedDict):
    correctness: int
    completeness: int
    faithfulness: int
    overall: int
    explanation: str


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """You are an expert biomedical evaluator assessing the quality of question-answering systems.

Your task is to score answers on three dimensions (0-10 scale):

1. **Correctness**: Does the answer's conclusion match the evidence? Is it factually accurate?
2. **Completeness**: Does it fully address the question with relevant details?
3. **Faithfulness**: Are all claims directly supported by the provided evidence passages?

Provide scores and a brief explanation."""

JUDGE_USER_PROMPT = """Question: {question}

Gold Label: {gold_label}

Retrieved Evidence Passages:
{passages}

System Answer:
{answer}

Task: Evaluate this answer on:
1. Correctness (0-10): Factual accuracy and alignment with evidence
2. Completeness (0-10): How fully it addresses the question
3. Faithfulness (0-10): All claims grounded in provided evidence
4. Overall (0-10): Holistic quality

Respond in JSON format:
{{
  "correctness": <0-10>,
  "completeness": <0-10>,
  "faithfulness": <0-10>,
  "overall": <0-10>,
  "explanation": "<2-3 sentences explaining the scores>"
}}"""


# ---------------------------------------------------------------------------
# Judge implementation
# ---------------------------------------------------------------------------

def judge_answer(
    question: str,
    answer: str,
    passages: List[RetrievedPassage],
    gold_label: str,
    model: str = OPENAI_MODEL,
) -> JudgeScore:
    """
    Use GPT-4o to evaluate answer quality.

    Parameters
    ----------
    question:   The biomedical question.
    answer:     The generated answer to evaluate.
    passages:   Retrieved evidence passages.
    gold_label: Gold-standard label (yes/no/maybe).
    model:      OpenAI model to use (default: GPT-4o).

    Returns
    -------
    JudgeScore with 0-10 scores and explanation.
    """
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        raise ImportError("Install openai: pip install openai>=1.0.0")

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY required for LLM-as-judge evaluation")

    # Format passages
    passages_text = "\n\n".join(
        f"[{p['source_id']}] {p['text'][:400]}"
        for p in passages
    )

    prompt = JUDGE_USER_PROMPT.format(
        question=question,
        gold_label=gold_label,
        passages=passages_text,
        answer=answer,
    )

    client = OpenAI(api_key=OPENAI_API_KEY)

    logger.debug("Judging answer with %s", model)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=300,
        response_format={"type": "json_object"},  # Force JSON output
    )

    content = response.choices[0].message.content or "{}"

    try:
        result = json.loads(content)
        return JudgeScore(
            correctness=int(result.get("correctness", 0)),
            completeness=int(result.get("completeness", 0)),
            faithfulness=int(result.get("faithfulness", 0)),
            overall=int(result.get("overall", 0)),
            explanation=str(result.get("explanation", "")),
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error("Failed to parse judge output: %s — %s", content, e)
        return JudgeScore(
            correctness=0,
            completeness=0,
            faithfulness=0,
            overall=0,
            explanation=f"Parse error: {e}",
        )


def batch_judge(
    records: List[dict],
    passages_map: dict,
) -> List[JudgeScore]:
    """
    Evaluate multiple answers using LLM-as-judge.

    Parameters
    ----------
    records:      List of result records (with question, answer, gold_label).
    passages_map: Dict mapping question_id -> List[RetrievedPassage].

    Returns
    -------
    List[JudgeScore] aligned with input records.
    """
    scores = []
    for rec in records:
        qid = rec["id"]
        question = rec["question"]
        gold_label = rec["gold_label"]
        # Use final summary as the answer
        answer = rec.get("system_c_summary", rec.get("draft_summary", ""))
        passages = passages_map.get(qid, [])

        score = judge_answer(question, answer, passages, gold_label)
        scores.append(score)

    return scores
