# Beacon live check — 6 October 2026

**Historical initial result — superseded by the later follow-ups below.** Initially this build was not ready for a reliable manager demo. The CRM preview works, but the new conversation flow and the trained model's complete customer result did not pass the live checks below. This is a selected diagnostic test, not a claim that every possible question was tested.

**Later runtime follow-up:** FP16 now produces complete adapter results in selected cases; the context-selection model still fails. The original timeout evidence below is retained as the before-change record. See the follow-up section at the end.

## What was actually running

- The running customer-extraction service loaded the latest v4 adapter. Its file fingerprint matched `slm/current_release.json`: `f1d618ed1152e2cb8443bda4e3316e6f5a704c4cb3fa6e8160bbf5e3afc1d99f`.
- Customer extraction uses the trained `beacon-v4` adapter. Demo selection uses the separate local Qwen base model. The trained sales adapter is not the demo-selection model.
- No external language-model calls were enabled. No test sales handoff was delivered and no customer records were created by these checks.
- The new conversation flow was tested separately on port 8013. The main application on port 8010 was not switched to the failed candidate.

## Conversation in the visible application

The test browser connected to the real test CRM. The page became usable after 3.507 seconds; this is the text/session readiness measurement, not time to the first preview image. The CRM Leads screen was visible in the final screenshot.

| What I asked | What Beacon replied | Time | Result |
|---|---|---:|---|
| Show leads | “I could not reliably understand that request. Please tell me which feature you want to explore.” | 26.509 seconds | Failed: no requested demo action was recorded. The pre-existing Leads screen is not evidence that this request succeeded. |
| I am a developer | Same fallback reply | 27.270 seconds | Failed: the business detail was not accepted and the discovery conversation did not progress. |

After two consecutive failures, dependent follow-up steps were not counted as tested. A separate seven-case real-model check also timed out on lead management, business type, team size, monthly lead count, manual work, another CRM, and changing to Projects. These are availability failures, not an accuracy score.

The earlier attempt on the main website could not complete a new conversation; a subsequent session request returned a capacity conflict. This was not counted as a successful main-site conversation test.

## Direct checks of the trained adapter

These calls used the actual training prompt and actual adapter, with strict checking before application corrections or fallback rules. Expected answers were specified in advance.

| Scenario and supplied conversation | Expected result | Actual outcome |
|---|---|---|
| “I am a property developer with 30 sales agents and 2000 new leads per month. We use Excel manually and miss follow-ups. I decide on the CRM purchase and want it within 30 days. I have not agreed to sales contact.” | Developer; 30 agents; 2,000 monthly leads; manual process; purchase decision-maker; within 30 days; no contact permission. | Incomplete result after 123.08 seconds. The partial text also called the visitor an evaluator and omitted the stated timing. Not usable. |
| Asked business type, team size, monthly leads and current tool; replies: “developer”, “300”, “100k”, “Excel”. | Developer; 300 agents; 100,000 monthly leads; manual process; no inferred contact permission. | Incomplete result after 122.44 seconds. Not usable. |
| “We are a brokerage with 300 sales agents and 5000 monthly leads.” Then: “Correction: 30 sales agents and 2000 monthly leads. My name is Demo Person.” | Replace old counts with 30 and 2,000; retain the explicitly stated name. | Incomplete result after 120.58 seconds. Partial text contained corrected counts but omitted the name. Not usable. |
| “We are a developer. Yes, sales may contact me at demo@example.invalid.” Then: “Do not contact me. Remove my email.” | Withdraw permission, remove email and close the contact request. | Incomplete result after 120.62 seconds. Not usable. |
| “How can a developer with 300 agents manage 100k leads? This is just a hypothetical question, not my business.” | Do not save hypothetical figures as this visitor's own business facts. | Incomplete result after 120.11 seconds. Not usable. |

**All five direct calls failed to produce a complete usable result within the runtime deadline. This must not be reported as “0% model accuracy”: output truncation prevented a valid full-answer accuracy measurement.** Historical training-report percentages remain separate and were not changed.

The YouTube process was using the GPU during the initial tests and was left running as requested. After it finished by itself, the first adapter case was repeated: it still returned incomplete output after 120.84 seconds. Other-process GPU contention is therefore not a sufficient explanation on its own.

A fresh restart of Beacon's own model service was also checked. The same case reached the deadline after **120.89 seconds** and correctly returned an explicit timeout with the new handling. Restarting did not resolve the generation-speed blocker. The model service remains running with the verified latest adapter; the isolated test web server was stopped.

## Fixes and verification

- A slow CRM sign-in check can no longer hold the prepared-session response indefinitely. The browser check continues in the background and the visitor receives session ownership promptly.
- Health checking no longer probes Ollama when the selected provider is local. New health fields distinguish the conversation engine, storage backend and knowledge readiness.
- Model unavailability now gets a retry message rather than incorrectly asking the user which feature they meant.
- A local generation stopped by its time limit now returns an explicit timeout rather than presenting a partial response as successful. This also prevents repeating the same long request as a formatting retry.
- The embedding model is pinned to a specific revision for reproducibility.
- Full application suite: **120 passed**, with two Windows subprocess cleanup warnings. After the final changes, **28 focused tests passed**. These overlap; they must not be added into one count or used as language-model accuracy.

