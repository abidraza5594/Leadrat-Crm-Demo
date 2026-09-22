"""Online speech for tutorial narration and session-authorized assistant replies."""

import asyncio
import re
from collections import OrderedDict

import edge_tts

from .catalog import NARRATIONS_BY_LANGUAGE

_cache: OrderedDict[tuple[str, str], bytes] = OrderedDict()
_gate = asyncio.Semaphore(2)
MAX_CACHE_BYTES = 12 * 1024 * 1024


async def synthesize_reply(text: str, voice: str) -> bytes:
    """Speak a server-issued reply. Do not retain reply audio in the shared cache."""
    spoken = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    spoken = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", spoken)
    spoken = spoken.replace('**', '').replace('`', '')
    async with _gate:
        async with asyncio.timeout(35):
            audio = bytearray()
            async for chunk in edge_tts.Communicate(spoken, voice, rate="+12%").stream():
                if chunk['type'] == 'audio':
                    audio.extend(chunk['data'])
                    if len(audio) > 3 * 1024 * 1024:
                        raise ValueError('Reply audio exceeded the allowed size.')
            if not audio:
                raise ValueError('Voice service returned no audio.')
            return bytes(audio)


async def synthesize(key: str, voice: str) -> bytes:
    language = voice.split("-", 1)[0]
    cache_key = (key, voice)
    # Ready audio must not queue behind unrelated network synthesis requests.
    if cache_key in _cache:
        _cache.move_to_end(cache_key)
        return _cache[cache_key]
    async with _gate:
        if cache_key in _cache:
            _cache.move_to_end(cache_key)
            return _cache[cache_key]
        async with asyncio.timeout(25):
            audio = bytearray()
            async for chunk in edge_tts.Communicate(NARRATIONS_BY_LANGUAGE[language][key], voice, rate="+12%").stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
                    if len(audio) > 1024 * 1024:
                        raise ValueError("Voice response exceeded the allowed size.")
        if not audio:
            raise ValueError("Voice service returned no audio.")
        _cache[cache_key] = bytes(audio)
        while sum(map(len, _cache.values())) > MAX_CACHE_BYTES:
            _cache.popitem(last=False)
        return _cache[cache_key]
