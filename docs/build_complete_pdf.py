"""Builds the complete Beacon documentation PDF (product, demo video, architecture, tech stack, detailed costs).

Usage: python docs/build_complete_pdf.py
Every cost figure is computed by eval/cost_model.py, so the PDF always matches the cost model.
Output: docs/Beacon_Complete_Documentation.pdf (and a copy next to the demo video).
"""
import asyncio, importlib.util, shutil
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'docs' / 'Beacon_Complete_Documentation.pdf'
VIDEO_COPY = ROOT / 'Beacon Video Demo' / 'Beacon_Complete_Documentation.pdf'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

cost = load('cost_model', ROOT / 'eval' / 'cost_model.py')
base = load('build_pdf', ROOT / 'docs' / 'build_pdf.py')   # architecture diagram + shared styling
P, M, A = cost.PRICES, cost.MEASURED, cost.ASSUME
FX = P['usd_inr']

def usd(v, d=2): return f"${v:,.{d}f}"
def inr(v, d=0): return f"₹{v * FX:,.{d}f}"
def both(v, d=2, di=0): return f"{usd(v, d)} <span class='inr'>({inr(v, di)})</span>"
def rows(data): return ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in data)
def table(head, data, cls=''):
    return f"<table class='{cls}'><thead><tr>{''.join(f'<th>{h}</th>' for h in head)}</tr></thead><tbody>{rows(data)}</tbody></table>"

def monthly(q, users=1000, speaking=False, peak=True):
    u = cost.per_user(q, peak=peak, speaking=speaking); h = cost.hosting(q, users)
    ai, tts, stt, host = u['llm'] * users, u['soniox'] * users, u['stt'] * users, h['total']
    return dict(ai=ai, tts=tts, stt=stt, host=host, h=h, edge=ai + host + stt, soniox=ai + tts + host + stt)

# ---------------------------------------------------------------------------------------------- cost sections
def unit_costs():
    plan = M['llm_plan_calls_per_turn'] * M['llm_plan_call_peak']
    ans, chk = M['llm_answer_call_peak'], M['llm_check_call_peak']
    tts_q = cost.soniox_tts(M['tts_chars_product_question'])
    stt_q = cost.stt(M['stt_seconds_product_question'])
    ai_q = plan + ans + chk
    data = [
        ['DeepSeek · understand &amp; plan (≈1.25 calls)', both(plan, 5, 2), 'Every question'],
        ['DeepSeek · grounded answer from the handbook', both(ans, 5, 2), 'Every question'],
        ['DeepSeek · source check of the answer', both(chk, 5, 2), 'Every question'],
        ['<b>AI subtotal</b>', f"<b>{both(ai_q, 5, 2)}</b>", ''],
        [f"Spoken reply · Microsoft Edge voice ({M['tts_chars_product_question']} characters)", '$0.00000 <span class="inr">(₹0.00)</span>', 'Option A (today)'],
        [f"Spoken reply · Soniox voice ({M['tts_chars_product_question']} characters)", both(tts_q, 5, 2), 'Option B'],
        [f"Visitor speaks the question · Soniox speech-to-text ({M['stt_seconds_product_question']:.0f} s of audio)", both(stt_q, 5, 2), 'Only if the visitor uses the mic'],
        ['<b>Total · Option A (Edge voice, typed)</b>', f"<b>{both(ai_q, 5, 2)}</b>", ''],
        ['<b>Total · Option B (Soniox voice, typed)</b>', f"<b>{both(ai_q + tts_q, 5, 2)}</b>", ''],
        ['<b>Total · Option C (Soniox voice + spoken question)</b>', f"<b>{both(ai_q + tts_q + stt_q, 5, 2)}</b>", ''],
    ]
    return table(['Part of one product question', 'Cost (peak prices)', 'When it applies'], data, 'num2')

def journey():
    data = []
    for q in (0, 5, 10, 20, 30, 50):
        u = cost.per_user(q); s = cost.per_user(q, speaking=True)
        data.append([f'<b>{q}</b>', f"{cost.demo_minutes(q):.0f} min", both(u['llm'], 4, 2), both(u['soniox'], 4, 2), both(s['stt'], 4, 2),
                     f"<b>{both(u['llm'], 4, 2)}</b>", f"<b>{both(u['llm'] + u['soniox'], 4, 2)}</b>", f"<b>{both(u['llm'] + u['soniox'] + s['stt'], 4, 2)}</b>"])
    return table(['Product questions', 'Time in demo', 'DeepSeek (AI)', 'Soniox voice', 'Speech-to-text', 'A · Edge voice', 'B · Soniox voice', 'C · Soniox + speech'], data, 'wide num')

