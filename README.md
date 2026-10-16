> **8 October 2026 — model migration:** old local Qwen2.5 weights and adapters have been moved to Recycle Bin and their service stopped. The completed 17,446-example Qwen3 adapter is active locally for application testing; remaining model-quality issues are recorded, so this is not production sign-off. See [the migration record](docs/QWEN3_FRESH_TRAINING_2026-10-08.md).

# Beacon — standalone website demo backend

Python backend + an embeddable HTML website widget. The backend owns a hidden, isolated Chrome browser, operates the existing test CRM through its UI, and streams authenticated screen images into the website popup: the live CRM on the left, the chat on the right. No separate Chrome window opens during a demo. No changes to the Angular CRM are required.

## Start on this Windows machine

1. **One time:** open `.env` and fill `BEACON_LOGIN_USER` and `BEACON_LOGIN_PASSWORD` (test CRM account only). `.env` is git-ignored: never commit or share it. Wrap a value containing `#`, `$` or spaces in single quotes.
2. Open PowerShell in `C:\Leadrat AI\Beacon` and run **`./start.ps1`**. It installs application dependencies and starts the Qwen3 conversation model (port 8014), the test website (port 8011) in the background and Beacon (port 8010) in this window, then opens **http://localhost:8011** when ready. Conversation and qualification share the current trained Qwen3 adapter on port 8014; the old service is not started. It asks only for a value that is missing from `.env`.
3. On the website choose **Start exploring**, and the session starts automatically. The hidden demo browser signs in (or reuses the login saved in `.browser/crm-state.json`), and the live CRM appears on the left of the popup with the chat on the right.
4. **Type or speak.** Type in the box, or tap **🎤** once: Beacon then listens all the time. Your words appear in the box as you speak and can be reviewed before sending; automatic sending after a pause is optional. Speak (or type) while Beacon is talking or running a demo and it stops at once and does the new request; say "stop" / "ruko" / "bas" to just silence it. Tap 🎤 again to stop listening. **🗣 English / हिन्दी** picks the language you speak. Headphones work best. Voice is on by default and reads every reply; the **Voice** button turns it off (both remembered per browser). End the session when done; its browser context closes. Project-scoped audit snapshots expire after seven days.
5. **Ctrl+C** stops the website/backend servers. The reusable Qwen3 conversation service stays loaded on port 8014.

Options: `./start.ps1 -NoBrowser` does not open the website. OpenAI/Ollama provider switches have been removed. `./start-test-page.ps1` still runs the website on its own. **Sign in manually** (for example when the account asks for two-factor verification) with `./login.ps1`: it opens a visible Chrome window once, saves the login when the CRM opens, and closes. A session that is already waiting picks the login up automatically. Credentials stay in process memory so the hidden browser can sign in again if the saved login expires. Install Google Chrome first. The servers bind to loopback only.

`HEADLESS=false` in `.env` additionally shows the demo browser as a separate window, for debugging only. `.browser/crm-state.json` contains CRM auth tokens: keep it on this machine and delete it to force a fresh sign-in.

The `.env` on this machine selects the user-designated test URL. `.env.example` is the portable template. Never configure a production account as a public demo.

## Current implementation

- FastAPI session API with random session capability tokens, registered website origins, one active browser, 15-minute interaction-idle timeout and 30-minute maximum lifetime.
- A server-owned Playwright browser executes fixed navigation capabilities; the visitor receives pixels, not CRM credentials or browser-control access.
- Qwen3-4B-Instruct-2507 Q4_K_M with the 8 October 17k multitask adapter selects conversation intent, reviewed demo capabilities and customer facts. The same authenticated local GPU service performs qualification extraction. The old Qwen2.5 service is disabled. Invalid or unavailable extraction still uses the explicit conservative human-review fallback. No hosted LLM fallback or regex demo routing is used. `/api/health` exposes runtime readiness. Earlier architecture and live-verification documents describe their dated test state.
- The trained local model selects a supported demo action and separately generates an answer from retrieved handbook evidence and conversation history. Knowledge is not limited to available demo screens. Navigation must be observed before success is narrated. Missing/ambiguous controls stop the action. There is no unrestricted browser tool available to the model.
- Stop cancels pending inference/action execution. Failed and cancelled steps are distinct from verified steps. Browser controls are fixed in `app/browser.py`; Lead adapters and popup policy are in `app/lead_browser.py` and `app/popups.py`; source-backed explanations are in `app/lead_guides.py` and `knowledge/features.json`.
- Optional neural narration: `TTS_PROVIDER=edge` uses a keyless online test speech connector (not a production availability guarantee). Only issued assistant guide replies are spoken. The browser displays a disclosure and falls back visibly to browser speech if unavailable. `TTS_PROVIDER=local` with `TTS_URL` supports an OpenAI-compatible local Kokoro `/audio/speech` service; Kokoro is not installed in this build.
- Explicit declines route to `graceful_close`, even when the calculated score is 40 or higher. Unknown scoring fields remain null/ranges. The new adapter extracts customer details; invalid or unavailable extraction produces the conservative human-review result. Accepted visitor facts constrain the final JSON, and scores are calculated locally. Handoffs require consent and contact details; the default destination is the local mock receiver.

