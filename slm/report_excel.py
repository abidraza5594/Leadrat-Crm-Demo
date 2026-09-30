"""Excel report of an evaluation run: per-question accuracy, and expected vs predicted for every conversation.

Usage: python slm/report_excel.py --pred "Fine-tuned (C)=slm/results/C.jsonl" [--pred "Hosted (A)=..."] --out report.xlsx
The first --pred is the main system; it gets the per-conversation sheets. Rows are evaluate.py outputs
(id, pred, gold, reason, ms).
"""
import argparse
import json
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# (field path, the question Beacon asks, how it is compared)
QUESTIONS = [
    ('organisation.type', 'What kind of business do you run?', 'exact'),
    ('organisation.agents', 'How big is your sales team?', 'exact'),
    ('monthly_leads', 'How many leads do you get a month?', 'exact'),
    ('lead_sources', 'Where do your leads come from?', 'set'),
    ('current_tooling', 'What do you use to manage leads today?', 'set'),
    ('process', 'How do you manage leads today (manual / CRM)?', 'exact'),
    ('pain_points', 'What problems do you face with leads? (number of distinct problems)', 'count'),
    ('role', 'What is your role?', 'text'),
    ('seniority', 'Seniority (from the stated role)', 'exact'),
    ('influence', 'Who decides on buying a CRM?', 'exact'),
    ('geography.cities', 'Which cities do you work in?', 'set'),
    ('geography.countries', 'Which countries do you work in?', 'set'),
    ('next_step', 'When would you like to take this forward?', 'exact'),
    ('consent', 'May our sales team contact you?', 'exact'),
    ('contact', 'Contact details (name, email, phone)', 'contact'),
    ('route', 'Final decision (sales / nurture / review / close)', 'exact'),
]
GREEN, RED, GREY, HEAD = (PatternFill('solid', fgColor=c) for c in ('C6EFCE', 'FFC7CE', 'EDEDED', '1F4E78'))

def get(d, path):
    for part in path.split('.'): d = d.get(part) if isinstance(d, dict) else None
    return d

def norm(v):
    return re.sub(r'[^a-z0-9]+', ' ', str(v).lower()).strip()

def same(pred, gold, path, how):
    p, g = get(pred, path), get(gold, path)
    if how == 'set':
        if p is None or g is None: return p == g
        return {norm(x) for x in p} == {norm(x) for x in g}
    if how == 'count': return (p is None) == (g is None) and len(p or []) == len(g or [])
    if how == 'text': return (p is None) == (g is None) and (p is None or norm(p) == norm(g))
    if how == 'contact': return all(norm(get(pred, f'contact.{k}') or '') == norm(get(gold, f'contact.{k}') or '') for k in ('name', 'email', 'phone'))
    return p == g

def show(v):
    if v is None: return '(not stated)'
    if isinstance(v, dict):
        if set(v) == {'min', 'max'}: return '(not stated)' if v['min'] is None else (str(v['min']) if v['min'] == v['max'] else f"{v['min']}–{v['max']}")
        return ', '.join(f'{k}: {x}' for k, x in v.items() if x) or '(not stated)'
    if isinstance(v, list): return ', '.join(map(str, v)) if v else '(none)'
    if v == 'unknown': return '(not stated)'
    return str(v)

def load(path):
    return [json.loads(l) for l in Path(path).read_text('utf-8').splitlines() if l.strip()]

