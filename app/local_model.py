"""Local inference only; no hosted fallback."""
import json
import os
import httpx
from . import config

def request_headers():
    if config.PLANNER_BACKEND=='llamacpp':
        from .planner_auth import headers
        return headers()
    from urllib.parse import urlsplit
    if urlsplit(config.PLANNER_MODEL_URL).hostname not in {'127.0.0.1','localhost','::1'}:
        raise ValueError('The conversation model must be local')
    return {}

async def complete(messages, schema, max_tokens=240):
    prompt = [dict(m) for m in messages]
    body={'model':config.PLANNER_MODEL,'messages':prompt,'max_tokens':max_tokens,'temperature':0}
    if config.PLANNER_BACKEND=='llamacpp':
        body['response_format']={'type':'json_object','schema':schema}
    # A decoding grammar constrains tokens; it does not tell the model what the
    # fields mean. Include the contract in the prompt for both runtimes.
    prompt[0]['content'] += '\nReturn only a JSON object matching this schema: ' + json.dumps(schema,separators=(',',':'))
    async with httpx.AsyncClient(timeout=httpx.Timeout(float(os.getenv('PLANNER_REQUEST_TIMEOUT','45')), connect=3)) as client:
        response = await client.post(config.PLANNER_MODEL_URL + '/v1/chat/completions',json=body,headers=request_headers())
        response.raise_for_status()
        choice=response.json()['choices'][0]
        if choice.get('finish_reason')=='length':raise ValueError('Conversation decision was truncated')
        raw = choice['message']['content']
    # A valid contract is a complete JSON object, not a fragment picked from
    # arbitrary model prose or multiple competing answers.
    parsed=json.loads(raw)
    if not isinstance(parsed,dict):raise ValueError('Local model returned no JSON object')
    return parsed
