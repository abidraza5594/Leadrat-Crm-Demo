"""Bounded in-memory speech cache; concurrent callers share synthesis."""
import asyncio
import hashlib
import time
from collections import OrderedDict
import httpx
from . import config

class VoiceCache:
    def __init__(self):
        self.reference=None
        self.tasks=OrderedDict()
        self.streams={}
        self.limit=asyncio.Semaphore(2)
        # text hash -> synthesis milliseconds (latency measurement only; no text is stored).
        self.timings={}

    def prepare(self,text):
        text=text[:3000]
        key=hashlib.sha256(text.encode()).hexdigest()
        if key in self.tasks:
            self.tasks.move_to_end(key)
            return self.tasks[key]
        entry={'chunks':[], 'changed':asyncio.Event(), 'done':False, 'error':None}
        self.streams[key]=entry
        async def produce():
            try:
                audio=await self.synthesize(text)
                if not entry['chunks']:entry['chunks'].append(audio)
                return audio
            except BaseException as exc:
                entry['error']=exc
                raise
            finally:
                entry['done']=True
                entry['changed'].set()
        task=asyncio.create_task(produce())
        self.tasks[key]=task
        # Retrieve errors from speculative work; a request can still await the same task.
        task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
        while len(self.tasks)>48:
            old_key,old=self.tasks.popitem(last=False)
            old_entry=self.streams.pop(old_key,None)
            if old_entry and not old_entry['done']:
                old_entry.update(done=True,error=asyncio.CancelledError())
                old_entry['changed'].set()
            if not old.done():old.cancel()
        return task

    async def stream(self,text):
        """Replay cached chunks, then follow one shared producer without buffering completion."""
        self.prepare(text)
        entry=self.streams[hashlib.sha256(text[:3000].encode()).hexdigest()]
        index=0
        while True:
            while index<len(entry['chunks']):
                chunk=entry['chunks'][index];index+=1
                yield chunk
            if entry['done']:
                if entry['error']:raise entry['error']
                return
            entry['changed'].clear()
            await entry['changed'].wait()

    async def synthesize(self,text):
        started=time.monotonic()
        try:return await self._synthesize(text)
        finally:self.timings[hashlib.sha256(text[:3000].encode()).hexdigest()]=round((time.monotonic()-started)*1000)

    async def _synthesize(self,text):
        async with self.limit:
            async with asyncio.timeout(22):
                if config.TTS_PROVIDER=='soniox':
                    from .soniox import synthesize
                    audio=await synthesize(text,self.reference)
                elif config.TTS_PROVIDER=='edge':
                    import edge_tts
                    chunks=[]
                    entry=self.streams.get(hashlib.sha256(text.encode()).hexdigest())
                    async for chunk in edge_tts.Communicate(text,'en-IN-NeerjaNeural',rate='+12%').stream():
                        if chunk['type']=='audio':
                            chunks.append(chunk['data'])
                            if entry is not None:
                                entry['chunks'].append(chunk['data'])
                                entry['changed'].set()
                    audio=b''.join(chunks)
                elif config.TTS_URL:
                    async with httpx.AsyncClient(timeout=10) as client:
                        result=await client.post(config.TTS_URL+'/audio/speech',json={'model':'kokoro','voice':config.TTS_VOICE,'input':text,'response_format':'mp3'})
                        result.raise_for_status();audio=result.content
                else:raise ValueError('No voice configured')
                if not audio:raise ValueError('Empty audio')
                return audio

    def close(self):
        for entry in self.streams.values():
            if not entry['done']:
                entry.update(done=True,error=asyncio.CancelledError())
                entry['changed'].set()
        for task in self.tasks.values():
            if not task.done():task.cancel()
        self.tasks.clear()
        self.streams.clear()
