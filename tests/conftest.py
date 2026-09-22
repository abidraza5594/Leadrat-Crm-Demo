"""Keep unit/API tests independent of an installed, running Ollama model."""

import pytest

from app import main
from app.question_understanding import Understanding
from app.crm_knowledge import tokens


@pytest.fixture(autouse=True)
def local_interpretation_stub(monkeypatch):
    async def interpret(question, previous):
        words = set(tokens(question))
        guide = "none"
        if {"lead", "note"} <= words:
            guide = "notes"
        elif {"lead", "bulk", "upload"} <= words:
            guide = "bulk"
        elif {"task", "priority"} <= words:
            guide = "priority"
        return Understanding(query=question, guide=guide)
    monkeypatch.setattr(main, "understand_question", interpret)
