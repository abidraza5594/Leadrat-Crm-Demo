# Data handling: what Beacon logs, redacts and keeps

| Data | Where it goes | Kept for | Notes |
|---|---|---|---|
| Visitor microphone audio | Chrome's speech service (Google), when the visitor turns the mic on | Not stored by Beacon | Beacon only receives the recognised text |
| Chat transcript (session) | Server memory only | Until the session ends: 15 min idle or 30 min maximum, or when the visitor closes the popup | Never written to disk or logs |
| Beacon's reply text | Microsoft Edge voice service (text-to-speech) | Not stored by Beacon | Only Beacon's own replies are voiced, never visitor text |
| Questions to the handbook model | OpenAI Responses API with `store=false` | Not stored by Beacon | Emails and phone numbers are replaced with `[redacted]` first; only the question and handbook excerpts are sent |
| Planner request | OpenAI with `store=false` (or local Ollama) | Not stored | Emails/phone numbers redacted; no CRM screenshots, DOM or records are sent |
| Qualification (hosted fallback) | OpenAI with `store=false` | Not stored | Transcript sent with emails and phone numbers redacted; contact details are re-attached locally |
| Qualification result | Server memory, shown in the session state | Session lifetime | |
| Handoff brief (consented, qualified only) | `.outbox/outbox.jsonl`, then the mock webhook `.outbox/mock_received.jsonl` | 7 days (`HANDOFF_RETENTION_DAYS`), pruned by `app/handoff.py: prune()` | Contains name/email/phone the visitor typed; git-ignored; sent only with explicit consent and a usable contact |
| Server logs | uvicorn console | Console lifetime | Access logs disabled; no transcripts or records are logged. Aggregate timings only |
| Latency timings | Session memory (`/api/sessions/{id}/timings`) | Session lifetime | Millisecond numbers and the route taken; no text |
| CRM screenshots | Streamed to the visitor's widget | Not stored | May show seeded sandbox records only |
| CRM login state | `.browser/crm-state.json` on the demo machine | Until deleted | Auth tokens; git-ignored |
| Test CRM credentials, API keys | `.env` on the demo machine | Until deleted | Git-ignored; never logged |

Visitor opt-out: saying "do not contact me" (or Hinglish/Devanagari equivalents) routes to `graceful_close`, stops
contact-detail requests and prevents any handoff.
