import pytest

@pytest.fixture(autouse=True)
def no_hosted_calls(monkeypatch, tmp_path):
    """Tests never call paid or external services, and never write the real handoff outbox."""
    from app import qualify, handoff
    async def offline(msgs): raise ValueError('hosted model disabled in tests')
    monkeypatch.setattr(qualify, '_hosted', offline)
    monkeypatch.setattr(handoff, 'OUTBOX', tmp_path / 'outbox')
