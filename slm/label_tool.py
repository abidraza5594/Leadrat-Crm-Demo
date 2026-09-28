"""Local hand-labelling tool for the frozen evaluation set.

Run:  .venv\\Scripts\\python.exe slm\\label_tool.py   then open http://127.0.0.1:8040
Reads slm/eval/pool.jsonl (unlabelled conversations), writes slm/eval/hand_labels.jsonl.
Once slm/eval/FROZEN.json exists (see slm/freeze_eval.py) labels can no longer be changed.
"""
import json
import sys
import time
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from slm.labels import Extraction, complete  # noqa: E402

EVAL = Path(__import__('os').getenv('BEACON_EVAL_DIR', ROOT / 'slm' / 'eval'))
POOL, LABELS, FROZEN = EVAL / 'pool.jsonl', EVAL / 'hand_labels.jsonl', EVAL / 'FROZEN.json'
app = FastAPI(title='Beacon hand-labelling')

def pool():
    return [json.loads(l) for l in POOL.read_text('utf-8').splitlines() if l.strip()] if POOL.is_file() else []

def labels():
    rows = [json.loads(l) for l in LABELS.read_text('utf-8').splitlines() if l.strip()] if LABELS.is_file() else []
    return {r['id']: r for r in rows}

def save(all_labels):
    temporary = LABELS.with_suffix('.tmp')
    temporary.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in all_labels.values()), 'utf-8')
    temporary.replace(LABELS)

class Submit(BaseModel):
    label: dict | None = None
    status: str = 'labelled'          # labelled | unusable
    note: str = ''
    labeller: str = ''
    seconds: int = 0

@app.get('/')
def page():
    return FileResponse(ROOT / 'slm' / 'label.html')

@app.get('/api/items')
def items():
    done = labels()
    return {'frozen': FROZEN.is_file(), 'items': [{'id': p['id'], 'language': p.get('language'),
            'status': done.get(p['id'], {}).get('status')} for p in pool()]}

@app.get('/api/item/{item_id}')
def item(item_id: str):
    found = next((p for p in pool() if p['id'] == item_id), None)
    if not found: raise HTTPException(404, 'Unknown item')
    return {**found, 'saved': labels().get(item_id)}

@app.post('/api/score')
def score(label: dict):
    try:
        result = complete(Extraction.model_validate(label))
    except ValidationError as exc:
        return {'valid': False, 'errors': [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]}
    return {'valid': True, 'icp_score': result.icp_score, 'score_range': result.score_range, 'route': result.route,
            'rationale': [r.model_dump() for r in result.score_rationale]}

@app.post('/api/label/{item_id}')
def submit(item_id: str, body: Submit):
    if FROZEN.is_file(): raise HTTPException(409, 'The evaluation set is frozen; labels cannot change.')
    found = next((p for p in pool() if p['id'] == item_id), None)
    if not found: raise HTTPException(404, 'Unknown item')
    visitor = {t['turn_id'] for t in found['transcript'] if t['speaker'] == 'visitor'}
    record = {'id': item_id, 'status': body.status, 'note': body.note[:500], 'labeller': body.labeller[:80],
              'seconds': body.seconds, 'labelled_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    if body.status == 'labelled':
        try:
            label = Extraction.model_validate(body.label or {})
        except ValidationError as exc:
            raise HTTPException(422, '; '.join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()))
        bad = sorted({t for ids in label.evidence.values() for t in ids} - visitor)
        if bad: raise HTTPException(422, f'Evidence must cite visitor turns only; not visitor turns: {bad}')
        record['label'] = label.model_dump()
    all_labels = labels(); all_labels[item_id] = record; save(all_labels)
    return {'saved': True, 'labelled': sum(r['status'] == 'labelled' for r in all_labels.values())}

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=int(__import__('os').getenv('LABEL_PORT', '8040')), log_level='warning')
