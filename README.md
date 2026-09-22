# Leadrat local AI demo backend

Python + FastAPI connects the Angular CRM to a locally running `ministral-3:3b` through Ollama. This is a local development prototype, not a publicly deployable authenticated service.

## Run on Windows

1. Install Ollama from its official installer or `winget install --id Ollama.Ollama --exact`.
2. Run `ollama pull ministral-3:3b`.
3. In this folder run `python -m venv .venv`, then `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
4. Run `.\start.ps1` (binds only to `127.0.0.1:8001`).
5. In the sibling `Leadrat-Black-Web` folder use the existing `ng serve` on port 4200, or run `npm run start:ai` for a separate server on port 4300.
6. Open `http://localhost:4200/login` for the existing real CRM. If using `start:ai`, use `http://localhost:4300/login`.

The local assistant calls `http://127.0.0.1:8001/api/assistant` directly, so the regular CRM development server does not require a proxy or a new login on another port. Ports 4200 and 4300 are allowed development origins. A separate optional sample playground exists at `/assistant-demo`; it does not replace verification in the actual authenticated CRM.

Use `localhost` for CRM login: this application's tenant detection interprets `127.0.0.1` as tenant `127`. Real CRM login may require actual device location and the user's account permissions. The assistant does not bypass these checks.

In the actual CRM assistant choose **Full CRM tour**, **Lead form walkthrough**, or ask **Reports kaise use karte hai live dikhao**. Close any unsaved form yourself before navigating to another module.

## What it can do

- Visit available Dashboard, Leads, Data, Invoice, Projects, Properties, Listing, Tasks, Reports, Users, Teams, Roles, Attendance, Global Config and Organisation Profile screens. Actual permissions and sidebar availability are checked before every action.
- Highlight supported controls on Dashboard, Leads and Global Config. Other modules currently receive a screen introduction, not every nested workflow.
- Walk through up to 21 visible Add Lead fields, including contact numbers, source, owners, budget and property requirements. Hidden/configuration-dependent fields are not claimed as demonstrated.
- At the end, fill only an untouched new-lead form with fixed sample name and email.
- Match each question's language automatically: Hindi/Hinglish uses Swara or Madhur; English uses Neerja or Prabhat. Voice on/off, preview, replay, pause/resume and stop follow the selected language. Each successful UI action is explained before the next one starts.
- Clear requests such as **how to add lead**, **lead add kaise kare**, **full CRM tour** and **Reports kaise use kare** start an allowlisted tutorial immediately without waiting for model inference. Lead creation tutorials open Add Lead directly. General questions and less clear requests still use the local model. A workflow controller expands visible steps and requires matching action results, preventing premature completion after name/email.

There is no save, send, delete, arbitrary script, arbitrary URL, or generic click tool. Filled values are **unsaved**. CRM credentials and existing lead values are not sent to this service. The model runs locally.

## Automatic Hindi and English narration

English questions receive English replies and tutorial narration; Hindi/Hinglish questions receive Hindi/Hinglish replies and Hindi narration. Language is detected locally on every new question, without another model request. Brief follow-ups such as "next" keep the previous language; explicit requests such as "explain in English" override detection. Narrator gender is retained when switching languages.

`edge-tts==7.2.8` connects to Microsoft Edge's online speech service without an API key. This prototype has no paid voice API configured, but the connector is unofficial and its free availability is not a production guarantee. Internet is required; a voice failure displays an explanation and continues with text.

Only reviewed text from `app/catalog.py` (Hindi) and `app/catalog_en.py` (English) is sent to the voice provider. Neither arbitrary user text, model replies, credentials nor existing CRM record values are accepted by the speech endpoint. The browser sends a narration key, language and matching voice, and the server looks up that key. Audio is cached in bounded process memory with separate voices/languages; there is no persistent audio/transcript history.

Use **Try voice** before starting the tour. If browser autoplay blocks narration, enable site audio or use the playback control; the app shows the failure instead of silently claiming it spoke.

Narration runs at `+12%` speech rate. The browser acknowledges a completed action and prepares the next step's audio while the current explanation plays. The next screen action still waits for that explanation and respects Pause/Stop. This overlaps speech generation with playback instead of adding a network pause between every step; first-time audio and screen loading can still take time.

## Protocol

`GET /api/assistant/health` checks Ollama/model availability. `POST /api/assistant/sessions` issues a random local session ID and capability token. Send the token as `X-Assistant-Session` to `POST /api/assistant/sessions/{id}/turn`, along with either a user message or the exact result of the pending action. The response contains explanation and at most one validated action. Execute it in Angular and report the result before requesting the next step. `DELETE /api/assistant/sessions/{id}` discards a session.

Context includes `available_modules`, `available_fields` and `available_controls`, containing allowlisted keys only, not record data. Responses add `language`, `progress` and `narration: {key, text, language}`. Speak action narration only after success. `POST /api/assistant/sessions/{id}/speech` with the same session token accepts `{key, voice, language}` and returns MP3; only narration issued to that session (plus `voice.preview`) is allowed. Mismatched voice/language combinations are rejected. The progress total expands after opening a screen, when its actual fields are known.

Only loopback clients, local hostnames and configured development origins are accepted. This local token is not CRM authentication. For production, add real identity/tenant verification, rate limits, persistent sessions and deployment controls; keep write permissions in the existing CRM backend.

## Configuration

Environment variables: `OLLAMA_URL` (default `http://127.0.0.1:11434`), `OLLAMA_MODEL` (default `ministral-3:3b`), `OLLAMA_TIMEOUT` (180 seconds), `OLLAMA_CONTEXT_SIZE` (8192 tokens). Restart the backend after changing settings or code.

