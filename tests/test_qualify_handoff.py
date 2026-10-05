import asyncio
import json
import httpx
from app import qualify, handoff, main

def chat(*visitor_lines):
    msgs = []
    for line in visitor_lines:
        msgs += [{'role': 'assistant', 'text': 'Tell me about your business.'}, {'role': 'user', 'text': line}]
    return msgs

def test_forced_invalid_json_walks_the_ladder_to_rules(monkeypatch):
    monkeypatch.setenv('QUAL_SLM_URL', 'http://slm.invalid/v1'); monkeypatch.setenv('QUAL_SLM_MODEL', 'beacon-qual')
    monkeypatch.setenv('QUAL_FORCE_INVALID', '1')
    async def fake_chat(url, model, msgs, headers=None): return '{"ok": true}'
    monkeypatch.setattr(qualify, '_chat', fake_chat)
    result = asyncio.run(qualify.qualify_session(chat('We are a brokerage with 25 agents and about 600 leads a month.')))
    assert [a['step'] for a in result['attempts']] == ['slm', 'slm', 'hosted', 'rules']
    assert result['attempts'][0]['result'] in {'no_json', 'invalid_json'} and result['source'] == 'rules'
    q = result['qualification']
    assert q['organisation'] == {'name': None, 'type': 'brokerage', 'agents': 25} and q['monthly_leads'] == {'min': 600, 'max': 600}
    assert q['route'] == 'human_review' and not q['consent']

def test_valid_slm_output_is_used_and_rescored(monkeypatch):
    monkeypatch.setenv('QUAL_SLM_URL', 'http://slm.invalid/v1'); monkeypatch.setenv('QUAL_SLM_MODEL', 'beacon-qual')
    monkeypatch.delenv('QUAL_FORCE_INVALID', raising=False)
    gold = json.loads(open('slm/data/dev.jsonl', encoding='utf-8').readline())['target']
    tampered = {**gold, 'route': 'sales_handoff'}
    async def fake_chat(url, model, msgs, headers=None): return json.dumps(tampered)
    monkeypatch.setattr(qualify, '_chat', fake_chat)
    rows = json.loads(open('slm/data/dev.jsonl', encoding='utf-8').readline())['transcript']
    msgs = [{'role': 'user' if t['speaker'] == 'visitor' else 'assistant', 'text': t['text']} for t in rows]
    result = asyncio.run(qualify.qualify_session(msgs))
    assert result['source'] == 'slm' and result['qualification']['route'] == gold['route']

def test_rules_close_a_decline_but_never_qualify():
    result = asyncio.run(qualify.qualify_session(chat('We are developers, 40 agents', 'please do not contact me')))
    assert result['source'] == 'rules' and result['qualification']['route'] == 'graceful_close'

def qualified():
    return {'route': 'sales_handoff', 'consent': True, 'contact': {'name': 'A', 'email': 'a@example.com', 'phone': None},
            'organisation': {'name': 'X Realty', 'type': 'brokerage', 'agents': 25}, 'monthly_leads': {'min': 600, 'max': 600},
            'evidence': {'organisation.type': [2]}, 'icp_score': 100, 'score_range': [100, 100], 'score_rationale': []}

def test_handoff_retries_then_delivers_once(monkeypatch):
    calls = {'n': 0}
    def respond(request):
        calls['n'] += 1
        if calls['n'] < 3: return httpx.Response(503)
        status, body = handoff.receive(json.loads(request.content))
        return httpx.Response(status, json=body)
    real = httpx.AsyncClient
    monkeypatch.setattr(handoff.httpx, 'AsyncClient', lambda **kw: real(transport=httpx.MockTransport(respond)))
    payload = handoff.brief('session-1', qualified(), {'leads'})
    assert payload['schema_version'] == 'beacon.handoff.v1' and payload['product_areas_shown'] == ['leads']
    assert asyncio.run(handoff.deliver(payload, backoff=0)) == 'delivered' and calls['n'] == 3
    assert handoff.receive(payload)[1]['duplicate'] is True

