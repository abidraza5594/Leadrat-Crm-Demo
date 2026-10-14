"""Soniox credentials stay on the server; browser streams use restricted keys."""
import os
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

async def synthesize(text, reference=None):
    async with transport.client() as client:
        response = await client.post('https://tts-rt.soniox.com/tts',
            headers={'Authorization': 'Bearer ' + key()}, timeout=20,
            json={'model': TTS_MODEL, 'voice': os.getenv('SONIOX_VOICE', 'Adrian'),
                  'language': os.getenv('SONIOX_TTS_LANGUAGE', 'en'), 'audio_format': 'mp3',
                  'text': text, 'client_reference_id': reference or usage.session_id.get() or 'beacon'})
        response.raise_for_status()
    # Provider usage logs supply exact audio tokens; characters are not labelled as billed tokens.
    await usage.record('soniox', TTS_MODEL, 'speech_output', status='usage_in_provider_logs',
                       input_characters=len(text), audio_bytes=len(response.content),
                       client_reference_id=reference or usage.session_id.get() or 'beacon',
                       request_id=response.headers.get('x-request-id'))
    return response.content