The Qwen2.5 qualification release is retired. Its local v1/v3/v4 adapters, cached base, release copies and downloaded adapter archives have been moved to Recycle Bin. `slm/current_release.json` identifies the active Qwen3 adapter, its checksums and the historical retirement record. Historical release metadata and evaluation reports are preserved. The remote Hugging Face repository remains historical and is not used by the new training. Use `slm/qwen3/` for the new training pipeline; old training/continuation entry points are disabled.

The v3 adapter was tested directly on 233 synthetic held-out English conversations on Kaggle: 4,693/5,126 field matches (91.6%), 50/233 conversations with all 22 fields matching (21.5%), and 6 incorrect sales handoffs. See the [evaluation workbook](outputs/01a0f0f0-6c7c-7de2-a39a-3465964ea299/Beacon_v3_Evaluation_Report.xlsx) for every expected/actual answer and the scoring limitations. These are normalized reference matches, not independently human-graded customer accuracy. These v3 numbers are historical and do not describe the active Qwen3 adapter.

## Website embedding

```html
<script async src="http://localhost:8010/widget.js"></script>
<button data-beacon-open>Explore Leadrat</button>
```

Serve the host page over HTTP; don't double-click a `file://` page. Register its exact origin in `BEACON_ORIGINS` and restart. Production requires HTTPS, a real deployment origin and the infrastructure below. The test HTML runs on a separate origin (8011) from the backend/widget (8010), demonstrating the embed boundary.

## Location and login

The **hidden demo browser** performs CRM login with the operator's test credentials, or reuses the login saved by `./login.ps1`. The visitor iframe never shows the login form; while the browser is not signed in, the popup shows the operator instructions and no CRM pixels. On this local Windows test machine, `LOCAL_DEVICE_LOCATION=true` reads the real Windows device location with the user's authorization and supplies that real reading to the demo browser in memory. It does not invent coordinates or bypass CRM validation. Windows Location Services must be enabled. If the OS cannot provide a reading, automatic login stops with a location message; sign in once with `./login.ps1` instead. The reading is taken once per server process and reused.

Keep `LOCAL_DEVICE_LOCATION=false` on servers. A public remote browser cannot obtain a visitor's physical location automatically. Deployment needs a CRM-approved sandbox authentication policy/service account; do not reuse a developer's location or password. This local machine's setting is not the production solution.

## Supported scope

| Area | Current browser action |
|---|---|
| Leads | Open and verify list |
| Add Lead | Collect details, review them, require explicit confirmation, then verify creation in the test CRM; never retry an uncertain save |
| Bulk upload | Open entry screen; no file selection/import |
| Projects, Properties, Tasks, Dashboard | Open and verify module |
| Status, site visits and reviewed lead operations | Show supported controls; existing records and appointments are not saved. Unsupported operations are labelled as overview-only |
| Unknown features and unsupported changes | Clarify coverage; no invented controls, deletion, messaging or arbitrary instructions |

This is an executable local vertical slice, **not completion of the full design document**. Remaining work includes deeper verified persona workflows, approved full-product RAG/pgvector ingestion, server-side speech recognition (browser recognition is used now), installed local Kokoro, independently evaluated qualification adapter, consented mock handoff/outbox, load/latency evaluation, and public deployment security.

Windows development uses authenticated JPEG polling (about six frames per second while Beacon navigates, four on a still screen), independently of chat polling. Linux Xvfb/VNC/websockify/noVNC transport and per-session containers are **not yet implemented**. The public architecture in the design document remains the deployment target. The website test harness is vanilla HTML rather than the final React client.

