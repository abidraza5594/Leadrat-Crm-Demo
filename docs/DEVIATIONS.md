# Deviations from the approved design doc

The design doc was approved on the plan below. These are the places where the build differs, why, and what it
costs. Each is a deliberate change, declared here rather than silently.

| Area | Design doc | Built | Why | Cost / risk |
|---|---|---|---|---|
| Speech-to-text | Whisper small.en (faster-whisper), push-to-talk | Browser Web Speech API (Chrome/Edge), continuous listening | No local GPU/CPU budget for Whisper at interactive latency on the demo laptop; the browser gives live interim results with no server cost | Chrome sends microphone audio to Google; Chrome/Edge only; recognition quality not under our control |
| Text-to-speech | Kokoro-82M, local | Microsoft Edge neural voice (edge-tts), browser voice as fallback | Kokoro was not installed/validated in time; Edge voice needs no key | Reply text goes to Microsoft; network-dependent; no availability guarantee |
| Barge-in | Deferred (half-duplex push-to-talk) | Full-duplex: speaking over Beacon stops the voice and cancels the running demo | Requested during development; implemented with an echo-cancelled mic track where supported and a word-pair echo filter | Stop time was measured only with a scripted recogniser (under 300 ms after an interim result); the 200 ms requirement is not claimed; loud speakers can still leak echo |
| Live display | Xvfb → VNC → websockify → noVNC | Hidden Chrome, JPEG screenshots polled by the widget (~4–5 fps), decoded before swap | Windows demo machine, no Xvfb; far less infrastructure | Lower frame rate than VNC; one session at a time |
| Frontend | React + TypeScript + Vite | Vanilla JS widget + launcher script | Small surface; avoided a build step | Less structure if the UI grows |
| Planner | Benchmark Qwen3-4B vs Gemini 2.5 Flash | OpenAI `gpt-6-luna` (low reasoning) or local Ollama `ministral-3:3b`, plus reviewed shortcuts | OpenAI key was available; the local 3B model was slow on CPU (first call ~20 s) | Paid calls; the planner comparison benchmark was not run |
| Retrieval | PostgreSQL + pgvector hybrid | BM25 keyword index over the company handbook PDF, in memory | Handbook is 29 pages / 139 chunks; keyword retrieval reached 30/30 answered and 20/20 refused on the dev set | No semantic retrieval; paraphrases rely on a small synonym list |
| UI navigation | 3 persona flows | Module navigation plus lead workflows (status, notes, history, meetings, site visits, WhatsApp, email, filters…) | Built incrementally against the test CRM | Persona mapping of flows still to be written up |
| Deployment | Linux Docker workers, public HTTPS URL | Runs locally on Windows (loopback only) | Not yet deployed | **Open:** a browser-reachable deployment is still required by the assignment |
| Guided "step boxes" | Not planned | Tried (labelled box before each click), then removed | Boxes were placed inaccurately on some controls | — |

Unchanged from the design doc: ICP scoring rules and handoff schema (approved), read-only action policy, grounded
answers with refusal, fine-tuned ≤3B SLM (Qwen2.5-1.5B-Instruct, QLoRA on a Colab T4), A/B/C evaluation with a
pre-registered threshold, fallback ladder, mock-webhook handoff.