def test_no_handoff_without_consent_or_contact():
    assert handoff.eligible(qualified())
    assert not handoff.eligible({**qualified(), 'consent': False})
    assert not handoff.eligible({**qualified(), 'contact': {'name': 'A', 'email': None, 'phone': None}})
    payload=handoff.brief('no-permission',{**qualified(),'consent':False,'route':'nurture'},{'leads'})
    assert payload['recommended_next_step'].startswith('Do not contact')

def test_discovery_asks_one_unknown_at_a_time_then_closes_with_contact():
    s = main.Session()
    s.messages.append({'id': 'u1', 'role': 'user', 'text': 'show leads'})
    asked = []
    for _ in range(10):
        before = len(s.messages); main.discover(s)
        # Resolve/skip each pending question before asking the next one.
        s.pending_discovery=None
        asked += [m['text'] for m in s.messages[before:]]
    assert len(asked) == len(main.DISCOVERY)+1 and asked[0].startswith('To tailor the demo')
    assert asked[-1].startswith('Would you like someone from Leadrat to contact you')

def test_hosted_model_never_sees_email_or_phone(monkeypatch):
    seen = []
    async def hosted(msgs):
        seen.append(json.dumps(msgs)); return '{}'
    monkeypatch.setattr(qualify, '_hosted', hosted)
    monkeypatch.delenv('QUAL_SLM_URL', raising=False)
    asyncio.run(qualify.qualify_session(chat('yes call me, rohan@acme.example.com or +91 90000 01234')))
    assert seen and 'rohan@acme' not in seen[0] and '90000 01234' not in seen[0] and 'private-contact-1@redacted.invalid' in seen[0]

def test_hosted_facts_keep_withdrawn_contact_removed(monkeypatch):
    from slm.labels import Extraction
    async def hosted(msgs):
        return json.dumps(Extraction(consent=True).model_dump())
    monkeypatch.setattr(qualify, '_hosted', hosted)
    monkeypatch.delenv('QUAL_SLM_URL', raising=False)
    result = asyncio.run(qualify.qualify_session(chat('Contact me at a@example.com.', 'That email is wrong; remove it.')))
    assert result['source'] == 'hosted'
    assert result['qualification']['contact']['email'] is None

def test_hosted_selects_corrected_contact_without_revealing_it(monkeypatch):
    from slm.labels import Extraction, Contact
    async def hosted(msgs):
        assert 'new@example.com' not in json.dumps(msgs)
        return json.dumps(Extraction(contact=Contact(email='private-contact-2@redacted.invalid')).model_dump())
    monkeypatch.setattr(qualify, '_hosted', hosted)
    monkeypatch.delenv('QUAL_SLM_URL', raising=False)
    result = asyncio.run(qualify.qualify_session(chat('a@example.com.', 'Correction: use new@example.com.')))
    assert result['qualification']['contact']['email'] == 'new@example.com'

def test_email_sentence_punctuation_is_not_part_of_address():
    q=qualify.rules_extract(qualify.transcript_of(chat('Write to a@example.com.')))
    assert q.contact.email == 'a@example.com'

def test_explicit_final_decline_overrides_stale_model_decision(monkeypatch):
    from slm.labels import Extraction
    async def hosted(msgs):
        return json.dumps(Extraction(consent=True,next_step='within_30_days').model_dump())
    monkeypatch.setattr(qualify, '_hosted', hosted)
    monkeypatch.delenv('QUAL_SLM_URL', raising=False)
    result = asyncio.run(qualify.qualify_session(chat('I want a demo.', 'I changed my mind. Do not contact me.')))
    q = result['qualification']
    assert q['consent'] is False and q['next_step'] == 'declined' and q['route'] == 'graceful_close'

def test_retention_prunes_old_handoffs(monkeypatch):
    import time as t
    handoff._append('outbox.jsonl', {'handoff_id': 'old', '_stored': t.time() - 8 * 86400})
    handoff._append('outbox.jsonl', {'handoff_id': 'new', '_stored': t.time()})
    handoff.prune()
    kept = [json.loads(l)['handoff_id'] for l in (handoff.OUTBOX / 'outbox.jsonl').read_text().splitlines()]
    assert kept == ['new']
