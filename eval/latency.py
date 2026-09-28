"""End-of-user-speech to first-audio-out latency, by stage, through the real widget.

Usage: python eval/latency.py --site http://localhost:8011/ --turns 100
Needs Beacon + the test website running. A scripted speech-recognition stand-in delivers each question
as a final speech result (so Chrome's own recognition endpointing is NOT included; see the report).
Writes eval/results/latency.json and prints p50/p95 per stage.
"""
import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = [
    # reviewed shortcuts that also run a screen demo
    'show leads', 'show projects', 'how to change status', 'schedule meeting', 'show notes', 'show tasks', 'show dashboard',
    'how to add a lead', 'show whatsapp', 'lead ka status kaise badle',
    # handbook questions (grounded answer path)
    'How do I import a spreadsheet of customer data?', 'Why does my dashboard show a different number than my manager?',
    'How do I add units to a project?', 'Why was my listing rejected when publishing to a portal?', 'How does clock in work?',
    'How do I create a task and assign it?', 'Why can a user not see a project?', 'How do I update our company logo?',
    'Can I connect Leadrat to ChatGPT?', 'My file had 1000 rows but fewer records were imported, why?',
    # not in the handbook (refusal path)
    'How much does Leadrat cost?', 'Does Leadrat integrate with Salesforce?', 'Is there a free trial?', 'What is your uptime SLA?',
    # small talk and Hinglish
    'hi', 'thank you', 'what can you do', 'mujhe batao dashboard ka number alag kyun hai', 'lead me note kaise add kare',
    'import karte waqt rows kyun reject hoti hai',
]

FAKE = r"""
(() => {
  class FakeRecognition { start() { window.__rec = this; this.results = []; } stop() { this.onend?.(); } abort() { this.onend?.(); } }
  window.SpeechRecognition = window.webkitSpeechRecognition = FakeRecognition;
  window.__say = text => { const r = window.__rec; if (!r?.onresult) return false;
    r.results.push(Object.assign([{transcript: text}], {isFinal: true})); r.onresult({resultIndex: r.results.length - 1, results: r.results}); return true; };
})();
"""

def pct(values, p):
    values = sorted(v for v in values if v is not None)
    if not values: return None
    return round(values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))])

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', default='http://localhost:8011/')
    parser.add_argument('--turns', type=int, default=100)
    args = parser.parse_args()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required'])
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        await page.context.add_init_script(FAKE)
        await page.goto(args.site); await page.click('[data-beacon-open]')
        frame = page.frame_locator('iframe.beacon-frame')
        await frame.locator('#start').click()
        fr = next(f for f in page.frames if 'widget.html' in f.url)
        for _ in range(120):
            if 'Ready' in await frame.locator('#status').inner_text(): break
            await asyncio.sleep(0.5)
        await frame.locator('#mic').click(); await asyncio.sleep(0.5)
        for n in range(args.turns):
            question = QUESTIONS[n % len(QUESTIONS)]
            before = await fr.evaluate('window.__beaconLatency.length')
            await fr.evaluate(f'window.__say({json.dumps(question)})')
            deadline = time.time() + 30
            while time.time() < deadline:
                turn = await fr.evaluate(f'window.__beaconLatency[{before}] || null')
                if turn and turn.get('audio'): break
                await asyncio.sleep(0.1)
            # Let the demo finish so the next question does not interrupt it (interruption is measured elsewhere).
            for _ in range(60):
                if 'Exploring' not in await frame.locator('#status').inner_text(): break
                await asyncio.sleep(0.5)
            await asyncio.sleep(0.8)
            print(f'{n + 1}/{args.turns} {question[:40]}', flush=True)
        client = await fr.evaluate('window.__beaconLatency')
        server = (await fr.evaluate('window.__beaconTimings()') or {}).get('turns', [])
        await browser.close()
    return client, server

if __name__ == '__main__':
    client, server = asyncio.run(main())
    rows = []
    for i, t in enumerate(client):
        srv = server[i] if i < len(server) else {}
        heard, sent, shown, audio = t.get('heard'), t.get('sent'), t.get('shown'), t.get('audio')
        rows.append({'question': QUESTIONS[i % len(QUESTIONS)],
                     'pause_before_send_ms': None if heard is None else sent - heard,
                     'sent_to_reply_shown_ms': None if shown is None else shown - sent,
                     'reply_shown_to_audio_ms': None if audio is None or shown is None else audio - shown,
                     'speech_result_to_audio_ms': None if audio is None or heard is None else audio - heard,
                     'server_plan_ms': srv.get('plan_ms'), 'server_first_reply_ms': srv.get('first_reply_ms'),
                     'server_first_tts_ms': srv.get('first_tts_ms'), 'plan_source': srv.get('plan_source')})
    stages = ['pause_before_send_ms', 'server_plan_ms', 'server_first_reply_ms', 'sent_to_reply_shown_ms', 'server_first_tts_ms',
              'reply_shown_to_audio_ms', 'speech_result_to_audio_ms']
    summary = {s: {'p50': pct([r[s] for r in rows], 50), 'p95': pct([r[s] for r in rows], 95)} for s in stages}
    summary['turns'] = len(rows); summary['audio_started'] = sum(r['speech_result_to_audio_ms'] is not None for r in rows)
    out = ROOT / 'eval' / 'results'; out.mkdir(exist_ok=True)
    (out / 'latency.json').write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1, ensure_ascii=False), 'utf-8')
    print(json.dumps(summary, indent=1))