## Testing

```powershell
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe voice-smoke.py
```

Unit tests check decline routing, unknowns, plan validation, token ownership, origin enforcement, capacity, cancellation, action failure, low reasoning, redaction and call budgets. They stub external services and do not replace live CRM tests. Live test results are recorded separately in `TEST_RESULTS.md`. Screenshots in `artifacts/` may contain test CRM data; do not publish them.

## Lead guides and popup handling

The Lead catalogue now separates status changes, scheduling meetings/site visits, notes, history, documents, ownership, email, personal/integrated/API WhatsApp, SMS, sources, filters, search, columns, bulk actions and other source-reviewed topics. This is not a claim that every nested operation is automated. Some topics show only the relevant overview or entry control. See the live verification matrix.

Missing email: cancel the notice, explain the prerequisite and try another visible test lead (bounded to three alternatives). If the checked samples have no address, open Edit Lead and highlight the Email prerequisite without inventing or saving an address; unavailable edit controls stop with an explanation. Communication choosers prefer SMTP for generic email and Personal WhatsApp for generic WhatsApp, falling back only to visible configured choices. Explicit Chat/API requests do not silently choose a different provider.

Source-reviewed confirmation dialogs cancel pending writes; unknown OK buttons are never treated as safe. Save-changes dialogs preserve operator input. The agent may close its own unchanged temporary scheduling selection, using an in-memory form fingerprint to detect intervening edits. Native browser dialogs are dismissed and reported. These rules do not claim support for every organisation-specific popup.

Voice is on by default. Each reply is one chat bubble; its speech is split into short parts with session-local bounded caching, two concurrent synthesis slots and a two-part client lookahead. One reusable audio player is unlocked by the first click, and each clip has a watchdog so a lost browser event cannot stall later replies. If the browser blocks sound, the voice status asks for a tap and resumes. Chat polls independently of screenshots, and screenshots are decoded before they replace the previous frame, so the live screen does not flash. A new question interrupts older narration. Neural first-audio time still depends on the voice network; it is not zero latency. Browser speech (an English-India voice when installed) remains the fallback.

The local model classifies the visitor's request with the pending question, then uses conversation history to select a supported capability. Product questions use handbook retrieval and generated answers; there is no keyword or exact-question fallback in this active path. Short greetings and validated customer acknowledgements still use ordinary UI wording. Beacon demonstrates supported procedures by default unless the visitor asks for explanation only. A session whose widget stops polling for 30 seconds (closed tab, crashed page) is reclaimed so a new visitor is not blocked.

## Speaking to Beacon

The 🎤 button uses the browser's built-in speech recognition (Chrome and Edge; hidden in browsers without it, where typing still works). Chrome sends the microphone audio to Google's speech service; the popup discloses this. The widget iframe is granted the microphone by `allow="microphone"`; the browser asks the visitor for permission the first time. Microphone access requires HTTPS outside `localhost`.

- Talk mode listens continuously, including while Beacon speaks or works, and restarts recognition whenever the browser ends it. Speech is transcribed live into the text box (which keeps anything already typed) and sent after a short pause, so a question spoken with a breath is not split.
- **Interrupting:** words that are not Beacon's own stop its voice at once; the question is then sent with `interrupt`, and the backend cancels the running demonstration (its steps are marked stopped) before starting the new request. Replies to the interrupted question are not read aloud. Typing while Beacon works interrupts the same way. "stop", "wait", "ruko", "bas", "chup" (and the Devanagari forms) only silence Beacon and stop the demonstration.
- **Beacon's own voice:** where the browser's recognition accepts a microphone track (newer Chrome), Beacon passes an echo-cancelled one. In every browser, a transcript whose word pairs mostly repeat what Beacon said in the last few seconds or its current reply is ignored. Speakers at high volume can still leak through; headphones avoid it.
- Hindi recognition returns Devanagari. The conversation model receives the original text; product answers use multilingual handbook retrieval.
- Blocked microphone, missing microphone and offline recognition show a message in the voice status line; typing is unaffected.

## Grounded answers from the company handbook

