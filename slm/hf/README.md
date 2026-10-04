---
base_model: Qwen/Qwen2.5-1.5B-Instruct
library_name: peft
pipeline_tag: text-generation
license: apache-2.0
language: [en, hi]
tags: [lora, qlora, information-extraction, lead-qualification]
---

# Beacon qualification adapter

Current release: **v3 continuation, 30 September 2026**.

This adapter extracts structured sales-qualification facts from Beacon / Leadrat conversations.
It returns the full `beacon.qualification.v1` JSON schema. It is not a general question-answer chatbot.

## Current training

Continued from revision `637c739100e160e70d3baea1137e20f5b4965049`.
All 392 saved adapter tensors were verified before training.
Training used 2,811 synthetic conversations (2,569 English, 207 Hinglish, 35 Hindi),
356 development conversations, two additional epochs, learning rate 0.00005, and a Kaggle Tesla T4.
The old adapter weights were restored. Optimizer and scheduler started fresh.
All 352 steps completed. Final training loss: 0.027671. Final development loss: 0.032205.
Loss is not question-answer accuracy. See the held-out evaluation below.
The synthetic reference labels are not independently human-reviewed.

Weights SHA256: `e23139ba1b61a4912f476120cef8ff6edb8a8a726a0d8c9a9537308cc492ffe3`.

## Load the latest adapter

Use this repository without an old revision pin to load the current release:

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
repo = "abidansari5594/beacon-qualification-qwen2.5-1.5b-qlora"
tokenizer = AutoTokenizer.from_pretrained(repo)
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", device_map="auto")
model = PeftModel.from_pretrained(base, repo).eval()
```

Use `system_prompt.txt` and numbered transcript turns as shown by `inference.py`.
For another training round, load with `PeftModel.from_pretrained(base, repo, is_trainable=True)`.
Resolve and record the current repository revision at the start of each new training run.
Do not use the previous revision pin or initialize a fresh LoRA adapter.

## Held-out evaluation of v3

Tested adapter revision: `5697b9c0d4c0dbda8321b781f113854d16e6863c`.

233 synthetic English conversations from 38 held-out scenario families; 22 reported fields per conversation.
Test IDs, scenario families and exact visitor transcripts do not overlap the train/development splits.

| Metric | Count | Rate |
| --- | ---: | ---: |
| All 22 fields match | 50 / 233 | 21.5% |
| Individual fields match, including unknowns | 4,693 / 5,126 | 91.6% |
| Known-reference fields match | 3,507 / 3,899 | 89.9% |
| Usable schema and visitor evidence IDs | 231 / 233 | 99.1% |
| Raw route matches reference | 214 / 233 | 91.8% |
| Incorrect sales handoffs | 6 / 233 | 2.6% |

Matching uses normalized equality, not human semantic grading. Correct unknown values contribute to the overall field rate.
Known-reference matching excludes null/unknown reference values. Valid paraphrases can count as mismatches.
Full-match excludes evidence and rationale text. Incorrect handoffs mean sales_handoff when the reference is not sales_handoff or consent is absent.
These results apply to structured qualification extraction, not general question-answer responses.
Synthetic labels are not independently human-reviewed; real-customer performance and improvement over the old adapter are not established.
See `eval_v3/summary.json` for the dataset hash, inference settings and measured totals.

Files under `eval/` are historical results of the previous adapter.
