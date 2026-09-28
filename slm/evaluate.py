"""Evaluate systems A/B/C on the same frozen set and write the comparison table.

  A: python slm/evaluate.py run --system A --backend openai          (few-shot hosted model)
  B: python slm/evaluate.py run --system B --backend hf               (few-shot base Qwen2.5-1.5B-Instruct)
  C: python slm/evaluate.py run --system C --backend hf --adapter DIR (fine-tuned adapter, zero-shot)
  Table: python slm/evaluate.py table

--eval defaults to the frozen hand-labelled set (slm/eval/eval_set.jsonl, field "gold"); until it exists,
pass --eval slm/data/dev.jsonl (teacher labels, field "target") and treat the numbers as development only.
Each run writes slm/results/<system>.jsonl (raw outputs) and <system>.json (metrics).
"""
import argparse
import json
import os
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from slm.prompting import messages, parse, rescore  # noqa: E402

RESULTS = ROOT / 'slm' / 'results'
SHOT_IDS = ['b2-001', 'b4-008', 'b5-038']   # fixed few-shot examples: high fit, injection+decline, Hinglish correction
SCALARS = ['seniority', 'organisation.type', 'organisation.agents', 'process', 'influence', 'next_step', 'consent',
           'monthly_leads.min', 'monthly_leads.max']
LISTS = ['current_tooling', 'lead_sources', 'geography.cities', 'geography.countries']
CATEGORICAL = ['seniority', 'organisation.type', 'process', 'influence', 'next_step', 'route']

def get(d, path):
    for k in path.split('.'): d = d.get(k) if isinstance(d, dict) else None
    return d

def load(path):
    rows = [json.loads(l) for l in Path(path).read_text('utf-8').splitlines() if l.strip()]
    for r in rows: r['gold'] = r.get('gold') or r['target']
    return rows

def shots():
    train = {r['id']: r for r in load(ROOT / 'slm' / 'data' / 'train.jsonl')}
    return [(train[i]['transcript'], train[i]['gold']) for i in SHOT_IDS if i in train]

# ---------------------------------------------------------------- backends
def openai_backend(model):
    import httpx
    key = os.environ['OPENAI_API_KEY']
    def generate(msgs):
        r = httpx.post('https://api.openai.com/v1/responses', timeout=90, headers={'Authorization': 'Bearer ' + key}, json={
            'model': model, 'store': False, 'input': msgs, 'max_output_tokens': 1500, 'reasoning': {'effort': 'low'},
            'text': {'format': {'type': 'json_object'}}})
        r.raise_for_status(); data = r.json()
        text = ''.join(c.get('text', '') for i in data.get('output', []) if i.get('type') == 'message' for c in i.get('content', []) if c.get('type') == 'output_text')
        return text, data.get('usage', {})
    return generate

def hf_backend(base, adapter=None):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(adapter or base)
    model = AutoModelForCausalLM.from_pretrained(base, torch_dtype=torch.float16, device_map='auto')
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    def generate(msgs):
        ids = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, return_tensors='pt').to(model.device)
        with torch.no_grad():
            out = model.generate(ids, max_new_tokens=900, do_sample=False, pad_token_id=tokenizer.eos_token_id)
        new = out[0][ids.shape[1]:]
        return tokenizer.decode(new, skip_special_tokens=True), {'input_tokens': int(ids.shape[1]), 'output_tokens': int(len(new))}
    return generate

# ---------------------------------------------------------------- metrics
def norm_set(v):
    return None if v is None else {re.sub(r'[^a-z0-9]+', ' ', str(x).lower()).strip() for x in v}

def f1(pred, gold):
    if pred is None and gold is None: return 1.0
    if pred is None or gold is None: return 0.0
    if not pred and not gold: return 1.0
    tp = len(pred & gold); p = tp / len(pred) if pred else 0; r = tp / len(gold) if gold else 0
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)

def macro_f1(pairs):
    labels = {g for _, g in pairs} | {p for p, _ in pairs}
    scores = []
    for label in labels:
        tp = sum(p == label and g == label for p, g in pairs); fp = sum(p == label and g != label for p, g in pairs)
        fn = sum(p != label and g == label for p, g in pairs)
        scores.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    return statistics.mean(scores) if scores else 0.0

def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))] if values else None

