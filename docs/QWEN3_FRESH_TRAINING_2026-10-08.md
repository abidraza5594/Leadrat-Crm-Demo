# Fresh Qwen3 fine-tuning — 8 October 2026

The next model starts a new LoRA adapter on **Qwen/Qwen3-4B-Instruct-2507**, pinned to `cdbee75f17c01a7cc42f958dc650907174af0554`. This is fine-tuning a pretrained base, not pretraining a language model from random weights. No Qwen2.5 adapter is loaded or continued. The existing Qwen3 GGUF is inference-only; Kaggle downloads the original base weights for training.

## Data

| Purpose | Training examples |
| --- | ---: |
| Extract customer facts for sales JSON | 10,611 |
| Understand the type of visitor message | 3,411 |
| Select a reviewed demo capability | 1,866 |
| Interpret customer replies and corrections | 1,558 |
| **Total** | **17,446** |

Training languages: 16,596 English, 815 Hinglish, 35 Hindi. There are 2,102 separate development examples and 1,746 test examples. Test messages are not uploaded in the training package. Original datasets and earlier reports remain unchanged; their hashes are recorded in `artifacts/model-retirement-2026-10-08/preserved_files.json`.

The historical qualification examples are reused as facts-only targets. Scores and sales routing remain application calculations, not model arithmetic. New controlled examples cover 38 reviewed feature IDs, numeric shorthand, corrections, tool names, short answers, interruption of discovery, demo offers, refusal to show a demo, unsupported actions and contact refusal. Answers do not contain arbitrary executable selectors.

Exact prompts and phrase families do not overlap between train/development/test. These are predominantly synthetic examples with shared construction patterns; they are not an independent real-customer benchmark. Dataset checks do not imply the trained model will answer every question correctly. The previous benchmark percentages remain historical and must not be relabelled as Qwen3 results.

## Checks performed locally

- All 17,446 training and 2,102 development conversations tokenize with the actual pinned Qwen3 tokenizer.
- Maximum observed length: 1,128 tokens. No targets were truncated.
- Input tokens are excluded from loss; only the intended assistant response is supervised.
- 32 focused dataset/runtime/conversation/backend tests passed, with two pre-existing Windows subprocess-cleanup warnings.
- The full model was not downloaded or trained on this laptop.

## Kaggle package

Files in `outputs/beacon-qwen3-fresh-training`:

- `beacon_qwen3_fresh_17446.ipynb`: small importable notebook.
- `training_source.json.xz`: private input payload with trainer, train/development data and hash manifest.
- `package_manifest.json`: counts and package information.

Keep the notebook and dataset private. Attach the payload as input, enable Internet and a GPU with at least 14 GiB VRAM, and use **Save Version → Save & Run All** to launch a server-side run. The notebook verifies its payload and data hashes, uses 4-bit QLoRA with fresh rank-16 adapter weights, and takes one pass at learning rate 0.00005. It writes checkpoints every 100 optimizer steps. No automatic Hugging Face upload or application deployment occurs.

A nine-hour training budget stops gracefully and exports a clearly labelled PARTIAL adapter if the epoch has not finished. Such a run must not be described as complete. The completed/partial status and epochs completed are in `run_metadata.json`. Training loss is not a response accuracy percentage.

## Old model cleanup status

The old release is marked retired, qualification endpoint settings are cleared, old automatic startup is disabled, and the old continuation entry points fail before downloading weights. The Qwen3 planner and original data/reports remain.

**Local cleanup completed after the user's renewed deletion request:** the nine verified old model/adapter/cache/archive targets were moved to Windows Recycle Bin, and the two identified old service processes were stopped. This is recoverable removal, not permanent disk-space reclamation. The initial permanent-cleanup attempt had been rejected by automatic approval review; the later explicitly requested recoverable cleanup succeeded. The result is recorded in `artifacts/model-retirement-2026-10-08/cleanup-result.json`. The existing remote Hugging Face repository was not modified or deleted.

## Before live deployment