Knowledge is in `app/knowledge.md`; model tools are in `app/tools.py`, tutorial plans in `app/workflows.py`, and reviewed narrations in `app/catalog.py`. The matching frontend catalog is `src/app/shared/components/ai-assistant/assistant.catalog.ts` in the sibling frontend. No fine-tuning is performed yet. No chat transcripts are persisted automatically. Sessions expire after two hours and are lost on server restart.

## Tests

Install `requirements-dev.txt`, then run `.\.venv\Scripts\python.exe -m pytest -q`. Tests cover allowlisting, session ownership, result correlation, unsafe form states, every visible field, mid-tour permission changes, failed steps, bounded sequential execution, speech authorization, arbitrary-text rejection and voice failure. These use stubs to isolate protocol behavior; actual CRM browser verification and live Ollama/voice smoke checks are separate validation.

To fine-tune later, curate reviewed tool-call conversations with actual results, separate evaluation examples, train outside Ollama and import a compatible exported model. Merely changing an Ollama Modelfile is not fine-tuning.


## Source-grounded CRM feature help

The assistant now retrieves local Angular source for detailed feature questions, independently of the limited live-action catalog. `app/crm_knowledge.py` indexes feature, shared-component and layout TypeScript/HTML on startup, excluding environment files, runtime records, tests and assistant code. It resolves matching UI translation labels and includes relevant permission/form evidence. `knowledge-coverage.md` lists the source inventory; indexed coverage does not mean every workflow has been manually verified or automated.

Set `CRM_SOURCE_ROOT` if the sibling `Leadrat-Black-Web` checkout moves. Restart the Python server after CRM source changes to rebuild the in-memory index. No CRM credentials, API responses or records are indexed. Retrieval and inference use the local Ollama service. Existing reviewed demo narration remains separate; arbitrary knowledge answers are text-only and are not sent to online TTS.

Try: “lead notes kaise add kare”, “lead reassign kaise kare”, “How do task priorities work?”, “How do I bulk upload leads?”, “Facebook integration kaise use kare”. Bare how-to module questions now request explanations; explicit “Reports ka demo dikhao” still starts its supported tour. Detailed questions never execute UI tools. Add Lead and full CRM tour shortcuts retain their existing behavior.

The small model can still make mistakes despite grounding. Reviewed guide facts take precedence over inferred steps; unsupported paths or backend behavior should be acknowledged. Add verified feature-specific facts in REVIEWED_GUIDES and retrieval regression examples in tests/test_knowledge.py when extending coverage.


### Natural-language question understanding

Free-form help questions first pass through a short, schema-constrained local Ollama interpretation (`app/question_understanding.py`). It rewrites paraphrases, Hindi/Hinglish and contextual follow-ups into an English feature search query, retaining specific operations and constraints. The original user question and selected language still drive the answer. An unidentified feature receives a clarification instead of an invented topic. Interpretation never executes actions; existing live-demo action authorization stays separate.

Reviewed guides are used only when the interpreted topic matches; permission, error, deletion and other specific questions go through source retrieval. Interpretation has a bounded timeout and falls back to the original question if Ollama fails or returns invalid JSON. This adds a short inference step to free-form help. The language model can still misinterpret questions; the included paraphrase smoke tests are evidence for tested cases, not a guarantee for all wording.


### Live lead feature walkthroughs

The live registry now includes individual lead status, meeting scheduling, site-visit scheduling, notes, history, documents and reassignment. These run through `show_lead_feature` with open/details/finish stages and reviewed English/Hindi narration. Clear status/scheduling requests bypass model inference. Paraphrased questions use semantic interpretation before selecting a registered feature. Actual UI results are acknowledged before advancing.

Frontend actions open the existing lead preview (or the first visible row), select its allowed tab, and highlight controls. Meeting/site-visit guides select only the matching schedule option and highlight the date/time input, leaving the form unsaved. They never press save/submit/assign/claim/delete or change an appointment's completion state. Close the unsaved form manually before another guide. Existing appointment-completion flows, hidden/renamed controls, missing permissions and dirty forms stop the guide rather than substituting a different action.

This registry is distinct from broad source-knowledge coverage. Unregistered feature workflows are not automatically executable. Test the real logged-in CRM for account-specific custom statuses and permissions. Frontend executor fixtures are run with `node scripts/test-assistant-feature-actions.cjs`; they do not replace actual account testing.


### Voice for all assistant replies

When voice is enabled, ordinary answers, clarification questions and stopped-guide replies now receive session-scoped reply narration, in addition to existing tutorial speech. The exact assistant reply text is sent to Edge online TTS only when the browser requests playback. This supersedes earlier tutorial-only/text-only speech limitations. Dynamic reply audio is not retained in the server-wide tutorial cache. Reply keys are restricted to the issuing session, bounded to its latest 16 replies, and disappear when the session ends. Voice OFF does not request synthesis. The UI explains that assistant replies are sent to the online voice service.

No site-visit wording or intent matching was changed for this voice fix.

### Communication and Lead coverage update

WhatsApp, email, combined communication overview, source attribution, bulk-upload entry, filters, search, columns, export, saved/date filters and integration overview now have registered guides with bilingual voice. Short template follow-ups preserve the communication channel. Known questions bypass model inference; semantic interpretation handles other wording. Bulk communication is never replaced by an individual-send guide. No send/import/export/write action is executed.

See `lead-feature-coverage.md` for the complete component inventory, executable boundaries and remaining knowledge-only workflows. This supersedes earlier descriptions suggesting only seven feature guides, or that all detailed how-to requests are text-only. Source indexing does not imply every feature has live automation. Actual logged-in account verification is still required.
