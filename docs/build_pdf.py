"""Builds docs/Beacon_Tech_Stack_and_Costs.pdf from docs/TECH_STACK_AND_COSTS.md.

Usage: python docs/build_pdf.py

The Markdown file stays the source of truth; this script adds a cover with a one-page summary (numbers taken
from eval/cost_model.py, so they always match the tables), draws the architecture diagram, and prints the page
with the same Google Chrome the demo uses.
"""
import asyncio, html, importlib.util
from pathlib import Path
from markdown_it import MarkdownIt
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'docs' / 'TECH_STACK_AND_COSTS.md'
OUTPUT = ROOT / 'docs' / 'Beacon_Tech_Stack_and_Costs.pdf'

spec = importlib.util.spec_from_file_location('cost_model', ROOT / 'eval' / 'cost_model.py')
cost = importlib.util.module_from_spec(spec); spec.loader.exec_module(cost)


def box(x, y, w, h, title, lines=(), tone='server'):
    fill, stroke, ink = {'site': ('#eef5f3', '#7fa8a0', '#104d46'), 'server': ('#104d46', '#104d46', '#ffffff'),
                         'external': ('#ffffff', '#b9c6c3', '#1d2b29')}[tone]
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>',
           f'<text x="{x + 12}" y="{y + 19}" class="t" fill="{ink}">{html.escape(title)}</text>']
    for i, line in enumerate(lines):
        out.append(f'<text x="{x + 12}" y="{y + 35 + i * 14}" class="s" fill="{ink}" opacity=".85">{html.escape(line)}</text>')
    return ''.join(out)

def arrow(x1, y1, x2, y2, label='', both=False, lx=None, ly=None, anchor='middle'):
    ends = 'marker-end="url(#a)"' + (' marker-start="url(#a)"' if both else '')
    text = f'<text x="{lx if lx is not None else (x1 + x2) / 2}" y="{ly if ly is not None else (y1 + y2) / 2 - 5}" class="l" text-anchor="{anchor}">{html.escape(label)}</text>' if label else ''
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#5b7974" stroke-width="1.3" {ends}/>' + text

def diagram():
    parts = [
        '<svg viewBox="0 0 760 420" xmlns="http://www.w3.org/2000/svg" class="diagram" role="img" aria-label="Beacon architecture">',
        '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 10 5 0 10z" fill="#5b7974"/></marker></defs>',
        '<text x="95" y="20" class="h" text-anchor="middle">Visitor’s browser</text>',
        '<text x="355" y="20" class="h" text-anchor="middle">Beacon server (Python · FastAPI)</text>',
        '<text x="660" y="20" class="h" text-anchor="middle">External services</text>',
        box(10, 36, 170, 50, 'Leadrat website', ['widget.js preloads the popup'], 'site'),
        box(10, 150, 170, 64, 'Beacon popup', ['live CRM screen + chat', 'voice plays as it streams'], 'site'),
        box(10, 360, 170, 44, 'Microphone', ['visitor speaks (optional)'], 'site'),
        box(260, 36, 190, 84, 'Conversation engine', ['LangGraph: plan → answer → check', 'search: 384-d vectors + BM25', 'PostgreSQL + pgvector'], 'server'),
        box(260, 160, 190, 44, 'Session API', ['chat, live frames, voice'], 'server'),
        box(260, 230, 190, 54, 'Warm browser pool', ['headless Chrome (Playwright)', 'signed in and waiting'], 'server'),
        box(260, 300, 190, 44, 'Registration, lead scoring', ['sales handoff with consent'], 'server'),
        box(570, 36, 180, 50, 'DeepSeek API', ['deepseek-flash (V4.1 Flash)'], 'external'),
        box(570, 160, 180, 44, 'Soniox text-to-speech', ['tts-rt-v2, voice Priya'], 'external'),
        box(570, 235, 180, 44, 'Leadrat CRM', ['test tenant, read-only demo'], 'external'),
        box(570, 300, 180, 44, 'Leadrat API', ['visitor saved as a lead'], 'external'),
        box(570, 360, 180, 44, 'Soniox speech-to-text', ['stt-rt-v5, temporary key'], 'external'),
        arrow(95, 86, 95, 148, 'click: opens in 50–250 ms', lx=101, ly=121, anchor='start'),
        arrow(182, 182, 258, 182, '', both=True),
        arrow(450, 61, 568, 61, 'plan, answer, check'),
        arrow(355, 158, 355, 122, ''),
        arrow(355, 206, 355, 228, ''),
        arrow(450, 182, 568, 182, 'one warm WebSocket'),
        arrow(450, 257, 568, 257, 'navigate, highlight'),
        arrow(450, 322, 568, 322, 'background save'),
        arrow(182, 382, 568, 382, 'audio streamed directly from the browser', lx=375, ly=376),
        '</svg>',
    ]
    return ''.join(parts)