The new flow's persistence used SQLite development storage. PostgreSQL/Docker is not verified working. Semantic-index warming was disabled on the isolated live server to avoid adding RAM pressure; supported feature facts were still available. Full retrieval coverage, real microphone transcription, real audible playback, all handbook demos, and production readiness were not verified by this run.

## Required before approval

1. Resolve generation latency and incomplete output with the actual adapter under the intended hardware workload.
2. Pass real conversations for short answers, corrections, topic changes and the previous customer examples using the actual demo-selection model.
3. Verify that the resulting answer, observed CRM action, customer facts and contact permission agree in the same session.
4. Repeat the handbook/demo and voice checks on the passing build before making any wider readiness claim.

## Evidence

- [Direct adapter questions, raw outputs and expected values](../artifacts/live-adapter-check-2026-10-06.json)
- [Recheck after the other GPU process finished](../artifacts/live-adapter-free-gpu-recheck.json)
- [Fresh-runtime comparison](../artifacts/live-adapter-fresh-runtime.json)
- [Visible conversation and recorded action results](../artifacts/live-context-isolated-2026-10-06.json)
- [Visible application screenshot](../artifacts/live-context-isolated-2026-10-06.png)
- [Full regression log](../artifacts/live-check-all-tests.log)
- [Final focused checks](../artifacts/live-check-final-targeted.log)

## Follow-up: precision and workload comparison

The old automatic memory threshold required 3.6 GiB free after CUDA initialization. This 4 GB GPU reported approximately 3300 MiB free, so it always selected NF4. An explicit FP16 experiment loaded the same adapter successfully, with the same weight fingerprint, without retraining or downloading another model.

| Actual adapter scenario | Earlier NF4 result | FP16 result |
|---|---|---|
| Complete customer | Truncated at 123.08 seconds; repeat also failed | Complete in 27.00 seconds; repeat 33.30 seconds. Raw score was 80 instead of 90 and the owner title was unsupported. Existing application validation corrected both. |
| Short contextual replies, including 300 / 100k / Excel | Truncated at 122.44 seconds | Complete in 62.73 seconds; selected expected fields and raw arithmetic passed. |
| Corrected team/lead counts and stated name | Truncated at 120.58 seconds | Complete in 38.09 seconds. Raw name was missing and arithmetic disagreed; existing validation restored the explicit name and recalculated scores. |

The latter benchmark overlapped a newly started YouTube GPU job. It is therefore not a controlled overall speed comparison. Remaining permission/hypothetical scenarios were not completed in this run. All three captured results were replayed through the actual qualification-validation functions, with external calls mocked; the specified expected-field assertions passed. This is a pipeline regression check using real recorded outputs, not a new independent model evaluation or proof of universal correctness.

Auto selection now permits FP16 at 3200 MiB free or above for this fixed 1.5B deployment, with a lower-memory mode retained when resources are limited. `BEACON_MODEL_PRECISION` can explicitly select `float16`, `nf4-float16`, or `auto`. This is not a latency guarantee when other GPU applications start later.

With FP16, the seven-case real context-model evaluation no longer timed out, but **all seven still failed decision validation/correctness** (approximately 3–11 seconds). The output invented fields/evidence or chose invalid categories. Narrow prompt experiments were also insufficient and were not put into the application. This separates the runtime bottleneck from the remaining conversation-understanding problem; the sales adapter should not be retrained as a substitute for fixing the separate planner.

Final focused verification: **29 passed** (overlaps earlier test counts), Python compilation passed and `git diff --check` passed. Main web application was not switched to the failing graph candidate. The active model service uses FP16 and the same latest adapter.

Additional evidence: [first FP16 comparison](../artifacts/live-adapter-fp16-first.json), [partial three-case FP16 run](../artifacts/live-adapter-fp16-all.json), [application validation replay](../artifacts/live-adapter-fp16-application-replay.json), [real context results](../artifacts/context-fp16-smoke.json), [focused regression log](../artifacts/runtime-fix-regression-final.log).


## Latest follow-up: separate conversation model and accepted customer facts

The main website now uses the local Qwen3-4B-Instruct-2507 Q4_K_M conversation model through LangGraph. The latest trained Beacon v4 adapter is unchanged on its original Qwen2.5-1.5B base, with the same fingerprint above. The rejected 2B trial download was removed. No OpenAI/GPT Luna inference was implemented or used. Both local model transports reject non-loopback endpoints.

### Decision checks

The final expanded diagnostic suite passed **22 of 22 selected cases**, with a median decision time of **8.98 seconds** on this laptop. It includes the user's misspelling, short numeric answers, corrections, switching to Projects while a monthly-lead question is pending, accepting a suggested demo, explicit explanation-only requests, unknown functionality, and Excel as an answer to a customer question. These are development regression cases used to improve the prompts, not a held-out estimate of customer accuracy. Earlier passing suites missed the live Excel failure; that failure and its follow-up are preserved in the evidence.

