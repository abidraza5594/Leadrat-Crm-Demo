# Evaluation data

- `dev.jsonl`: the 124-conversation development test set, held out by scenario family from training. Each row has
  `transcript` (the conversation) and `target` (the expected `beacon.qualification.v1` output). Labels are
  teacher-labelled and all contacts are fake. This is not the final hand-labelled set.
- `predictions_A.jsonl` / `_B` / `_C`: every model output on that set. Each row has `raw`, the parsed `pred`, `gold`,
  the failure `reason` (if any) and latency. A is the hosted model, B the base Qwen2.5-1.5B few-shot, C this adapter.
- `A.json`, `B.json`, `C.json`: metrics per system. `table.md`: the comparison table.
