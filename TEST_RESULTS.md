# Local verification — 24 September 2026

Target: user-designated test CRM at `https://doit.leadrat.info/login`.
Host website: `http://localhost:8011`; backend/widget: `http://localhost:8010`.

## Automated checks

- 10 pytest tests passed: consent/decline routing, score 40 override, unknown ranges, plan schemas, ownership tokens, origin enforcement, single-session capacity, failure reporting, cancellation, hosted-call budget, low reasoning and basic redaction.
- Browser regression fixture passed: when both the sidebar and toolbar show Add Lead, the toolbar control is selected and the sidebar link is not clicked.
- Frontend checks passed with stub APIs: login-required state, chat, stop/end, replay, autoplay failure/fallback, keyboard focus and mobile/tablet layouts. These are separate from the real CRM evidence below.
- Standalone neural speech smoke test generated 30,096 audio bytes.

## Actual CRM / actual model checks

| Check | Result |
|---|---|
| Login with Windows real device location | Passed; normal CRM login, no fabricated coordinates |
| Host HTML embeds independently hosted widget | Passed |
| Live Leads screen displayed | Passed |
| “Could you take me to the place where our projects are managed?” | GPT-6 Luna, low selected Projects; actual navigation verified |
| Tasks module | Actual navigation verified |
| Add Lead | Initial duplicate-control failure was fixed; retest opened actual form and observed name/email inputs |
| Return from untouched Add Lead form to Leads | Passed; no record saved |
| Bulk Upload | Actual entry screen verified; no file uploaded |
| Unsupported payroll/tax question | Refused without inventing a workflow |
| “Do not contact me or follow up” | `graceful_close`; no handoff |
| Neural reply narration | MP3 playback produced a real browser `playing` event |
| JavaScript page errors during live test | None |

First hosted paraphrase check used 508 input + 34 output tokens. Subsequent tests used the same low-effort, bounded-output configuration. Exact shortcut requests make no paid model call. This is test evidence, not a latency benchmark or cost projection.

`artifacts/live-test-results.json` records the broader run including the initial Add Lead failure. `artifacts/live-form-results.json` records the successful post-fix form retest. `live-add-lead.png`, `live-leads.png` and `live-projects.png` are local screenshots of the actual test CRM. These may contain sandbox records and should not be published.

## Not verified or not implemented

No load test, public hosting, multi-user isolation deployment, noVNC transport, microphone STT, local Kokoro installation, full-product RAG, trained SLM qualification or sales handoff delivery is claimed. Properties and Dashboard have bounded navigation adapters but were not included in this live run. The updated Lead checks below supersede the earlier nested-workflow limitation. Remaining specialised subflows still require implementation and live verification.

The backend and test website remain running for local inspection. Only one session is supported; use the already-open Chrome test window, or end its session before starting another. Browser sessions expire after 15 minutes without a new interaction or 30 minutes total.

## Lead expansion and popup verification

- 23 automated tests pass, including real Chrome popup fixtures. Yes/Delete/Override/Save/Discard are not approved by the generic popup handler. Unknown OK buttons stop safely.
- Actual CRM: status editor, notes, history, documents, reassignment controls, meeting scheduling, site-visit scheduling, search, advanced filters, bulk selection entry, Source and Add Lead screens were observed successfully. Nothing was saved, sent, uploaded or deleted.
- Actual WhatsApp: provider chooser selects the available Personal WhatsApp option and opens the composer. Explicit Chat/API topics are separate capabilities, but their live account-specific flows are not certified.
- Actual consecutive website test: status → email prerequisite notice → WhatsApp composer → meeting schedule → notes. The WhatsApp-to-meeting and meeting-to-notes transitions succeeded. Missing-email fallback remains separately reported; no fake address is inserted.
- First observed audio starts on measured turns: 3034 ms, 3384 ms and 2543 ms. These are individual local test samples, not percentile guarantees. Turns with null first_audio_ms ended before the next playing event and were interrupted by the automated next question; they are not proof of instant playback.
- Voice preparation now uses short clips, concurrent lookahead and bounded per-session caching. Chat updates no longer wait on screenshot completion. Neural voice still depends on a network service.

