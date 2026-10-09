# Context-driven Beacon

**Validation status (2026-10-06): local demonstration build; not production approved.** The isolated conversation now recognizes the previous short replies and changes the visible Leads/Projects workspace. Remaining limits include latency under RAM pressure, limited real-model coverage, unverified PostgreSQL deployment and untested microphone/audio quality. See `LIVE_CHECK_2026-10-06.md` for dated before/after evidence; contract tests are not model accuracy.

Later FP16 runtime comparison removed timeouts on seven selected context cases but all seven still failed decision correctness/validation. Three adapter scenarios produced complete output and passed selected application-normalization replay checks. Precision optimization does not establish planner quality. The runtime supports `BEACON_MODEL_PRECISION=auto|float16|nf4-float16`; auto prefers FP16 with at least 3200 MiB free after CUDA initialization for this fixed 1.5B model.

The application uses a LangGraph workflow: load context → local model decision → topic-constrained knowledge → save decision. A compact first model call classifies the turn; a second chooses the reviewed feature or extracts quoted customer facts. Answer and browser executor consume the same validated decision. There is no regex/keyword demo-routing fallback.

The local conversation model is Qwen3-4B-Instruct-2507 Q4_K_M, served on the CPU by a pinned llama.cpp runtime at localhost:8014 with a private API key. Run `python slm/setup_planner.py` once to download checksum-verified files. The latest trained Beacon v4 adapter remains on its original Qwen2.5-1.5B base at localhost:8012, preferably FP16 on the existing GPU. The adapter is not compatible with the separate 4B base and is not loaded into it. OpenAI/GPT Luna was not implemented; there is no hosted LLM fallback.

The current Leadrat browser executor remains intentionally project-specific. `knowledge/project.json` contains the project id, document directory, module-to-topic mapping and capability descriptions. A new product needs its own knowledge and reviewed browser/API executor, not just a renamed project id.

## State and storage

`BEACON_DATABASE_URL` selects PostgreSQL with pgvector. `setup-database.ps1` provisions a dedicated localhost Docker database, using a generated password kept in ignored `.state/database.env`. It never resets Docker or deletes volumes. Database errors fail startup rather than silently falling back.

Without a database URL, the explicit development backend is `.state/conversations.sqlite3`. Both backends persist project/session-scoped conversation snapshots, customer fact evidence, decisions, action outcomes and a versioned embedding index. Conversation records older than seven days are pruned at startup. Tokens, passwords and CRM cookies are not stored in these records. Back up the PostgreSQL volume before deployment upgrades.

The live browser and session authentication remain process-owned. Stored conversation state is an audit/recovery foundation; restarting the server does not automatically restore browser sessions or replay actions. The widget opens a fresh session. A secure user-facing resume flow is a separate requirement.

## Knowledge

The pinned multilingual MiniLM embedding model runs through quantized ONNX on CPU, without importing PyTorch into the web server. `python slm/setup_knowledge.py` explicitly downloads verified files. Embeddings are cached with the document/model version; PostgreSQL queries use pgvector. SQLite development queries use the same vectors locally. Approved capability facts remain available while the semantic index warms up. Exact reviewed handbook answers are consulted only AFTER deciding the topic, and only when their module agrees.

Accepted visitor facts retain a message reference and quoted evidence. A delayed adapter result cannot overwrite newer corrections. Product questions and hypothetical examples are excluded from customer extraction; unaccepted business counts and consent cannot be added to sales JSON by the adapter. Scores are recalculated, and incomplete/fallback results require human review. Refusal prevents contact delivery immediately, including while extraction is still running. Do not interpret the lead-fit score as model confidence.

Embedding similarity is not a probability of correctness. The small language model must be evaluated on dialogue, corrections and topic changes. A malformed/unavailable model decision produces clarification, never a keyword-selected action. The installed local model service is used; LangGraph has no hosted-model requirement.

## Safety and cleanup

Removed: `shortcut`, `keyword_match`, `scope_plan`, old provider classifier, regex discovery routing and the separate answer/demo decision paths. Regex remains for input formats and write/opt-out guards. Lead creation still requires reviewed details and explicit confirmation and does not retry an uncertain Save. Browser selectors are reviewed code; model output cannot supply selectors, URLs or JavaScript.

Unit tests mock model decisions to check contracts and failure behavior, NOT language accuracy. `eval/context_engine.py` runs real local-model decisions and saves correctness/latency by scenario. Earlier regex tests are replaced by graph-contract tests and contextual evaluation cases. Do not compare the changed unit-test count to model accuracy.
