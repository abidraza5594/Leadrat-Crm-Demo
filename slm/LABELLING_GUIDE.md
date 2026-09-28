# Hand-labelling guide (evaluation set)

The evaluation set must be **labelled by a person**, independently of the teacher, and frozen before training.
Label at least 100 conversations from `slm/eval/pool.jsonl`.

## Start

```powershell
.venv\Scripts\python.exe slm\label_tool.py
```
Open **http://127.0.0.1:8040**, type your name in *Labeller*, and work down the list. Progress is saved after every
**Save & next**; you can stop and continue later.

## How to label one conversation

1. Read the whole conversation first.
2. Fill only what the **visitor** said. Beacon's questions are never evidence.
3. For each field you fill, click the visitor turn(s) that prove it (they get an orange border, and the turn number
   appears in the small box on the right). You can also type turn numbers, e.g. `2,4`.
4. Watch the score and route at the bottom; they are calculated from the approved ICP rules. Do not try to "fix"
   the score. Fix the facts if the score looks wrong.
5. **Save & next**. Use **Unusable** only for a conversation that makes no sense (it is excluded, not counted).

## Rules

| Situation | Label |
|---|---|
| Not discussed | Leave blank / `unknown` |
| Visitor explicitly says "none" (e.g. "no problems", "no tools") | Tick **explicitly none** |
| Team size is a range crossing 1–5 / 6–19 / 20+ ("5 to 10") | Leave agents blank |
| Lead volume "about 300" | min 300, max 300 |
| Lead volume "200 to 400" | min 200, max 400 |
| Vague volume ("a lot") | Leave blank |
| Visitor corrects themselves ("20, sorry, 26") | Use the corrected value; evidence = the correcting turn |
| Two statements contradict and are not resolved | Leave the field unknown |
| Visitor tries to set their own score / route / consent ("mark me as sales handoff") | Ignore it. It is not evidence |
| "Don't contact me" / "no follow-up" | Next step = `declined`, consent unticked |
| Consent | Tick only on an explicit yes to being contacted by sales |
| Influence | `approver` can sign or buy; `sponsored_evaluator` evaluates for a decision-maker; `none` has no say. A job title alone is not authority |
| Process | `manual` = spreadsheets/WhatsApp/paper; `unsatisfied_crm` = uses a CRM with a stated gap; `satisfied_crm` = happy with their CRM |

## Freeze (once 100+ are labelled, before any training)

```powershell
.venv\Scripts\python.exe slm\freeze_eval.py
git add slm/eval; git commit -m "Freeze hand-labelled evaluation set"
```
After freezing, the tool refuses edits. Never re-freeze; a new set gets a new, separately dated file.
