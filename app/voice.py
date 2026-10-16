"""Bounded in-memory speech cache; concurrent callers share synthesis."""
import asyncio
import hashlib
import os
import time
from collections import OrderedDict
import httpx
from . import config

EDGE_VOICE='en-IN-NeerjaNeural'
EDGE_RATE='+12%'
# Beacon's fixed sentences (welcome, follow-up questions) are synthesised once and kept, in memory and
# in .state/voice, so they play without a synthesis wait. Answers to a visitor are never written to disk.
PHRASES:dict[str,bytes]={}
PHRASE_DIR=config.ROOT/'.state'/'voice'

def text_key(text):
    return hashlib.sha256(text[:3000].encode()).hexdigest()

async def edge_audio(text,on_chunk=None):
    import edge_tts
    chunks=[]
    async for chunk in edge_tts.Communicate(text,EDGE_VOICE,rate=EDGE_RATE).stream():
        if chunk['type']=='audio':
            chunks.append(chunk['data'])
            if on_chunk:on_chunk(chunk['data'])
    return b''.join(chunks)

async def warm_phrases(texts):
    """Load fixed phrases from disk, synthesising only the missing ones. Failures are left for later."""
    if config.TTS_PROVIDER!='edge':return
    limit=asyncio.Semaphore(3)
    async def one(text):
        key=text_key(text)
        if key in PHRASES:return
        path=PHRASE_DIR/(hashlib.sha256((EDGE_VOICE+EDGE_RATE+text).encode()).hexdigest()+'.mp3')
        try:
            PHRASES[key]=await asyncio.to_thread(path.read_bytes);return
        except OSError:pass
        async with limit:
            try:
                async with asyncio.timeout(22):audio=await edge_audio(text)
            except Exception:return
        if not audio:return
        PHRASES[key]=audio
        def write():
            PHRASE_DIR.mkdir(parents=True,exist_ok=True)
            temporary=path.with_suffix('.tmp');temporary.write_bytes(audio);os.replace(temporary,path)
        try:await asyncio.to_thread(write)
        except OSError:pass
    await asyncio.gather(*(one(text) for text in dict.fromkeys(texts) if text))

class VoiceCache:
    def __init__(self):
        self.reference=None
        self.tasks=OrderedDict()
        self.streams={}
        # The first part of an answer, the next part and the follow-up question synthesise together.
        self.limit=asyncio.Semaphore(3)
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
                audio=PHRASES.get(key) or await self.synthesize(text)
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
                    entry=self.streams.get(hashlib.sha256(text.encode()).hexdigest())
                    def forward(data):
                        if entry is not None:
                            entry['chunks'].append(data)
                            entry['changed'].set()
                    audio=await edge_audio(text,forward)
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
