import pytest
from fastapi.testclient import TestClient

from app import main
from app.question_understanding import Understanding


@pytest.mark.parametrize('question,reply,language,clarification', [
    ('What do you mean?', 'Which feature would you like me to explain?', 'en', True),
    ('ye kya hai', 'Aap kis feature ke baare mein pooch rahe hain?', 'hi', True),
    ('Explain source', 'A source records where an enquiry came from.', 'en', False),
])
def test_every_text_reply_has_session_scoped_audio(monkeypatch, question, reply, language, clarification):
    async def interpret(*args):
        return Understanding(query=question, clarification=reply if clarification else '')
    async def model(*args):
        return {'content': reply}
    spoken = []
    async def speech(text, voice):
        spoken.append(text)
        return b'audio'
    monkeypatch.setattr(main, 'understand_question', interpret)
    monkeypatch.setattr(main, 'model_reply', model)
    monkeypatch.setattr(main, 'synthesize_reply', speech)
    with TestClient(main.app) as client:
        first = client.post('/api/assistant/sessions').json()
        base = f"/api/assistant/sessions/{first['session_id']}"
        headers = {'X-Assistant-Session': first['session_token']}
        response = client.post(base + '/turn', headers=headers, json={'message': question, 'context': {
            'route': '/leads/manage-leads', 'mode': 'crm', 'available_actions': []}})
        assert response.status_code == 200
        narration = response.json()['narration']
        assert narration['text'] == reply and narration['language'] == language
        assert narration['key'].startswith('reply.')
        assert spoken == []  # Voice OFF does not contact TTS.
        body = {'key': narration['key'], 'language': language,
                'voice': 'hi-IN-SwaraNeural' if language == 'hi' else 'en-IN-NeerjaNeural'}
        assert client.post(base + '/speech', headers=headers, json=body).content == b'audio'
        assert spoken == [reply]
        other = client.post('/api/assistant/sessions').json()
        assert client.post(f"/api/assistant/sessions/{other['session_id']}/speech",
            headers={'X-Assistant-Session': other['session_token']}, json=body).status_code == 403


def test_failed_demo_reply_is_also_spoken():
    with TestClient(main.app) as client:
        session = client.post('/api/assistant/sessions').json()
        response = client.post(f"/api/assistant/sessions/{session['session_id']}/turn",
            headers={'X-Assistant-Session': session['session_token']}, json={
                'message': 'how to add lead', 'context': {'route': '/leads/manage-leads', 'mode': 'crm', 'available_actions': []}})
        assert response.status_code == 200
        assert response.json()['narration']['text'] == response.json()['message']
