import asyncio
import pytest
from app import config
from app.voice import VoiceCache


def test_first_chunk_shared_stream_replay_and_disconnect(monkeypatch):
    async def run():
        import edge_tts
        release=asyncio.Event();calls=[]
        class Fake:
            def __init__(self,*args,**kwargs):calls.append(args)
            async def stream(self):
                yield {'type':'audio','data':b'first'}
                await release.wait()
                yield {'type':'audio','data':b'last'}
        monkeypatch.setattr(config,'TTS_PROVIDER','edge')
        monkeypatch.setattr(edge_tts,'Communicate',Fake)
        cache=VoiceCache();one=cache.stream('Hello');two=cache.stream('Hello')
        assert await asyncio.wait_for(anext(one),1)==b'first'
        assert not cache.prepare('Hello').done()
        assert await anext(two)==b'first'
        await one.aclose()  # Closing one HTTP consumer must not cancel the shared producer.
        release.set()
        assert b''.join([chunk async for chunk in two])==b'last'
        assert b''.join([chunk async for chunk in cache.stream('Hello')])==b'firstlast'
        assert len(calls)==1
        cache.close()
    asyncio.run(run())


def test_stream_failure_and_close_wake_waiters(monkeypatch):
    async def run():
        import edge_tts
        class Fake:
            def __init__(self,*args,**kwargs):pass
            async def stream(self):
                yield {'type':'audio','data':b'first'}
                raise RuntimeError('provider disconnected')
        monkeypatch.setattr(config,'TTS_PROVIDER','edge')
        monkeypatch.setattr(edge_tts,'Communicate',Fake)
        cache=VoiceCache();stream=cache.stream('Hello')
        assert await anext(stream)==b'first'
        with pytest.raises(RuntimeError):await anext(stream)
        cache.close()
        class Waiting(Fake):
            async def stream(self):
                await asyncio.Event().wait()
                yield {}
        monkeypatch.setattr(edge_tts,'Communicate',Waiting)
        waiting=asyncio.create_task(anext(cache.stream('Wait')))
        await asyncio.sleep(0)
        cache.close()
        with pytest.raises(asyncio.CancelledError):await asyncio.wait_for(waiting,1)
    asyncio.run(run())
