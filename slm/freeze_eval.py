"""Freeze the hand-labelled evaluation set before any training run.

Usage: python slm/freeze_eval.py
Writes slm/eval/eval_set.jsonl (transcript + gold target derived from the hand labels by the approved rules)
and slm/eval/FROZEN.json (count, labellers, SHA-256). Commit both immediately; the commit is the timestamp.
After this the labelling tool refuses edits.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from slm.labels import Extraction, complete  # noqa: E402

EVAL = Path(os.getenv('BEACON_EVAL_DIR', ROOT / 'slm' / 'eval'))
MINIMUM = 100

def main():
    if (EVAL / 'FROZEN.json').is_file(): raise SystemExit('Already frozen. Do not re-freeze; create a new, separately dated set instead.')
    pool = {r['id']: r for r in map(json.loads, filter(str.strip, (EVAL / 'pool.jsonl').read_text('utf-8').splitlines()))}
    labels = [json.loads(l) for l in (EVAL / 'hand_labels.jsonl').read_text('utf-8').splitlines() if l.strip()]
    usable = [l for l in labels if l['status'] == 'labelled']
    if len(usable) < MINIMUM: raise SystemExit(f'Only {len(usable)} labelled examples; at least {MINIMUM} are required before freezing.')
    rows = []
    for record in usable:
        source = pool[record['id']]
        gold = complete(Extraction.model_validate(record['label'])).model_dump()
        rows.append({'id': record['id'], 'source': source.get('source', 'unknown'), 'language': source.get('language'),
                     'transcript': source['transcript'], 'gold': gold, 'labeller': record.get('labeller', '')})
    data = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows)
    (EVAL / 'eval_set.jsonl').write_text(data, 'utf-8')
    manifest = {'frozen_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'examples': len(rows),
                'unusable_excluded': len(labels) - len(usable), 'labellers': sorted({r['labeller'] for r in rows}),
                'sources': {s: sum(r['source'] == s for r in rows) for s in sorted({r['source'] for r in rows})},
                'label_origin': 'hand-labelled with slm/label_tool.py; no teacher labels',
                'sha256': {'eval_set.jsonl': hashlib.sha256(data.encode()).hexdigest(),
                           'hand_labels.jsonl': hashlib.sha256((EVAL / 'hand_labels.jsonl').read_bytes()).hexdigest()}}
    (EVAL / 'FROZEN.json').write_text(json.dumps(manifest, indent=1), 'utf-8')
    print(json.dumps(manifest, indent=1))
    print('\nNow commit slm/eval/ immediately: git add slm/eval && git commit -m "Freeze hand-labelled evaluation set"')

if __name__ == '__main__':
    main()