Evidence: `artifacts/lead-live-checks.json`, `artifacts/lead-communication-checks.json`, `artifacts/lead-widget-final.json`. Earlier failures are retained as evidence and are not overwritten with fabricated passing results.

Limits: this is source-backed topic coverage, not 100% completed Lead automation. Bulk actions currently show the selection entry, not all nested bulk forms. Booking, appointment completion, matching properties, flags, pool operations, archive/restore and calls have explanations/overview boundaries; they are not executed. Organisation-specific custom forms and unrecognised popups stop with an explanation. No claim of a fully trained or fully autonomous CRM operator is made.

### Final popup retest

The missing-email flow now checks a bounded set of available sample leads, then opens Edit Lead and highlights Email when all checked samples lack an address. The final live result is `overview_only`, with no error and no claim that the email composer opened. No address was invented or saved. The subsequent WhatsApp → meeting → notes sequence passed without a blocking popup. Measured first audio in this final sequence ranged from 2280 to 4356 ms; full UI operations ranged from 5992 to 14840 ms for those latter four turns. These measurements do not meet an instant-response guarantee.

## Bug-fix round — 28 September 2026

Reported: no voice for replies; the demo also opened in an extra, flickering Chrome window instead of only the popup (CRM left, chat right); several other issues.

Causes found and fixed:

- **Extra Chrome window / flicker:** the demo browser ran with `HEADLESS=false`. It now runs hidden by default and appears only as frames in the popup. Login is automatic with operator credentials or reused from `.browser/crm-state.json` (`./login.ps1` for a manual sign-in).
- **Popup flicker:** the chat list was rebuilt on every change, which reset the scroll, and the screen image was hidden and shown on transient sign-in misses. Chat bubbles are now appended, frames are decoded before they swap, and sign-in state is debounced (a page mid-navigation no longer switches the session to "login required" or "error").
- **Voice:** voice started off; a lost browser-speech `onend` event could stall all later replies; a silent unlock clip could interrupt a playing reply. Voice is now on by default with one reusable player, a per-clip watchdog and a tap-to-resume when sound is blocked. One bubble per reply (it was split into several).
- **Planner:** the small model returned `demo=false` for "where do I see my projects" (nothing shown) and needed about 20 s for a first question. Beacon now demonstrates unless the visitor asks for an explanation only, preloads the model and its catalogue prompt, understands more Hinglish forms, and falls back to reviewed catalogue keywords when the model is unavailable.
- **Blocked sessions:** a closed tab could block new sessions for 15 minutes; a session silent for 30 s is now reclaimed.

Verification:

- 40 pytest tests pass (17 new: greetings, Hinglish shortcuts, show-by-default, keyword fallback, budget past limit, one bubble with voice parts, debounced sign-in, re-login, abandoned-session reclaim). The popup browser test now runs headless.
- End to end against a local **fake CRM fixture** (login form + left nav + routes; not the real CRM): hidden browser signed in automatically, saved the login, and the next session started signed in (1.9 s) with no credentials. A waiting session picked up a login saved mid-session in about 0.5 s. A wrong password stopped with a message and saved nothing. The popup streamed 188–239 frames per run with zero blank frames, and every neural reply played in order (browser speech used 0 times). With neural voice disabled, all replies fell back to browser speech without stalling.
- **Real CRM (`doit.leadrat.info`):** the hidden browser loaded the login page in 2.3 s and found the username, password and Log In controls. No sign-in was attempted (no credentials in this run), so real-CRM login, lead walkthroughs and live frames after this change are **not yet verified**.
- Local planner: first question after load took 19.7 s before the prompt warm-up; later questions took about 2.4 s. These are single samples, not a latency guarantee.

## Talk mode and popup layout — 28 September 2026

Reported: the text box was not visible in the popup; visitors should be able to both type and speak.

