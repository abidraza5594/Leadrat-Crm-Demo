"""Content-free API metering. Provider invoices remain the billing authority."""
import asyncio
import contextvars
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from .config import ROOT

session_id = contextvars.ContextVar('usage_session', default=None)

async def record(provider, model, stage, *, usage=None, status='ok', request_id=None, **extra):
    entry = {'at': datetime.now(timezone.utc).isoformat(), 'provider': provider,
             'model': model, 'stage': stage, 'session_id': session_id.get(),
             'status': status, 'request_id': request_id, 'usage': usage or {}, **extra}
    path = Path(os.getenv('BEACON_USAGE_FILE', ROOT / '.state' / 'api-usage.jsonl'))
    def append():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf8') as f:
            f.write(json.dumps(entry, ensure_ascii=True) + '\n')
    try: await asyncio.to_thread(append)
    except OSError:
        # A disk failure must not turn a successful CRM action into a retry.
        import logging
        logging.getLogger(__name__).error('API metering could not be saved')


async def model_response(data, model, stage):
    await record('deepseek', model, stage, usage=data.get('usage'),
                 request_id=data.get('id'), status='ok' if data.get('usage') else 'usage_missing')