Put the company-provided handbook PDF in `knowledge/docs/` (internal, git-ignored). The installed v0.2 PDF has 29 pages, indexed as 139 passages across 13 main Pre-Sales modules. These are modules, not a count of individual features or a claim of complete commercial-product coverage. The module inventory is derived from the document, not a hardcoded list of recognised questions.

Each product question is searched across the handbook, with a second contextual search using recent conversation and the selected topic. The trained local model selects evidence IDs and composes an answer from those references. A second local call checks the draft against the selected evidence; one revision is allowed before reporting a checking failure. References and checks are retained in the conversation decision. Quantized multilingual ONNX embeddings are cached locally or in PostgreSQL/pgvector. Demo availability is independent of knowledge availability: a documented feature can be explained without claiming that its screen was demonstrated.

The evidence checker uses the same small model and is not an independent factual guarantee. The current PDF does not establish exact subscription prices or every tenant-specific permission, integration or workflow. Missing evidence must be disclosed rather than guessed. There are no exact-question canned product answers in the active knowledge path; supported browser actions and safety checks remain explicit application code.

Install the pinned files once using `python slm/setup_planner.py` and `python slm/setup_knowledge.py` in the application environment. First-time model downloads need internet; normal local language-model inference does not. `eval/context_engine.py` measures real conversation decisions; unit tests measure application contracts. Neither proves every handbook action works. Some topics have an explanation but no supported demo.

## Current local adapter service

`PLANNER_PROVIDER=local` uses `beacon-qwen3-17k` with the current adapter on port 8014. `QUAL_SLM_URL=http://127.0.0.1:8014/v1` and `QUAL_SLM_MODEL=beacon-qwen3-17k` use that same service. Startup checks the base and adapter hashes; runtime readiness checks the loaded adapter path and scale. `/api/health` reports `trained_adapter_active` and `adapter_release`. The old port 8012 service and Qwen2.5 training entry points stay disabled. Ports 8010, 8011 and 8014 bind only to this machine. Edge voice remains a separate speech service.

The current adapter is active for structured customer facts and conversation/demo decisions. The application calculates scores and routes from validated facts. Qualification errors fall back to conservative rules with a labelled scorer; no hosted model is substituted. The 4 GB GPU runs one inference slot with a 4,096-token context and no host prompt-cache allocation. All model layers run on the GPU; partial CPU offload caused slow generation in testing. Specific handbook questions omit unrelated module overviews, and evidence-ID enums are not duplicated in the text prompt. A cancelled request may finish generation on the GPU before the next request runs.

1 October comparison: 233 original conversations, details 91.6% → 92.4%, follow-up decisions 91.8% → 92.7%; six wrong raw sales referrals remain. On 60 additional prepared examples, details 87.0% → 98.4%. These are reference-match tests, not real-customer reliability. Full manager report: `outputs/01a0f0f0-6c7c-7de2-a39a-3465964ea299/Beacon_Before_After_Training.xlsx`. Preserve the old test record.

The active knowledge path generates and verifies answers locally, so product questions require more inference than the historical extractive path. Latency depends on document context and other workloads on this laptop. Customer qualification runs asynchronously and may time out under contention; its rules fallback is clearly labelled and is not counted as a model success. Historical `DOCS_ANSWER` options do not select the current contextual knowledge path.


## Reviewed handbook questions (4 October 2026)

`knowledge/handbook-faq.json` and `app/handbook_faq.py` preserve the historical reviewed-question implementation. The live contextual answer path no longer calls this exact-wording lookup. The older checks in `outputs/demo-readiness-2026-10-04/Beacon_Demo_Checks.html` describe that earlier version and must not be presented as results for the current Qwen3 model.

## Registration phone field and speech (12 October 2026)

Registration uses `intl-tel-input` 29.5.4 with a searchable country selector, India selected initially, and package-based phone validation. The frontend submits the normalized international number. Package browser assets and flags are served locally from `web/vendor/intl-tel-input`; no CDN or country lookup service is required. To refresh the pinned assets, run `npm ci --ignore-scripts` and then `npm run vendor` from `web/`. The lockfile and MIT license are included.

Current speech configuration: `STT_PROVIDER=soniox` and `TTS_PROVIDER=edge`. Soniox transcribes visitor speech; Microsoft's previous `edge-tts` voice reads replies. Soniox TTS is disabled. Set `SONIOX_API_KEY` only in the untracked `.env` file.