- **Cause of the hidden text box:** the live CRM image took its height from its width, and the grid row grew to fit it, pushing the chat input below the popup at 125% zoom or on shorter windows. The row is now fixed to the popup height and the image is fitted inside it. Verified in a browser at 1473×700 (the reported window at 125% zoom), 1280×620 with walkthrough activity visible, and 1920×1000: the text box, 🎤, send and End session were inside the popup each time.
- **Talk mode**, with a scripted stand-in for the browser's speech recognition (real microphone recognition cannot run in automated headless Chrome): two spoken questions were transcribed into the box, auto-sent and answered with voice. Listening restarted only after each spoken reply ended (0 starts while audio played), and talk mode paused after two silences.
- **Real microphone speech recognition was not tested automatically;** it needs a person speaking in Chrome or Edge.
- 45 pytest tests pass (5 new: Hindi Devanagari shortcuts, greeting and opt-out).

## Continuous listening and interruption — 28 September 2026

Requested: listen all the time; if the visitor says something while Beacon is speaking, stop at once and do the new request.

Browser checks with a scripted speech-recognition stand-in driven step by step (the real microphone cannot run in automated headless Chrome):

| Check | Result |
|---|---|
| Spoken question sent after a pause | Passed (sent 0.8 s after the final words, visible in chat at 1.3 s) |
| Beacon's own sentence picked up by the mic | Ignored; voice kept playing |
| Visitor speaks over Beacon ("which projects have units available", which shares a phrase with the reply) | Voice stopped within 300 ms of the interim words; question sent |
| Visitor speaks while a demonstration runs | Running request cancelled; new request answered |
| "stop" while Beacon speaks | Voice silenced; nothing sent |
| Browser ends recognition three times | Restarted each time; still hears afterwards |
| Mic turned off | No further restarts |

Backend: 46 pytest tests pass, including an interrupting turn that cancels a running demonstration (409 without `interrupt`, 202 with it).

Not verified: real microphone recognition quality, echo leakage from loud speakers, and the echo-cancelled track path (it needs a newer Chrome with a real microphone).

## Grounded Q&A from the company handbook — 28 September 2026

Source: FLOE Leadrat Pre-Sales Product Knowledge Handbook v0.2 (company-provided, 29 pages, 13 modules), indexed as 139 chunks.

| Mode | Answerable answered, citing the expected module | Unanswerable refused | p50 |
|---|---|---|---|
| `llm` (OpenAI, excerpts only, must cite) | 30 / 30 | 20 / 20 (100%) | 2.27 s |
| `extractive` (no model) | 20 / 30 | 18 / 20 (90%) | < 1 ms |

The unanswerable set covers pricing, trials, integrations (Salesforce, HubSpot/Zapier, portal list), certification, hosting, SLA, payroll/GST, post-sales payments, competitors, discounts, support hours, offline mobile, refunds, API limits and a prompt-injection request.

Limits: I wrote these 50 questions and tuned retrieval while running them, so they are a development set, not a held-out test; a set written by someone else should be the final measurement. "Expected module" is an automatic proxy: answer correctness still needs a person to read `eval/results/groundedness-llm.json`. The two extractive refusal misses (portal list, support hours) show why the model verifier is used when available.

### Handbook coverage audit

All 29 pages produce chunks; each of the 13 modules has its 6 sections (purpose, feature catalogue, operating/setup flow, rules, troubleshooting, response guidance) plus the handbook guidance pages. Of 1,244 distinct words in the PDF, 47 are in no chunk: module numbers and section headings (kept as chunk labels), removed table headers, and words that appear only in the excluded "Questions FLOE should be able to answer" lists. Their answers exist elsewhere in the module; synonyms were added for "outdated", "database", "move" and "deactivate". Eval results were unchanged after the audit (llm 30/30 and 20/20; extractive 20/30 and 18/20).

