"""Live qualification with the fallback ladder from the design doc.

1. Fine-tuned SLM (any OpenAI-compatible endpoint: QUAL_SLM_URL + QUAL_SLM_MODEL, e.g. Ollama) → strict parse and
   validation; one retry on invalid output.
2. Hosted model (PLANNER_PROVIDER=openai, within the call budget) with the same prompt.
3. Deterministic rules extractor: only plainly stated facts (organisation words, "N agents", "N leads",
   explicit declines, typed email/phone). Consent is never inferred, so rules alone cannot produce a handoff.
4. Rules results, and anything left incomplete, route to human_review (declines still close gracefully).
Score, range and route are always re-derived from the extracted facts with the approved ICP rules.
QUAL_FORCE_INVALID=1 replaces the SLM output with broken JSON to demonstrate the ladder.
"""
import os
import re
import time
import httpx
from . import config
from .planner import declined, romanize, USAGE
from slm.labels import Extraction, complete
from slm.prompting import messages, parse, rescore

def transcript_of(session_messages):
    """Session chat → numbered turns (voice-only acknowledgements excluded)."""
    turns = []
    for m in session_messages:
        if m.get('kind') == 'ack': continue
        turns.append({'turn_id': len(turns) + 1, 'speaker': 'visitor' if m['role'] == 'user' else 'beacon', 'text': m['text']})
    return turns

async def _chat(url, model, msgs, headers=None):
    async with httpx.AsyncClient(timeout=httpx.Timeout(40, connect=3)) as client:
        r = await client.post(url.rstrip('/') + '/chat/completions', headers=headers or {}, json={
            'model': model, 'messages': msgs, 'temperature': 0, 'max_tokens': 900})
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content']

async def _hosted(msgs):
    key = os.environ.get('OPENAI_API_KEY', '')
    if config.PROVIDER != 'openai' or not key: raise ValueError('hosted model not configured')
    if USAGE['requests'] >= int(os.getenv('OPENAI_MAX_TEST_CALLS', '30')): raise ValueError('call budget reached')
    USAGE['requests'] += 1
    async with httpx.AsyncClient(timeout=httpx.Timeout(40, connect=5)) as client:
        r = await client.post('https://api.openai.com/v1/responses', headers={'Authorization': 'Bearer ' + key}, json={
            'model': config.OPENAI_MODEL, 'store': False, 'input': msgs, 'max_output_tokens': 1500,
            'reasoning': {'effort': 'low'}, 'text': {'format': {'type': 'json_object'}}})
        r.raise_for_status(); data = r.json()
        for k in ['input_tokens', 'output_tokens']: USAGE[k] += data.get('usage', {}).get(k, 0)
        return ''.join(c.get('text', '') for i in data.get('output', []) if i.get('type') == 'message'
                       for c in i.get('content', []) if c.get('type') == 'output_text')

CONTACT = re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+|\+?\d[\d -]{8,}\d')
ORG_WORDS = [('channel_partner', r'\bchannel partners?\b|\bcp firm\b'), ('developer', r'\b(developer|builder|builders|developers)\b'),
             ('brokerage', r'\b(broker|brokers|brokerage|real estate agency|property agency)\b')]

def rules_extract(turns):
    """Conservative deterministic extraction; ambiguous or repeated-conflicting values stay unknown."""
    x = {'organisation': {}, 'monthly_leads': {}, 'contact': {}, 'evidence': {}}
    orgs, agents, leads = set(), set(), set()
    for t in turns:
        if t['speaker'] != 'visitor': continue
        text = romanize(t['text']).lower(); tid = t['turn_id']
        for kind, pattern in ORG_WORDS:
            if re.search(pattern, text): orgs.add(kind); x['evidence'].setdefault('organisation.type', []).append(tid)
        for n in re.findall(r'\b(\d{1,4})\s*(?:sales\s*)?(?:agents|people|members|log|brokers|executives)\b', text):
            agents.add(int(n)); x['evidence'].setdefault('organisation.agents', []).append(tid)
        for n in re.findall(r'\b(\d{1,5})\s*(?:\+\s*)?(?:new\s*)?leads?\b', text):
            leads.add(int(n)); x['evidence'].setdefault('monthly_leads', []).append(tid)
        if declined(t['text']): x['next_step'] = 'declined'; x['evidence']['next_step'] = [tid]
        email = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', t['text']); phone = re.search(r'\+?\d[\d -]{8,}\d', t['text'])
        if email: x['contact']['email'] = email.group(0)
        if phone: x['contact']['phone'] = phone.group(0)
    if len(orgs) == 1: x['organisation']['type'] = orgs.pop()
    else: x['evidence'].pop('organisation.type', None)
    if len(agents) == 1: x['organisation']['agents'] = agents.pop()
    else: x['evidence'].pop('organisation.agents', None)
    if len(leads) == 1: n = leads.pop(); x['monthly_leads'] = {'min': n, 'max': n}
    else: x['evidence'].pop('monthly_leads', None)
    return Extraction.model_validate(x)

async def qualify_session(session_messages):
    """{'qualification': dict, 'source': slm|hosted|rules, 'attempts': [...], 'ms': int}. Never raises."""
    started = time.monotonic(); turns = transcript_of(session_messages); msgs = messages(turns); attempts = []
    url, model = os.getenv('QUAL_SLM_URL', ''), os.getenv('QUAL_SLM_MODEL', '')
    if url and model:
        for attempt in (1, 2):
            try:
                text = await _chat(url, model, msgs)
                if os.getenv('QUAL_FORCE_INVALID') == '1': text = '{"schema_version": "beacon.qualification.v1", "route": '
                q, reason = parse(text, turns)
            except Exception as exc:
                q, reason = None, 'unavailable:' + type(exc).__name__
            attempts.append({'step': 'slm', 'attempt': attempt, 'result': reason or 'ok'})
            if q is not None: return _done(rescore(q), 'slm', attempts, started)
            if reason and reason.startswith('unavailable'): break
    else:
        attempts.append({'step': 'slm', 'result': 'not_configured'})
    try:
        # Contact details never leave for the hosted model; they are re-attached from the transcript locally.
        redacted = [{**t, 'text': CONTACT.sub('[redacted]', t['text'])} for t in turns]
        q, reason = parse(await _hosted(messages(redacted)), redacted)
        attempts.append({'step': 'hosted', 'result': reason or 'ok'})
        if q is not None:
            q = q.model_copy(update={'contact': rules_extract(turns).contact.model_copy(update={'name': q.contact.name})})
            return _done(rescore(q), 'hosted', attempts, started)
    except Exception as exc:
        attempts.append({'step': 'hosted', 'result': 'unavailable:' + str(exc)[:60]})
    q = complete(rules_extract(turns))
    # Low confidence: the rules scorer can close a decline, but never qualifies a lead on its own.
    if q.route != 'graceful_close': q = q.model_copy(update={'route': 'human_review'})
    attempts.append({'step': 'rules', 'result': 'ok'})
    return _done(q, 'rules', attempts, started)

def _done(q, source, attempts, started):
    return {'qualification': q.model_dump(), 'source': source, 'attempts': attempts, 'ms': round((time.monotonic() - started) * 1000)}
