
Assignment 1 README — writes ASSIGNMENT1_README.md:
```powershell
@'
# Assignment 1 — Ablation Study & Prompt Experiments

This folder contains experiments and results evaluating different prompting strategies (zero-shot, few-shot, chain-of-thought) for classifying and summarizing reviews.

**Flow of the experiments**
- Input: `yelp.csv` → preprocessing → experiment scripts:
  - `zero_shot.py`, `few_shot.py`, `chain_of_thought.py`
- Each script produces model outputs and evaluation metrics saved under `Assignment1/ablation_study_results/`.

**Prompts (summary & guidelines)**
- Zero-shot:
  - Instruction: produce a single-sentence summary and a classification tag. Enforce JSON output:
  ```json
  {"summary": "...", "classification": "..."}