def hosting_table(users=1000):
    data = []
    for q in (0, 10, 20, 30, 50):
        h = cost.hosting(q, users); vcpu, ram, hr = cost.SERVERS[h['server']]
        server = (f"{h['count']} × " if h['count'] > 1 else '') + f"{h['server']}<br><span class='mut'>{vcpu} vCPU · {ram} GB · up to {h['capacity']} demos</span>"
        data.append([f'<b>{q}</b>', f"{h['hours']:,.0f}", str(h['demos']), server, both(h['compute']), both(h['extras']), f"<b>{both(h['total'])}</b>", f"{h['egress_gb']:.0f} GB"])
    return table(['Questions per user', 'Demo hours / month', 'Demos at once*', 'AWS server (Mumbai)', 'Server', 'Disk, backups, IP', 'Hosting / month', 'Data out'], data, 'wide num')

def fixed_parts():
    disk = A['disk_gb'] * P['ebs_gp3_per_gb_month']; snap = A['snapshot_gb'] * P['ebs_snapshot_per_gb_month']; ip = P['public_ipv4_per_hour'] * P['hours_per_month']
    return table(['Fixed part of every deployment', 'Size', 'Price', 'Per month'], [
        ['System disk (EBS gp3)', f"{A['disk_gb']} GB", f"${P['ebs_gp3_per_gb_month']} / GB-month", both(disk)],
        ['Daily backups (EBS snapshots)', f"≈{A['snapshot_gb']} GB", f"${P['ebs_snapshot_per_gb_month']} / GB-month", both(snap)],
        ['Public IPv4 address', '1', f"${P['public_ipv4_per_hour']} / hour", both(ip)],
        ['PostgreSQL + pgvector, web proxy, HTTPS (Let’s Encrypt)', 'same server', 'free', '$0.00'],
        ['Data sent to visitors', 'up to 100 GB', 'first 100 GB free', '$0.00'],
        ['<b>Total fixed extras</b>', '', '', f"<b>{both(disk + snap + ip)}</b>"],
    ], 'num')

def options_table(users=1000):
    data = []
    for q in (0, 10, 20, 30, 50):
        m = monthly(q, users); s = monthly(q, users, speaking=True)
        data.append([f'<b>{q}</b>', both(m['host']), both(m['ai']), both(m['tts']), both(s['stt']),
                     f"<b>{both(m['edge'])}</b>", f"<b>{both(m['soniox'])}</b>", f"<b>{both(s['soniox'])}</b>"])
    return table(['Questions per user', 'Hosting (AWS)', 'DeepSeek (AI)', 'Soniox voice', 'Speech-to-text', 'A · Edge voice<br>(free) + hosting', 'B · Soniox voice<br>+ hosting', 'C · Soniox voice<br>+ speech input'], data, 'wide num')

def share_table(users=1000, q=20):
    m = monthly(q, users)
    def pct(v, tot): return f"{v / tot * 100:.0f}%"
    return table(['Where the money goes (1,000 users × 20 questions)', 'Option A · Edge voice', 'Share', 'Option B · Soniox voice', 'Share'], [
        ['Hosting (AWS Mumbai)', both(m['host']), pct(m['host'], m['edge']), both(m['host']), pct(m['host'], m['soniox'])],
        ['DeepSeek (AI answers)', both(m['ai']), pct(m['ai'], m['edge']), both(m['ai']), pct(m['ai'], m['soniox'])],
        ['Voice (text-to-speech)', '$0.00 (free)', '0%', both(m['tts']), pct(m['tts'], m['soniox'])],
        ['<b>Total per month</b>', f"<b>{both(m['edge'])}</b>", '100%', f"<b>{both(m['soniox'])}</b>", '100%'],
    ], 'num')

def scale_table(q=20):
    data = []
    for n in (250, 500, 1000, 2500, 5000):
        m = monthly(q, n); h = m['h']
        server = (f"{h['count']} × " if h['count'] > 1 else '') + h['server']
        data.append([f'<b>{n:,}</b>', server, both(m['host']), both(m['ai']), both(m['tts']), f"<b>{both(m['edge'])}</b>", f"<b>{both(m['soniox'])}</b>",
                     f"{inr(m['edge'] / n, 1)} / {inr(m['soniox'] / n, 1)}"])
    return table(['Users / month', 'Server', 'Hosting', 'DeepSeek', 'Soniox voice', 'A · Edge voice', 'B · Soniox voice', 'Per user (A / B)'], data, 'wide num')