def summary():
    rows = []
    for q in (0, 20, 30, 50):
        u = cost.per_user(q); h = cost.hosting(q)
        today = u['llm'] * 1000 + h['total']; soniox = today + u['soniox'] * 1000
        rows.append(f"<tr><td>{q}</td><td>{cost.money(h['total'])}</td><td>{cost.money(u['llm'] * 1000)}</td>"
                    f"<td><b>{cost.money(today)}</b></td><td><b>{cost.money(soniox)}</b></td></tr>")
    return f"""
<section class="summary">
  <h2 class="plain">Summary</h2>
  <div class="cards">
    <div class="card"><div class="k">Vector database</div><div class="v">PostgreSQL + pgvector</div><div class="d"><b>384-dimension</b> vectors (multilingual MiniLM, INT8 ONNX), hybrid with BM25</div></div>
    <div class="card"><div class="k">AI model</div><div class="v">DeepSeek V4.1 Flash</div><div class="d">3 calls per question: understand, answer from the handbook, check</div></div>
    <div class="card"><div class="k">Voice</div><div class="v">Soniox real-time</div><div class="d">Speech-to-text stt-rt-v5, text-to-speech tts-rt-v2 (Edge voice free backup)</div></div>
    <div class="card"><div class="k">Speed</div><div class="v">Demo opens in 55–245 ms</div><div class="d">Answer 3.3–4.7 s; voice starts 45–77 ms after the text</div></div>
  </div>
  <h3>Monthly cost for 1,000 users</h3>
  <table class="sum">
    <thead><tr><th>Questions per user</th><th>Hosting (AWS Mumbai)</th><th>DeepSeek (AI)</th><th>Total today<br>(Edge voice, free)</th><th>Total with<br>Soniox voice</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <p class="note">Visitors type and voice replies are on; DeepSeek at peak prices; prices without taxes; $1 = ₹90. The free Edge voice adds nothing.
  If visitors also speak their questions, Soniox speech-to-text adds $27–63 a month at 20–50 questions (section 7.4).</p>
</section>"""

