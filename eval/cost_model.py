"""Monthly running cost of Beacon from measured usage, for docs/TECH_STACK_AND_COSTS.md.

Usage: python eval/cost_model.py            (prints the Markdown tables used in the document)

Measured inputs come from sessions on 16 October 2026 (a 16-turn session: 8 product questions and 8 answers to
Beacon's business questions; an 8-question session for memory, CPU and bandwidth) and from
.state/api-usage.jsonl. Prices are list prices checked on 16 October 2026; they change, so update PRICES and
SERVERS before relying on the totals. Free items (the current Microsoft Edge voice, local search, the database
on the same server, SSL, monitoring) carry no price and are not listed as costs.
"""
import math

# ---- Prices (USD) -------------------------------------------------------------------------------
PRICES = {
    # DeepSeek deepseek-flash (DeepSeek-V4.1-Flash), per 1M tokens, api-docs.deepseek.com/quick_start/pricing.
    # Peak 01:00-04:00 and 06:00-10:00 UTC Mon-Fri (06:30-09:30 and 11:30-15:30 IST); off-peak is half.
    'llm_cache_hit_peak': 0.006, 'llm_cache_miss_peak': 0.30, 'llm_output_peak': 1.20,
    # Soniox, soniox.com/pricing: TTS input text $4 / 1M tokens, output audio $21.50 / 1M tokens;
    # 1 hour of speech = 30,000 audio tokens; 15,000 text tokens ~ 1 hour ~ 50,000 characters (0.3 token/char).
    'soniox_tts_text_per_m_tokens': 4.00, 'soniox_tts_audio_per_m_tokens': 21.50,
    'soniox_audio_tokens_per_hour': 30000, 'soniox_text_tokens_per_char': 0.3,
    # Soniox real-time speech-to-text (stt-rt-v5): $0.12 per hour of audio streamed.
    'soniox_stt_per_hour': 0.12,
    # AWS Asia Pacific (Mumbai), official price files published 15 October 2026: EBS gp3 storage, EBS snapshots,
    # and a public IPv4 address (aws.amazon.com/vpc/pricing). The first 100 GB a month sent to the internet is free.
    'ebs_gp3_per_gb_month': 0.0912, 'ebs_snapshot_per_gb_month': 0.05, 'public_ipv4_per_hour': 0.005,
    'free_egress_gb': 100,
    'hours_per_month': 730,
    'usd_inr': 90.0,  # planning rate; use the day's rate for real budgets
}

# AWS EC2 on-demand Linux, Asia Pacific (Mumbai): name -> (vCPU, GiB RAM, USD per hour). x86 (AMD), because
# Google Chrome for Linux, which the demo browser uses, is not published for ARM.
SERVERS = {
    'c6a.xlarge': (4, 8, 0.0935),
    'c6a.2xlarge': (8, 16, 0.187),
    'm6a.2xlarge': (8, 32, 0.2222),
    'c6a.4xlarge': (16, 32, 0.374),
}

# ---- Measured usage ------------------------------------------------------------------------------
MEASURED = {
    # Characters Beacon speaks that are not pre-recorded fixed sentences (those are synthesised once and cached).
    'tts_chars_product_question': 479,   # answer + screen confirmation (+ follow-up when not cached)
    'tts_chars_business_answer': 44,     # "Okay, a team of 25." etc.; the next question is cached
    'tts_chars_registration': 101,       # "Thanks, <name>! What would you like to explore first? ..."
    'soniox_chars_per_second': 19.1,     # Priya voice at speed 1.1, measured from generated MP3s
    # DeepSeek cost per call at peak prices, from the session's usage records.
    'llm_plan_call_peak': 0.00985 / 20,   # understanding/plan, screen choice, fact checks, control choice
    'llm_answer_call_peak': 0.00620 / 8,  # grounded handbook answer
    'llm_check_call_peak': 0.00184 / 8,   # source check of the answer
    'llm_plan_calls_per_turn': 20 / 16,
    'llm_qualification_peak': 0.000374,   # lead scoring extraction (historic average), about every 2nd answer
    # Microphone audio streamed per turn when the visitor talks instead of typing (talk mode listens
    # continuously, also while Beacon answers).
    'stt_seconds_product_question': 6 + 5 + 479 / 19.1,
    'stt_seconds_business_answer': 4 + 3 + 44 / 19.1 + 3,
    'business_answers_per_engaged_user': 8,  # Beacon asks each business question once
    # One live demo = one Beacon worker: Python server 554 MB + Playwright driver 81 MB + Chrome 0.8-1.0 GB.
    # Measured 1.45 GB at the start and 1.61 GB after 8 questions (Windows); 0.94 CPU cores while answering
    # questions back to back with no pause, about 0.3 core while the visitor reads or listens.
    'demo_ram_gb': 1.75, 'demo_vcpu': 0.75,
    # Data sent to the visitor per product question: live screen (82 KB JPEG frames; unchanged frames are a
    # 304 with no body), chat polling, and the MP3 voice (64 kbps).
    'mb_per_product_question': 0.9,
}

