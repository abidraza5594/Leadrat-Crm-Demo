import pytest
from fastapi.testclient import TestClient

from app import main
from app.feature_guides import FEATURES, feature_for_query
from app.catalog import NARRATIONS_BY_LANGUAGE


@pytest.mark.parametrize('question,feature', [
    ('how to change status', 'status'), ('status kaise update kare', 'status'),
    ('site visit schedule kaise kare', 'site_visit'), ('siteviste schedule kaise kare', 'site_visit'),
    ('meeting schedule kaise kare', 'meeting'), ('set up a meeting', 'meeting'),
    ('lead reassign kaise kare', 'reassign'), ('lead notes kaise add kare', 'notes'),
])
def test_feature_intents(question, feature):
    assert feature_for_query(question) == feature


@pytest.mark.parametrize('question', ['task status update', 'bulk status update', 'delete lead notes', 'no demo lead notes'])
def test_other_actions_are_not_substituted(question):
    assert feature_for_query(question) is None


def test_scheduling_tour_advances_only_after_success_and_has_bilingual_voice(monkeypatch):
    async def no_model(*args):
        raise AssertionError('Known feature guides must start immediately')
    monkeypatch.setattr(main, 'model_reply', no_model)
    with TestClient(main.app) as client:
        session = client.post('/api/assistant/sessions').json()
        url = f"/api/assistant/sessions/{session['session_id']}/turn"
        headers = {'X-Assistant-Session': session['session_token']}
        context = {'route': '/leads/manage-leads', 'mode': 'crm', 'available_actions': ['show_lead_feature']}
        response = client.post(url, headers=headers, json={'message': 'meeting schedule kaise kare', 'context': context})
        for stage in ('open', 'details', 'finish'):
            assert response.status_code == 200
            body = response.json()
            action = body['actions'][0]
            assert action['name'] == 'show_lead_feature'
            assert action['arguments'] == {'feature': 'meeting', 'stage': stage}
            assert body['narration']['key'] == 'feature.meeting.' + stage
            assert body['narration']['language'] == 'hi'
            response = client.post(url, headers=headers, json={'context': context, 'results': [
                {'id': action['id'], 'name': action['name'], 'ok': True, 'detail': 'Visible'}]})
        assert response.json()['done'] and not response.json()['actions']


def test_all_feature_voice_keys_exist_in_both_languages():
    for feature in FEATURES:
        for stage in ('open', 'details', 'finish'):
            for language in ('hi', 'en'):
                assert NARRATIONS_BY_LANGUAGE[language][f'feature.{feature}.{stage}']