def annual_table(users=1000):
    data = []
    for q in (0, 20, 30, 50):
        m = monthly(q, users); s = monthly(q, users, speaking=True)
        data.append([f'<b>{q}</b>', both(m['edge'] * 12), both(m['soniox'] * 12), both(s['soniox'] * 12), both((m['soniox'] - m['edge']) * 12)])
    return table(['Questions per user', 'A · Edge voice / year', 'B · Soniox voice / year', 'C · Soniox + speech / year', 'Extra for Soniox voice / year'], data, 'num')

def offpeak_table(users=1000):
    data = []
    for q in (20, 30, 50):
        pk = monthly(q, users); op = monthly(q, users, peak=False)
        data.append([f'<b>{q}</b>', both(pk['ai']), both(op['ai']), both(pk['ai'] - op['ai']), both(op['edge']), both(op['soniox'])])
    return table(['Questions per user', 'DeepSeek at peak', 'DeepSeek off-peak', 'Saving / month', 'A · Edge total off-peak', 'B · Soniox total off-peak'], data, 'num')

# ------------------------------------------------------------------------------------------------- document
def body():
    m20 = monthly(20); s20 = monthly(20, speaking=True)
    ai_q = M['llm_plan_calls_per_turn'] * M['llm_plan_call_peak'] + M['llm_answer_call_peak'] + M['llm_check_call_peak']
    tts_q = cost.soniox_tts(M['tts_chars_product_question'])
    return f"""
<header class="cover"><span class="mark">b.</span><span class="brand">Beacon by Leadrat</span>
<h1>Complete documentation</h1><div class="sub">Live demo · how it works · technology stack · detailed cost analysis — prices as of 16 October 2026</div></header>

<p><b>Beacon</b> is an AI product guide for the Leadrat website. A visitor clicks <b>Start exploring</b>, sees the real Leadrat CRM live on the left
of a popup and talks to Beacon on the right, by typing or by voice. Beacon answers from the company's product handbook, opens and highlights the
matching CRM screen while it explains, speaks the answer, asks follow-up questions about the visitor's business, and saves the visitor as a lead
in the CRM tenant (today: <b>surya</b>).</p>

<h2 class="plain">At a glance</h2>
<div class="cards">
  <div class="card"><div class="k">AI model</div><div class="v">DeepSeek V4.1 Flash</div><div class="d">3 calls per question: understand, answer from the handbook, check the answer</div></div>
  <div class="card"><div class="k">Vector database</div><div class="v">PostgreSQL + pgvector</div><div class="d"><b>384-dimension</b> vectors, multilingual (incl. Hinglish), hybrid with keyword search</div></div>
  <div class="card"><div class="k">Voice</div><div class="v">Soniox (or free Edge voice)</div><div class="d">Speech-to-text stt-rt-v5 · text-to-speech tts-rt-v2</div></div>
  <div class="card"><div class="k">Leads</div><div class="v">Saved to tenant “surya”</div><div class="d">Leadrat API; any tenant can be configured</div></div>
</div>
<table class="sum"><thead><tr><th>Cost at a glance (1,000 users / month, 20 questions each)</th><th>Per month</th><th>Per year</th></tr></thead><tbody>
<tr><td>A · Free Microsoft Edge voice + AWS hosting</td><td><b>{both(m20['edge'])}</b></td><td>{both(m20['edge'] * 12)}</td></tr>
<tr><td>B · Soniox voice + AWS hosting</td><td><b>{both(m20['soniox'])}</b></td><td>{both(m20['soniox'] * 12)}</td></tr>
<tr><td>C · Soniox voice + visitors speak their questions</td><td><b>{both(s20['soniox'])}</b></td><td>{both(s20['soniox'] * 12)}</td></tr>
<tr><td>One product question, averaged over a visit (Edge voice / Soniox voice)</td><td colspan="2">{both(cost.per_user(20)['llm'] / 20, 4, 2)} / {both((cost.per_user(20)['llm'] + cost.per_user(20)['soniox']) / 20, 4, 2)}</td></tr>
</tbody></table>
<p class="note">Prices exclude GST. $1 = ₹{FX:.0f} (planning rate). DeepSeek at peak prices (worst case). Full details in section 8.</p>

<h2 class="break">1. What the demo video shows</h2>
<p>The video <code>Beacon_Demo_Video.mp4</code> (7 min 27 s) is a real screen recording of the product with Beacon's own voice, plus a short
voice-over and animated explanations.</p>
{table(['Time', 'What happens', 'What it proves'], [
 ['0:00', 'Intro: what Beacon is', '—'],
 ['0:14', 'Visitor fills name, work email and phone; Beacon greets them by name', 'Registration in the widget, phone validated with country code'],
 ['0:42', 'The Surya CRM: the new lead appears with name, phone, email and Source = Website', 'Details are saved to a specific tenant (surya); any tenant can be configured'],
 ['0:59', 'Typed question: “tell me about Sales Copilot”', 'Beacon opens the Sales Copilot page live and answers only from the handbook'],
 ['1:46', 'Spoken question about bulk operations (microphone)', 'Soniox speech-to-text; Beacon selects leads and shows bulk actions without running them'],
 ['2:47', 'Question about Leadrat AI', 'Opens the Leadrat AI page, explains tenant permissions'],
 ['3:29', 'Beacon asks its follow-up questions; the visitor answers', 'Business type, team size, monthly leads, tools, problem, decision, timeline, contact consent → lead score'],
 ['4:57', '“How do I add a lead?”', 'Opens the Add Lead form; saves only after the visitor confirms'],
 ['5:41', 'Animated explanation of the architecture, tech stack, vector database and costs', 'Sections 2–8 of this document'],
])}

<h2>2. How it works</h2>
{base.diagram()}
<ol>
<li>The widget sends the visitor's message. If Beacon is still speaking, the new question interrupts it.</li>
<li>Local search (≈5 ms): hybrid search over the handbook and the CRM screen map (2,054 screens from the CRM code + 38 prepared walkthroughs).</li>
<li><b>DeepSeek “plan”</b>: decides what the visitor means (product question, business answer, small talk, refusal, data-change request) and which screen to show.</li>
<li>The hidden Chrome browser opens and highlights that screen <b>while</b> the answer is written.</li>
<li><b>DeepSeek “answer”</b>: writes the reply only from selected handbook passages and screen facts.</li>
<li><b>DeepSeek “check”</b>: verifies every claim against those passages; meanwhile the voice is already being generated.</li>
<li>The widget shows the text and plays the voice as it streams; the live screen shows the walkthrough.</li>
</ol>
<p><b>Safety rules in the code:</b> the demo browser can only navigate and highlight; the only write is Add Lead, saved after an explicit
confirmation; bulk actions and Delete are pointed at, never clicked; a command to change CRM data is refused; contact details go to sales only with consent.</p>

<h2>3. Technology stack</h2>
{table(['Layer', 'Technology', 'Used for'], [
 ['Backend', 'Python 3.11, FastAPI 0.141, Uvicorn 0.53', 'Session API, widget files'],
 ['Conversation engine', 'LangGraph 1.2', 'Turn pipeline: context → plan → grounded answer → check → save'],
 ['Language model', 'DeepSeek API, <code>deepseek-flash</code> (V4.1 Flash)', 'Understanding, answers, source checks, lead facts (JSON mode)'],
 ['Live CRM', 'Playwright 1.58 + Google Chrome (headless)', 'Signs in, navigates, highlights; frames sent as JPEG'],
 ['Embeddings', 'paraphrase-multilingual-MiniLM-L12-v2, INT8 ONNX on ONNX Runtime', '384-dimension vectors, 50+ languages incl. Hinglish'],
 ['Vector database', 'PostgreSQL + pgvector (deployment); SQLite + NumPy (local today)', 'Handbook passages, conversation state'],
 ['Speech-to-text', 'Soniox real-time <code>stt-rt-v5</code>', 'Visitor voice → text (English, Hindi, Hinglish)'],
 ['Noise cleanup', 'RNNoise (web-noise-suppressor 0.4.1)', 'Removes background noise before Soniox'],
 ['Text-to-speech', 'Soniox real-time <code>tts-rt-v2</code>, voice Priya', 'Beacon’s spoken replies (streamed MP3)'],
 ['Backup / free voice', 'Microsoft Edge read-aloud (<code>edge-tts</code> 7.3.1)', 'Free voice today; backup if Soniox fails'],
 ['Widget', 'HTML, CSS, JavaScript, intl-tel-input', 'Popup UI, phone field, streaming audio'],
 ['Registration', 'Leadrat API (tenant <b>surya</b>), phonenumbers', 'Visitor saved as a CRM lead in the background'],
])}

<h2>4. Knowledge search and the vector database</h2>
{table(['Item', 'Value'], [
 ['Embedding model', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, INT8-quantised ONNX, runs on the CPU (no GPU, no per-call cost)'],
 ['<b>Vector dimension</b>', '<b>384</b> (float32), normalised, cosine similarity'],
 ['Handbook', 'FLOE Leadrat Pre-Sales Product Knowledge Handbook v0.2 (29 pages) → 139 passages, 13 modules'],
 ['CRM screens', '2,054 screens/sections + 38 walkthroughs = 2,092 entries × 384 dimensions'],
 ['Database (deployment)', 'PostgreSQL with <b>pgvector</b>: column <code>vector(384)</code>, cosine distance operator <code>&lt;=&gt;</code>; exact search'],
 ['Database (local today)', 'SQLite file + in-memory NumPy search'],
 ['Search method', 'Hybrid: vector similarity + BM25 keywords, merged with reciprocal rank fusion (k = 60); Hinglish is romanised first'],
 ['Speed', '≈5 ms of CPU per question'],
])}
<p>The model never sees the whole handbook: each question gets the best few passages, the model must cite them, and a second call checks the answer.</p>

<h2>5. Voice</h2>
<ul>
<li><b>Visitor → Beacon:</b> Soniox <code>stt-rt-v5</code> streamed from the browser with a single-use 60-second key (the real key never reaches the browser). RNNoise cleans the microphone first.</li>
<li><b>Beacon → visitor:</b> Soniox <code>tts-rt-v2</code> (voice Priya) over one warm WebSocket; up to five sentences generated in parallel; audio plays while it is still being generated.</li>
<li><b>Fixed sentences</b> (welcome, follow-up and business questions) are generated once and cached, so they cost nothing per visitor.</li>
<li><b>Microsoft Edge voice</b> is free but unofficial (no contract or guarantee; an older version was blocked with HTTP 403 in October 2026). Soniox is the licensed, paid option.</li>
</ul>

<h2>6. Measured speed and resources</h2>
{table(['What', 'Measured'], [
 ['Click “Start exploring” → live CRM visible', '55–245 ms'],
 ['Product question → answer text', '3.3–4.7 s (three DeepSeek calls)'],
 ['Answer text → voice starts (Soniox)', '45–77 ms'],
 ['Memory per live demo', '1.45 GB at start, 1.61 GB after 8 questions'],
 ['CPU per live demo', '≈0.3 core while the visitor reads, up to 0.94 core while answering'],
 ['Data sent to the visitor', '≈0.9 MB per product question'],
])}

<h2>7. Leads, tenant and qualification</h2>
<ul>
<li>The registration form (name, work email, phone with country code) is validated and saved through the Leadrat API to the configured tenant — in the demo, <b>surya</b> (Surya QA). The tenant, API address and credentials are settings, so any company tenant can be used.</li>
<li>The lead is created with Source = Website; a duplicate check by phone number runs first; the demo continues without waiting for the save.</li>
<li>Beacon then asks business questions once each — business type, team size, monthly leads, current tool, biggest problem, decision role, timeline, sales contact — and scores the lead. Sales contact happens only with the visitor's consent.</li>
</ul>

<h2 class="break">8. Detailed cost analysis</h2>
<p>Beacon has three kinds of cost: <b>AI</b> (DeepSeek, per question), <b>voice</b> (free Microsoft Edge voice, or Soniox per spoken character;
optional Soniox speech-to-text when visitors speak), and <b>deployment</b> (an AWS server in Mumbai, a fixed monthly bill sized for how many demos run at the same time).
Three options are compared everywhere:</p>
{table(['Option', 'Voice the visitor hears', 'Visitor input', 'Licensing'], [
 ['<b>A</b>', 'Microsoft Edge voice — free', 'Typing', 'Unofficial, no guarantee'],
 ['<b>B</b>', 'Soniox voice (Priya)', 'Typing', 'Licensed, paid per use'],
 ['<b>C</b>', 'Soniox voice (Priya)', 'Speaking (microphone)', 'Licensed, paid per use'],
])}

<h3>8.1 Prices used</h3>
{table(['Service', 'Price', 'Source'], [
 ['DeepSeek <code>deepseek-flash</code>', 'Per 1M tokens (peak): cached input $0.006, uncached input $0.30, output $1.20. Off-peak is half.', 'api-docs.deepseek.com/quick_start/pricing'],
 ['Soniox text-to-speech <code>tts-rt-v2</code>', '$4 / 1M text tokens + $21.50 / 1M audio tokens ≈ <b>$0.70 per hour of speech</b> ≈ $10.58 per 1M spoken characters', 'soniox.com/pricing'],
 ['Soniox speech-to-text <code>stt-rt-v5</code>', '<b>$0.12 per hour</b> of audio', 'soniox.com/pricing'],
 ['Microsoft Edge voice', '<b>Free</b>', '—'],
 ['AWS EC2 Mumbai (on demand, Linux)', 'c6a.xlarge $0.0935/h · c6a.2xlarge $0.187/h · m6a.2xlarge $0.2222/h · c6a.4xlarge $0.374/h', 'aws.amazon.com/ec2/pricing'],
 ['AWS disk, backups, IP', 'EBS gp3 $0.0912/GB-month · snapshots $0.05/GB-month · IPv4 $0.005/h', 'aws.amazon.com/ebs/pricing, /vpc/pricing'],
 ['AWS data to the internet', 'First 100 GB a month free', 'aws.amazon.com/ec2/pricing'],
])}
<p class="note">DeepSeek peak hours: 01:00–04:00 and 06:00–10:00 UTC Mon–Fri (06:30–09:30 and 11:30–15:30 IST). Repeated prompt parts are cached, which is why a question that sends ≈6,000 prompt tokens costs so little.</p>

<h3>8.2 Cost of one product question</h3>
{unit_costs()}
<p class="note">Answers to Beacon's business questions are cheaper: {both(cost.llm_answer(), 5, 2)} AI and {both(cost.soniox_tts(M['tts_chars_business_answer']), 5, 2)} Soniox voice each.
The welcome and Beacon's fixed questions are cached and cost nothing per visitor. Averaged over a full visit (each question plus the business answers and registration around it), one question costs
{both(cost.per_user(20)['llm'] / 20, 4, 2)} with the Edge voice and {both((cost.per_user(20)['llm'] + cost.per_user(20)['soniox']) / 20, 4, 2)} with the Soniox voice — the ₹0.65 shown in the video.</p>

<h3>8.3 Cost of one visitor journey (without hosting)</h3>
<p>One visitor registers, asks N product questions and, if they ask any, answers Beacon's 8 business questions once.</p>
{journey()}

<h3>8.4 Deployment cost (hosting)</h3>
<p>Each live demo needs its own signed-in Chrome browser: measured ≈1.6 GB of memory and up to ≈0.9 CPU core while answering. The server is sized
for the busiest hour (twice the average traffic, working days, 10 hours a day), so 95% of busiest-hour moments are served at once, plus one spare demo kept
ready so “Start exploring” stays instant. The cheapest AWS Mumbai server that fits is chosen.</p>
{hosting_table()}
<p class="note">* Demos running at the same time in the busiest hour, plus one ready. Visitor pace assumed: 2 min to register, 45 s per product question, 15 s per business answer.</p>
{fixed_parts()}
<p><b>Cheaper hosting alternatives (not in the totals):</b> DigitalOcean Bangalore — 8 vCPU / 16 GB Basic droplet $96/month (shared CPU, disk and 6 TB data included),
CPU-Optimized $168/month; an AWS 1-year Savings Plan also lowers the server price. <b>One-time engineering (no bill):</b> today one server process runs one demo;
production needs a small router that gives each visitor a free worker, and a “please wait” message when all are busy.</p>

<h3>8.5 Monthly total for 1,000 users — all options, deployment included</h3>
{options_table()}
{share_table()}
<p><b>Reading the numbers:</b> hosting is the largest fixed cost (≈$77/month even with no questions). With the free Edge voice, AI is the only usage cost.
With Soniox, the voice becomes the largest usage cost — about {both(tts_q, 4, 2)} per spoken answer versus {both(ai_q, 4, 2)} for all AI calls behind it.
Moving from Edge to Soniox adds {both(m20['soniox'] - m20['edge'])} a month at 20 questions per user.</p>

<h3>8.6 Scaling with the number of users (20 questions each)</h3>
{scale_table()}
<p class="note">More users need more demos at the same time, so the server grows in steps. Data sent to visitors stays inside AWS's free 100 GB up to 5,000 users × 20 questions (≈90 GB).</p>

<h3>8.7 Annual cost for 1,000 users a month</h3>
{annual_table()}

<h3>8.8 Saving by running outside DeepSeek peak hours</h3>
{offpeak_table()}

<h3>8.9 Edge voice vs Soniox voice</h3>
{table(['', 'A · Microsoft Edge voice', 'B/C · Soniox voice'], [
 ['Price', 'Free', f"≈{both(tts_q, 4, 2)} per spoken answer; {both(m20['tts'])} / month at 1,000 users × 20 questions"],
 ['Licence and reliability', 'Unofficial use of a browser read-aloud service; no contract; can be blocked (HTTP 403 seen in Oct 2026)', 'Commercial API with an account and pricing'],
 ['Speed', 'First audio 530–600 ms', 'First audio 480–550 ms; 45–77 ms after the text appears (generated during the source check)'],
 ['Voice', 'en-IN Neerja', 'Priya (Indian English), consistent with Soniox speech-to-text'],
 ['Recommendation', 'Fine for internal demos and testing', 'Recommended for the public website'],
])}

<h3>8.10 Not included in the totals</h3>
<ul>
<li>Taxes (e.g. 18% GST), discounts and credits.</li>
<li>Leadrat CRM licence — the demo uses an existing test tenant.</li>
<li>A second server for redundancy (roughly doubles the server price).</li>
<li>Engineering time for the multi-demo router and deployment.</li>
<li>Data transfer above 100 GB a month (only beyond ≈5,000 users × 20 questions).</li>
</ul>

<h2>9. Assumptions and sources</h2>
<ul>
<li>Measured on 16 October 2026: a 16-turn session (8 product questions + 8 business answers, 36 DeepSeek calls, 4,185 new spoken characters) and an 8-question session for memory, CPU and bandwidth.</li>
<li>Spoken characters: {M['tts_chars_product_question']} per product answer, {M['tts_chars_business_answer']} per business answer, {M['tts_chars_registration']} for the registration reply; Soniox Priya at speed 1.1 speaks {M['soniox_chars_per_second']} characters per second.</li>
<li>Visitors arrive on working days, 10 hours a day; the busiest hour has twice the average traffic; 95% of busiest-hour moments served at once plus one ready demo.</li>
<li>Exchange rate $1 = ₹{FX:.0f}; prices exclude taxes; DeepSeek at peak prices unless stated.</li>
<li>All tables are produced by <code>eval/cost_model.py</code>; re-run <code>python docs/build_complete_pdf.py</code> after any price change.</li>
</ul>
<p class="note">Sources: api-docs.deepseek.com/quick_start/pricing · soniox.com/pricing · soniox.com/docs · aws.amazon.com/ec2/pricing/on-demand · aws.amazon.com/ebs/pricing ·
aws.amazon.com/vpc/pricing · digitalocean.com/pricing/droplets</p>
"""

CSS = base.CSS + """
.cards { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 8px 0 12px; }
.inr { color: #52636a; font-size: 92%; }
.mut { color: #5b7974; font-size: 92%; }
table.num td { white-space: nowrap; }
table.wide td { white-space: normal; }
table.num2 td:nth-child(2) { white-space: nowrap; }
"""

async def main():
    page_html = f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Beacon — complete documentation</title><style>{CSS}</style></head><body>{body()}</body></html>"
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel='chrome', headless=True)
        page = await browser.new_page()
        await page.set_content(page_html, wait_until='load')
        footer = ('<div style="width:100%;font:8px Segoe UI,Arial;color:#7a8a87;padding:0 15mm;display:flex;justify-content:space-between">'
                  '<span>Beacon · Complete documentation</span><span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>')
        await page.pdf(path=str(OUTPUT), format='A4', print_background=True, display_header_footer=True,
                       header_template='<div></div>', footer_template=footer,
                       margin={'top': '16mm', 'bottom': '18mm', 'left': '15mm', 'right': '15mm'})
        await browser.close()
    shutil.copyfile(OUTPUT, VIDEO_COPY)
    print(OUTPUT); print(VIDEO_COPY)

if __name__ == '__main__':
    asyncio.run(main())