Microphone cleanup (14 October 2026): capture requests mono audio, echo cancellation, native noise suppression and voice isolation where supported. Automatic gain control is disabled to avoid boosting quiet room noise. Before Soniox encoding, a local 48 kHz AudioWorklet applies an 80 Hz high-pass and RNNoise (`@sapphi-red/web-noise-suppressor` 0.4.1); assets are served locally, with no extra audio vendor or paid API. Unsupported/failed processing falls back to the browser-cleaned microphone stream. Start/stop disposes audio tracks and the processing context. This reduces non-speech noise; it does not identify the visitor or reliably reject other nearby speakers. Controlled browser checks covered synthetic noise, a spoken sample, resource cleanup and missing assets; the user's actual microphone/room has not been measured.

Demo recovery checks (14 October 2026): authenticated widget polling uses a 4-second timeout and preserves the current session on transient failures. Turn submissions retry transport errors/502/503/504 with the same request ID, and wait for CRM reconnection without issuing Stop. Closing the tab sends an authenticated keepalive departure request and releases the demo after a 10-second grace period. Reloading within that grace period reattaches using its sessionStorage credential and cancels departure cleanup; an old page's delayed departure cannot close the new page's session. Switching tabs does not send a departure request. Explicit End/Close still ends the session immediately. If the browser cannot send the departure request, 120 seconds without a heartbeat makes the session eligible for cleanup on the next 15-second cleanup pass, without waiting for another visitor. Accepted background lead registration continues independently. Active demos no longer expire solely because they are 30 minutes old; normal idle expiry remains 15 minutes.

Read-only navigation can retry once after a transient timeout or authentication loss, restoring the last verified checkpoint first. A crashed Chromium instance can reopen and restore that checkpoint. CRM recovery is bounded to 45 seconds per attempt and three automatic attempts; Save and other writes are never replayed by this recovery path. Isolated live CRM checks verified the same lead and Notes tab after forced auth expiry (19.609 s), an injected navigation timeout (6.344 s), and closing/reopening Chromium (9.516 s). Browser fault-injection checks verified lost-response deduplication, transient polling failure, reload reattachment, and reconnect without Stop. These are individual measurements, not latency guarantees. A backend process restart or a fully expired/reclaimed Beacon session still creates a new session; durable browser/session restoration across process restarts is not implemented.

Recovery speed update (14 October 2026): confirmed main-frame login redirects, page crashes/closure, and browser disconnects now signal recovery without waiting for the next HTTP poll. Read-only navigation waiting on a broken page is cancelled before one bounded recovery/retry; write operations are excluded. Login waits for the CRM's rendered success/error state instead of a half-second sleep loop, and the extra ten-second saved-login grace wait is removed. An unchanged checkpoint is verified using its document identity, URL, tracked record and local hash of visible text/form values, then reused without reloading. A replacement browser opens the saved URL directly; partial or changed screens still require verified restoration. Raw customer text from the comparison is not persisted or sent to a model.

Latest isolated CRM measurements: navigation timeout recovery **0.203 s** (another run **0.719 s**); browser replacement and same lead/Notes restoration **6.703 s** (another run **6.766 s**); login expiry and restoration **4.547 s with the real device location already cached**. A cold location lookup took **8.125 s**, making that cold login recovery **12.078 s** (another cold run **14.562 s**). Application startup already preloads device location; unavailable/slow location services, CRM/API response times and browser startup can still delay recovery. The timeout measurement injects an error while the verified screen survives; changed-page restoration is intentionally slower. These timings begin at recovery invocation, exclude the injected fault and final widget polling/render, and are observations rather than guarantees. **54 targeted tests passed**, including event interruption, cancellation, checkpoint reuse/reset, session and retry behavior; four existing Windows subprocess cleanup warnings were reported. Latest source was exercised in isolated browsers, not by restarting the existing application server. Detailed timings are in ignored `.state/recovery-speed-2026-10-14.json`.

Edge speech now streams MP3 chunks through the authenticated `/speech?stream=true` endpoint to a MediaSource player, beginning playback before synthesis finishes. Upcoming parts share the existing bounded synthesis cache; replay does not regenerate cached audio. Stop and new questions abort the current browser download/playback. Browsers without MP3 MediaSource support use the complete-clip path. This streams audio for available answer parts, not unfinished model tokens. `edge-tts` is pinned to 7.3.1, which passed the live provider check on 14 October 2026 after 7.2.8 returned HTTP 403. One sample delivered its first audio chunk in 734 ms and completed in 1,844 ms; these are sample provider timings, not an end-to-end latency guarantee.

