"""
test_setup.py — Verify experimental setup before running full experiments.

This script checks:
1. OpenAI API key configured
2. All dependencies installed
3. PubMedQA data accessible
4. FAISS index loadable
5. GPT-4o generation working
6. NLI verification working
7. Rewrite module working

Usage:
    python test_setup.py

Expected output: ✅ All checks pass
"""

import sys
from pathlib import Path


def check_env():
    """Check .env configuration."""
    print("\n🔍 Checking environment configuration...")

    env_file = Path(".env")
    if not env_file.exists():
        print("  ❌ .env file not found")
        print("     Run: cp .env.example .env")
        print("     Then add your OPENAI_API_KEY")
        return False

    content = env_file.read_text()

    if "OPENAI_API_KEY=sk-" not in content and "OPENAI_API_KEY=sk-proj-" not in content:
        print("  ❌ OPENAI_API_KEY not set in .env")
        print("     Edit .env and add: OPENAI_API_KEY=sk-proj-your_key_here")
        return False

    print("  ✅ .env file configured")
    return True


def check_dependencies():
    """Check required packages installed."""
    print("\n🔍 Checking dependencies...")

    required = [
        ("openai", "pip install openai>=1.0.0"),
        ("datasets", "pip install datasets"),
        ("sentence_transformers", "pip install sentence-transformers"),
        ("faiss", "pip install faiss-cpu"),
        ("transformers", "pip install transformers"),
    ]

    all_ok = True
    for pkg, install_cmd in required:
        try:
            if pkg == "faiss":
                import faiss  # type: ignore
            else:
                __import__(pkg)
            print(f"  ✅ {pkg}")
        except ImportError:
            print(f"  ❌ {pkg} not installed")
            print(f"     Run: {install_cmd}")
            all_ok = False

    return all_ok


def check_data():
    """Check PubMedQA data access."""
    print("\n🔍 Checking PubMedQA data access...")

    try:
        from src.data import load_pubmedqa
        examples = load_pubmedqa(split="train", limit=5)
        print(f"  ✅ Loaded {len(examples)} examples")
        return True
    except Exception as e:
        print(f"  ❌ Failed to load data: {e}")
        return False


def check_index():
    """Check FAISS index."""
    print("\n🔍 Checking FAISS index...")

    from src.config import INDEX_DIR
    index_path = INDEX_DIR / "pubmedqa_index.faiss"

    if index_path.exists():
        print(f"  ✅ FAISS index exists at {index_path}")
        return True
    else:
        print(f"  ⚠️  FAISS index not found (will be built on first run)")
        return True  # Not fatal


def check_gpt4o():
    """Check GPT-4o access."""
    print("\n🔍 Checking GPT-4o API access...")

    try:
        from openai import OpenAI
        from src.config import OPENAI_API_KEY, OPENAI_MODEL

        if not OPENAI_API_KEY:
            print("  ❌ OPENAI_API_KEY not loaded from .env")
            return False

        client = OpenAI(api_key=OPENAI_API_KEY)

        # Quick test call
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "user", "content": "Say 'test successful' in 2 words"}
            ],
            max_tokens=10,
        )

        result = response.choices[0].message.content
        print(f"  ✅ GPT-4o accessible (model: {OPENAI_MODEL})")
        print(f"     Test response: {result}")
        return True

    except Exception as e:
        print(f"  ❌ GPT-4o API error: {e}")
        print("     Check your OPENAI_API_KEY and billing status")
        return False


def check_nli():
    """Check NLI model."""
    print("\n🔍 Checking NLI verification model...")

    try:
        from sentence_transformers import CrossEncoder
        from src.config import NLI_MODEL

        print(f"  Loading {NLI_MODEL}...")
        model = CrossEncoder(NLI_MODEL)

        # Quick test
        score = model.predict([
            ("The sky is blue.", "The sky has a blue color.")
        ])
        print(f"  ✅ NLI model loaded successfully")
        print(f"     Test entailment score: {score}")
        return True

    except Exception as e:
        print(f"  ❌ NLI model error: {e}")
        return False


def check_modules():
    """Check custom modules import."""
    print("\n🔍 Checking custom modules...")

    modules_ok = True

    try:
        from src.generate import generate_draft
        print("  ✅ src.generate")
    except Exception as e:
        print(f"  ❌ src.generate: {e}")
        modules_ok = False

    try:
        from src.verify import verify_claims
        print("  ✅ src.verify")
    except Exception as e:
        print(f"  ❌ src.verify: {e}")
        modules_ok = False

    try:
        from src.rewrite import rewrite_unsupported
        print("  ✅ src.rewrite")
    except Exception as e:
        print(f"  ❌ src.rewrite: {e}")
        modules_ok = False

    try:
        from src.repair import repair
        print("  ✅ src.repair")
    except Exception as e:
        print(f"  ❌ src.repair: {e}")
        modules_ok = False

    return modules_ok


def main():
    print("=" * 70)
    print("  CS592 Verified RAG — Setup Verification")
    print("=" * 70)

    checks = [
        ("Environment", check_env),
        ("Dependencies", check_dependencies),
        ("Data Access", check_data),
        ("FAISS Index", check_index),
        ("Custom Modules", check_modules),
        ("NLI Model", check_nli),
        ("GPT-4o API", check_gpt4o),
    ]

    results = []
    for name, check_fn in checks:
        try:
            passed = check_fn()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ {name} check crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("\n🎉 ALL CHECKS PASSED! Ready to run experiments.")
        print("\nNext steps:")
        print("  1. Quick test:  python -m src.run_three_systems --n 5 --k 3")
        print("  2. Full run:    python -m src.run_three_systems --n 100 --k 3 --final")
        print("  3. See Final_Steps.md for complete experimental plan\n")
        sys.exit(0)
    else:
        print("\n⚠️  SOME CHECKS FAILED. Fix the issues above before running experiments.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
