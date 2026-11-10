# Beacon — technology, architecture and costs

Prepared 16 October 2026. Prices were checked on that date and change; measured figures come from this
laptop and a test CRM. Recompute the cost tables with `python eval/cost_model.py` after any price change.
Free items (the current Microsoft Edge voice, local search, the database on the same server, SSL) have no price
and are not counted as costs.

## 1. What Beacon is

Beacon is an AI product guide for the Leadrat website. A visitor clicks **Start exploring**, sees the real Leadrat
CRM live on the left of a popup and talks to Beacon on the right, by typing or by voice. Beacon understands the
question, answers from the company's product handbook, opens and highlights the matching CRM screen, and speaks
the answer. It also registers the visitor as a lead, asks a few business questions, scores the lead and can hand
it to the sales team with the visitor's consent.

## 2. How it is built

```
Website (any page)                       Beacon server (Python, FastAPI)                     External services
──────────────────                       ───────────────────────────────                     ─────────────────
widget.js ── preloads ──► widget.html    Session API (/api/sessions…)
             (hidden)     chat + live    ├─ Warm browser pool ──► headless Chrome (Playwright) ──► Leadrat CRM (test tenant)
                          screen         │    one signed-in CRM page always ready
   click ─► session in ~50–250 ms        ├─ Conversation engine (LangGraph) ───────────────────► DeepSeek API (deepseek-flash)
                                         │    1. search handbook + CRM screen map (local)
   mic ──────────────────────────────────┼──── temporary key ──► browser streams audio ────────► Soniox speech-to-text
                                         │    2. plan: what the visitor means, which screen
   ◄── live CRM frames (JPEG, ETag) ─────┤    3. open the screen (in parallel) + grounded answer
   ◄── chat state (polled, ETag) ────────┤    4. source check of the answer
   ◄── voice (MP3 stream) ───────────────┼── one warm WebSocket ──────────────────────────────► Soniox text-to-speech
                                         ├─ Registration ───────────────────────────────────────► Leadrat API (Surya QA)
                                         └─ Lead scoring + sales handoff (consent required)
```

**One visitor question, step by step**

1. The widget sends the message (`POST /turn`). If Beacon is still speaking or demonstrating, the new
   question interrupts it.
2. Local search runs in a few milliseconds: hybrid search over the handbook (meaning + keywords) and over the
   CRM screen map (2,054 screens generated from the CRM code + 38 prepared walkthroughs).
3. **DeepSeek "plan" call**: reads the conversation and the search results and decides what the visitor
   means (product question, business answer, small talk, refusal, data-change request) and which screen to show.
4. As soon as the plan is ready, the hidden Chrome opens and highlights that screen, **while** the answer is
   being written.
5. **DeepSeek "answer" call**: writes the reply only from selected handbook passages and screen facts.
6. **DeepSeek "check" call**: verifies every claim against those passages. While it runs, Soniox already
   starts generating the speech, so the voice is ready when the text appears.
7. The widget shows the text and plays the voice as it streams in; the live screen shows the walkthrough.

**Safety rules built into the code** (not left to the model): the demo browser can only navigate and highlight;
the only write is Add Lead, saved after an explicit confirmation; bulk actions and Delete are pointed at, never
clicked; a command to change CRM data is refused; contact details go to sales only with consent.

## 3. Technology stack