Visitor onboarding shows the welcome conversation first. Selecting Start my demo or sending a first request opens the contact form. The widget keeps that request and submits it as soon as Beacon accepts validated contact details, while CRM capture runs in the background. Registration calls the separate capture API; it never navigates, fills, or saves in the demo browser. A duplicate lookup can reject an existing number; the visitor can correct the phone and retry. Registration errors appear on the form, without spoken internal save warnings. Inputs stay locked only during a pending save. An uncertain save blocks another submission for that same normalized phone number; a different phone can be submitted. Existing uncertain receipts are preserved rather than reset blindly.


### Visitor capture destination

The initial visitor form registers via a server-to-server API in **Surya QA** (`https://surya.leadrat.info/`), separately from the demonstration tenant. Configure `BEACON_REGISTRATION_API_BASE=https://qa-lrb-webapi.leadrat.info`, `BEACON_REGISTRATION_TENANT=surya`, and a dedicated Surya bearer credential in `BEACON_REGISTRATION_TOKEN`. Keep the credential in ignored `.env`; it is never returned to the widget. The demo browser cookies and login are not used. Configure BEACON_REGISTRATION_IDENTITY_BASE, BEACON_REGISTRATION_USERNAME and BEACON_REGISTRATION_PASSWORD for server-side login and expired-token renewal. Authentication is cached in memory. A rejected read-only preflight may sign in once and repeat; Add Lead is never blindly replayed. Missing/invalid credentials fail registration; there is no browser fallback.

The backend validates international numbers with phonenumbers, checks `GET /api/v1/lead/contactno`, then sends name, email, split country code/number, optional company and Website source to `POST /api/v1/lead`, using the tenant and Bearer headers from the existing CRM API contract. Success requires `succeeded: true` and a nonempty UUID in `data`. Surya QA login, visitor creation and read-back were verified on 2026-10-13. Empty contact lookup in this tenant returns succeeded=false with null data and no error. The enquiry currency is read from tenant global settings. Other tenants still need contract validation.

Receipts are scoped to API host + tenant + phone, independently of old demo receipts. A committed receipt precedes the POST. Ambiguous writes are never automatically retried; confirmed validation/authentication rejection may be corrected and retried. A phone change permits a new request. This is local at-most-once protection, not a claim of server-side idempotency. A production service credential/refresh lifecycle and multi-instance shared receipts remain deployment considerations.

User-requested Add Lead walkthroughs are separate and still use the demo CRM. Initial registration does not move the demo screen or wait for its browser to initialize.


### Background visitor registration

Save hides the valid form immediately; the local API acknowledges with accepted=true and status=saving without waiting for Surya. Conversation access is based on accepted details, independently of the CRM save result. The widget sends the queued first question once and displays a quiet background status. Failed capture offers Update details without stopping the demo or speaking an unrelated save/error message. The contact form values are preserved.

Registration errors are isolated from demo errors. Accepted capture jobs survive closing/ending the viewer session; orderly backend shutdown gives them up to 30 seconds to finish. This is an in-process background task, not a persistent distributed queue: forcibly terminating the server can interrupt work. Existing durable receipts still prevent ambiguous Add Lead writes from being blindly repeated.


## Speed update (16 October 2026)

- **Opening the demo.** `widget.js` loads the demo window in the background once the website is idle (or when a launcher is hovered/focused). It stays laid out but transparent and inert, and no session starts until the visitor clicks. The click shows the already-rendered window and posts `beacon.open`; only then is the session created. Closing prepares the next window.
- **Warm browser.** One signed-in CRM browser waits for the next visitor (`BEACON_PREWARM_BROWSER=1`, set by `start.ps1`). A crashed idle browser is replaced, and an idle one is replaced in the background every 10 minutes before its login can go stale; the old one keeps serving until the replacement is ready. The first screen request returns a frame captured while it waited. Ending a session returns at once: the next browser starts preparing immediately and the used one saves its login and closes in the background. A used browser is never handed to another visitor.
- **Sign-in check.** The signed-in check that runs before every frame is now one in-page script instead of one browser round trip per sidebar link (measured 1.4 s before).
- **Voice.** Beacon's fixed sentences (welcome, follow-up offers, discovery questions) are synthesised once and kept in `.state/voice` (git-ignored; `BEACON_WARM_VOICE=0` disables this). Answers to a visitor are never written to disk. A drafted product answer starts speech synthesis while its source check runs; only a checked answer is shown or spoken. Fact checks within a turn run in parallel, the two handbook searches run together, and the hosted-model connection is opened when a session starts.