Evaluate the new adapter on the separate tests and fresh conversations; verify customer-field evidence, consent, corrections and feature selection. Then verify actual browser actions and latency. A fine-tune alone does not fix network timeouts, microphone transcription or incorrect CRM selectors. Until this succeeds, Beacon has no activated replacement qualification adapter and any conservative fallback is not a Qwen3 model result.

## Kaggle run record

- Private notebook: https://www.kaggle.com/code/abidrazaansari/beacon-qwen3-fresh-multitask-17k
- Private dataset: https://www.kaggle.com/datasets/abidrazaansari/beacon-qwen3-fresh-training-17446
- Version 1 (356284858) stopped before model training because text packaging normalized Windows CRLF line endings, causing an original-byte checksum mismatch.
- The notebook now restores original bytes only when they match the original manifest hash; checksum checks remain enforced. A Linux-style packaging round-trip test passed.
- Version 2 (356285607) loaded a fresh adapter and reached two optimizer steps, but was cancelled after showing approximately 165 seconds per step. Its precision detection allowed emulated BF16 on T4.
- Version 3 (356289296) uses native-only precision detection: FP16 on T4 and BF16 only on compatible hardware. The six training-specific tests passed, including emulation rejection and an exact check of the embedded trainer source. The existing private data payload is unchanged; the notebook embeds the corrected trainer with a separately verified SHA256 and exports its provenance.
- Version 3 reached its first optimizer step in 37.64 seconds using native FP16. It was then cancelled to enable both allocated T4 GPUs and improve the chance of finishing the entire epoch within the time budget.
- The current notebook uses torchrun distributed training on both T4 GPUs, with gradient accumulation 8 per GPU (effective batch size 16). Each GPU loads the same fresh pretrained base and trains on its data shard. It does not load any cancelled run's adapter. A synchronized time-budget stop prevents one worker from exiting ahead of the other. Only rank 0 exports the final adapter and metadata.
- Live execution state is recorded in the local package status file. Submission does not establish training completion or accuracy.
- Version 4 (356291931) confirmed both GPU workers using native FP16 with effective batch size 16, fresh adapter initialization, and the first three optimizer steps at approximately 18 seconds per step. The early ETA was roughly 5.5 hours; it is an estimate, not a completion guarantee. Run: https://www.kaggle.com/code/abidrazaansari/beacon-qwen3-fresh-multitask-17k?scriptVersionId=356291931
- Final startup check observed 6 of 1,091 optimizer steps and a finite first logged loss of 0.812 with finite gradient norm. Speed was approximately 19 seconds per step. This verifies training is progressing, not that it has completed or achieved a response accuracy. Evidence: `artifacts/qwen3-kaggle-version4-startup.log` and `artifacts/qwen3-kaggle-run.jpg`.

## Verified completion

Version 4 completed successfully on 8 October 2026: 1,091 optimizer steps, one complete epoch on 17,446 training examples; no time-budget stop. Kaggle notebook runtime was 5h 58m 3s. The executed export cell verified the ZIP and produced `beacon_qwen3_new_adapter.zip`. Adapter SHA256: `778b4cea3667da01b25589f08f54c24d363bbf37f5251f75f1a1ed4f2bb33cd2`. Average training loss: 0.02286391682951864. These are training results, not test accuracy. Independent evaluation and live deployment remain pending. Completion evidence and printed metadata are saved locally.


## Download and local inference checks — 8 October 2026

The downloaded ZIP was verified and moved from Downloads into `slm/runs/qwen3-17k-2026-10-08/`. The original adapter is in its `adapter/` folder. Its SHA256 matches the Kaggle export; all 504 tensors contain finite values. ZIP CRC verification passed. The original weights are unchanged.

An isolated local CUDA runtime tested the converted LoRA at scale 1 on the Qwen3-4B-Instruct-2507 Q4_K_M base. This is a compact local deployment check, not a full-precision PEFT benchmark. The application's live configuration was not changed.

Results on 144 deterministic, family-stratified samples from the separate test file:

| Check | Exact matches | Percentage |
| --- | ---: | ---: |
| Message classification | 31/32 | 96.9% |
| Demo selection | 60/64 | 93.8% |
| Customer updates, including exact wording/evidence | 17/24 | 70.8% |
| Complete customer extraction | 24/24 | 100% |

