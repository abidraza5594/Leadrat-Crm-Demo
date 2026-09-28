"""Validate teacher-written examples, derive scores/routes, split by scenario family, write the dataset.

Usage: python slm/build.py            -> slm/data/{train,dev}.jsonl + slm/data/stats.json
Rejected examples are listed with the reason; nothing invalid reaches the dataset.
"""
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from slm.labels import Extraction, complete  # noqa: E402

RAW = ROOT / 'slm' / 'data' / 'raw'
OUT = ROOT / 'slm' / 'data'
SEED = 20260928

def check(example):
    """Raises ValueError with the reason when an example is unusable."""
    turns = example['transcript']
    if [t['turn_id'] for t in turns] != list(range(1, len(turns) + 1)): raise ValueError('turn ids not 1..n')
    if {t['speaker'] for t in turns} - {'beacon', 'visitor'}: raise ValueError('unknown speaker')
    visitor = {t['turn_id'] for t in turns if t['speaker'] == 'visitor'}
    label = Extraction.model_validate(example['label'])
    for path, ids in label.evidence.items():
        if not set(ids) <= visitor: raise ValueError(f'evidence for {path} cites a non-visitor turn')
    data = label.model_dump()
    def known(path):
        value = data
        for part in path.split('.'): value = value.get(part) if isinstance(value, dict) else None
        return value not in (None, 'unknown', False, {'min': None, 'max': None}) and value != {'countries': None, 'cities': None} \
            and value != {'name': None, 'email': None, 'phone': None}
    for path in ['role', 'organisation.type', 'organisation.agents', 'pain_points', 'process', 'monthly_leads', 'influence', 'next_step', 'consent']:
        if known(path) and not label.evidence.get(path):
            raise ValueError(f'{path} is set without evidence')
    return label

def main():
    rows, rejected = [], []
    for file in sorted(RAW.glob('batch_*.jsonl')):
        for n, line in enumerate(file.read_text('utf-8').splitlines(), 1):
            if not line.strip(): continue
            try:
                example = json.loads(line)
                label = check(example)
                target = complete(label).model_dump()
                rows.append({'id': example['id'], 'family': example['family'], 'language': example.get('language', 'en'),
                             'partial': bool(example.get('partial')), 'transcript': example['transcript'], 'target': target})
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                rejected.append(f'{file.name}:{n} {str(exc)[:160]}')
    ids = Counter(r['id'] for r in rows)
    if any(c > 1 for c in ids.values()): raise SystemExit('duplicate ids: ' + str([i for i, c in ids.items() if c > 1]))
    # Near-duplicate check: identical visitor text across different examples.
    fingerprint = Counter(hashlib.sha1(' '.join(t['text'].lower() for t in r['transcript'] if t['speaker'] == 'visitor').encode()).hexdigest() for r in rows)
    duplicates = sum(c - 1 for c in fingerprint.values() if c > 1)
    # Family-level split: all variations of one scenario stay in the same split (~85/15).
    families = sorted({r['family'] for r in rows}); random.Random(SEED).shuffle(families)
    dev_families = set(families[:max(1, round(len(families) * 0.15))])
    split = {'train': [r for r in rows if r['family'] not in dev_families], 'dev': [r for r in rows if r['family'] in dev_families]}
    for name, items in split.items():
        (OUT / f'{name}.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in items), 'utf-8')
    stats = {'accepted': len(rows), 'rejected': len(rejected), 'rejections': rejected, 'identical_visitor_text': duplicates,
             'families': len(families), 'dev_families': sorted(dev_families),
             'split_sizes': {k: len(v) for k, v in split.items()},
             'routes': dict(Counter(r['target']['route'] for r in rows)),
             'organisation_types': dict(Counter(r['target']['organisation']['type'] for r in rows)),
             'languages': dict(Counter(r['language'] for r in rows)), 'partial': sum(r['partial'] for r in rows),
             'scored_complete': sum(r['target']['icp_score'] is not None for r in rows),
             'sha256': {k: hashlib.sha256((OUT / f'{k}.jsonl').read_bytes()).hexdigest() for k in split}}
    (OUT / 'stats.json').write_text(json.dumps(stats, indent=1, ensure_ascii=False), 'utf-8')
    print(json.dumps({k: v for k, v in stats.items() if k != 'rejections'}, indent=1))
    for r in rejected[:40]: print('REJECTED', r)

if __name__ == '__main__':
    main()
