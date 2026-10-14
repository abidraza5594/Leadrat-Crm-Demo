"""The conversation model: the local runtime, or a hosted OpenAI-compatible API (PLANNER_PROVIDER=deepseek)."""
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

async def complete(messages, schema, max_tokens=240, prompt_schema=None):
    if config.PROVIDER=='deepseek':return await hosted(messages,schema,max_tokens,prompt_schema)
    prompt = [dict(m) for m in messages]
    body={'model':config.PLANNER_MODEL,'messages':prompt,'max_tokens':max_tokens,'temperature':0}
    if config.PLANNER_BACKEND=='llamacpp':
        body['response_format']={'type':'json_object','schema':schema}
    # A decoding grammar constrains tokens; it does not tell the model what the
    # fields mean. Include the contract in the prompt for both runtimes.
    prompt[0]['content'] += '\nReturn only a JSON object matching this schema: ' + json.dumps(prompt_schema or schema,separators=(',',':'))
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


async def hosted(messages, schema, max_tokens=240, prompt_schema=None):
    """One JSON object from the hosted model. JSON mode guarantees valid JSON; the schema is stated in the
    prompt and every result is validated by the caller. Transient failures are retried once."""
    prompt=[dict(m) for m in messages]
    prompt[0]['content']+='\nReturn only a JSON object matching this schema: '+json.dumps(prompt_schema or schema,separators=(',',':'))
    body={'model':config.DEEPSEEK_MODEL,'messages':prompt,'max_tokens':max_tokens,'temperature':0,
          'response_format':{'type':'json_object'}}
    # Reasoning tokens count against max_tokens; off by default for speed (DEEPSEEK_THINKING=1 enables it).
    if os.getenv('DEEPSEEK_THINKING','0')=='1':body['max_tokens']=max_tokens+2048
    else:body['thinking']={'type':'disabled'}
    headers={'Authorization':'Bearer '+config.DEEPSEEK_API_KEY}
    from . import transport, usage
    properties=schema.get('properties',{})
    stage='verification' if 'valid' in properties else 'answer' if 'evidence_ids' in properties else 'planner'
    async with transport.client() as client:
        for attempt in (1,2):
            try:
                response=await client.post(config.DEEPSEEK_URL+'/chat/completions',json=body,headers=headers,
                    timeout=httpx.Timeout(float(os.getenv('PLANNER_REQUEST_TIMEOUT','45')),connect=5))
                if response.is_success:await usage.model_response(response.json(),config.DEEPSEEK_MODEL,stage)
                else:await usage.record('deepseek',config.DEEPSEEK_MODEL,stage,status='http_'+str(response.status_code))
                if response.status_code in {429,500,502,503,504} and attempt==1:continue
                response.raise_for_status();break
            except (httpx.TimeoutException,httpx.NetworkError):
                await usage.record('deepseek',config.DEEPSEEK_MODEL,stage,status='unknown_after_network_error')
                if attempt==2:raise
        choice=response.json()['choices'][0]
    if choice.get('finish_reason')=='length':raise ValueError('Conversation decision was truncated')
    parsed=json.loads(choice['message']['content'] or '{}')
    if not isinstance(parsed,dict):raise ValueError('The model returned no JSON object')
    return parsed