The seven customer-update mismatches preserve core meaning; they are mostly quote length, shorter wording or capitalization differences. The immediate-timeline case can nevertheless fail application validation because its value and evidence differ. Do not present 70.8% as semantic comprehension accuracy. No selected test prompt exactly matches a training prompt, but the synthetic sets share construction patterns and are not an independent customer benchmark.

The existing application decision tests passed 21/22. A separate connected conversation passed 12/13 turns. Six diagnostic cases selected after observed failures passed 2/6; these must not be pooled into general accuracy. Confirmed problems include a monthly-lead statement selecting Bulk Upload, historical activities selecting Notes, general WhatsApp selecting the narrower integrated chat capability, manually being stored as process rather than the pending problem, and an immediate-timeline statement producing a validation clarification. Email selected the general communication feature in one raw case but passed the application replay, showing sensitivity to context/prompts.

Records: `outputs/qwen3-adapter-check-2026-10-08/Beacon_Qwen3_Checks.html`, `results.json`, `conversation_replay.json`, `reviewed_differences.json`, and `verification.json`. These contain actual requests and responses. No CRM clicks, microphone/speech, database persistence or live website operation was verified in this adapter check. Production readiness remains unconfirmed; the new adapter is a candidate, not the active website release.

## Subsequent local activation and contextual answers — 8 October 2026

The preceding sections preserve the results before activation. The same verified adapter is now active in the website as `beacon-qwen3-17k`, served locally with its Qwen3-4B-Instruct-2507 base. Startup verifies hashes, and readiness verifies the loaded base, adapter path and adapter scale. Conversation and qualification use the same service. No hosted OpenAI language model is used.

An initial eight-turn browser test verified Leads, developer/team/monthly-lead conversation, Excel follow-up, the unsaved site-visit scheduling screen, Projects and the Add Lead form. Qualification used the trained model. Evidence is in `outputs/qwen3-live-2026-10-08/website-results.json` and its screenshots. This did not create CRM records or verify every possible workflow.

The user then identified broad feature questions being refused. The old live answer path returned a selected capability's static facts or refused an unknown capability. It has been replaced with contextual semantic handbook retrieval, evidence selection, generated answers and a source-checking pass. The module catalogue is derived from the installed PDF. Exact-wording FAQ lookup is no longer used in that path. Browser actions still use explicit supported tools and observed results.

The installed handbook has 29 pages, 139 indexed passages and 13 main Pre-Sales modules. This does not establish a count of all individual features or complete commercial-product coverage. Generated answers and the source checker are fallible. Earlier exploratory checks also found unsupported claims and timeouts; their records remain under `outputs/qwen3-knowledge-2026-10-08/` and are not counted as passing customer accuracy.

The targeted application-contract suite passed 31 tests. These use mocks for inference and do not measure model accuracy. The browser checks in `outputs/qwen3-knowledge-2026-10-08/final-live-check/website-results.json` exposed a follow-up timeout and slow generation with partial CPU offload. The runtime was subsequently changed to one slot, 4,096 context tokens and all layers on the GPU, with host prompt caching disabled and more compact evidence prompts. Production readiness remains unconfirmed, particularly for response time under load and unsupported or ambiguous requests. Later checks must be identified separately from these failed or superseded runs.

The subsequent all-GPU browser check completed all three questions: the full feature/module list, Leads versus Data Management, and the contextual follow-up "Which one should I use for active enquiries?" The follow-up selected Lead Management and verified the Leads workspace. Observed times were 114.425, 98.947 and 105.028 seconds respectively. This resolves the tested refusal/context cases but is too slow for a smooth live demo. No complete-CRM accuracy percentage is established. The list also repeats module names in its introduction. Results and screenshots are preserved in `outputs/qwen3-knowledge-2026-10-08/gpu-live-check/`, with the readable `Beacon_Context_Checks.html` report. Final health confirmed the trained adapter active, knowledge ready and no external language-model calls.
