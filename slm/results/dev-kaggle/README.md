# Development run — B vs C on dev.jsonl (29 Sep 2026)

**These are development numbers, not the ship evaluation.** They are measured on `slm/data/dev.jsonl`
(124 teacher-labelled examples from 21 held-out scenario families), not on the frozen hand-labelled set
that `slm/PREREGISTRATION.md` names. A has not been run yet.

Run: Kaggle Tesla T4, QLoRA NF4 r16/a32, 2 epochs (86 steps), train 2,301 s, peak VRAM 4.63 GiB.
Eval loss 0.078 (epoch 1) → 0.067 (epoch 2); train loss 0.57 → 0.06. Data hashes match `slm/data/stats.json`.
Files: `B.json`, `C.json`, `table.md`, `run_metadata.json`. The adapter is kept locally in `slm/runs/kaggle/adapter`
(git-ignored).

| Metric (raw model output) | B | C | Pre-registered gate |
|---|---|---|---|
| JSON schema validity | 49.2% | 96.0% | ≥ 99% ✗ |
| Routing accuracy, as written | 34.7% | 74.2% | ≥ 90% ✗ |
| Routing accuracy, score/route re-derived by the rules | 33.9% | 83.1% | (reported, not a gate) |
| Macro F1 (categorical) | 0.198 | 0.551 | ≥ 0.90 ✗ |
| ICP score MAE | 14.38 (n=8) | 4.44 (n=9) | ≤ 8 ✓ (small n) |
| Unsafe handoffs, as written | 2 | 3 | 0 ✗ |
| p50 / p95 latency (T4, HF generate) | 17.2 / 26.3 s | 25.3 / 30.2 s | — |

## What the errors are

- **`score_range` is the model's weak spot.** 102 of 124 C outputs are valid facts with a score, range or route
  that disagrees with the rules; the range is wrong in 101. The live path never trusts these: `rescore()`
  re-derives score, range and route from the extracted facts.
- **Nurture is never predicted as written (0/19).** After re-derivation 14/19 are correct, so the facts are
  mostly right and the model's own routing is not.
- **Unsafe handoffs after re-derivation: 5**, all with gold `human_review` (b4-011, b7-037, b7-038, b7-040,
  b7-041). In each the visitor consented and left a contact, but one ICP dimension was not stated; the model
  filled it in. This is hallucinated extraction, and re-scoring cannot catch it.
- Weakest fields: `geography.countries` 57%, `pain_points` count 58%, `influence` (F1 0.39),
  `organisation.type` (F1 0.53).

## Consequence

On these numbers C would fail four of the five gates. Per the decision rule, C is not recommended for the live
path; the rules scorer (and A where budget allows) stay primary, and any C output that proposes
`sales_handoff` must be treated as a proposal for human review. The binding decision waits for the
hand-labelled set.
