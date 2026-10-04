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
from slm.prompting import facts_messages, messages as trained_messages, parse_facts, parse, rescore

def extraction_schema():
    schema = Extraction.model_json_schema()
    paths = ['role','seniority','organisation.name','organisation.type','organisation.agents',
             'pain_points','current_tooling','process','geography.countries','geography.cities',
             'monthly_leads','lead_sources','influence','next_step','consent','contact.name','contact.email','contact.phone']
    schema['properties']['evidence'] = {'type':'object','properties':{
        p:{'type':'array','items':{'type':'integer'}} for p in paths}}
    def strict(node):
        if isinstance(node, dict):
            node.pop('default', None)
            if node.get('type') == 'object':
                node['additionalProperties'] = False
                node['required'] = list(node.get('properties', {}))
            for value in node.values(): strict(value)
        elif isinstance(node, list):
            for value in node: strict(value)
    strict(schema)
    return schema

def transcript_of(session_messages):
    """Session chat → numbered turns (voice-only acknowledgements excluded)."""
    turns = []
    for m in session_messages:
        if m.get('kind') == 'ack': continue
        turns.append({'turn_id': len(turns) + 1, 'speaker': 'visitor' if m['role'] == 'user' else 'beacon', 'text': m['text']})
    return turns

async def _chat(url, model, msgs, headers=None):
    async with httpx.AsyncClient(timeout=httpx.Timeout(float(os.getenv('QUAL_SLM_TIMEOUT', '40')), connect=3)) as client:
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
            'reasoning': {'effort': 'low'}, 'text': {'format': {'type': 'json_schema',
                'name':'beacon_customer_facts', 'strict':True, 'schema':extraction_schema()}}})
        r.raise_for_status(); data = r.json()
        for k in ['input_tokens', 'output_tokens']: USAGE[k] += data.get('usage', {}).get(k, 0)
        return ''.join(c.get('text', '') for i in data.get('output', []) if i.get('type') == 'message'
                       for c in i.get('content', []) if c.get('type') == 'output_text')

EMAIL = r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+'
PHONE = r'\+?\d[\d -]{8,}\d'
CONTACT = re.compile(EMAIL + '|' + PHONE)

def private_transcript(turns):
    """Keep distinct contact references so corrections/removals survive redaction."""
    mapping = {}
    reverse = {}
    def hide(match):
        value = match.group(0)
        if value not in reverse:
            index = str(len(mapping) + 1)
            token = 'private-contact-' + index + '@redacted.invalid' if '@' in value else '[redacted-phone-' + index + ']'
            mapping[token] = value
            reverse[value] = token
        return reverse[value]
    return [{**t, 'text': CONTACT.sub(hide, t['text'])} for t in turns], mapping

def qualification_prompt(turns):
    msgs = facts_messages(turns)
    msgs[0]['content'] += (' Contact placeholders such as private-contact-1@redacted.invalid or [redacted-phone-1] represent private contact details. '
        'Copy the exact placeholder into contact.email or contact.phone only if the visitor currently offers it as their contact. '
        'If withdrawn, incorrect or someone else\'s, return null. Consent must be false when absent or withdrawn.')
    return msgs

def parse_extraction(text, turns):
    q, reason = parse_facts(text, turns)
    # Older endpoint deployments can still return the full scored schema.
    if q is None:
        legacy, legacy_reason = parse(text, turns)
        if legacy is not None: return legacy, legacy_reason
    return q, reason
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
        email = re.search(EMAIL, t['text']); phone = re.search(PHONE, t['text'])
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
    started = time.monotonic(); turns = transcript_of(session_messages); msgs = qualification_prompt(turns); attempts = []
    url, model = os.getenv('QUAL_SLM_URL', ''), os.getenv('QUAL_SLM_MODEL', '')
    if os.getenv('QUAL_SLM_FORMAT') == 'full': msgs = trained_messages(turns)
    if url and model:
        for attempt in (1, 2):
            try:
                text = await _chat(url, model, msgs)
                if os.getenv('QUAL_FORCE_INVALID') == '1': text = '{"schema_version": "beacon.qualification.v1", "route": '
                q, reason = parse_extraction(text, turns)
            except Exception as exc:
                q, reason = None, 'unavailable:' + type(exc).__name__
            attempts.append({'step': 'slm', 'attempt': attempt, 'result': reason or 'ok'})
            if q is not None: return _done(rescore(q), 'slm', attempts, started, turns)
            if reason and reason.startswith('unavailable'): break
    else:
        attempts.append({'step': 'slm', 'result': 'not_configured'})
    try:
        # Contact details never leave for the hosted model; they are re-attached from the transcript locally.
        redacted, contact_map = private_transcript(turns)
        q, reason = parse_extraction(await _hosted(qualification_prompt(redacted)), redacted)
        attempts.append({'step': 'hosted', 'result': reason or 'ok'})
        if q is not None:
            # Resolve only model-selected placeholders grounded in visitor turns.
            visitor_contacts = {m.group(0) for t in turns if t['speaker'] == 'visitor' for m in CONTACT.finditer(t['text'])}
            restored = {}
            for field, pattern in [('email', EMAIL), ('phone', PHONE)]:
                value = contact_map.get(getattr(q.contact, field))
                restored[field] = value if value in visitor_contacts and re.fullmatch(pattern, value or '') else None
            q = q.model_copy(update={'contact': q.contact.model_copy(update=restored)})
            return _done(rescore(q), 'hosted', attempts, started, turns)
    except Exception as exc:
        attempts.append({'step': 'hosted', 'result': 'unavailable:' + str(exc)[:60]})
    q = complete(rules_extract(turns))
    # Low confidence: the rules scorer can close a decline, but never qualifies a lead on its own.
    if q.route != 'graceful_close': q = q.model_copy(update={'route': 'human_review'})
    attempts.append({'step': 'rules', 'result': 'ok'})
    return _done(q, 'rules', attempts, started, turns)