def header(ws, cols, widths):
    ws.append(cols)
    for i, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=i); c.font = Font(bold=True, color='FFFFFF'); c.fill = HEAD
        c.alignment = Alignment(wrap_text=True, vertical='center'); ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A2'

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--pred', action='append', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--data', default='slm/data/dev.jsonl'); ap.add_argument('--title', default='Beacon qualification model — test results')
    args = ap.parse_args()
    systems = [(p.split('=', 1)[0], load(p.split('=', 1)[1])) for p in args.pred]
    data = {r['id']: r for r in load(args.data)} if Path(args.data).is_file() else {}
    wb = Workbook()

    # ---- Summary
    ws = wb.active; ws.title = 'Summary'
    ws.append([args.title]); ws['A1'].font = Font(bold=True, size=14)
    ws.append([f'Test conversations: {len(systems[0][1])}. Each conversation was checked field by field against the expected answer.'])
    ws.append([])
    ws.append(['Metric'] + [n for n, _ in systems] + ['Target'])
    for c in ws[4]: c.font = Font(bold=True, color='FFFFFF'); c.fill = HEAD
    def pct(x): return f'{100 * x:.1f}%'
    lines = []
    for name, rows in systems:
        n = len(rows); valid = [r for r in rows if r['pred']]
        route = sum(1 for r in valid if r['pred']['route'] == r['gold']['route'])
        allright = sum(1 for r in valid if all(same(r['pred'], r['gold'], p, h) for p, _, h in QUESTIONS))
        unsafe = sum(1 for r in valid if r['pred']['route'] == 'sales_handoff' and (r['gold']['route'] != 'sales_handoff' or not r['gold']['consent']))
        fields = [sum(1 for r in valid if same(r['pred'], r['gold'], p, h)) / n for p, _, h in QUESTIONS if p != 'route']
        ms = sorted(r['ms'] for r in rows)
        lines.append({'Valid output (readable JSON)': pct(len(valid) / n), 'Correct final decision (route)': pct(route / n),
                      'Average field accuracy (all questions)': pct(sum(fields) / len(fields)),
                      'Conversations with every field correct': pct(allright / n),
                      'Leads wrongly sent to sales': str(unsafe), 'Median time per conversation': f'{ms[len(ms) // 2] / 1000:.1f} s'})
    targets = {'Valid output (readable JSON)': '≥ 99%', 'Correct final decision (route)': '≥ 90%', 'Leads wrongly sent to sales': '0'}
    for metric in lines[0]:
        ws.append([metric] + [l[metric] for l in lines] + [targets.get(metric, '')])
    ws.column_dimensions['A'].width = 42
    for i in range(len(systems) + 1): ws.column_dimensions[get_column_letter(i + 2)].width = 20

    # ---- Per question
    wq = wb.create_sheet('Per question')
    header(wq, ['Question Beacon asks', 'Field'] + [f'{n} — % correct' for n, _ in systems] + ['Stated in', 'Not stated in'],
           [46, 22] + [20] * len(systems) + [12, 14])
    for path, question, how in QUESTIONS:
        row = [question, path]
        for _, rows in systems:
            row.append(round(100 * sum(1 for r in rows if r['pred'] and same(r['pred'], r['gold'], path, how)) / len(rows), 1))
        g = [get(r['gold'], path) for r in systems[0][1]]
        stated = sum(1 for v in g if v not in (None, 'unknown', {'min': None, 'max': None}, {'name': None, 'email': None, 'phone': None}))
        wq.append(row + [stated, len(g) - stated])
    for r in wq.iter_rows(min_row=2):
        for c in r[2:2 + len(systems)]:
            c.number_format = '0.0"%"'; c.fill = GREEN if c.value >= 90 else (GREY if c.value >= 75 else RED)

    # ---- Per conversation (main system)
    name, rows = systems[0]
    wc = wb.create_sheet('Per conversation')
    cols = ['#', 'Conversation id', 'Conversation', 'Result', 'Fields wrong']
    for path, _, _ in QUESTIONS: cols += [f'{path} — expected', f'{path} — {name}']
    header(wc, cols, [5, 12, 70, 10, 30] + [18, 18] * len(QUESTIONS))
    for i, r in enumerate(rows, 1):
        convo = '\n'.join(f"{t['speaker'].upper()}: {t['text']}" for t in data.get(r['id'], {}).get('transcript', []))
        wrong = [p for p, _, h in QUESTIONS if not (r['pred'] and same(r['pred'], r['gold'], p, h))]
        line = [i, r['id'], convo, 'Invalid output' if not r['pred'] else ('All correct' if not wrong else f'{len(wrong)} wrong'), ', '.join(wrong)]
        for path, _, _ in QUESTIONS: line += [show(get(r['gold'], path)), show(get(r['pred'], path)) if r['pred'] else '(invalid)']
        wc.append(line)
        rr = wc.max_row
        wc.cell(row=rr, column=3).alignment = Alignment(wrap_text=True, vertical='top')
        wc.cell(row=rr, column=4).fill = GREEN if line[3] == 'All correct' else RED
        for k, (path, _, _) in enumerate(QUESTIONS):
            wc.cell(row=rr, column=7 + 2 * k).fill = GREEN if path not in wrong else RED

    # ---- Errors only
    we = wb.create_sheet('Mistakes')
    header(we, ['Conversation id', 'Question', 'Expected', f'{name} answered'], [14, 46, 34, 34])
    for r in rows:
        for path, question, how in QUESTIONS:
            if not (r['pred'] and same(r['pred'], r['gold'], path, how)):
                we.append([r['id'], question, show(get(r['gold'], path)), show(get(r['pred'], path)) if r['pred'] else '(invalid output)'])

    Path(args.out).parent.mkdir(parents=True, exist_ok=True); wb.save(args.out); print('wrote', args.out)

if __name__ == '__main__':
    main()
