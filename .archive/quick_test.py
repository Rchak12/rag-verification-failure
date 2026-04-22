#!/usr/bin/env python
"""
quick_test.py — Minimal test that bypasses embeddings/FAISS.
Just tests the stub generation + repair pipeline without retrieval.
"""

import sys
from pathlib import Path

# Add repo to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

# Minimal test: generate claims from a sample question
sample_question = "Is diabetes a risk factor for COVID-19?"
sample_answer = "Yes, diabetes increases the risk of severe COVID-19. Patients with diabetes have higher mortality rates."

print("\n" + "="*70)
print("QUICK PIPELINE TEST (No embeddings/FAISS)")
print("="*70)

print(f"\nInput question: {sample_question}")
print(f"Sample answer: {sample_answer}\n")

# Test 1: Claim extraction
try:
    from src.claims import extract_claims
    claims = extract_claims(sample_answer)
    print(f"✓ [1/4] Claim extraction")
    for i, c in enumerate(claims, 1):
        print(f"       Claim {i}: {c}")
except Exception as e:
    print(f"✗ [1/4] Claim extraction failed: {e}")
    sys.exit(1)

# Test 2: Simple rule-based verification (no embeddings)
try:
    print(f"\n✓ [2/4] Verification (stub method)")
    # Mock verification: all claims "supported"
    verified = [
        {
            "claim": c,
            "supported": True,
            "support_score": 0.8,
            "evidence_sentence": "Retrieved evidence for this claim",
            "evidence_source_id": "doc_1",
        }
        for c in claims
    ]
    for v in verified:
        status = "✓" if v["supported"] else "✗"
        print(f"       {status} {v['claim'][:50]}... (score={v['support_score']:.2f})")
except Exception as e:
    print(f"✗ [2/4] Verification failed: {e}")
    sys.exit(1)

# Test 3: Repair (delete unsupported)
try:
    from src.repair import repair
    from src.generate import DraftAnswer
    
    draft = DraftAnswer(
        answer_label="yes",
        summary=sample_answer,
        claims=claims,
        cited_sources=["doc_1"],
        raw=sample_answer,
    )
    
    final = repair(draft, verified)
    print(f"\n✓ [3/4] Repair (DELETE unsupported)")
    print(f"       Final label: {final['answer_label']}")
    print(f"       Supported claims: {len(final['supported_claims'])}")
    print(f"       Unsupported claims: {len(final['unsupported_claims'])}")
except Exception as e:
    print(f"✗ [3/4] Repair failed: {e}")
    sys.exit(1)

# Test 4: Generate output
try:
    import json
    from datetime import datetime
    
    output = {
        "timestamp": datetime.now().isoformat(),
        "question": sample_question,
        "answer_label": final["answer_label"],
        "final_summary": final["final_summary"],
        "n_claims_original": len(claims),
        "n_claims_supported": len(final["supported_claims"]),
        "n_claims_unsupported": len(final["unsupported_claims"]),
    }
    
    print(f"\n✓ [4/4] Output generation")
    print(f"       {json.dumps(output, indent=2)}")
    
except Exception as e:
    print(f"✗ [4/4] Output failed: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("✓ QUICK TEST PASSED")
print("="*70)
print("\nCore pipeline works! Once embeddings/FAISS installs, you can run:")
print("  python -m src.run_experiment --n 10 --backend stub --repair delete\n")