Chat-path fix found in the audit: a question that also triggers a screen demo lost its handbook answer when the demo could not run, and Hinglish questions with the question word mid-sentence ("… kyun hai") were not recognised. The handbook answer is now given first and kept when the demo fails.

## Demo readiness check — 1 October 2026

82 automated tests passed after fixes to natural greetings, visible login detection, expired-login screen status, and duplicate-message prevention on request retries. JavaScript syntax check passed.

Live browser checks passed: updated CRM sign-in, automatic login recovery, Leads, Projects, Tasks, Dashboard, and opening the Add Lead form without saving. Earlier checks confirmed lead-source explanations, refusal to invent pricing, and refusal to delete CRM data. Voice generation produced audio; after enabling Voice on, the widget displayed Speaking during the form explanation.

Limits: real microphone recognition and actual speaker audibility were not independently verified. These are demo-flow checks, not complete production acceptance or load testing. The new Kaggle adapter remains separate from the live application; these results do not evaluate it. One earlier chat timeout caused a duplicate on retry; request IDs now prevent the same accepted request being processed twice, covered by an automated test. Intermittent latency itself is not claimed resolved.

Detailed record: artifacts/demo-checks-2026-10-01.json. Screenshot: artifacts/demo-voice-on.png. No credentials are included in these records.

## Feature explanations and customer JSON — 1 October 2026

Current application uses the hosted model; the Kaggle adapter is not connected. All 30 feature questions covering 13 handbook modules passed the expected-source check, and review found the saved replies consistent with the cited documentation. Ten unsupported questions were refused. This is a small development set, not a general accuracy claim. Some replies still use terms such as tenant and mapping.

Initial customer extraction frequently rejected model JSON and fell back to incomplete rules. Fixed by using facts-only extraction with a strict hosted response schema and computing scores/routes locally. Distinct private contact placeholders now preserve corrections and withdrawals without exposing contact values to the hosted service. Trailing email punctuation is excluded. A final explicit refusal overrides a stale follow-up decision and clears consent.

Retest: 13/13 synthetic customer scenarios passed all 51 selected checks. An additional real session API check passed name, team size, monthly leads, no consent, no delivery, and hosted-source checks. These are selected-field assertions, not full semantic grading of every output. No handoff was delivered. The full unit suite passed 85 tests before the last decline guard; 33 affected tests passed afterward, including the new guard regression.

Evidence files: artifacts/acceptance-summary-2026-10-01.json; artifacts/acceptance-2026-10-01.json (initial results); artifacts/acceptance-2026-10-01-more-features.json; artifacts/acceptance-2026-10-01-fixed.json (final customer results); artifacts/live-customer-check-2026-10-01.json. Example qualification and undelivered handoff JSON are saved separately. Backend refreshed and demo left ready with Voice on.


## Latest adapter application checks — 1 October 2026

This section supersedes the earlier hosted-model deployment status. The v4 adapter is active locally, with its published weight hash verified. Application health reports local mode and no external LLM calls. The backend was refreshed after the final validation fixes. The comparison workbook was completed and delivered before switching the application; its raw benchmark results remain unchanged.

93 automated tests passed, with seven dependency/Windows pipe-cleanup warnings. Application validation now preserves explicit customer names, avoids using a name as a job title or assuming ownership, and distinguishes absent permission from an explicit refusal. These are application fixes, not changes to the trained weights or raw comparison scores.

After voice generation stopped, NVIDIA reported only the Beacon model process, 0% idle GPU utilization, 1433 MiB used and 2530 MiB free. A real model retest returned Neha, corrected team size 8, consent false and human review correctly, in 89.42 seconds (artifacts/local-v4-gpu-free-final-validated.json). Prior warm checks took 33.91 and 26.52 seconds; response time is variable and remains a limitation. Earlier cold retries were slower. These selected checks are not overall accuracy or production-readiness evidence.

The current handbook mode answered 23/30 supported development questions with the expected source and refused 20/20 unsupported questions; seven supported questions still received a safe refusal. These automatic source checks do not establish semantic correctness of every answer. Evidence: artifacts/local-handbook-tests.json. Real speaker audibility and microphone recognition remain unverified. Public rollout is not recommended until latency and independent answer review are addressed.


