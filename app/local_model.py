"""Local inference only; no hosted fallback."""
import json
import re
import httpx
from . import config

async def complete(messages, schema, max_tokens=240):
    prompt = [dict(m) for m in messages]
    prompt[0]['content'] += '\nReturn only a JSON object matching this schema: ' + json.dumps(schema)
    async with httpx.AsyncClient(timeout=httpx.Timeout(25, connect=3)) as client:
        response = await client.post(config.LOCAL_MODEL_URL + '/v1/chat/completions', json={
            'model': config.LOCAL_CHAT_MODEL, 'messages': prompt, 'max_tokens': max_tokens, 'temperature': 0})
        response.raise_for_status()
        raw = response.json()['choices'][0]['message']['content']
    match = re.search(r'\{.*\}', raw, re.S)
    if not match: raise ValueError('Local model returned no JSON')
    return json.loads(match.group(0))
