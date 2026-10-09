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

Windows development uses authenticated JPEG polling at up to four frames per second, independently of chat polling. Linux Xvfb/VNC/websockify/noVNC transport and per-session containers are **not yet implemented**. The public architecture in the design document remains the deployment target. The website test harness is vanilla HTML rather than the final React client.

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
