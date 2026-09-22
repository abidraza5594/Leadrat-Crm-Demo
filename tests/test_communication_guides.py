import pytest
from fastapi.testclient import TestClient
from app import main
from app.feature_guides import feature_for_query


@pytest.mark.parametrize('query,expected', [
    ('lead ko whatsapp and email kaise bheje', 'communications'),
    ('yes whtsper per message kaise bheje', 'whatsapp'),
    ('send a whatsapp template', 'whatsapp'),
    ('email a customer', 'email'), ('lead kaha se aata hai', 'sources'),
    ('import leads from excel', 'bulk_upload'), ('Facebook integration kaise use kare', 'integrations'),
    ('find a lead', 'search'), ('export leads', 'export'),
])
def test_direct_routes(query, expected):
    assert feature_for_query(query) == expected


def test_template_retains_channel():
    assert feature_for_query('template', 'whatsapp') == 'whatsapp'
    assert feature_for_query('template', 'email') == 'email'
    assert feature_for_query('template', 'communications') == 'whatsapp'
    assert feature_for_query('template') is None
    assert feature_for_query('email a lead', 'whatsapp') == 'email'
    assert feature_for_query('bulk whatsapp leads') is None
    assert feature_for_query('delete whatsapp template') is None


def test_actual_user_conversation_never_calls_model(monkeypatch):
    async def forbidden(*args):
        raise AssertionError('Known requests should not wait for the model or clarify')
    monkeypatch.setattr(main, 'model_reply', forbidden)
    monkeypatch.setattr(main, 'understand_question', forbidden)
    with TestClient(main.app) as client:
        session = client.post('/api/assistant/sessions').json()
        headers = {'X-Assistant-Session': session['session_token']}
        url = f"/api/assistant/sessions/{session['session_id']}/turn"
        context = {'route': '/leads/manage-leads', 'mode': 'crm', 'available_actions': ['show_lead_feature']}
        for query, feature in [('lead ko whatsapp and email kaise bheje', 'communications'),
                               ('yes whtsper per message kaise bheje', 'whatsapp'), ('template', 'whatsapp')]:
            response = client.post(url, headers=headers, json={'message': query, 'context': context})
            for stage in ('open', 'details', 'finish'):
                assert response.status_code == 200
                body = response.json()
                action = body['actions'][0]
                assert action['arguments'] == {'feature': feature, 'stage': stage}
                assert body['narration']['key'] == f'feature.{feature}.{stage}'
                response = client.post(url, headers=headers, json={'context': context, 'results': [
                    {'id': action['id'], 'name': action['name'], 'ok': True, 'detail': 'Visible'}]})
            assert response.json()['done']