# ---- Assumptions (visitor behaviour; not measured) ------------------------------------------------
ASSUME = {
    'minutes_registration': 2.0,           # open, register, hear the welcome
    'minutes_per_product_question': 0.75,  # ~5 s answer + ~25 s spoken reply + reading and typing the next one
    'minutes_per_business_answer': 0.25,
    'busy_hours_per_month': 22 * 10,       # visitors arrive on working days, 10 hours a day
    'busiest_hour_factor': 2.0,            # the busiest hour has twice the average traffic
    'served_at_once': 0.95,                # size for 95% of busiest-hour moments; the rest wait for a free demo
    'spare_demos': 1,                      # one signed-in browser always ready, so "Start exploring" is instant
    'server_base_ram_gb': 1.5, 'server_base_vcpu': 0.5,  # Linux, PostgreSQL + pgvector, web proxy
    'disk_gb': 40, 'snapshot_gb': 20,      # system disk; daily backups (incremental snapshots)
}


def soniox_tts(chars):
    seconds = chars / MEASURED['soniox_chars_per_second']
    audio = seconds / 3600 * PRICES['soniox_audio_tokens_per_hour'] * PRICES['soniox_tts_audio_per_m_tokens'] / 1e6
    text = chars * PRICES['soniox_text_tokens_per_char'] * PRICES['soniox_tts_text_per_m_tokens'] / 1e6
    return audio + text

def stt(seconds):
    return seconds / 3600 * PRICES['soniox_stt_per_hour']

def llm_product(peak=True):
    m = MEASURED
    cost = m['llm_plan_calls_per_turn'] * m['llm_plan_call_peak'] + m['llm_answer_call_peak'] + m['llm_check_call_peak']
    return cost if peak else cost / 2

def llm_answer(peak=True):
    m = MEASURED
    cost = m['llm_plan_calls_per_turn'] * m['llm_plan_call_peak'] + m['llm_qualification_peak'] / 2
    return cost if peak else cost / 2

def answers(questions):
    return MEASURED['business_answers_per_engaged_user'] if questions else 0

def per_user(questions, peak=True, speaking=False):
    """Cost of one visitor who registers, asks `questions` product questions and, if they ask any,
    answers Beacon's business questions once. Voice replies are on (the default)."""
    m = MEASURED
    chars = m['tts_chars_registration'] + questions * m['tts_chars_product_question'] + answers(questions) * m['tts_chars_business_answer']
    llm = questions * llm_product(peak) + answers(questions) * llm_answer(peak)
    mic = stt(questions * m['stt_seconds_product_question'] + answers(questions) * m['stt_seconds_business_answer']) if speaking else 0
    return {'chars': chars, 'llm': llm, 'stt': mic, 'soniox': soniox_tts(chars)}

# ---- Hosting ------------------------------------------------------------------------------------------
def poisson_quantile(mean, q):
    """Smallest k with P(X <= k) >= q for Poisson(mean): how many demos run at once in the busiest hour."""
    k, p = 0, math.exp(-mean)
    total = p
    while total < q:
        k += 1; p *= mean / k; total += p
    return k

def demo_minutes(questions):
    a = ASSUME
    return a['minutes_registration'] + questions * a['minutes_per_product_question'] + answers(questions) * a['minutes_per_business_answer']

def demos_needed(questions, users):
    hours = users * demo_minutes(questions) / 60
    busiest = hours / ASSUME['busy_hours_per_month'] * ASSUME['busiest_hour_factor']
    return max(1, poisson_quantile(busiest, ASSUME['served_at_once'])) + ASSUME['spare_demos'], hours

def capacity(server):
    vcpu, ram, _ = SERVERS[server]
    a, m = ASSUME, MEASURED
    return int(min((ram - a['server_base_ram_gb']) / m['demo_ram_gb'], (vcpu - a['server_base_vcpu']) / m['demo_vcpu']))

