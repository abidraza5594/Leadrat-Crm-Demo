"""Groundedness eval: 30 answerable / 20 unanswerable questions against the company handbook.

Usage: python eval/groundedness.py [--mode extractive|llm]
Writes eval/results/groundedness-<mode>.json with every answer for hand review.

Automatic metrics are proxies: "answered from the expected module" for answerable questions and
refusal rate for unanswerable ones. Final answer accuracy needs a person to read the saved answers.
"""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['extractive', 'llm'], default='extractive')
    args = parser.parse_args()
    os.environ['DOCS_ANSWER'] = args.mode
    from app import docs
    cases = [json.loads(line) for line in (ROOT / 'eval' / 'groundedness.jsonl').read_text('utf-8').splitlines() if line.strip()]
    chunks = {c['id']: c for c in docs.load()}
    rows = []
    for case in cases:
        started = time.perf_counter()
        result = await docs.answer(case['question'])
        elapsed = round((time.perf_counter() - started) * 1000)
        top = chunks[result['sources'][0]]['module'] if result['sources'] else None
        rows.append({**case, 'grounded': result['grounded'], 'mode': result['mode'], 'top_module': top,
                     'module_correct': top == case.get('module'), 'ms': elapsed, 'answer': result['text']})
    answerable = [r for r in rows if r['answerable']]; unanswerable = [r for r in rows if not r['answerable']]
    summary = {
        'mode': args.mode, 'chunks': len(chunks),
        'answerable': len(answerable), 'answered': sum(r['grounded'] for r in answerable),
        'answered_from_expected_module': sum(r['grounded'] and r['module_correct'] for r in answerable),
        'unanswerable': len(unanswerable), 'refused': sum(not r['grounded'] for r in unanswerable),
        'refusal_rate_pct': round(100 * sum(not r['grounded'] for r in unanswerable) / len(unanswerable), 1),
        'p50_ms': sorted(r['ms'] for r in rows)[len(rows) // 2],
    }
    out = ROOT / 'eval' / 'results'; out.mkdir(exist_ok=True)
    (out / f'groundedness-{args.mode}.json').write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1, ensure_ascii=False), 'utf-8')
    print(json.dumps(summary, indent=1))
    for r in rows:
        passed = (r['grounded'] and r['module_correct']) if r['answerable'] else not r['grounded']
        flag = 'OK ' if passed else 'XX '
        print(flag, r['id'], r['mode'].ljust(14), (r['top_module'] or '-')[:22].ljust(22), r['question'][:70])

asyncio.run(main())
