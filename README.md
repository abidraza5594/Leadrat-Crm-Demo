# Beacon — standalone website demo backend

Python backend + an embeddable HTML website widget. The backend owns a hidden, isolated Chrome browser, operates the existing test CRM through its UI, and streams authenticated screen images into the website popup: the live CRM on the left, the chat on the right. No separate Chrome window opens during a demo. No changes to the Angular CRM are required.

## Start on this Windows machine

1. Open PowerShell in `C:\Leadrat AI\Beacon`.
2. Run `./start.ps1 -OpenAI`. Enter the temporary OpenAI API key and test CRM credentials at the prompts. Password and key input are hidden and held in process memory only; Beacon never writes them to disk. The hidden browser signs in with them and saves the resulting CRM login (not the password) to `.browser/crm-state.json`, so later sessions and restarts start signed in. The credentials stay in memory so the hidden browser can sign in again if the saved login expires.
3. In another PowerShell window run `./start-test-page.ps1`.
4. Open **http://localhost:8011**, choose **Start exploring**, then **Start a session**. The live CRM appears on the left of the popup and the chat on the right.
5. Voice is on by default and reads every reply; the **Voice** button turns it off (remembered per browser). End the session when done; its browser context and conversation are discarded.

`./start.ps1 -Login` runs the Ollama alternative with the same credential prompt. `./start.ps1` starts without prompting and uses the saved login. **Sign in manually** (for example when the account asks for two-factor verification) with `./login.ps1`: it opens a visible Chrome window once, saves the login when the CRM opens, and closes. A session that is already waiting picks the login up automatically. Install Google Chrome first. The server binds to loopback only. Ctrl+C stops each server.

`HEADLESS=false` in `.env` additionally shows the demo browser as a separate window, for debugging only. `.browser/crm-state.json` contains CRM auth tokens: keep it on this machine and delete it to force a fresh sign-in.

The `.env` on this machine selects the user-designated test URL. `.env.example` is the portable template. Never configure a production account as a public demo.

## Current implementation

- FastAPI session API with random session capability tokens, registered website origins, one active browser, 15-minute interaction-idle timeout and 30-minute maximum lifetime.
- A server-owned Playwright browser executes fixed navigation capabilities; the visitor receives pixels, not CRM credentials or browser-control access.
- GPT-6 Luna with **low** reasoning, strict structured classification, response validation, 512 maximum output tokens and 30 model requests per process. Common unambiguous Lead requests use reviewed shortcuts without a model call. `/api/health` exposes aggregate token usage. `store=false` is requested. Only the visitor question, previous feature ID and generic catalogue are sent to OpenAI; no CRM screenshot, DOM, credential or record data is sent. Simple email/phone/key redaction is included; it is not a complete PII detector.
- The model selects a catalogue entry; user-facing facts come from the reviewed catalogue, not unrestricted generation. Navigation must be observed before success is narrated. Missing/ambiguous controls stop the action. There is no generic click, JS execution, URL, save, delete, upload or send tool available to the model.
- Stop cancels pending inference/action execution. Failed and cancelled steps are distinct from verified steps. Browser controls are fixed in `app/browser.py`; Lead adapters and popup policy are in `app/lead_browser.py` and `app/popups.py`; source-backed explanations are in `app/lead_guides.py` and `knowledge/features.json`.
- Optional neural narration: `TTS_PROVIDER=edge` uses a keyless online test speech connector (not a production availability guarantee). Only issued assistant guide replies are spoken. The browser displays a disclosure and falls back visibly to browser speech if unavailable. `TTS_PROVIDER=local` with `TTS_URL` supports an OpenAI-compatible local Kokoro `/audio/speech` service; Kokoro is not installed in this build.
- Explicit declines route to `graceful_close`, even when the calculated score is 40 or higher. Unknown scoring fields remain null/ranges. The scoring module is a **rules fallback**, not a successfully evaluated fine-tuned SLM. No handoff is transmitted.

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
| Add Lead | Open form, inspect visible name/email controls; no submission |
| Bulk upload | Open entry screen; no file selection/import |
| Projects, Properties, Tasks, Dashboard | Open and verify module |
| Sources, status, communications | Grounded overview and Leads entry point; nested workflows are not automated |
| Unknown features, scheduling, deletion, arbitrary instructions | No invented workflow; explain the coverage boundary |

This is an executable local vertical slice, **not completion of the full design document**. Remaining work includes deeper verified persona workflows, approved full-product RAG/pgvector ingestion, microphone STT, installed local Kokoro, independently evaluated qualification adapter, consented mock handoff/outbox, load/latency evaluation, and public deployment security.

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

Greetings, thanks and "what can you do" are answered without a model call. Beacon demonstrates by default; only an explicit "just explain" / "sirf batao" keeps the screen unchanged. Common Hinglish forms ("status kaise badle", "lead me note add karo") use reviewed shortcuts. If the planner model is unavailable, times out or exhausts its call budget, reviewed catalogue keywords are used; no keyword match stays unknown. The local model is preloaded at startup and when a session starts. A session whose widget stops polling for 30 seconds (closed tab, crashed page) is reclaimed so a new visitor is not blocked.
