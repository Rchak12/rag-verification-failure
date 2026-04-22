Reproducibility instructions for Verified RAG project

This folder documents how to create a reproducible environment and run the experiments.

Conda-based setup (recommended, macOS / Linux)
---------------------------------------------
1. Create and activate the conda environment:

   conda create -n cs592 python=3.10 -y
   conda activate cs592

2. Install core ML packages (convenient, compatible wheels):

   conda install -c conda-forge faiss-cpu sentence-transformers datasets pytorch -y

3. Install remaining Python dependencies from the project repo (use pip inside conda env):

   pip install -r requirements.txt --no-deps

4. Optionally set a Hugging Face token to increase download rate-limits:

   export HF_TOKEN=hf_xxx

5. Run unit tests:

   python -m pytest -q

6. Run a quick sanity experiment (stub backend, inexpensive):

   python -m src.run_experiment --n 10 --k 3 --tau 0.55 --backend stub --repair delete --final

7. Sanity REWRITE test (uses OpenAI; be careful with API cost):

   # ensure OPENAI_API_KEY is set in .env or env var
   python -m src.run_experiment --n 5 --k 3 --tau 0.55 --backend openai --repair rewrite --final

Notes and tips
---------------
- Why conda? Conda-forge provides prebuilt native wheels for packages like faiss and pytorch that avoid segmentation faults common with pip on macOS.
- If you cannot use conda, try the project's venv (we provide a basic `.venv` setup command in the project root), but you may run into binary incompatibilities.
- The script `setup_conda.sh` in the repo automates the environment creation steps; run it and then follow the printed instructions.

Running full experiments
------------------------
- For the final experiments (N >= 100), pick `--n 150` and run both repair modes separately:

  python -m src.run_experiment --n 150 --k 3 --tau 0.55 --backend openai --repair delete --final
  python -m src.run_experiment --n 150 --k 3 --tau 0.55 --backend openai --repair rewrite --final

- For ablations:

  python -m src.ablation --n 50 --mode tau --backend stub --repair delete
  python -m src.ablation --n 50 --mode k   --backend stub --repair delete

Collecting outputs
------------------
- Each run creates `outputs/runs/<timestamp>/` containing `results.csv`, `metrics.json`, `qual_examples.md`, `failure_analysis.md`, and `drafts.jsonl`.
- Use `--final` to copy clean artifacts to `outputs/` (used for report submission).

If you want, I can also add a small helper `tools/run_one_example.py` that runs retrieval → generate → verify → rewrite for a single example and prints debug info; tell me if you want that added.