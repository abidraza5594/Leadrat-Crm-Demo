# Pre-registered ship decision — Beacon qualification SLM

**Registered:** 2026-09-28T10:54:33Z (the git commit that adds this file is the authoritative timestamp).
**Registered before:** the hand-labelled evaluation set exists, and before any training or evaluation run of
system C on the new dataset. These thresholds will not change after results are seen. Any later change is a
new, separately dated file that also reports the original result against this one.

Disclosure: a practice fine-tune on 22 Sep 2026 (12 synthetic items, an older rubric) was run while learning
the tooling. It is not part of this evaluation and its data is not reused.

## Systems (same frozen hand-labelled set)

| | System |
|---|---|
| A | Few-shot prompt to a hosted frontier model |
| B | Few-shot prompt to the base SLM (Qwen2.5-1.5B-Instruct), no fine-tuning |
| C | The fine-tuned SLM (QLoRA adapter on the same base) |

## Ship criteria — C ships over A only if **all** hold

| # | Metric (on the frozen hand-labelled set, raw model output, no fallback) | Threshold |
|---|---|---|
| 1 | JSON schema validity (parses and validates as `beacon.qualification.v1`) | ≥ 99% |
| 2 | Routing accuracy (route vs hand label) | ≥ 90% **and** no more than 3 percentage points below A |
| 3 | Macro F1 across extracted fields | ≥ 0.90 |
| 4 | ICP score MAE, on examples where both gold and prediction are numeric | ≤ 8 points |
| 5 | Unsafe automatic handoffs: predicted `sales_handoff` where the gold label is not `sales_handoff`, or consent is not explicit | 0 |

Additionally reported (not ship gates): per-class routing accuracy and confusion matrix, per-field
accuracy/F1, the share of examples with a numeric score, p50/p95 latency, cost per 1,000 conversations,
fallback-assisted results (reported separately from raw results), and the 20 worst cases.

## Decision rule

- All five criteria met → recommend shipping C with the fallback ladder.
- Any criterion missed → **recommend against shipping** C, keep the rules-based scorer (and A where budget
  allows) in the live path, and explain which criterion failed and why.
- If A cannot be run (no approved budget), criterion 2's comparison is incomplete and no ship recommendation
  is made; B and C are still reported.
