"""Bounded in-memory speech cache; concurrent callers share synthesis."""
import asyncio
import hashlib
import time
from collections import OrderedDict
import httpx
from . import config

class VoiceCache:
    def __init__(self):
        self.tasks=OrderedDict()
        self.limit=asyncio.Semaphore(2)
        # text hash -> synthesis milliseconds (latency measurement only; no text is stored).
        self.timings={}

    def prepare(self,text):
        text=text[:3000]
        key=hashlib.sha256(text.encode()).hexdigest()
        if key in self.tasks:
            self.tasks.move_to_end(key)
            return self.tasks[key]
        task=asyncio.create_task(self.synthesize(text))
        self.tasks[key]=task
        # Retrieve errors from speculative work; a request can still await the same task.
        task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
        while len(self.tasks)>48:
            _,old=self.tasks.popitem(last=False)
            if not old.done():old.cancel()
        return task

    async def synthesize(self,text):
        started=time.monotonic()
        try:return await self._synthesize(text)
        finally:self.timings[hashlib.sha256(text[:3000].encode()).hexdigest()]=round((time.monotonic()-started)*1000)

    async def _synthesize(self,text):
        async with self.limit:
            async with asyncio.timeout(12):
                if config.TTS_PROVIDER=='edge':
                    import edge_tts
                    chunks=[]
                    async for chunk in edge_tts.Communicate(text,'en-IN-NeerjaNeural',rate='+12%').stream():
                        if chunk['type']=='audio':chunks.append(chunk['data'])
                    audio=b''.join(chunks)
                elif config.TTS_URL:
                    async with httpx.AsyncClient(timeout=10) as client:
                        result=await client.post(config.TTS_URL+'/audio/speech',json={'model':'kokoro','voice':config.TTS_VOICE,'input':text,'response_format':'mp3'})
                        result.raise_for_status();audio=result.content
                else:raise ValueError('No voice configured')
                if not audio:raise ValueError('Empty audio')
                return audio

    def close(self):
        for task in self.tasks.values():
            if not task.done():task.cancel()
        self.tasks.clear()
