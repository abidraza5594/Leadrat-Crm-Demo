"""Real-time Soniox speech against a local stand-in for the Soniox TTS WebSocket (no network, no cost)."""
import asyncio,base64,json
import websockets
from app import config,soniox
from app.voice import VoiceCache


def setup(monkeypatch,url):
    monkeypatch.setenv('SONIOX_API_KEY','test-key')
    monkeypatch.setattr(config,'TTS_PROVIDER','soniox')
    monkeypatch.setattr(soniox,'TTS_URL',url)
    monkeypatch.setattr(soniox,'realtime_speech',soniox.RealtimeSpeech())


def test_speech_streams_on_one_warm_connection_and_an_interruption_cancels_it(monkeypatch):
    async def run():
        seen={'connections':0,'configs':[],'cancelled':[]};release=asyncio.Event()
        async def handler(ws):
            seen['connections']+=1
            assert ws.request.headers['Authorization']=='Bearer test-key'
            async def speak(stream_id,text):
                await ws.send(json.dumps({'audio':base64.b64encode(b'first').decode(),'stream_id':stream_id}))
                if text=='Hold on':await release.wait()
                await ws.send(json.dumps({'audio':base64.b64encode(b'last').decode(),'audio_end':True,'stream_id':stream_id}))
                await ws.send(json.dumps({'terminated':True,'stream_id':stream_id}))
            async for raw in ws:
                message=json.loads(raw)
                if 'model' in message:seen['configs'].append(message)
                elif message.get('cancel'):seen['cancelled'].append(message['stream_id'])
                elif message.get('text_end'):asyncio.ensure_future(speak(message['stream_id'],message['text']))
        server=await websockets.serve(handler,'127.0.0.1',0)
        setup(monkeypatch,'ws://127.0.0.1:%d'%server.sockets[0].getsockname()[1])
        cache=VoiceCache()
        assert b''.join([c async for c in cache.stream('Welcome to Beacon.')])==b'firstlast'
        assert b''.join([c async for c in cache.stream('नमस्ते, बीकन में आपका स्वागत है।')])==b'firstlast'
        held=cache.stream('Hold on')
        assert await asyncio.wait_for(anext(held),2)==b'first'  # played before the rest exists
        cache.close();await held.aclose()
        for _ in range(50):
            if seen['cancelled']:break
            await asyncio.sleep(.02)
        assert seen['connections']==1  # one warm connection for every reply
        assert [c['language'] for c in seen['configs']]==['en','hi','en']
        assert all(c['voice']=='Priya' and c['audio_format']=='mp3' and c['model']=='tts-rt-v2' for c in seen['configs'])
        assert seen['cancelled']==[seen['configs'][2]['stream_id']]
        release.set();await soniox.realtime_speech.close();server.close();await server.wait_closed()
    asyncio.run(run())


def test_a_soniox_failure_before_any_audio_uses_the_backup_voice(monkeypatch):
    async def run():
        import edge_tts
        async def handler(ws):
            async for raw in ws:
                message=json.loads(raw)
                if message.get('text_end'):
                    await ws.send(json.dumps({'error_code':402,'error_type':'balance_exhausted','stream_id':message['stream_id']}))
        class Edge:
            def __init__(self,*args,**kwargs):pass
            async def stream(self):yield {'type':'audio','data':b'backup'}
        monkeypatch.setattr(edge_tts,'Communicate',Edge)
        server=await websockets.serve(handler,'127.0.0.1',0)
        setup(monkeypatch,'ws://127.0.0.1:%d'%server.sockets[0].getsockname()[1])
        cache=VoiceCache()
        assert b''.join([c async for c in cache.stream('Hello')])==b'backup'
        cache.close();await soniox.realtime_speech.close();server.close();await server.wait_closed()
    asyncio.run(run())