def metrics(rows, price_in=0.0, price_out=0.0, gpu_hourly=0.0):
    n = len(rows); valid = [r for r in rows if r['pred'] is not None]
    out = {'examples': n, 'schema_valid_pct': round(100 * len(valid) / n, 1),
           'arithmetic_mismatch': sum(r['reason'] == 'arithmetic_mismatch' for r in rows)}
    field = {}
    for path in SCALARS:
        field[path] = round(100 * sum(r['pred'] is not None and get(r['pred'], path) == get(r['gold'], path) for r in rows) / n, 1)
    for path in LISTS:
        field[path] = round(100 * statistics.mean(f1(norm_set(get(r['pred'], path)) if r['pred'] else set(['__invalid__']), norm_set(get(r['gold'], path))) for r in rows), 1)
    field['pain_points.count'] = round(100 * sum(r['pred'] is not None and len(r['pred']['pain_points'] or []) == len(r['gold']['pain_points'] or [])
                                                 and (r['pred']['pain_points'] is None) == (r['gold']['pain_points'] is None) for r in rows) / n, 1)
    out['field_accuracy_pct'] = field
    out['macro_f1_categorical'] = {c: round(macro_f1([(get(r['pred'], c) if r['pred'] else '__invalid__', get(r['gold'], c)) for r in rows]), 3) for c in CATEGORICAL}
    out['macro_f1'] = round(statistics.mean(out['macro_f1_categorical'].values()), 3)
    both = [(r['pred']['icp_score'], r['gold']['icp_score']) for r in valid if r['pred']['icp_score'] is not None and r['gold']['icp_score'] is not None]
    out['score_mae'] = round(statistics.mean(abs(p - g) for p, g in both), 2) if both else None
    out['score_mae_n'] = len(both)
    out['routing_accuracy_pct'] = round(100 * sum(r['pred'] is not None and r['pred']['route'] == r['gold']['route'] for r in rows) / n, 1)
    out['routing_accuracy_rescored_pct'] = round(100 * sum(r['pred'] is not None and rescore_route(r) == r['gold']['route'] for r in rows) / n, 1)
    out['routing_by_class'] = {c: {'n': sum(r['gold']['route'] == c for r in rows),
                                   'correct': sum(r['gold']['route'] == c and r['pred'] is not None and r['pred']['route'] == c for r in rows)}
                               for c in ['sales_handoff', 'nurture', 'graceful_close', 'human_review']}
    out['unsafe_handoffs'] = sum(r['pred'] is not None and r['pred']['route'] == 'sales_handoff' and
                                 (r['gold']['route'] != 'sales_handoff' or not r['gold']['consent']) for r in rows)
    ms = [r['ms'] for r in rows]
    out['latency_ms'] = {'p50': pct(ms, 50), 'p95': pct(ms, 95)}
    tokens_in = sum(r['usage'].get('input_tokens', 0) for r in rows); tokens_out = sum(r['usage'].get('output_tokens', 0) for r in rows)
    api = (tokens_in * price_in + tokens_out * price_out) / 1e6
    compute = gpu_hourly * sum(ms) / 3.6e6
    out['cost_per_1000_usd'] = round(1000 * (api + compute) / n, 4)
    return out

def rescore_route(r):
    from slm.labels import Qualification
    return rescore(Qualification.model_validate(r['pred'])).route

# ---------------------------------------------------------------- commands
def run(args):
    rows = load(args.eval)
    few = shots() if args.system in {'A', 'B'} else []
    if args.backend == 'openai': generate = openai_backend(args.model or os.getenv('OPENAI_MODEL', 'gpt-6-luna'))
    else: generate = hf_backend(args.base, args.adapter if args.system == 'C' else None)
    RESULTS.mkdir(exist_ok=True); out_rows = []
    for i, row in enumerate(rows, 1):
        started = time.perf_counter()
        try: text, usage = generate(messages(row['transcript'], few))
        except Exception as exc: text, usage = f'ERROR {type(exc).__name__}', {}
        ms = round((time.perf_counter() - started) * 1000)
        pred, reason = parse(text, row['transcript'])
        out_rows.append({'id': row['id'], 'raw': text, 'pred': pred.model_dump() if pred else None, 'reason': reason,
                         'gold': row['gold'], 'ms': ms, 'usage': usage})
        print(f"{args.system} {i}/{len(rows)} {row['id']} {reason or 'ok'} {ms}ms", flush=True)
    (RESULTS / f'{args.system}.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in out_rows), 'utf-8')
    m = metrics(out_rows, args.price_in, args.price_out, args.gpu_hourly)
    m.update(system=args.system, backend=args.backend, eval_file=str(args.eval), model=args.model or args.base, adapter=args.adapter)
    (RESULTS / f'{args.system}.json').write_text(json.dumps(m, indent=1), 'utf-8')
    print(json.dumps(m, indent=1))

def table(args):
    systems = {s: json.loads((RESULTS / f'{s}.json').read_text('utf-8')) for s in 'ABC' if (RESULTS / f'{s}.json').is_file()}
    lines = ['| Metric | ' + ' | '.join(systems) + ' |', '|---|' + '---|' * len(systems)]
    for label, key in [('JSON schema validity %', 'schema_valid_pct'), ('Routing accuracy %', 'routing_accuracy_pct'),
                       ('Macro F1 (categorical)', 'macro_f1'), ('ICP score MAE', 'score_mae'), ('Unsafe handoffs', 'unsafe_handoffs'),
                       ('p50 latency ms', ('latency_ms', 'p50')), ('p95 latency ms', ('latency_ms', 'p95')), ('Cost per 1,000 USD', 'cost_per_1000_usd')]:
        cells = [str(m[key[0]][key[1]] if isinstance(key, tuple) else m[key]) for m in systems.values()]
        lines.append(f'| {label} | ' + ' | '.join(cells) + ' |')
    text = '\n'.join(lines); (RESULTS / 'table.md').write_text(text + '\n', 'utf-8'); print(text)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run'); r.add_argument('--system', choices='ABC', required=True); r.add_argument('--backend', choices=['openai', 'hf'], required=True)
    r.add_argument('--eval', default=str(ROOT / 'slm' / 'eval' / 'eval_set.jsonl')); r.add_argument('--model'); r.add_argument('--base', default='Qwen/Qwen2.5-1.5B-Instruct')
    r.add_argument('--adapter'); r.add_argument('--price-in', type=float, default=0.0); r.add_argument('--price-out', type=float, default=0.0)
    r.add_argument('--gpu-hourly', type=float, default=0.0)
    sub.add_parser('table')
    args = parser.parse_args(); run(args) if args.cmd == 'run' else table(args)
