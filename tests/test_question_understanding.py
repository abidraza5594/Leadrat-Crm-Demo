import json

import httpx
import pytest

from app import question_understanding as interpretation
from app import main
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_semantic_query_preserves_followup_and_uses_no_action_tools(monkeypatch):
    original = httpx.AsyncClient
    def handle(request):
        body = json.loads(request.content)
        assert "tools" not in body
        data = json.loads(body["messages"][-1]["content"])
        assert data["previous_questions"] == ["How do I give a lead to another agent?"]
        assert data["question"] == "who is allowed to do that?"
        return httpx.Response(200, json={"message": {"content": json.dumps({
            "query": "lead reassignment required permissions", "guide": "none", "clarification": ""})}})
    monkeypatch.setattr(interpretation.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
    result = await interpretation.understand_question("who is allowed to do that?", ["How do I give a lead to another agent?"])
    assert result.query == "lead reassignment required permissions"
    assert result.guide == "none"


def test_incorrect_guide_label_cannot_override_semantic_topic(monkeypatch):
    async def interpret(question, previous):
        return interpretation.Understanding(query="Facebook integration", guide="bulk")
    async def reply(messages, tools):
        assert tools == []
        assert any("integration/facebook" in item.get("content", "") for item in messages)
        return {"content": "Facebook integration help."}
    monkeypatch.setattr(main, "understand_question", interpret)
    monkeypatch.setattr(main, "model_reply", reply)
    with TestClient(main.app) as client:
        session = client.post('/api/assistant/sessions').json()
        response = client.post(f"/api/assistant/sessions/{session['session_id']}/turn",
            headers={"X-Assistant-Session": session['session_token']}, json={
                "message": "Can enquiries from FB come here?", "context": {
                    "route": "/leads/manage-leads", "available_actions": [], "mode": "crm"}})
        assert response.status_code == 200
        assert response.json()["message"] == "Facebook integration help."


def test_specific_questions_do_not_return_generic_reviewed_guide():
    from app.reviewed_help import reviewed_answer
    for question in ("lead notes deletion", "lead notes permissions", "why lead notes failed", "task priority editing"):
        assert reviewed_answer(question, "en") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("content", ['not json', '{"query":"lead","guide":"delete_lead"}', '{}'])
async def test_invalid_model_interpretation_falls_back_without_actions(monkeypatch, content):
    original = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"message": {"content": content}}))
    monkeypatch.setattr(interpretation.httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs))
    result = await interpretation.understand_question("my upload failed", [])
    assert result.query == "my upload failed"
    assert result.guide == "none"