Measured on this laptop with a separate test instance (DeepSeek, edge voice, test CRM, another heavy job running), from the click: window ready 2–11 ms, welcome text 34–100 ms, welcome audio available 36–225 ms, live CRM frame shown 55–240 ms (before: 290–770 ms for the frame and 650–1,040 ms for the welcome audio). Questions: answer text 3.2–4.6 s for product questions and 1.2 s for a greeting, with the answer audio usually starting 30–60 ms after the text (before: about 0.6–0.9 s after). The remaining time is the three hosted-model calls (plan about 1.1 s, answer about 1.5 s, source check about 0.6 s). Reopening right after closing waits for the next browser (about 5 s on this machine) unless the visitor takes longer than that. These are individual observations, not latency guarantees.

### Review pass (16 October 2026)

- **Popup redesign.** `web/widget.html`/`widget.css` were rewritten: the live CRM sits in a browser-style window with a LIVE badge and a step card ("What Beacon is doing"), the chat uses message bubbles, the composer has SVG mic/send icons, and settings sit in one toolbar row. No external fonts or CDNs (CSP unchanged); layouts checked at 1440×900, 1280×720 and 390 px wide. All element ids used by `widget-client.js` are unchanged.
- **Fewer browser round trips.** Visibility checks for walkthroughs, popups and sign-in run as one in-page script with Playwright's own visibility rule (`app/visibility.py`, checked against `is_visible()` in a real browser), and the popup check returns after one call when nothing is open.
- **Screen search.** `app/screens.py` uses inverted indexes (trigram → CRM words, word → screens, name trigram → screens) and caches word matches, instead of scanning the whole vocabulary and every screen per message. An equivalence test compares the results with the original full scans; CPU time on the event loop fell from about 35–50 ms to about 5 ms per message. Repeated query embeddings are cached.
- **Polling.** Session state and screen frames carry an ETag; when nothing changed the server answers 304 with no body and the widget skips parsing and image decoding.
- **Fixes.** A second record walkthrough in a row (for example Notes, then History) failed because the closing lead preview was still in the page; Beacon now waits for it to close (6 of 12 consecutive steps failed before, 0 of 24 after, on the test CRM). Speech that was still waiting for its pause is now discarded when the visitor sends the text box, so it is not joined to the next question. Handoff outbox file work runs off the event loop.

Live measurements after this pass (same laptop, another heavy job running): click to live CRM frame 160–245 ms after warm-up; product answers 3.7–4.2 s (6.4 s for the first question of a session), voice starting 0.1–0.9 s after the text. The three sequential hosted-model calls remain the main cost.

### Conversation understanding and tone (16 October 2026)

- **Model first, rules as fallback.** "Do not contact me" and commands to change CRM data are judged by the conversation model in the same plan call (`kind=decline`, new `change_request` field), so "lead assign karna sikhao" is answered and "not interested in WhatsApp, show leads" is not an opt-out. The fixed `declined()`/`write_request()` patterns now apply only when the model could not read the message. Nothing in the browser can change CRM data except the confirmed Add Lead flow.
- **Add Lead form.** Each reply is read by the model in context (value, skip, confirm, cancel or something else), then validated by code. A question mid-form ("Explain lead sources") leaves the unsaved form and is answered; the business question that was open before resumes. Phone numbers still need a country code the visitor stated, and saving needs a short, explicit approval (never one inside a question). Keyword checks remain as an offline fallback.
- **Tone.** Answers get their own short reactions ("Great, so you're a developer.", "Okay, a team of 25.") instead of "Got it — …" every time; an unanswered business question is raised again once ("By the way, …") rather than after every answer; screen confirmations read "I've opened the Manage Leads page for you." Registration is answered by name, and the registration record (email, phone) is no longer shown as a chat bubble or sent with every model request.
- Checked with the hosted model: decline/change/question classification for six phrasings and nine Add Lead replies, plus a simulated conversation through discovery and Add Lead.

