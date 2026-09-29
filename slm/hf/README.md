---
base_model: Qwen/Qwen2.5-1.5B-Instruct
library_name: peft
pipeline_tag: text-generation
license: apache-2.0
language:
- en
- hi
tags:
- lora
- qlora
- peft
- information-extraction
- structured-output
- json
- lead-qualification
- real-estate
- crm
---

# Beacon Qualification — Qwen2.5-1.5B QLoRA adapter

A LoRA adapter for [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct). It reads a
website demo conversation between **Beacon**, the AI demo agent for Leadrat CRM, and a prospect. It returns one JSON object in the
`beacon.qualification.v1` schema: who the prospect is, what they need, the transcript turn each fact came from,
an ICP (ideal customer profile) score, and a routing decision.

| | |
|---|---|
| **Version** | 0.1.0-dev (29 Sep 2026) |
| **Status** | ⚠️ **Development release. Not approved for production.** It fails 4 of 5 pre-registered ship gates on the development split ([Evaluation](#evaluation)). |
| **Task** | Structured information extraction and lead scoring from a chat transcript |
| **Base model** | Qwen2.5-1.5B-Instruct (Apache-2.0), 1.54B parameters |
| **Adapter** | LoRA r=16, α=32, 18.5M trainable parameters (1.18%), 70 MB |
| **Languages** | English (primary). Hinglish and Devanagari Hindi were in training but are weaker. |
| **Hardware** | Runs in 1.2 GB VRAM in 4-bit (tested on an RTX 2050, 4 GB) or ~3.5 GB in fp16 |

## Contents

- [Intended use](#intended-use)
- [Quick start](#quick-start)
- [Input and output](#input-and-output)
- [Integration guidance](#integration-guidance)
- [Training](#training)
- [Evaluation](#evaluation)
- [Limitations and risks](#limitations-and-risks)
- [Files](#files)
- [License and data provenance](#license-and-data-provenance)
- [Changelog](#changelog)

## Intended use

**Use it for:**

- Turning a (possibly partial) sales demo conversation into structured fields a CRM can store.
- Pre-filling a lead record for a person to review.
- Research into small models for structured extraction in real-estate sales.

**Do not use it for:**

- Automatic sales handoffs, or any automatic action on a lead without human review or rule-based checks.
- Scoring without re-deriving the score from the extracted facts (the model's own `score_range` is unreliable).
- Domains outside real-estate CRM sales, or conversations about something other than a sales demo.
- Decisions about individuals beyond sales follow-up (credit, employment, eligibility).

## Quick start

```bash
pip install "transformers>=4.45" peft accelerate huggingface_hub bitsandbytes
```

```python
import json, torch
from huggingface_hub import hf_hub_download
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

REPO = "abidansari5594/beacon-qualification-qwen2.5-1.5b-qlora"
tok = AutoTokenizer.from_pretrained(REPO)
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", dtype=torch.float16, device_map="auto")
model = PeftModel.from_pretrained(base, REPO).eval()          # downloads the base model and this adapter

system = open(hf_hub_download(REPO, "system_prompt.txt"), encoding="utf-8").read().strip()
transcript = [
    {"turn_id": 1, "speaker": "beacon",  "text": "Hi! Which part of Leadrat would you like to see?"},
    {"turn_id": 2, "speaker": "visitor", "text": "We run a brokerage in Pune with 18 agents. Our biggest problem is missed follow-ups."},
    {"turn_id": 3, "speaker": "beacon",  "text": "Roughly how many leads do you get a month?"},
    {"turn_id": 4, "speaker": "visitor", "text": "Around 400 a month, mostly from MagicBricks and Facebook. Everything is in Excel today."},
    {"turn_id": 5, "speaker": "beacon",  "text": "Would you like our team to follow up?"},
    {"turn_id": 6, "speaker": "visitor", "text": "Yes, I'm the owner. Call me on +91 90000 04321 next week."},
]
user = "\n".join(f"[{t['turn_id']}] {t['speaker'].upper()}: {t['text']}" for t in transcript)
prompt = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                 add_generation_prompt=True, tokenize=False)
ids = tok(prompt, add_special_tokens=False, return_tensors="pt")["input_ids"].to(model.device)
out = model.generate(ids, max_new_tokens=900, do_sample=False, pad_token_id=tok.eos_token_id)
print(json.loads(tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)))
```

Or use the bundled script: `python inference.py example_transcript.json --4bit`.

For a 4 GB GPU, load the base with
`BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)`.

Use greedy decoding (`do_sample=False`). Use **no few-shot examples**, because the adapter was trained zero-shot on
exactly this system prompt and turn format.

## Input and output

**Input:** the system prompt in `system_prompt.txt` plus one user message. The user message holds the transcript,
one turn per line, `[turn_id] SPEAKER: text`, with SPEAKER either `BEACON` or `VISITOR`. Transcripts in training
were 2–16 turns, and none was over 1,283 tokens.

**Output:** one JSON object that validates against `qualification.schema.json`. Output of the example above (on
an RTX 2050, 4-bit, ~40 s), abridged:

```json
{
  "schema_version": "beacon.qualification.v1",
  "role": "owner", "seniority": "owner",
  "organisation": {"name": null, "type": "brokerage", "agents": 18},
  "pain_points": ["missed follow-ups"],
  "current_tooling": ["Excel"],
  "geography": {"countries": null, "cities": ["Pune"]},
  "monthly_leads": {"min": 400, "max": 400},
  "lead_sources": ["MagicBricks", "Facebook"],
  "next_step": "within_30_days", "consent": true,
  "contact": {"name": null, "email": null, "phone": "+91 90000 04321"},
  "evidence": {"organisation.type": [2], "organisation.agents": [2], "monthly_leads": [4], "consent": [6], "...": []},
  "icp_score": 80, "score_range": [80, 80],
  "score_rationale": [{"dimension": "organisation", "points": 20, "evidence_turn_ids": [2]}, "..."],
  "route": "sales_handoff"
}
```

| Field | Values |
|---|---|
| `seniority` | owner, executive, manager, individual_contributor, unknown |
| `organisation.type` | brokerage, developer, channel_partner, other_real_estate, unrelated, unknown |
| `process` | manual, unsatisfied_crm, satisfied_crm, unknown |
| `influence` | approver, sponsored_evaluator, none, unknown |
| `next_step` | within_30_days, later, declined, unknown |
| `route` | sales_handoff, human_review, nurture, graceful_close |
| `evidence` | field path → visitor turn ids the fact came from |

Unknown facts are `null` or `"unknown"`. A fact that the visitor states and later corrects takes the corrected
value.

### Scoring rules the output should follow

| Dimension | Points |
|---|---|
| Organisation | brokerage, developer or channel partner 20; other real estate 10; unrelated 0 |
| Agents | ≥20: 15; 6–19: 10; 1–5: 5 |
| Monthly leads | ≥500: 15; 100–499: 10; 1–99: 5 |
| Pain points | ≥2: 20; 1: 10; none: 0 |
| Process | manual 10; unsatisfied CRM 5; satisfied CRM 0 |
| Purchase influence | approver 10; sponsored evaluator 5; none 0 |
| Next step | within 30 days 10; later 5; declined 0 |

`icp_score` is the sum only when all seven are known, otherwise `null`. `score_range` is [known sum, known sum + the
maximum for each unknown dimension].

Routing:
- Any unknown dimension → `human_review`.
- Declined → `graceful_close`.
- Score ≥70 with consent, an email or phone, and a next step within 30 days → `sales_handoff`.
- Score ≥70 otherwise, or 40–69 → `nurture`.
- Below 40 → `graceful_close`.

## Integration guidance

Treat the model as an **extractor**, not a decision-maker:

1. **Validate** the output against `qualification.schema.json`. If it fails, retry once, then fall back to a larger
   model or rules, then to a person. Invalid output was 4% of the development split.
2. **Check evidence.** Every `evidence` turn id must be a VISITOR turn in the transcript. Drop facts that fail.
3. **Re-derive** `icp_score`, `score_range` and `route` from the extracted facts with the rules above. Do not use
   the model's own values. This alone raised routing accuracy from 74% to 83% on the development split.
4. **Gate handoffs in code.** Before any automatic sales action, require explicit consent and a real contact in the
   transcript. Even then, send the lead to a person for review, because of the hallucination risk below.
5. **Redact** emails and phone numbers before sending transcripts to any third-party fallback model.

## Training

### Data

800 synthetic demo conversations about Leadrat CRM:
- Split: 676 train, 124 dev. The split is by scenario family (139 families), so near-duplicates never cross it.
- Language: English 513, Hinglish 232, Devanagari Hindi 55.
- Partial transcripts: 356 stop mid-demo.
- Hard cases:
  - prompt injection (fake system messages, pasted JSON, injected company names)
  - declines
  - consent without contact
  - corrections and contradictions
  - lakh/crore budgets that must not be read as lead counts

Conversations and fact labels were written by a teacher model (Claude Opus 5.5). **Scores and routes were not
teacher output**: they were derived from the approved ICP rules. Every example was validated, and 0 of 800 were
rejected. All contact details are fake (example.com addresses, +91 90000… numbers).

### Procedure

| Setting | Value |
|---|---|
| Method | QLoRA: base in 4-bit NF4 with double quantisation, fp16 compute, gradient checkpointing |
| LoRA | r 16, α 32, dropout 0.05; q, k, v, o, gate, up, down projections |
| Optimisation | AdamW, lr 2e-4, cosine schedule, 5% warm-up; batch 1 × gradient accumulation 16 |
| Epochs / steps | 2 / 86 |
| Loss | Causal LM loss on the JSON answer only (prompt tokens masked) |
| Max length | 2,048 tokens (no example truncated) |
| Seed | 20260928 |
| Hardware | 1 × Tesla T4 16 GB (Kaggle); 2,301 s; peak 4.63 GiB allocated |
| Software | torch 2.10, transformers 5.17, peft 0.21.1, bitsandbytes 0.50.2 |

Train loss 0.57 → 0.06. Dev loss 0.078 (epoch 1) → 0.067 (epoch 2), with no sign of over-fitting. Full log and data
hashes are in `run_metadata.json`.

## Evaluation

Measured on the **124-example dev split**, whose labels are teacher-labelled. These are development numbers. The
binding evaluation is a frozen, hand-labelled set that has not been run yet. Metrics use raw model output, with
no retries or fallback.

| Metric | Base model, few-shot | **This adapter** | Ship gate |
|---|---|---|---|
| JSON schema validity | 49.2% | **96.0%** | ≥ 99% ✗ |
| Routing accuracy (model's own route) | 34.7% | **74.2%** | ≥ 90% ✗ |
| Routing accuracy (route re-derived from facts) | 33.9% | **83.1%** | not a gate |
| Macro F1, categorical fields | 0.198 | **0.551** | ≥ 0.90 ✗ |
| ICP score MAE (n = 9 numeric pairs) | 14.38 | **4.44** | ≤ 8 ✓ |
| Unsafe automatic handoffs | 2 | 3 | 0 ✗ |
| Latency p50 / p95 (T4, fp16, HF generate) | 17.2 / 26.3 s | 25.3 / 30.2 s | not a gate |

**English only (79 dev examples):** schema validity 96%; routing, re-derived from facts, 86%; monthly leads
96%; agents 89%; seniority 84%; consent 82%; organisation type 71%; 1 unsafe handoff after re-derivation.

**Field accuracy (all languages):**

| Field | Accuracy |
|---|---|
| geography.cities | 92% |
| organisation.agents | 89% |
| lead_sources | 85% (F1) |
| seniority | 85% |
| next_step | 84% |
| monthly_leads | 82–83% |
| current_tooling | 81% (F1) |
| consent | 81% |
| process | 76% |
| organisation.type | 73% |
| influence | 73% |
| pain_points count | 58% |
| geography.countries | 57% |

Routing by class (model's own route):

| Class | Correct |
|---|---|
| human_review | 73/81 |
| sales_handoff | 10/15 |
| graceful_close | 9/9 |
| nurture | 0/19 |

## Limitations and risks

- **Unreliable `score_range`.** It was wrong in 101 of 124 dev outputs, even when the facts were right. Always
  re-derive it.
- **Hallucinated facts.** The model sometimes fills in an ICP dimension the visitor never stated. On the dev
  split, five conversations (four of them in Hindi) would have gone to sales on facts the visitor never gave.
  Re-scoring does not catch this. That is why the guidance above keeps a person in the loop for every handoff.
- **Nurture is under-predicted.** As written, the model's route is never `nurture` on dev (0/19).
- **Weak fields:** countries, pain-point counts, purchase influence, organisation type.
- **Synthetic, single-teacher data.** Real prospects are terser, messier and more off-topic, so expect lower
  accuracy on real transcripts. Geography covers India metros and the UAE only.
- **Slow on small GPUs.** Latency is 20–60 s per conversation. Run it after the conversation, not while the user is
  talking.
- **Personal data.** Output can contain names, emails and phone numbers from the transcript. Handle it under your
  data-protection policy, and store it only with consent.

## Files

| File | Purpose |
|---|---|
| `adapter_model.safetensors`, `adapter_config.json` | LoRA weights and config |
| `tokenizer.json`, `tokenizer_config.json`, `chat_template.jinja` | Tokenizer (same as the base) |
| `system_prompt.txt` | The exact system prompt used in training. Required. |
| `qualification.schema.json` | JSON Schema for `beacon.qualification.v1` |
| `inference.py`, `example_transcript.json` | Standalone inference script and sample input |
| `run_metadata.json` | Hyperparameters, versions, data hashes, full training log |

## License and data provenance

- The adapter is released under Apache-2.0, the same licence as the base model.
- The training data was generated by a Claude model. Check the applicable Anthropic usage terms before you use this
  adapter commercially.
- No real customer data was used.

## Changelog

- **0.1.0-dev (2026-09-29):** first development adapter; Kaggle T4, 2 epochs.
- **Next:** an English-only training round with more organisation-type and missing-fact examples; the model
  extracts facts only and the rules compute the score; evaluation on the hand-labelled set.