The test for `excels` accepts it as the visitor's current tool. It does not manufacture a specific pain such as missed follow-ups. Beacon then asks what is difficult about that tool. The `me` and `now` checks now require the saved field/value, not just a customer-response classification.

Evidence: [final 22 cases and decisions](../artifacts/context-final-verification.json), [earlier main-site Excel failure](../artifacts/live-context-main-acceptance.json). In the earlier live file, the seven narrow checks do not cover the failed Excel conversation and must not be read as an overall passing result.

### Direct adapter stress checks

All five direct FP16 calls returned complete results in 25.53–54.02 seconds. Only **1 of 5 passed the strict raw whole-result check**. Four contained incorrect arithmetic; the correction case omitted an explicitly supplied name, and the hypothetical example was partly mistaken for customer information. This tiny stress set is not overall adapter accuracy and does not replace previous training reports.

The application recalculates scores, applies explicit name/withdrawal corrections, discards outdated background results and limits business counts/contact permission to accepted visitor facts. Product questions and unverified replies are excluded from extraction. While extraction is pending, accepted counts are visible but the result is explicitly marked preliminary and cannot trigger a handoff. The complete local adapter result is still required; application corrections must not be described as improved raw model accuracy.

Evidence: [actual five questions and raw adapter outputs](../artifacts/live-adapter-final-verification.json), [qualification/transport regression](../artifacts/final-qualification-contracts.log).

### Operational changes and remaining limitations

- Preloaded isolated browsers and automatic session startup are retained; used customer sessions are never passed to the next visitor.
- The knowledge index uses pinned, quantized ONNX embeddings instead of loading another PyTorch stack into the web server.
- The sales extraction waits until the interactive conversation is idle, reducing repeated work/cancellation. Browser cleanup continues even if the old page or saved login cannot be read.
- The private conversation-model service checks the configured checkpoint and requires an API key. Re-running verified setup skips unchanged locked runtime files.
- Production approval is still withheld: the local application supports one active session, response latency is material, PostgreSQL/Docker is not operationally verified, and this run does not prove all handbook workflows, real microphone transcription or audible playback. No guarantee about every possible visitor phrasing is justified.
- SQLite is explicitly the development store. The previous Docker repair attempt was blocked by automatic review; no Docker reset or data deletion was performed.
- The full application suite before the final small changes passed 138 tests with five Windows subprocess-cleanup warnings. Later focused checks are separate, overlapping checks, not added to that count. Those warnings were not hidden.

Historical training spreadsheets and their percentages were not changed by this work. No real sales contact was sent by these checks.


## Final main-website verification

The main website was restarted with the new local conversation engine and extraction filtering. A fresh visible-browser run completed **11 conversation turns**. Leads → Projects → Leads navigation was verified; customer answers did not switch to unrelated screens. The final preview showed the loaded Leads table. There were no captured JavaScript errors or unexpected clarification replies in this selected flow.

- First visible preview: **3.339 seconds**; median turn completion: **15.199 seconds**. Ordinary model-backed replies took approximately 14–23 seconds; explicit refusal was immediate. This is not instant or production-load performance.
- The visitor's `23` people and `20k` leads were saved correctly. `excels` was recorded as the current tool, followed by a question about its difficulty. “We miss follow-ups”, “me” and “now” advanced the relevant questions. No redundant current-tool question or “keep the current screen open” acknowledgement was emitted.
- The trained v4 adapter returned the final qualification result in approximately **52 seconds**, in the background. Final checked fields contained developer, 23 people, 20,000 monthly leads, missed follow-ups, Excel/manual process, purchase decision-maker and explicit refusal. No handoff was delivered. The application recalculated the model's incorrect arithmetic.
- Inspection found one additional unsupported raw job-level assumption (`individual_contributor` from “I am a developer”). The final guard clears it to unknown. This last guard was tested against the captured result and in focused tests, then loaded by restarting Beacon; the 11-turn browser run predates this final narrow guard.
- Full application suite: **141 passed**, five Windows subprocess-cleanup warnings. After the job-level guard, **34 focused tests passed**; these overlap and must not be summed. Python compilation, client JavaScript syntax and Git whitespace checks passed. Starting `start.ps1` again reused the running server without the duplicate-port error.

Evidence: [final website conversation and qualification](../artifacts/live-beacon-release-check.json), [visible final screen](../artifacts/live-beacon-release-check.png), [recorded conversation replay after filtering](../artifacts/live-qualification-filtered-replay.json), [last job-level correction replay](../artifacts/final-field-protection-replay.json), [full application checks](../artifacts/final-all-tests.log), [last field checks](../artifacts/final-field-validation.log).

**Current decision:** the reported conversation examples have improved and the updated local build is running. This remains a local demonstration build, not production approval. Significant reply/extraction latency, database deployment validation, multi-user testing, full handbook action coverage and real microphone/audio checks remain. Selected passing questions are not a universal correctness or confidence percentage. The raw adapter still needs application validation.
