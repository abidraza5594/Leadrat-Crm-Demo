import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client():
    main.sessions.clear()
    with TestClient(main.app) as client:
        yield client


def session(client):
    data = client.post('/api/assistant/sessions', json={}).json()
    return f"/api/assistant/sessions/{data['session_id']}/turn", {
        'X-Assistant-Session': data['session_token']}


def context(route='/leads/manage-leads', ready=False):
    return {'route': route, 'mode': 'crm', 'form_ready': ready,
            'available_actions': ['open_leads_page', 'open_add_lead_form',
                                  'highlight_field', 'fill_demo_lead']}


def fake_tool(name, args=None):
    async def reply(messages, tools):
        return {'content': 'Already completed!', 'tool_calls': [
            {'function': {'name': name, 'arguments': args or {}}}]}
    return reply


def test_session_requires_secret(client):
    url, _ = session(client)
    response = client.post(url, json={'message': 'hello', 'context': context()})
    assert response.status_code == 403


def test_reject_foreign_origin(client):
    assert client.post('/api/assistant/sessions', headers={'Origin': 'https://evil.example'}).status_code == 403


def test_explicit_local_origin_can_connect_directly_without_proxy(client):
    response = client.post('/api/assistant/sessions', headers={
        'Origin': 'http://localhost:4200', 'Sec-Fetch-Site': 'cross-site'})
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://localhost:4200'


def test_reject_destructive_model_tool(client, monkeypatch):
    monkeypatch.setattr(main, 'model_reply', fake_tool('delete_lead'))
    url, headers = session(client)
    response = client.post(url, headers=headers, json={'message': 'demo', 'context': context()})
    assert response.status_code == 502
    assert main.sessions[url.split('/')[4]].pending is None


def test_no_fill_on_edit_or_unready_form(client, monkeypatch):
    monkeypatch.setattr(main, 'model_reply', fake_tool('fill_demo_lead'))
    url, headers = session(client)
    for route, ready in [('/leads/edit-lead/123', True), ('/leads/add-lead', False)]:
        response = client.post(url, headers=headers, json={'message': 'demo', 'context': context(route, ready)})
        assert response.status_code == 502


def test_action_requires_matching_result_and_failure_stops(client, monkeypatch):
    monkeypatch.setattr(main, 'model_reply', fake_tool('open_add_lead_form'))
    url, headers = session(client)
    response = client.post(url, headers=headers, json={'message': 'demo', 'context': context()})
    assert response.status_code == 200
    data = response.json()
    assert 'Already completed' not in data['message']
    action = data['actions'][0]
    body = {'context': context(), 'results': [{'id': 'wrong-id', 'name': action['name'],
                                             'ok': True, 'detail': 'ready'}]}
    assert client.post(url, headers=headers, json=body).status_code == 409
    body['results'][0].update(id=action['id'], ok=False, detail='Permission denied')
    response = client.post(url, headers=headers, json=body)
    assert response.json()['done'] is True
    assert response.json()['actions'] == []
    assert 'Permission denied' in response.json()['message']
    assert client.post(url, headers=headers, json=body).status_code == 409


def test_only_one_action_and_actual_result_passed_to_model(client, monkeypatch):
    captured = []

    async def reply(messages, tools):
        captured.append(messages)
        if len(captured) == 1:
            return {'tool_calls': [{'function': {'name': 'open_add_lead_form', 'arguments': {}}},
                                   {'function': {'name': 'fill_demo_lead', 'arguments': {}}}]}
        return {'content': 'Form khula hai. Abhi save nahi hua.'}

    monkeypatch.setattr(main, 'model_reply', reply)
    url, headers = session(client)
    data = client.post(url, headers=headers, json={'message': 'demo', 'context': context()}).json()
    assert len(data['actions']) == 1
    action = data['actions'][0]
    response = client.post(url, headers=headers, json={'context': context('/leads/add-lead', True),
        'results': [{'id': action['id'], 'name': action['name'], 'ok': True, 'detail': 'Actual form mounted'}]})
    assert response.json()['done'] is True
    assert any(m.get('role') == 'tool' and 'Actual form mounted' in m['content'] for m in captured[1])


def test_injected_field_rejected(client, monkeypatch):
    monkeypatch.setattr(main, 'model_reply', fake_tool('highlight_field', {'field': 'button[type=submit]'}))
    url, headers = session(client)
    response = client.post(url, headers=headers,
                           json={'message': 'demo', 'context': context('/leads/add-lead', True)})
    assert response.status_code == 502


def test_stop_invalidates_session(client):
    url, headers = session(client)
    assert client.delete(url.removesuffix('/turn'), headers=headers).status_code == 200
    assert client.post(url, headers=headers, json={'message': 'hello', 'context': context()}).status_code == 404
