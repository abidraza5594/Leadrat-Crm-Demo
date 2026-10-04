"""Sales handoff brief (beacon.handoff.v1, approved schema) with a durable outbox and a mock webhook.

A brief is sent only for route sales_handoff with explicit consent and a usable email or phone. Every brief is
appended to the outbox before delivery; delivery retries three times with backoff; handoff_id makes delivery
idempotent (the mock receiver ignores repeats). Outbox and receiver files hold contact details: they are
git-ignored and pruned after HANDOFF_RETENTION_DAYS (default 7).
"""
import asyncio
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx
from . import config

OUTBOX = Path(os.getenv('BEACON_OUTBOX_DIR', config.ROOT / '.outbox'))
WEBHOOK = os.getenv('HANDOFF_WEBHOOK_URL', 'http://127.0.0.1:8010/mock-crm/handoff')
RETENTION_DAYS = int(os.getenv('HANDOFF_RETENTION_DAYS', '7'))
NEXT_STEP = {'sales_handoff': 'Call within one business day and book a tailored demo.',
             'nurture': 'Add to nurture; follow up when the stated timeline approaches.',
             'human_review': 'Review unknowns before contacting.', 'graceful_close': 'No follow-up.'}

def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def brief(session_id, q, product_areas_shown, created_at=None):
    """Map a qualification to the approved handoff payload. Unknown values stay null."""
    handoff_id = 'hnd_' + hashlib.sha256(session_id.encode()).hexdigest()[:20]
    org = q['organisation']; evidence = sorted({t for ids in q['evidence'].values() for t in ids})
    next_step=NEXT_STEP[q['route']]
    if not q.get('consent') and q['route']!='graceful_close':
        next_step='Do not contact the customer without explicit permission. Review the missing details first.'
    return {'schema_version': 'beacon.handoff.v1', 'handoff_id': handoff_id, 'session_id': session_id,
            'contact': q['contact'] if any(q['contact'].values()) else None,
            'company': {'name': org.get('name'), 'type': None if org.get('type') == 'unknown' else org.get('type'), 'agents': org.get('agents')},
            'role': q.get('role'), 'seniority': q.get('seniority', 'unknown'), 'pain_points': q.get('pain_points'),
            'current_tooling': q.get('current_tooling'), 'geography': q.get('geography'),
            'monthly_leads': q['monthly_leads'] if q['monthly_leads'].get('min') is not None else None,
            'lead_sources': q.get('lead_sources'), 'product_areas_shown': sorted(product_areas_shown),
            'icp_score': q.get('icp_score'), 'score_range': q.get('score_range'),
            'score_rationale': q.get('score_rationale', []), 'route': q['route'],
            'recommended_next_step': next_step, 'evidence_turn_ids': evidence, 'consent': bool(q.get('consent')),
            'created_at': created_at or now(), 'updated_at': now(), 'delivery_status': 'pending'}

def eligible(q):
    return q['route'] == 'sales_handoff' and q.get('consent') and bool(q['contact'].get('email') or q['contact'].get('phone'))

def _append(name, record):
    OUTBOX.mkdir(exist_ok=True)
    with open(OUTBOX / name, 'a', encoding='utf-8') as f: f.write(json.dumps(record, ensure_ascii=False) + '\n')

def prune():
    """Drop outbox/receiver records older than the retention period."""
    cutoff = time.time() - RETENTION_DAYS * 86400
    for name in ['outbox.jsonl', 'mock_received.jsonl']:
        path = OUTBOX / name
        if not path.is_file(): continue
        keep = [l for l in path.read_text('utf-8').splitlines() if l.strip() and json.loads(l).get('_stored', time.time()) >= cutoff]
        path.write_text(''.join(l + '\n' for l in keep), 'utf-8')

async def deliver(payload, attempts=3, backoff=1.0):
    """Outbox first, then POST with retries. Returns the final delivery_status."""
    prune()
    _append('outbox.jsonl', {**payload, '_stored': time.time()})
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(WEBHOOK, json=payload, headers={'Idempotency-Key': payload['handoff_id']})
                if r.status_code < 300:
                    _append('outbox.jsonl', {'handoff_id': payload['handoff_id'], 'delivery_status': 'delivered', 'attempt': attempt, 'at': now(), '_stored': time.time()})
                    return 'delivered'
        except httpx.HTTPError:
            pass
        if attempt < attempts: await asyncio.sleep(backoff * 2 ** (attempt - 1))
    _append('outbox.jsonl', {'handoff_id': payload['handoff_id'], 'delivery_status': 'failed', 'attempt': attempts, 'at': now(), '_stored': time.time()})
    return 'failed'

def receive(payload):
    """Mock CRM endpoint: stores each handoff_id once."""
    path = OUTBOX / 'mock_received.jsonl'
    seen = {json.loads(l)['handoff_id'] for l in path.read_text('utf-8').splitlines() if l.strip()} if path.is_file() else set()
    if payload.get('schema_version') != 'beacon.handoff.v1' or not payload.get('handoff_id'): return 422, {'error': 'invalid payload'}
    if payload['handoff_id'] in seen: return 200, {'received': payload['handoff_id'], 'duplicate': True}
    _append('mock_received.jsonl', {**payload, '_stored': time.time()})
    return 200, {'received': payload['handoff_id'], 'duplicate': False}
