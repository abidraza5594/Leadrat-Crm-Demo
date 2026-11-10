"""Soniox credentials stay on the server; browser streams use restricted keys."""
import asyncio
import base64
import json
import os
import re
import secrets
import httpx
from . import transport, usage

STT_MODEL = 'stt-rt-v5'
TTS_MODEL = 'tts-rt-v2'
STT_URL = 'wss://stt-rt.soniox.com/transcribe-websocket'

def key():
    value = os.getenv('SONIOX_API_KEY', '').strip()
    if not value: raise ValueError('Soniox API key is not configured')
    return value

async def temporary_key(session_id):
    async with transport.client() as client:
        response = await client.post('https://api.soniox.com/v1/auth/temporary-api-key',
            headers={'Authorization': 'Bearer ' + key()}, timeout=10,
            json={'usage_type': 'transcribe_websocket', 'expires_in_seconds': 60,
                  'single_use': True, 'max_session_duration_seconds': 120,
                  'client_reference_id': session_id})
        response.raise_for_status()
        result = response.json()
    return {'api_key': result['api_key'], 'expires_at': result['expires_at'],
            'url': STT_URL, 'model': STT_MODEL, 'max_seconds': 115}

# Real-time speech output. One WebSocket is opened before it is needed and kept alive, so a reply never pays
# the connection set-up (about a second from India to the default region). Up to five speech streams share
# it; audio arrives as MP3 chunks while the rest is still being generated.
TTS_URL = os.getenv('SONIOX_TTS_URL', 'wss://tts-rt.soniox.com/tts-websocket')
TTS_VOICE = os.getenv('SONIOX_VOICE', 'Priya')
TTS_SPEED = float(os.getenv('SONIOX_TTS_SPEED', '1.1'))
DEVANAGARI = re.compile('[ऀ-ॿ]')

class RealtimeSpeech:
    def __init__(self):
        self.ws = None; self.reader = None; self.keeper = None
        self.lock = asyncio.Lock(); self.slots = asyncio.Semaphore(5); self.streams = {}

    async def connect(self):
        import websockets
        async with self.lock:
            if self.ws is not None and self.ws.state.name == 'OPEN': return self.ws
            self.ws = await websockets.connect(TTS_URL, additional_headers={'Authorization': 'Bearer ' + key()},
                                               max_size=None, open_timeout=10)
            self.reader = asyncio.create_task(self.read(self.ws)); self.keeper = asyncio.create_task(self.keep(self.ws))
            return self.ws

    async def read(self, ws):
        try:
            async for raw in ws:
                message = json.loads(raw); queue = self.streams.get(message.get('stream_id'))
                if queue: queue.put_nowait(message)
        except Exception: pass
        finally:
            # A lost connection ends every stream on it; the next request opens a new one.
            for queue in self.streams.values(): queue.put_nowait({'error_code': 503, 'error_message': 'connection closed'})
            if self.ws is ws: self.ws = None

    async def keep(self, ws):
        try:
            while True:
                await asyncio.sleep(20)
                await ws.send('{"keep_alive": true}')
        except Exception: pass

    async def stream(self, text, reference=None):
        """MP3 chunks for text, yielded as soon as Soniox produces them."""
        async with self.slots:
            ws = await self.connect()
            stream_id = secrets.token_hex(8); queue = asyncio.Queue(); self.streams[stream_id] = queue; done = False
            try:
                await ws.send(json.dumps({'stream_id': stream_id, 'model': TTS_MODEL, 'voice': TTS_VOICE, 'speed': TTS_SPEED,
                    'language': 'hi' if DEVANAGARI.search(text) else 'en', 'audio_format': 'mp3', 'sample_rate': 24000,
                    'bitrate': 64000, 'client_reference_id': reference or usage.session_id.get() or 'beacon'}))
                await ws.send(json.dumps({'text': text, 'text_end': True, 'stream_id': stream_id}))
                while True:
                    message = await asyncio.wait_for(queue.get(), 20)
                    if message.get('error_code'):
                        raise RuntimeError('Soniox speech failed: %s %s' % (message.get('error_code'), message.get('error_type') or message.get('error_message')))
                    if message.get('audio'): yield base64.b64decode(message['audio'])
                    if message.get('terminated'): done = True; return
            finally:
                self.streams.pop(stream_id, None)
                if not done and self.ws is ws:
                    # Interrupted (a new question, a closed player): stop generating and billing at once.
                    try: await ws.send(json.dumps({'stream_id': stream_id, 'cancel': True}))
                    except Exception: pass
                await usage.record('soniox', TTS_MODEL, 'speech_output', status='usage_in_provider_logs',
                                   input_characters=len(text), completed=done)

    async def close(self):
        ws, self.ws = self.ws, None
        for task in (self.reader, self.keeper):
            if task and not task.done(): task.cancel()
        if ws is not None:
            try: await ws.close()
            except Exception: pass

realtime_speech = RealtimeSpeech()
