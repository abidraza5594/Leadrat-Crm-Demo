import pytest
from fastapi.testclient import TestClient

from app import main
from app.catalog import FIELDS


@pytest.fixture
def client():
    main.sessions.clear()
    with TestClient(main.app) as value:
        yield value


def start(client):
    data = client.post('/api/assistant/sessions').json()
    return f"/api/assistant/sessions/{data['session_id']}", {'X-Assistant-Session': data['session_token']}


def context(**extra):
    return {'mode': 'crm', 'route': '/teams/manage-user', 'form_ready': False,
            'available_actions': ['open_module', 'open_leads_page', 'open_add_lead_form'],
            'available_modules': ['dashboard', 'leads', 'reports'], **extra}


def intent(monkeypatch, name, args=None):
    calls = []

    async def model(messages, tools):
        calls.append(messages)
        assert len(calls) == 1, 'A started tour must not rely on another model prediction.'
        return {'tool_calls': [{'function': {'name': name, 'arguments': args or {}}}]}

    monkeypatch.setattr(main, 'model_reply', model)
    return calls


def acknowledge(client, base, headers, action, state, ok=True):
    response = client.post(base + '/turn', headers=headers, json={'context': state, 'results': [
        {'id': action['id'], 'name': action['name'], 'ok': ok, 'detail': 'UI confirmed' if ok else 'Unsaved input'}]})
    assert response.status_code == 200, response.text
    return response.json()


def test_full_tour_waits_for_results_and_expands_every_visible_field(client, monkeypatch):
    calls = intent(monkeypatch, 'start_crm_tour')
    base, headers = start(client)
    response = client.post(base + '/turn', headers=headers,
                           json={'message': 'Pura CRM demo', 'context': context()}).json()
    observed = []
    state = context()
    for _ in range(60):
        if response['done']:
            break
        action = response['actions'][0]
        observed.append((action['name'], action['arguments']))
        assert response['narration']['key']
        assert response['progress']['current'] == len(observed)
        if action['name'] == 'open_module':
            module = action['arguments']['module']
            controls = ['leads.add', 'leads.grid'] if module == 'leads' else []
            state = context(route=f'/{module}', available_controls=controls,
                            available_actions=['open_module', 'open_add_lead_form', 'highlight_module_control'])
        elif action['name'] == 'open_add_lead_form':
            state = context(route='/leads/add-lead', form_ready=True, available_fields=list(FIELDS),
                            available_actions=['highlight_field', 'fill_demo_lead'])
        elif action['name'] == 'fill_demo_lead':
            state['available_actions'] = ['highlight_field']
        response = acknowledge(client, base, headers, action, state)
    assert response['done'] is True
    assert len(calls) == 0  # Explicit CRM requests take the immediate path.
    assert [args['module'] for name, args in observed if name == 'open_module'] == ['dashboard', 'leads', 'reports']
    assert [args['field'] for name, args in observed if name == 'highlight_field'] == list(FIELDS)
    assert observed[-1][0] == 'fill_demo_lead'
    assert response['progress']['current'] == response['progress']['total'] == len(observed)


def test_failed_navigation_stops_tour_without_completion_narration(client, monkeypatch):
    intent(monkeypatch, 'start_crm_tour')
    base, headers = start(client)
    action = client.post(base + '/turn', headers=headers, json={'message': 'tour', 'context': context()}).json()['actions'][0]
    response = acknowledge(client, base, headers, action, context(), ok=False)
    assert response['done'] and response['actions'] == []
    assert response['narration']['key'].startswith('reply.')
    assert response['narration']['text'] == response['message']
    assert 'stopped' in response['narration']['text']
    assert 'Unsaved input' in response['message']


def test_module_permission_rechecked_mid_tour(client, monkeypatch):
    intent(monkeypatch, 'start_crm_tour')
    base, headers = start(client)
    action = client.post(base + '/turn', headers=headers, json={'message': 'tour', 'context': context()}).json()['actions'][0]
    response = acknowledge(client, base, headers, action, context(available_modules=['dashboard']))
    assert response['done']
    assert 'unavailable' in response['message']


def test_read_only_user_can_tour_without_add_lead(client, monkeypatch):
    intent(monkeypatch, 'start_module_tour', {'module': 'reports'})
    base, headers = start(client)
    state = context(available_actions=['open_module'], available_modules=['reports'])
    response = client.post(base + '/turn', headers=headers, json={'message': 'reports demo', 'context': state}).json()
    response = acknowledge(client, base, headers, response['actions'][0], state)
    assert response['done']
    assert response['progress']['total'] == 1


