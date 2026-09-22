from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.crm_knowledge import KnowledgeIndex, knowledge
from app.intents import fast_guide_intent


@pytest.mark.parametrize("question,path", [
    ("lead notes kaise add kare", "lead-notes"),
    ("lead reassign kaise kare", "individual-reassign"),
    ("lead documents upload", "leads-document-upload"),
    ("bulk upload leads", "/bulk-upload/"),
    ("attendance clock in", "clock-in-out"),
    ("task priority", "task-priority"),
    ("facebook integration", "/facebook/"),
    ("lead history", "lead-history"),
])
def test_actual_feature_retrieval(question, path):
    assert any(path in chunk.source for chunk in knowledge.search(question, 3))


@pytest.mark.parametrize("question", ["lead notes kaise add kare", "lead status kaise change kare",
                                         "reports kaise use kare", "task priority samjhao"])
def test_feature_questions_do_not_start_generic_tour(question):
    assert fast_guide_intent(question) is None


def test_excludes_secrets_and_commented_ui(tmp_path: Path):
    area = tmp_path / "src/app/features/leads"
    area.mkdir(parents=True)
    (area / "notes.component.html").write_text('<!-- obsolete secretbutton -->\n<button>Notes</button>')
    (tmp_path / ".env").write_text('PRIVATE_TOKEN=hidden')
    index = KnowledgeIndex(tmp_path)
    assert len(index.files) == 1
    text = index.context("notes")
    assert "secretbutton" not in text and "PRIVATE_TOKEN" not in text


def test_grounded_answer_has_no_action_tools(monkeypatch):
    called = False
    async def reply(messages, tools):
        nonlocal called
        called = True
        assert tools == []
        text = "\n".join(message.get("content", "") for message in messages)
        assert "lead-notes.component" in text
        assert "Permissions.Leads.UpdateNotes" in text
        return {"content": "Notes ka purpose conversation ki details record karna hai."}

    monkeypatch.setattr(main, "model_reply", reply)
    monkeypatch.setattr(main, "reviewed_answer", lambda *args: None)
    with TestClient(main.app) as client:
        session = client.post('/api/assistant/sessions').json()
        response = client.post(f"/api/assistant/sessions/{session['session_id']}/turn",
            headers={"X-Assistant-Session": session['session_token']},
            json={"message": "lead notes kaise add kare", "context": {
                "route": "/leads/manage-leads", "mode": "crm", "form_ready": False,
                "available_actions": ["open_module"], "available_modules": ["leads"]}})
        assert response.status_code == 200
        assert response.json()["actions"] == []
        assert response.json()["language"] == "hi"
        assert called


def test_reviewed_help_is_immediate_and_does_not_invent_controls(monkeypatch):
    async def no_inference(*args):
        raise AssertionError("Reviewed instructions should not wait for inference")
    monkeypatch.setattr(main, "model_reply", no_inference)
    with TestClient(main.app) as client:
        session = client.post('/api/assistant/sessions').json()
        response = client.post(f"/api/assistant/sessions/{session['session_id']}/turn",
            headers={"X-Assistant-Session": session['session_token']},
            json={"message": "How do task priorities work?", "context": {
                "route": "/task/manage-task", "mode": "crm", "form_ready": False,
                "available_actions": []}})
        assert response.status_code == 200
        answer = response.json()
        assert "Critical" in answer["message"] and "radio" in answer["message"]
        assert "dropdown" not in answer["message"]
        assert answer["actions"] == []