## Demo and full handbook check — 4 October 2026

Read all 29 pages of the supplied v0.2 PDF, verified identical to the installed handbook, and inventoried all 70 listed questions across 13 modules. Initial extractive answers included irrelevant excerpts despite source-module matches. Added 70 reviewed answers with source pages and conservative exact-normalized matching, plus a reviewed response for the suggested lead-source question. These are authored handbook guidance, not trained-model predictions or a held-out accuracy measurement. Different wording still uses existing retrieval.

Submitted all 70 questions through the actual widget. All reviewed answers observed; 25 questions opened relevant workspaces/controls, 45 explicitly reported explanation-only support. Full procedures were not executed and no CRM records were saved. Fixed incorrect module substitution and a reproducible filter-sheet navigation failure; Filter then Leads passed on retest. Voice generation succeeded for every speech part of all 70 answers. Physical speaker audibility and microphone recognition remain unverified.

13 synthetic customer scenarios passed 51 selected-field checks after fixing delayed demo timing, explicit email withdrawal and Hinglish introductions. Three failing cases were rerun through the real model. 12 final scenarios used the SLM; one used conservative rules fallback and is not counted as model success. No real sales delivery attempted. Payload scenario product areas were mapping fixtures, not click telemetry. Separate live API test passed all 8 assertions, including current-model source and actual Leads-area tracking, in 37.48 seconds.

105 automated checks passed (7 dependency/Windows cleanup warnings). Response latency in customer scenarios remained approximately 26–127 seconds including contention. During startup only ~0.5–0.7 GB system RAM was free. Recommended: supervised demo of verified scope, not a claim that all product workflows or arbitrary paraphrases are reliable. Previous training Excel is unchanged.

Evidence: artifacts/pdf-questions-2026-10-04.json (before); artifacts/pdf-questions-final-2026-10-04.json; artifacts/pdf-ui-2026-10-04.json (all attempts, including failure and retest); artifacts/pdf-voice-2026-10-04.json; artifacts/customers-2026-10-04.json; artifacts/customers-retest-2026-10-04.json; artifacts/customers-final-2026-10-04.json; artifacts/live-demo-final-2026-10-04.json. Human-readable report: outputs/demo-readiness-2026-10-04/Beacon_Demo_Checks.html.

## 2026-10-06: confirmed lead creation and connection/speech fixes
- Added a name -> international phone -> optional email -> displayed review -> explicit confirmation flow for creating one lead through the test CRM UI. Repeated confirmation after an uncertain save cannot submit again; changed forms require a new review. Creation turns are excluded from visitor sales qualification.
- Live CRM created two clearly marked synthetic leads: Beacon Test 20261006 Creation Check (5299596d-9042-46aa-aae0-d20416fcee49) and Beacon Test 20261006 Final Check (4ff56957-09c2-4447-9bf9-370953f319c0). Both received succeeded=true; the first was independently found by exact name in Leads. The final conversation reported success correctly. No existing records were deleted.
- Background local-model startup; requirements installation cached by file hash; session polls no longer wait for CRM login refresh. Observed workspace startup 3.94 seconds and maximum poll duration 1.063 seconds in one live run; these are measurements, not latency guarantees.
- Speech defaults to an editable preview; auto-send is optional, with a longer pause. Browser test injects recognition events and verifies preview/edit/manual send/auto-send; actual acoustic transcription accuracy was not measured.
- Excel-only reply is recorded as tooling and prompts for the actual difficulty; late business-type replies are retained.
- Validation: 208 automated tests passed, 8 cleanup/dependency warnings. JS syntax check passed. Evidence: artifacts/lead-create-final-2026-10-06.json and artifacts/fixes-2026-10-06-live.json. Existing unsupported walkthrough coverage is unchanged.