def test_speech_requires_session_and_issued_key_and_rejects_arbitrary_text(client, monkeypatch):
    received = []

    async def fake_speech(key, voice):
        received.append((key, voice))
        return b'fake-mp3-for-protocol-test'

    monkeypatch.setattr(main, 'synthesize', fake_speech)
    base, headers = start(client)
    assert client.post(base + '/speech', json={'key': 'voice.preview'}).status_code == 403
    assert client.post(base + '/speech', headers=headers, json={'key': 'lead.sample'}).status_code == 403
    assert client.post(base + '/speech', headers=headers, json={'key': 'voice.preview', 'text': 'Customer PII'}).status_code == 422
    assert client.post(base + '/speech', headers=headers, json={'key': 'voice.preview', 'voice': 'unknown'}).status_code == 422
    response = client.post(base + '/speech', headers=headers, json={'key': 'voice.preview'})
    assert response.status_code == 200
    assert response.headers['content-type'] == 'audio/mpeg'
    assert received == [('voice.preview', 'hi-IN-SwaraNeural')]
    client.delete(base, headers=headers)
    assert client.post(base + '/speech', headers=headers, json={'key': 'voice.preview'}).status_code == 404


def test_voice_failure_is_explicit_without_stopping_tour(client, monkeypatch):
    async def unavailable(key, voice):
        raise TimeoutError('provider unavailable')

    monkeypatch.setattr(main, 'synthesize', unavailable)
    base, headers = start(client)
    response = client.post(base + '/speech', headers=headers, json={'key': 'voice.preview'})
    assert response.status_code == 503
    assert 'continue with text' in response.json()['detail']


@pytest.mark.parametrize('prompt', [
    'how to add lead', 'How do I add a new lead?', 'lead add kaise kare',
    'Lead form ka poora walkthrough Hindi voice mein dikhao. Saare available fields samjhao.',
])
def test_add_lead_starts_immediately_without_model_or_list_detour(client, monkeypatch, prompt):
    async def must_not_call_model(*args):
        raise AssertionError('A clear lead tutorial must not wait for Ollama.')

    monkeypatch.setattr(main, 'model_reply', must_not_call_model)
    base, headers = start(client)
    response = client.post(base + '/turn', headers=headers, json={'message': prompt, 'context': context()})
    assert response.status_code == 200
    body = response.json()
    assert not body['done']
    assert body['actions'][0]['name'] == 'open_add_lead_form'
    assert body['narration']['key'] == 'lead.open'
    assert body['progress']['current'] == 1


def test_fast_lead_request_cannot_bypass_create_permission(client, monkeypatch):
    base, headers = start(client)
    response = client.post(base + '/turn', headers=headers, json={'message': 'how to add lead',
        'context': context(available_actions=['open_leads_page'])}).json()
    assert response['done'] and response['actions'] == []
    assert 'permission' in response['message']


def test_text_only_model_response_never_claims_requested_demo_started(client, monkeypatch):
    async def prose_only(*args):
        return {'content': 'Demo start ho gaya. Wait kare.'}

    monkeypatch.setattr(main, 'model_reply', prose_only)
    base, headers = start(client)
    response = client.post(base + '/turn', headers=headers,
                           json={'message': 'workflow demo dikhao', 'context': context()}).json()
    assert response['actions'] == []
    assert 'start nahi hua' in response['message']
    assert 'start ho gaya' not in response['message']


def test_each_question_switches_language_and_all_result_steps_retain_it(client, monkeypatch):
    async def must_not_call_model(*args):
        raise AssertionError('Known demos and language selection must not wait for Ollama.')

    monkeypatch.setattr(main, 'model_reply', must_not_call_model)
    base, headers = start(client)
    state = context(available_actions=['open_module'], available_modules=['reports'])
    for prompt, language, first_words in [
        ('Show me reports', 'en', 'This is'),
        ('Reports ka demo dikhao', 'hi', 'यह'),
        ('Show me reports again', 'en', 'This is'),
    ]:
        response = client.post(base + '/turn', headers=headers, json={'message': prompt, 'context': state}).json()
        assert response['language'] == response['narration']['language'] == language
        assert response['narration']['text'].startswith(first_words)
        complete = acknowledge(client, base, headers, response['actions'][0], state)
        assert complete['done'] and complete['language'] == complete['narration']['language'] == language


def test_general_model_answer_receives_current_language_instruction(client, monkeypatch):
    instructions = []

    async def model(messages, tools):
        instructions.append(messages[-1]['content'])
        return {'content': 'Source identifies where an enquiry originated.'}

    monkeypatch.setattr(main, 'model_reply', model)
    base, headers = start(client)
    for prompt, language in [('What is a lead source?', 'en'), ('lead source kya hai', 'hi')]:
        response = client.post(base + '/turn', headers=headers, json={'message': prompt, 'context': context()}).json()
        assert response['language'] == language
    assert 'English only' in instructions[0]
    assert 'Hindi or natural Hinglish' in instructions[1]
