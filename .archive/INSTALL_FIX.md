# QUICK START — What's Happening

## Current Issue
Environment has binary incompatibilities (FAISS segfault on macOS). 

## Solution in Progress
Installing PyTorch + FAISS from conda-forge (better macOS support). This takes ~10–15 minutes.

## Once conda install finishes:

```bash
cd '/Users/rishabchakravarty/CS592 project/cs592-verified-rag'
conda activate cs592
pip install -r requirements.txt --no-deps  # install remaining Python deps
python -m src.run_experiment --n 10 --backend stub --repair delete
```

Expected output: `outputs/runs/<TIMESTAMP>/results.csv` with 10 rows.

## If still crashes:
Use the **Docker approach** (if available) or file a builtout on the FAISS/PyTorch compatibility.

## Estimated total wait time:
- Conda install: 10-15 min
- First test run: 5 min
- **Total: 20 min then you have working system**
