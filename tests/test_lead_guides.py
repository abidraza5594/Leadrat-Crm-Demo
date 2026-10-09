import asyncio
import pytest
from app.planner import FEATURES, Plan
from app.voice import VoiceCache
from app import main



def test_audio_prefetch_deduplicates_and_stable_ids(monkeypatch):
    async def run():
        calls=[]
        async def synth(self,text):calls.append(text);await asyncio.sleep(0);return b'audio'
        monkeypatch.setattr(VoiceCache,'synthesize',synth)
        s=main.Session(voice_enabled=True)
        s.say('First reply');first=s.messages[0]['id']
        task=s.voice_cache.prepare('First reply')
        assert task is s.voice_cache.prepare('First reply')
        assert await task==b'audio' and calls==['First reply']
        s.voice_enabled=False
        for _ in range(90):s.say('Next reply')
        assert first not in {m['id'] for m in s.messages}
        assert len({m['id'] for m in s.messages})==80
        s.voice_cache.close()
    asyncio.run(run())

def test_failed_nested_action_explains_without_claiming_demo(monkeypatch):
    class Worker:
        async def open_module(self,f):return 'Leads is open.'
    async def blocked(*args):raise main.DemoError('No email control is available.')
    monkeypatch.setattr(main,'walkthrough',blocked)
    async def run():
        s=main.Session(worker=Worker())
        await main.execute(s,'show email')
        assert s.steps[-1]['status']=='failed'
        assert 'email' not in s.shown
        assert any('No email control' in m['text'] for m in s.messages)
    asyncio.run(run())
