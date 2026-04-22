"""
Run a single end-to-end RAG+Verification pipeline example with verbose output.
Usage:
  python tools/run_one_example.py --question "What is the role of p53 in cancer?" --backend stub --repair delete --k 3 --tau 0.55
  # or for rewrite (System C):
  python tools/run_one_example.py --question "..." --backend openai --repair rewrite --k 3 --tau 0.55

Requires: run from repo root, conda env active, and (for rewrite) OPENAI_API_KEY in .env or env.
"""
import argparse
import os
import sys
from src import retrieve, generate, claims, verify, repair, rewrite


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--question', type=str, required=True, help='Input question')
    parser.add_argument('--backend', type=str, default='stub', choices=['stub', 'openai'])
    parser.add_argument('--repair', type=str, default='delete', choices=['delete', 'rewrite'])
    parser.add_argument('--k', type=int, default=3)
    parser.add_argument('--tau', type=float, default=0.55)
    parser.add_argument('--nli', action='store_true', help='Use NLI verification (default: cosine)')
    args = parser.parse_args()

    print(f"\n[1] RETRIEVE: k={args.k}")
    ctxs = retrieve.retrieve(args.question, k=args.k)
    for i, c in enumerate(ctxs):
        print(f"  [{i+1}] {c}")

    print(f"\n[2] GENERATE: backend={args.backend}")
    draft = generate.generate_draft(args.question, ctxs, backend=args.backend)
    print(f"Drafted answer:\n{draft}\n")

    print("[3] EXTRACT CLAIMS:")
    claim_list = claims.extract_claims(draft)
    for i, c in enumerate(claim_list):
        print(f"  Claim {i+1}: {c}")

    print(f"\n[4] VERIFY: method={'nli' if args.nli else 'cosine'}, tau={args.tau}")
    if args.nli:
        verdicts = verify.verify_claims_nli(claim_list, ctxs, tau=args.tau)
    else:
        verdicts = verify.verify_claims_cosine(claim_list, ctxs, tau=args.tau)
    for i, v in enumerate(verdicts):
        print(f"  Claim {i+1}: {v['claim']}\n    Supported: {v['supported']} (score={v['score']:.3f})")

    print(f"\n[5] REPAIR: mode={args.repair}")
    if args.repair == 'delete':
        final = repair.repair(draft, verdicts)
        print(f"\nFinal answer (DELETE unsupported):\n{final['answer']}")
    else:
        final = rewrite.rewrite_unsupported(draft, verdicts)
        print(f"\nFinal answer (REWRITE unsupported):\n{final['answer']}")

    print("\n[Done]")

if __name__ == '__main__':
    main()