def hosting(questions, users=1000):
    demos, hours = demos_needed(questions, users)
    # The cheapest single server that runs every demo needed at the busiest hour; several of the largest otherwise.
    fitting = [s for s in SERVERS if capacity(s) >= demos]
    name = min(fitting, key=lambda s: SERVERS[s][2]) if fitting else max(SERVERS, key=capacity)
    count = 1 if fitting else math.ceil(demos / capacity(name))
    compute = count * SERVERS[name][2] * PRICES['hours_per_month']
    extras = count * (ASSUME['disk_gb'] * PRICES['ebs_gp3_per_gb_month'] + ASSUME['snapshot_gb'] * PRICES['ebs_snapshot_per_gb_month']
                      + PRICES['public_ipv4_per_hour'] * PRICES['hours_per_month'])
    egress_gb = users * questions * MEASURED['mb_per_product_question'] / 1000
    assert egress_gb <= PRICES['free_egress_gb'], 'add the AWS data-transfer price above 100 GB a month'
    return {'demos': demos, 'hours': hours, 'server': name, 'count': count, 'capacity': capacity(name),
            'compute': compute, 'extras': extras, 'total': compute + extras, 'egress_gb': egress_gb}

def money(usd):
    return f"${usd:,.2f} (₹{usd * PRICES['usd_inr']:,.0f})"

def tables(users=1000, scenarios=(0, 20, 30, 50)):
    out = []
    m = MEASURED
    out.append('| Per unit | Soniox voice |')
    out.append('|---|---|')
    out.append(f"| 1 million spoken characters | ${soniox_tts(1e6):.2f} |")
    out.append(f"| One product question ({m['tts_chars_product_question']} characters) | ${soniox_tts(m['tts_chars_product_question']):.5f} |")
    out.append(f"| One answer to a business question ({m['tts_chars_business_answer']} characters) | ${soniox_tts(m['tts_chars_business_answer']):.5f} |")
    out.append('')
    out.append(f'Server needed for {users:,} users a month (AWS Mumbai, on demand):')
    out.append('')
    out.append('| Questions per user | Demo time per user | Demo hours per month | Demos at once (busiest hour + 1 ready) | Server | Server price | Disk, backups, IP address | **Hosting per month** |')
    out.append('|---|---|---|---|---|---|---|---|')
    for q in scenarios:
        h = hosting(q, users); vcpu, ram, _ = SERVERS[h['server']]
        server = f"{h['count']} × " if h['count'] > 1 else ''
        out.append(f"| {q} | {demo_minutes(q):.0f} min | {h['hours']:,.0f} | {h['demos']} | {server}{h['server']} ({vcpu} vCPU, {ram} GB; up to {h['capacity']} demos) | {money(h['compute'])} | {money(h['extras'])} | **{money(h['total'])}** |")
    out.append('')
    out.append(f'Monthly cost for {users:,} users, each asking the given number of product questions (visitors type; peak DeepSeek prices):')
    out.append('')
    out.append('| Questions per user | Spoken characters | DeepSeek (AI answers) | Hosting (AWS) | Soniox voice | **Total today (Edge voice)** | **Total with Soniox voice** | DeepSeek off-peak saving |')
    out.append('|---|---|---|---|---|---|---|---|')
    for q in scenarios:
        u = per_user(q); off = per_user(q, peak=False); h = hosting(q, users)
        n = users
        out.append(f"| {q} | {u['chars'] * n / 1e6:,.2f} M | {money(u['llm'] * n)} | {money(h['total'])} | {money(u['soniox'] * n)} | **{money(u['llm'] * n + h['total'])}** | **{money((u['llm'] + u['soniox']) * n + h['total'])}** | −{money((u['llm'] - off['llm']) * n)} |")
    out.append('')
    out.append('If visitors also speak their questions (Soniox speech-to-text, microphone on during the conversation), add:')
    out.append('')
    out.append('| Questions per user | Speech-to-text per month | Total today (Edge voice) with speech input | Total with Soniox voice and speech input |')
    out.append('|---|---|---|---|')
    for q in scenarios:
        u = per_user(q, speaking=True); h = hosting(q, users)
        n = users
        out.append(f"| {q} | {money(u['stt'] * n)} | {money((u['llm'] + u['stt']) * n + h['total'])} | {money((u['llm'] + u['stt'] + u['soniox']) * n + h['total'])} |")
    out.append('')
    out.append('Data sent to visitors: ' + ', '.join(f"{q} questions ≈ {hosting(q, users)['egress_gb']:.0f} GB" for q in scenarios)
               + f" a month, inside AWS's free {PRICES['free_egress_gb']} GB.")
    return '\n'.join(out)

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')  # ₹ on a Windows console
    print(tables())