## 2026-10-06: interactive latency optimization
- Product-only navigation and greetings no longer start sales extraction; customer facts still schedule trained-model extraction after a 600 ms debounce. Existing extraction is not cancelled by pure navigation.
- Handbook index warmed in the background, verified Leads workspace reused, idle/busy polling changed from 700/150 ms to 300/100 ms. Shortened duplicate Add Lead narration. Whisper experiment stopped on request; no Whisper STT integration enabled.
- 211 automated tests passed (5 cleanup/dependency warnings). Live API smoke after restart: workspace ready 3.687 s; text first reply 0.015-0.031 s for hi/Show Leads/Show Tasks, excluding browser polling and audio; completed Leads demos 0.203/0.234 s; Tasks 0.656 s. Not an end-to-end spoken latency guarantee. Earlier baseline Site Visit test could not complete because that session's lead list had no visible records; no overall before/after percentage claimed.
- Evidence: artifacts/performance-after.json, artifacts/navigation-after.json, artifacts/performance-tests-2026-10-06.log.
## Preview startup — 2026-10-06

- Server now prepares one fresh CRM browser before a visitor starts. It is handed to one session only; ending that session prepares a new browser. No previous visitor's screenshot or browser is reused.
- Prepared sessions return ready immediately after checking sign-in. Voice setup runs independently of preview rendering.
- Full suite: **216 passed, 3 warnings** (dependency/Windows cleanup warnings). JavaScript syntax check passed. Regression checks include failed/cancelled warm-up cleanup and a stalled voice setup that must not block preview requests.
- Actual Chrome tests against an isolated test service using the same CRM: first visible preview at **4.551 s, 0.365 s, 1.006 s** from widget navigation. The last two session creation requests took **79 ms and 579 ms**. These samples are not a guarantee; cold preparation and CRM/network delays can still take several seconds.
- Latest timing: `artifacts/preview-timing-2026-10-06.json`; screenshot: `artifacts/preview-ready-2026-10-06.png`; test log: `artifacts/preview-tests-2026-10-06.log`. Test service stopped; primary Beacon service remains running with the change.
# Latest live validation — 2026-10-06

The new context-driven candidate is **not demo-ready**. Five direct latest-v4 adapter calls returned truncated results at 120–123 seconds. A selected seven-case context test timed out; visible `Show leads` and `I am a developer` turns both fell back after about 27 seconds, with no requested action recorded. The actual CRM preview was visible. Main server was not switched to this candidate.

Full application checks: 120 passed (2 Windows cleanup warnings); final focused checks after additional changes: 28 passed. These are overlapping contract/regression checks, not model accuracy. Historical report percentages above are not replaced by these timeout results. With the other GPU process finished, the adapter recheck remained incomplete at 120.84 seconds; after restarting Beacon's model runtime it returned the explicit deadline error at 120.89 seconds. Full evidence and limitations: [live check](docs/LIVE_CHECK_2026-10-06.md).


## 2026-10-06 — final context-engine follow-up

- Main build now uses Qwen3-4B-Instruct-2507 Q4_K_M for conversation decisions and the unchanged current Beacon v4 adapter on Qwen2.5-1.5B for qualification. No hosted LLM was enabled.
- Real diagnostic decisions: 22/22 selected cases passed. These prompts were used during development; this is not held-out general accuracy.
- Visible main website: 11-turn conversation, verified Leads/Projects navigation, final checked customer fields and consent refusal passed. Preview 3.339 seconds; median reply 15.199 seconds; background v4 extraction about 52 seconds.
- Final narrow unsupported-job-level guard was verified separately against the captured result and focused tests, then loaded into the running server.
- Full suite 141 passed with five Windows subprocess-cleanup warnings; subsequent focused suite 34 passed (overlapping). No change to historical training percentages/workbooks.
- Local demonstration only: latency, PostgreSQL deployment, multi-user operation and full live handbook/voice coverage remain unapproved. See [detailed evidence and limitations](docs/LIVE_CHECK_2026-10-06.md).