| Layer | Technology | Version | Used for |
|---|---|---|---|
| Backend | Python, FastAPI, Uvicorn | 3.11.9, 0.141.1, 0.53.0 | Session API, static widget files |
| Conversation engine | LangGraph | 1.2.13 | Turn pipeline: context → plan → grounded answer → save |
| Language model | DeepSeek API, model `deepseek-flash` (DeepSeek-V4.1-Flash) | hosted | Understanding, answers, source checks, lead facts. JSON mode, thinking off |
| Local model (inactive) | Qwen3-4B-Instruct + Beacon adapter (llama.cpp) | — | Offline alternative; not used while `PLANNER_PROVIDER=deepseek` |
| Live CRM | Playwright + Google Chrome (headless) | 1.58.0 | Signs in, navigates, highlights; frames sent as JPEG |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2`, INT8 ONNX (`model_quint8_avx2.onnx`) on ONNX Runtime | ort 1.30.0, tokenizers 0.23.2 | 384-dimension vectors for handbook and screen search, 50+ languages incl. Hindi |
| Vector store | PostgreSQL + **pgvector** `vector(384)` in deployment; SQLite + in-memory NumPy for local development (current) | psycopg 3.3.6, numpy 2.4.6 | Handbook passages, conversation state |
| Screen index | NumPy matrix 2,092 × 384 (`.state/screens-<version>.npy`) + per-text vector store (`.state/screen-vectors.npz`) + inverted indexes (trigram → words, word → screens) | — | Finding the CRM screen a question is about |
| Speech-to-text | Soniox real-time `stt-rt-v5`, browser WebSocket with single-use temporary keys | — | Visitor's voice → text (English, Hindi, Hinglish) |
| Noise cleanup | RNNoise via `@sapphi-red/web-noise-suppressor` (AudioWorklet) | 0.4.1 | Removes background noise before Soniox |
| Text-to-speech | **Soniox real-time `tts-rt-v2`, voice Priya** (Indian English, speed 1.1), one persistent server WebSocket | websockets 16.1.1 | Beacon's spoken replies (streamed MP3) |
| Backup voice | Microsoft Edge read-aloud via `edge-tts`, voice `en-IN-NeerjaNeural` | 7.3.1 | Used only if Soniox fails before any audio |
| Widget | Vanilla HTML/CSS/JS, MediaSource audio, intl-tel-input | intl-tel-input 29.5.4 | Popup UI, phone field, streaming audio |
| Registration | Leadrat API (tenant `surya`), phonenumbers | 9.0.41 | Visitor saved as a CRM lead (background) |
| Documents | pypdf | 5.4.0 | Reads the Pre-Sales handbook PDF |

## 4. Knowledge search and the vector database

| Item | Value |
|---|---|
| Embedding model | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (pinned revision `e8f8c211…`), INT8-quantised ONNX, runs on the CPU |
| **Vector dimension** | **384** (float32), mean-pooled and L2-normalised, so cosine similarity = dot product |
| Handbook | FLOE Leadrat Pre-Sales Product Knowledge Handbook v0.2 (29 pages) → **139 passages**, 13 main modules |
| Database (deployment) | PostgreSQL with **pgvector**: table `beacon_knowledge`, column `search_vector vector(384)`, cosine distance operator `<=>`. Exact search (no ANN index needed at this size) |
| Database (now, local) | SQLite file `.state/conversations.sqlite3` (vectors stored as JSON) + in-memory NumPy search |
| Search method | Hybrid: dense vector similarity + BM25 keyword ranking, merged with reciprocal rank fusion (k = 60). Hinglish/Devanagari words are romanised first |
| CRM screens | 2,054 screens/sections generated from the CRM code + 38 prepared walkthroughs = 2,092 entries × 384 dims. Ranked by meaning, name words, on-screen words and spelling (trigrams), via inverted indexes |
| Speed | About 5 ms of server CPU per question for screen search; repeated query embeddings are cached |

The model never sees the whole handbook: each question gets the best few passages, the model must cite them by
ID, and a second call checks the answer against them.

## 5. Voice

- **Visitor → Beacon (speech-to-text):** Soniox `stt-rt-v5` from the browser. The server issues a single-use
  temporary key (60 s), so the real key never reaches the browser. Microphone audio is cleaned by RNNoise first.
- **Beacon → visitor (text-to-speech): Soniox real-time `tts-rt-v2`, voice Priya.** The server keeps one
  WebSocket to Soniox open (with a keep-alive every 20 s), so a reply never pays the ~1.1 s connection set-up.
  Up to five sentences are generated in parallel; MP3 chunks are passed to the browser as they arrive and play
  before the sentence is finished. Beacon's fixed sentences (welcome, follow-up questions, business questions)
  are generated once and cached on disk, so they cost nothing per visitor and play instantly. If Soniox fails
  before any audio arrives, the same sentence is spoken with the Microsoft Edge voice.
- Settings: `TTS_PROVIDER=soniox`, `SONIOX_VOICE=Priya`, `SONIOX_TTS_SPEED=1.1`, `SONIOX_TTS_URL`
  (Soniox's India region can be used once access is approved; it needs a region-specific project key).

## 6. Measured speed (this laptop, test CRM)

| What | Measured |
|---|---|
| Click "Start exploring" → live CRM screen visible | 55–245 ms (window preloaded, signed-in browser waiting) |
| Welcome voice available after the click | 36–235 ms (pre-generated) |
| Product question → answer text | 3.3–4.7 s (three DeepSeek calls; varies with DeepSeek load) |
| Answer text → voice starts (Soniox) | 45–77 ms (speech generated during the source check) |
| Small talk ("hi") → voice starts after text | ~440 ms (Soniox first audio from India to the default region) |
| Soniox first audio on a warm connection | 480–550 ms; Microsoft Edge voice 530–600 ms |
| Demo browser CPU | 28% of one core idle, 33% with the live view (endless CRM animations held still); 0.94 cores while answering questions back to back |
| Memory per live demo | 1.45 GB at the start, 1.61 GB after 8 questions (server 554 MB + browser driver 81 MB + Chrome 0.8–1.0 GB) |
| Data sent to the visitor | ≈ 0.9 MB per product question (live screen frames ~82 KB each, unchanged frames not re-sent; voice MP3 at 64 kbps) |

The remaining wait is the language model. Voice and screen loading run in parallel with it.

## 7. Cost analysis

### 7.1 Prices used (list prices, 16 October 2026)

| Service | Price | Source |
|---|---|---|
| DeepSeek `deepseek-flash` | per 1M tokens: cached input $0.003 / $0.006, uncached input $0.15 / $0.30, output $0.60 / $1.20 (off-peak / peak). Peak: 01:00–04:00 and 06:00–10:00 UTC Mon–Fri = 06:30–09:30 and 11:30–15:30 IST | [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing) |
| Soniox text-to-speech `tts-rt-v2` | input text $4 / 1M tokens + output audio $21.50 / 1M tokens (30,000 audio tokens per hour of speech) ≈ **$0.70 per hour of speech** | [Soniox pricing](https://soniox.com/pricing) |
| Soniox speech-to-text `stt-rt-v5` | **$0.12 per hour** of audio streamed | [Soniox pricing](https://soniox.com/pricing) |
| AWS EC2 server, Asia Pacific (Mumbai), on demand, Linux | c6a.xlarge (4 vCPU, 8 GB) $0.0935/h · c6a.2xlarge (8 vCPU, 16 GB) $0.187/h · m6a.2xlarge (8 vCPU, 32 GB) $0.2222/h · c6a.4xlarge (16 vCPU, 32 GB) $0.374/h; 730 hours a month | [EC2 on-demand pricing](https://aws.amazon.com/ec2/pricing/on-demand/) (AWS price file published 15 Oct 2026) |
| AWS disk and backups (Mumbai) | EBS gp3 $0.0912 per GB-month; snapshots $0.05 per GB-month | [EBS pricing](https://aws.amazon.com/ebs/pricing/) |
| AWS public IPv4 address | $0.005 per hour (≈ $3.65 a month) | [VPC pricing](https://aws.amazon.com/vpc/pricing/) |
| AWS data sent to the internet | first 100 GB a month free | [EC2 on-demand pricing](https://aws.amazon.com/ec2/pricing/on-demand/) |

**The current voice (Microsoft Edge, `edge-tts`) is free**, so it has no price and adds nothing to the totals.
It is an unofficial use of the Edge browser's read-aloud service (no contract or guarantee; version 7.2.8 was
already blocked with HTTP 403 in October 2026). Soniox is the licensed, paid option.

Exchange rate for ₹ figures: $1 = ₹90 (planning rate). Prices exclude taxes (for example 18% GST in India).

### 7.2 What one conversation actually uses (measured)

A 16-turn session (8 product questions + 8 answers to Beacon's business questions) made 36 DeepSeek calls and
generated 4,185 new spoken characters:

| Per turn | DeepSeek calls | DeepSeek cost (peak) | New spoken characters | Soniox voice |
|---|---|---|---|---|
| Product question | plan (~1.25) + answer + check | **$0.00162** | 479 | **$0.00507** |
| Answer to a business question | plan (~1.25) + lead scoring every 2nd | $0.00080 | 44 | $0.00047 |
| Registration reply ("Thanks, Abid! …") | — | — | 101 | $0.00107 |
| Welcome and fixed questions | — | — | cached | no charge |

Soniox costs about **$10.58 per million spoken characters** (Priya at speed 1.1 speaks 19.1 characters per
second). DeepSeek caches the repeated parts of each prompt (instructions, schemas), which is why a product
question costs only about $0.0016 even though it sends about 6,000 prompt tokens.

### 7.3 Deployment (hosting)

Today Beacon runs on one laptop, so there is no hosting bill. On the website it needs a cloud server close to
Indian visitors. The plan below uses **AWS Mumbai**:

| Part | What runs there | Price |
|---|---|---|
| One Linux server (EC2) | Beacon workers: each worker is a Beacon server with its own signed-in Chrome and runs one live demo; one spare worker is always ready so "Start exploring" stays instant | by size, see below |
| Disk (40 GB gp3), daily backups (≈ 20 GB of snapshots), public IP address | Code, models, screen index, database files | $8.30 a month |
| PostgreSQL + pgvector | Same server (container) | no extra charge |
| Web proxy and HTTPS certificate (Caddy or Nginx, Let's Encrypt) | Same server | no extra charge |
| Data sent to visitors | 18–45 GB a month at 20–50 questions per user | inside AWS's free 100 GB |

**How the server size is chosen**

- Measured per live demo: about 1.6 GB of memory and up to ~0.9 CPU core while answering (≈ 0.3 core while the
  visitor reads or listens). Planned at 1.75 GB and 0.75 vCPU per demo, plus 1.5 GB and 0.5 vCPU for Linux,
  the database and the proxy.
- Visitor pace (assumption): 2 minutes to open and register, 45 seconds per product question (a 5-second
  answer, a 25-second spoken reply, reading and typing the next one), 15 seconds per business answer.
- Visitors arrive on working days, 10 hours a day; the busiest hour has twice the average traffic. The server
  runs enough demos for 95% of busiest-hour moments (Poisson model) plus one ready spare; anyone beyond that
  waits briefly for a free demo.

| Questions per user | Demo time per user | Demo hours per month | Demos at once (busiest hour + 1 ready) | Server | Server price | Disk, backups, IP address | **Hosting per month** |
|---|---|---|---|---|---|---|---|
| 0 | 2 min | 33 | 2 | c6a.xlarge (4 vCPU, 8 GB; up to 3 demos) | $68.25 (₹6,143) | $8.30 (₹747) | **$76.55 (₹6,890)** |
| 20 | 19 min | 317 | 7 | c6a.2xlarge (8 vCPU, 16 GB; up to 8 demos) | $136.51 (₹12,286) | $8.30 (₹747) | **$144.81 (₹13,033)** |
| 30 | 26 min | 442 | 9 | m6a.2xlarge (8 vCPU, 32 GB; up to 10 demos) | $162.21 (₹14,599) | $8.30 (₹747) | **$170.50 (₹15,345)** |
| 50 | 42 min | 692 | 12 | c6a.4xlarge (16 vCPU, 32 GB; up to 17 demos) | $273.02 (₹24,572) | $8.30 (₹747) | **$281.32 (₹25,319)** |

A cheaper alternative is DigitalOcean's Bangalore region: a Basic droplet with 8 vCPU and 16 GB is $96 a month
(shared CPU; disk and 6 TB of data included) and a CPU-Optimized one is $168 a month
([DigitalOcean pricing](https://www.digitalocean.com/pricing/droplets)). A 1-year AWS Savings Plan also lowers
the server price. Neither is counted in the totals.

**Before deploying (engineering work, no bill):** the code serves **one demo per server process** (a second
visitor gets "One demo is already active"). Running several demos needs a small router that gives each visitor a
free worker and keeps them on it, plus a "please wait" message when all workers are busy. Chrome needs Linux on
x86 (Google Chrome is not published for Linux on ARM).

### 7.4 Monthly cost for 1,000 users

Assumptions: every user opens the demo and registers; a user who asks questions also answers Beacon's 8
business questions once; voice replies are on (the default); visitors type. "Today" uses the free Microsoft Edge
voice; "with Soniox" uses the paid Soniox voice. Hosting is the AWS server above.

Monthly cost for 1,000 users, each asking the given number of product questions (visitors type; peak DeepSeek prices):

| Questions per user | Spoken characters | DeepSeek (AI answers) | Hosting (AWS) | Soniox voice | **Total today (Edge voice)** | **Total with Soniox voice** | DeepSeek off-peak saving |
|---|---|---|---|---|---|---|---|
| 0 | 0.10 M | $0.00 (₹0) | $76.55 (₹6,890) | $1.07 (₹96) | **$76.55 (₹6,890)** | **$77.62 (₹6,986)** | −$0.00 (₹0) |
| 20 | 10.03 M | $38.83 (₹3,495) | $144.81 (₹13,033) | $106.15 (₹9,554) | **$183.64 (₹16,528)** | **$289.80 (₹26,082)** | −$19.42 (₹1,748) |
| 30 | 14.82 M | $55.04 (₹4,954) | $170.50 (₹15,345) | $156.83 (₹14,115) | **$225.54 (₹20,299)** | **$382.38 (₹34,414)** | −$27.52 (₹2,477) |
| 50 | 24.40 M | $87.45 (₹7,871) | $281.32 (₹25,319) | $258.19 (₹23,238) | **$368.77 (₹33,189)** | **$626.97 (₹56,427)** | −$43.73 (₹3,935) |

If visitors also speak their questions (Soniox speech-to-text, microphone on during the conversation), add:

| Questions per user | Speech-to-text per month | Total today (Edge voice) with speech input | Total with Soniox voice and speech input |
|---|---|---|---|
| 0 | $0.00 (₹0) | $76.55 (₹6,890) | $77.62 (₹6,986) |
| 20 | $27.33 (₹2,460) | $210.97 (₹18,988) | $317.13 (₹28,542) |
| 30 | $39.36 (₹3,542) | $264.90 (₹23,841) | $421.74 (₹37,956) |
| 50 | $63.41 (₹5,707) | $432.18 (₹38,896) | $690.38 (₹62,134) |

**Reading the tables**

- **Hosting is the largest fixed cost**: about $77 a month even with no questions, rising to $281 when every
  user asks 50 questions, because more demos run at the same time.
- **With Soniox, the voice is the largest per-question cost**: about $0.005 per spoken answer versus $0.0016 for
  all the AI calls behind it. With the free Edge voice, or for visitors who turn voice off, this cost is zero.
- Moving from the free Edge voice to Soniox adds about $106 a month at 20 questions per user, $157 at 30 and
  $258 at 50.
- If most traffic falls outside DeepSeek's peak windows, the DeepSeek column halves (last column).
- Without hosting, one product question costs about **$0.0072 with Soniox** (≈ $0.0022 with the free Edge
  voice), including the business answers and registration around it.

### 7.5 Not included in the tables

| Item | Notes |
|---|---|
| Leadrat CRM | The demo uses an existing test tenant; no extra licence counted. |
| Taxes | Prices exclude GST and other taxes. |
| Discounts and credits | AWS Savings Plans, Soniox or DeepSeek credits: not counted. |
| A second server | Running two servers for redundancy roughly doubles the server price. |
| Engineering time | The multi-demo router and the deployment work above. |

### 7.6 Recompute

`python eval/cost_model.py` prints the tables above. Edit `PRICES` and `SERVERS` when providers change prices,
`MEASURED` after re-measuring a session, and `ASSUME` if visitor behaviour differs (session length, busy hours).

## 8. Sources

- DeepSeek API pricing: https://api-docs.deepseek.com/quick_start/pricing
- Soniox pricing: https://soniox.com/pricing
- Soniox text-to-speech WebSocket API: https://soniox.com/docs/api-reference/tts/websocket-api
- Soniox TTS models and voices: https://soniox.com/docs/tts/models, `GET https://api.soniox.com/v1/tts-models`
- Soniox WebSocket authentication: https://soniox.com/docs/guides/websocket-authentication
- Soniox India region (limited availability): https://soniox.com/blog/india-region
- AWS EC2 on-demand pricing (Mumbai; 100 GB free data transfer out): https://aws.amazon.com/ec2/pricing/on-demand/
- AWS EBS pricing: https://aws.amazon.com/ebs/pricing/
- AWS VPC pricing (public IPv4 address): https://aws.amazon.com/vpc/pricing/
- DigitalOcean droplet pricing: https://www.digitalocean.com/pricing/droplets
