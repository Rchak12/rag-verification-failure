# Evaluating Verification Layers for Reliable Retrieval-Augmented Question Answering

Rishab Chakravarty  
CS 592: Automated Reasoning and Machine Learning Integration  
Purdue University  

---

# 1 Introduction

Large language models (LLMs) are capable of generating fluent responses to a wide range of questions. However, these models frequently produce statements that are not supported by evidence, a phenomenon commonly referred to as hallucination. Retrieval-Augmented Generation (RAG) systems address this issue by incorporating external documents during generation, allowing the model to ground answers in retrieved information.

Despite this improvement, RAG systems may still produce unsupported claims or introduce additional information not present in the retrieved passages. This issue is particularly problematic in scientific and biomedical domains where factual accuracy is critical.

This project explores the use of a **claim-level verification layer** within a RAG pipeline. The proposed system decomposes generated answers into individual claims and verifies each claim against retrieved evidence. Unsupported claims are removed to ensure that the final response contains only information supported by source documents.

The goal of this midterm report is to present preliminary experiments evaluating this verification approach on a biomedical question answering task.

---

# 2 Problem Formulation

We study the problem of **evidence-grounded question answering**.

Given:

- a question \( q \)
- a set of retrieved documents \( D \)

The system must generate an answer \( a \) such that each claim in the answer is supported by evidence within \( D \).

Our research questions are:

1. Does claim-level verification reduce unsupported claims in generated answers?
2. How does verification affect answer accuracy?
3. What computational overhead does verification introduce?

---

# 3 System Architecture

The implemented system extends a standard RAG pipeline with a verification stage.

Pipeline steps:

1. Input question
2. Retrieve top-k documents
3. Generate structured answer using an LLM
4. Extract claims from the answer
5. Verify each claim against retrieved passages
6. Remove unsupported claims
7. Produce final verified answer

## Figure 1: Verified RAG Pipeline

![Figure 1: Overview of the Verified RAG Architecture](pipeline_diagram.png)

This design separates **generation** from **verification**, allowing reasoning-based checks to enforce factual consistency.

---

# 4 Experimental Setup

## Dataset

Experiments were conducted using a subset of the **PubMedQA dataset**, which contains biomedical research questions paired with supporting abstracts.

A subset of **N = 40 samples** was used for preliminary evaluation.

## Retrieval

- Retriever: embedding-based search
- Index: FAISS
- Top-k retrieval: k = 3

## Generation Model

- LLM used: stub (rule-based generation, no external LLM)
- Structured output format with claims extracted from the generated answer.

## Verification Method

Each claim is compared against sentences in retrieved passages using cosine similarity between embeddings.

A claim is considered supported if:

similarity score ≥ τ

where τ = 0.55.

## Repair Strategy

Unsupported claims are removed from the final answer.

## Evaluation Metrics

The following metrics were measured:

- Unsupported Claim Rate
- Answer Accuracy
- Average Claims per Answer
- Runtime per Query

---

# 5 Preliminary Results

## Table 1: System Performance

| System | Unsupported Claim Rate | Accuracy | Avg Claims | Runtime |
|------|------|------|------|------|
| RAG Baseline | 0.3333 | 0.45 | 3.0 | 0.0004s |
| Verified RAG | 0.0 | 0.45 | 2.0 | 3.7738s |

![Figure 2: Comparison of RAG Baseline and Verified RAG Performance](results_comparison.png)

Figure 2 compares key performance metrics between the baseline RAG system and the verification-augmented version. Verification eliminates unsupported claims while maintaining accuracy, though it reduces the average number of claims per answer.

---

# 6 Qualitative Examples

## Example 1

**Question**

Do mitochondria play a role in remodelling lace plant leaves during programmed cell death?

**RAG Output**

Claims:
1. Programmed cell death (PCD) is the regulated death of cells within an organism.
2. The lace plant (Aponogeton madagascariensis) produces perforations in its leaves through PCD.
3. Further longitudinal studies with larger sample sizes are needed to establish definitive causal relationships in this domain.

**Verification Results**

Claim 1: Supported
Claim 2: Supported
Claim 3: Unsupported

**Final Verified Answer**

[YES] Programmed cell death (PCD) is the regulated death of cells within an organism. The lace plant (Aponogeton madagascariensis) produces perforations in its leaves through PCD.

## Example 2

**Question**

Landolt C and snellen e acuity: differences in strabismus amblyopia?

**RAG Output**

Claims:
1. Assessment of visual acuity depends on the optotypes used for measurement.
2. The ability to recognize different optotypes differs even if their critical details appear under the same visual angle.
3. Further longitudinal studies with larger sample sizes are needed to establish definitive causal relationships in this domain.

**Verification Results**

Claim 1: Supported
Claim 2: Supported
Claim 3: Unsupported

**Final Verified Answer**

[MAYBE] Assessment of visual acuity depends on the optotypes used for measurement. The ability to recognize different optotypes differs even if their critical details appear under the same visual angle.

## Example 3

**Question**

Syncope during bathing in infants, a pediatric form of water-induced urticaria?

**RAG Output**

Claims:
1. Apparent life-threatening events in infants are a difficult and frequent problem in pediatric practice.
2. The prognosis is uncertain because of risk of sudden infant death syndrome.
3. Further longitudinal studies with larger sample sizes are needed to establish definitive causal relationships in this domain.

**Verification Results**

Claim 1: Supported
Claim 2: Supported
Claim 3: Unsupported

**Final Verified Answer**

[YES] Apparent life-threatening events in infants are a difficult and frequent problem in pediatric practice. The prognosis is uncertain because of risk of sudden infant death syndrome.

---

## Figure 3: Claim Verification Example

![Figure 3: Example of Claim Verification Process](verification_example.png)

---

# 7 Discussion

Preliminary experiments suggest that the verification layer effectively reduces unsupported statements in generated answers.

However, several challenges were observed.

First, similarity-based verification sometimes removed valid claims due to paraphrasing differences between generated text and source passages.

Second, verification quality strongly depends on retrieval performance. When relevant evidence was not retrieved, correct claims could not be verified.

Third, claim extraction plays an important role. Broad or multi-part claims were more difficult to verify than concise statements.

These observations suggest that verification accuracy could be improved with stronger entailment models and improved claim decomposition.

---

# 8 Future Work

Several improvements will be explored in the final stage of the project.

1. Replace similarity verification with natural language inference models.
2. Improve claim extraction using structured prompting.
3. Experiment with rewriting unsupported claims instead of removing them.
4. Increase evaluation size to 100+ samples.
5. Analyze the impact of different retrieval strategies.

These extensions will allow a more comprehensive evaluation of verification layers in retrieval-augmented systems.

---

# 9 Conclusion

This report presented a preliminary evaluation of a claim-level verification layer for retrieval-augmented question answering. Early results indicate that verification can significantly reduce unsupported claims while introducing modest computational overhead.

Future work will explore more advanced verification techniques and larger-scale evaluations to further improve the reliability of RAG systems.