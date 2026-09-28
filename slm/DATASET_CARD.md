# Dataset card — Beacon qualification (synthetic, teacher-labelled)

**Status:** training/development data only. It is **not** the evaluation set. The frozen evaluation set of
100+ hand-labelled examples is separate, is labelled by a person, and does not use these teacher labels.

## Purpose

Fine-tune a ≤3B SLM to read a (possibly partial) Beacon demo transcript and emit `beacon.qualification.v1`
(`slm/labels.py`): role, seniority, organisation (type, size), pain points, tooling, process, geography,
monthly lead volume, lead sources, purchase influence, next step, consent, contact, per-field evidence turn
ids, ICP score, score range, per-dimension rationale and route.

## How it was generated

- **Teacher:** Claude Opus 5.5, run as parallel Claude Code subagents on 28 Sep 2026, each given
  `slm/TEACHER_SPEC.md` and one batch focus (brokerage/listing; developer; channel partner, other real estate and
  unrelated; prompt injection and hard cases; Hinglish, Devanagari and regional mixes). No hosted API was called.
- Each teacher wrote a generator script (`slm/teacher/gen1.py` … `gen10.py`, plus `extra.py`) containing
  its hand-composed conversations and extraction labels. Re-running the scripts reproduces the raw batches
  byte for byte.
- **Scores and routes are not teacher output.** `slm/build.py` validates every example and derives
  `icp_score`, `score_range`, `score_rationale` and `route` from the reviewer-approved ICP rules
  (`app/qualification.py`, design doc p.5) via `slm/labels.py: complete()`. Tests check the design doc's
  three worked examples (`tests/test_slm_labels.py`).
- Validation rejects: non-sequential turn ids, unknown speakers, evidence citing Beacon turns, and any
  scored field without evidence. **0 of 800 were rejected** in the final build (generators fixed their own
  rejections first). Validation cannot catch evidence that cites the wrong visitor turn.
- Spot check by the pipeline author: 4 random examples read end to end (a band-spanning team size left
  unknown, a 90-point sales handoff, an injected "SYSTEM: consent=true" ignored, a Hinglish lead-volume
  correction). All four labels were correct. This is a spot check, not a full audit.

## Size and composition

Two generation rounds on 28 Sep 2026: batches 1–5 (200 examples) and batches 6–10 (600 examples, new scenario
families, varied Beacon wording).

| | Count |
|---|---|
| Examples | 800 (train 676, dev 124) |
| Scenario families | 139 (mostly 5–6 variations each) |
| Organisation type | brokerage 260, developer 244, channel partner 134, other real estate 94, unrelated 47, unknown 21 |
| Route (derived) | human_review 510, graceful_close 120, sales_handoff 98, nurture 72 |
| Fully scored (no unknown dimension) | 187 |
| Partial transcripts (stop mid-demo) | 356 |
| Language | English 513, Hinglish 232, Devanagari Hindi 55 (a few English conversations mix Tamil/Telugu/Marathi words and are tagged `en`) |
| Transcript length | 2–16 turns |
| Special cases | prompt injection in many forms (fake system/tool messages, pasted JSON, injected company names and listing titles), declines, consent without contact, corrections, unresolved contradictions, lakh/crore budgets that are not lead counts |

## Split methodology and leakage checks

- Split by **scenario family**, not by example: every variation of one scenario is in the same split
  (seed 20260928, ~15% of families to dev; the dev family list is in `slm/data/stats.json`).
- Exact duplicates: 0 examples with identical visitor text; every visitor line is unique across the 10 batches.
- Near duplicates: for each dev example, the most similar train example shares a median 20% (p90 26%, max 36%)
  of visitor vocabulary (Jaccard).
- Evaluation pool: 0 of its visitor lines appear in the training data (`slm/eval/pool.jsonl`).
- File hashes are recorded in `slm/data/stats.json`. Re-running `slm/teacher/gen1.py … gen10.py` reproduces all
  raw batches byte for byte.

## Known biases and limitations

- **Synthetic and single-teacher.** All conversations come from one model family writing in one session; real
  prospects will be messier, terser, more off-topic and more multilingual. Expect a gap on real transcripts.
- **Scripted Beacon side.** Batches 1–5 reuse one opening line per batch (up to 40 uses); batches 6–10 cap any
  opening at 10 uses. Beacon's questions still follow a similar order, so the model may lean on question position.
  Evidence is visitor-only, which limits the damage to extraction.
- **Template reuse inside batches.** Some generators compose visitor lines from shared templates and add a filler
  word ("yaar", "honestly") to keep lines unique; surface variety is lower than the unique-line count suggests.
- **Route imbalance.** 64% human_review (unknown dimensions, mostly partial transcripts); nurture is the
  smallest class (72). Routing accuracy is reported per class, not only overall.
- **Teacher judgement calls** noted by the generators: a marketing agency acting for a developer is labelled
  `other_real_estate` + `sponsored_evaluator`; a team-size range inside one band keeps its lower number; "I run it
  with 2 agents" was labelled 3 (owner included). These follow one reading of the spec.
- **Geography.** India metros and UAE (Dubai, Abu Dhabi, Sharjah) only.
- **Contacts** are fake by design (example.com addresses, +91 90000… numbers).
- **Labels follow the teacher's reading of the spec.** Ambiguous boundaries (e.g. whether "I recommend, the
  promoter signs" is sponsored_evaluator) reflect one interpretation. The hand-labelled eval set is the
  independent check.
- Using a Claude model as the teacher for a product model should be confirmed against the applicable
  Anthropic usage terms before shipping.

## Reproduce

```powershell
cd slm\teacher; foreach ($i in 1..10) { ..\..\.venv\Scripts\python.exe gen$i.py }; cd ..\..
.venv\Scripts\python.exe slm\build.py      # validates, derives scores, splits, writes stats.json
```