CSS = """
@page { size: A4; margin: 18mm 15mm 18mm 15mm; }
* { box-sizing: border-box; }
body { font-family: 'Segoe UI', Arial, sans-serif; color: #1d2b29; font-size: 9.6pt; line-height: 1.5; margin: 0; }
.cover { background: #104d46; color: #fff; border-radius: 10px; padding: 22px 26px; margin-bottom: 18px; }
.cover .mark { display: inline-block; background: #fff; color: #104d46; font-weight: 800; border-radius: 7px; padding: 2px 9px; font-size: 13pt; margin-right: 10px; }
.cover .brand { font-size: 13pt; font-weight: 700; letter-spacing: .2px; }
.cover h1 { font-size: 23pt; margin: 14px 0 4px; line-height: 1.15; }
.cover .sub { opacity: .85; font-size: 10.5pt; }
h2 { color: #104d46; font-size: 14.5pt; margin: 22px 0 8px; padding-bottom: 4px; border-bottom: 2px solid #d5e4e1; break-after: avoid; }
h2.plain { margin-top: 0; }
h3 { color: #1b5c4f; font-size: 11.2pt; margin: 16px 0 6px; break-after: avoid; }
p { margin: 6px 0; }
ul, ol { margin: 6px 0; padding-left: 20px; }
li { margin: 2px 0; }
code { font-family: Consolas, monospace; font-size: 8.6pt; background: #eef3f2; padding: 0 3px; border-radius: 3px; }
a { color: #1b5c4f; text-decoration: none; }
table { width: 100%; border-collapse: collapse; margin: 8px 0 12px; font-size: 8.4pt; line-height: 1.35; break-inside: auto; }
table.wide { font-size: 7.4pt; }
thead { display: table-header-group; }
th { background: #104d46; color: #fff; text-align: left; font-weight: 600; padding: 5px 6px; vertical-align: bottom; }
td { padding: 4px 6px; border-bottom: 1px solid #e1e9e7; vertical-align: top; }
tr { break-inside: avoid; }
tbody tr:nth-child(even) td { background: #f6f9f8; }
strong, b { font-weight: 650; }
.summary .cards { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 8px 0 12px; }
.card { border: 1px solid #d5e4e1; border-radius: 8px; padding: 9px 12px; background: #f7fbfa; }
.card .k { font-size: 7.8pt; text-transform: uppercase; letter-spacing: .6px; color: #5b7974; }
.card .v { font-size: 12pt; font-weight: 700; color: #104d46; }
.card .d { font-size: 8.6pt; color: #3c4e4b; }
table.sum { font-size: 9pt; }
table.sum td:first-child { font-weight: 650; }
.note { font-size: 8.4pt; color: #52636a; }
.diagram { width: 100%; height: auto; margin: 6px 0 10px; }
.diagram .h { font: 700 11px 'Segoe UI', Arial; fill: #104d46; }
.diagram .t { font: 650 11.5px 'Segoe UI', Arial; }
.diagram .s { font: 9.6px 'Segoe UI', Arial; }
.diagram .l { font: 9px 'Segoe UI', Arial; fill: #3c4e4b; }
pre { background: #f3f6f5; border-radius: 6px; padding: 8px 10px; font-size: 7.6pt; overflow: hidden; white-space: pre-wrap; }
.break { break-before: page; }
h2 + ul { break-inside: avoid; }
"""

def build_html():
    text = SOURCE.read_text('utf-8')
    title_end = text.index('\n## ')
    intro = text[:title_end].split('\n', 1)[1].strip()
    body = MarkdownIt('commonmark').enable('table').render(text[title_end:])
    # The ASCII sketch in section 2 becomes a drawn diagram.
    start = body.index('<pre>'); end = body.index('</pre>', start) + len('</pre>')
    body = body[:start] + diagram() + body[end:]
    # Main sections after the summary start on a fresh page when they are long.
    for heading in ('<h2>3. Technology stack</h2>', '<h2>7. Cost analysis</h2>'):
        body = body.replace(heading, heading.replace('<h2>', '<h2 class="break">'), 1)
    intro_html = MarkdownIt('commonmark').render(intro)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Beacon — technology, architecture and costs</title>
<style>{CSS}</style></head><body>
<header class="cover"><span class="mark">b.</span><span class="brand">Beacon by Leadrat</span>
<h1>Technology, architecture and costs</h1><div class="sub">AI product guide for the Leadrat website · 16 October 2026</div></header>
{intro_html}
{summary()}
<div class="break"></div>
{body}
</body></html>"""

async def main():
    page_html = build_html()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel='chrome', headless=True)
        page = await browser.new_page()
        await page.set_content(page_html, wait_until='load')
        await page.evaluate("""() => document.querySelectorAll('table').forEach(t => {
            if (t.querySelectorAll('thead th').length >= 7) t.classList.add('wide'); })""")
        footer = ('<div style="width:100%;font:8px Segoe UI,Arial;color:#7a8a87;padding:0 15mm;display:flex;justify-content:space-between">'
                  '<span>Beacon · Technology, architecture and costs</span>'
                  '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>')
        await page.pdf(path=str(OUTPUT), format='A4', print_background=True, display_header_footer=True,
                       header_template='<div></div>', footer_template=footer,
                       margin={'top': '16mm', 'bottom': '18mm', 'left': '15mm', 'right': '15mm'})
        await browser.close()
    print(OUTPUT)

if __name__ == '__main__':
    asyncio.run(main())