def _done(q, source, attempts, started, turns):
    visitor = [t for t in turns if t['speaker'] == 'visitor']
    if source == 'slm':
        # Explicit introductions/corrections are authoritative; never guess a name from
        # an email, an assistant example, a job title, or a company name.
        identity = None
        stated_names = set()
        for turn in visitor:
            text = turn['text']
            events=[(m.start(),None) for m in re.finditer(r"\b(?:remove|forget|delete)\s+my\s+name\b|\b(?:don't|do not)\s+(?:use|save)\s+my\s+name\b", text, re.I)]
            for match in re.finditer(r"\bmy name is\s+([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){0,3})(?=[.,!?;\n]|$)", text, re.I):
                name=match.group(1).strip()
                if not any(w.lower() in {'and','we','not','unknown','private','none'} for w in name.split()):
                    events.append((match.start(),name));stated_names.add(name.casefold())
            for match in re.finditer(r"\bmera naam\s+([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){0,3}?)\s+hai\b",text,re.I):
                name=match.group(1).strip()
                if not any(w.lower() in {'nahi','nahin','unknown'} for w in name.split()):
                    events.append((match.start(),name));stated_names.add(name.casefold())
            for _, name in sorted(events):identity=(name,turn['turn_id'])
        if identity is not None:
            name, tid = identity
            if q.contact.name != name:
                q=q.model_copy(update={'contact':q.contact.model_copy(update={'name':name}),
                    'evidence':{**q.evidence,'contact.name':[tid]}})
                attempts.append({'step':'validation','result':'explicit_visitor_name_applied'})
            if q.role and q.role.casefold() in stated_names:
                evidence=dict(q.evidence);evidence.pop('role',None)
                q=q.model_copy(update={'role':None,'evidence':evidence})
        text=' '.join(t['text'] for t in visitor)
        # Explicit contact withdrawal must override a stale model value. Later
        # sharing of a new address/number allows the model's new selection again.
        for field,pattern in [('email',EMAIL),('phone',PHONE)]:
            withdrawn=None
            for turn in visitor:
                line=turn['text']
                withdrawal=re.search(r'\b(?:remove|forget|delete)\s+(?:my |that |the )?'+field+r'\b|\b'+field+r'\b[^\n]{0,90}\b(?:remove|forget|delete)\s+it\b',line,re.I)
                if withdrawal:withdrawn=turn['turn_id']
                elif re.search(pattern,line):withdrawn=None
            if withdrawn is not None:
                q=rescore(q.model_copy(update={'contact':q.contact.model_copy(update={field:None}),
                    'evidence':{**q.evidence,'contact.'+field:[withdrawn]}}))
                attempts.append({'step':'validation','result':field+'_withdrawal_applied'})
        # Anchor durations to a customer's requested demo/call, not company age
        # or lead volumes. Later explicit timing statements take precedence.
        timing=None
        numbers={w:i for i,w in enumerate(['zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve'])}
        for turn in visitor:
            line=turn['text'].lower()
            if re.search(r'\b(?:correction|instead|changed my mind)\b',line):timing=None
            for match in re.finditer(r'\b(?:i|we)\s+(?:want|need|would like)\s+(?:a |the )?(?:demo|call|meeting)\s+(?:in|after)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(days?|weeks?|months?)\b',line):
                count=int(match[1]) if match[1].isdigit() else numbers[match[1]]
                days=count*(30 if match[2].startswith('month') else 7 if match[2].startswith('week') else 1)
                timing=('later' if days>30 else 'within_30_days',turn['turn_id'])
        if timing and q.next_step!='declined':
            q=rescore(q.model_copy(update={'next_step':timing[0],'evidence':{**q.evidence,'next_step':[timing[1]]}}))
            attempts.append({'step':'validation','result':'explicit_requested_timing_applied'})
        if q.next_step=='declined' and re.search(r"\b(?:have not|haven't|not yet)\s+(?:agreed|consented)\b|\bnot\s+given\s+consent\b",text,re.I) and not any(declined(t['text']) for t in visitor):
            evidence=dict(q.evidence);evidence.pop('next_step',None)
            q=rescore(q.model_copy(update={'next_step':'unknown','consent':False,'evidence':evidence}))
            attempts.append({'step':'validation','result':'absence_of_permission_is_not_a_decline'})
        if q.seniority=='owner' and not re.search(r'\b(?:owner|founder|cofounder|proprietor)\b|\bi\s+(?:own|run|founded)\b',text,re.I):
            evidence=dict(q.evidence);evidence.pop('seniority',None)
            update={'seniority':'unknown','evidence':evidence}
            if q.role and re.search(r'\b(?:owner|founder|proprietor)\b',q.role,re.I):
                update['role']=None;evidence.pop('role',None)
            q=q.model_copy(update=update)
            attempts.append({'step':'validation','result':'unsupported_owner_title_removed'})
    if visitor and declined(visitor[-1]['text']):
        tid = visitor[-1]['turn_id']
        q = rescore(q.model_copy(update={'next_step':'declined','consent':False,
            'evidence':{**q.evidence,'next_step':[tid],'consent':[tid]}}))
    return {'qualification': q.model_dump(), 'source': source, 'attempts': attempts, 'ms': round((time.monotonic() - started) * 1000)}
