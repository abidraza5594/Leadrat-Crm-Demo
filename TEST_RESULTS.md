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
