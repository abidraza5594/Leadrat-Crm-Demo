import asyncio
import hashlib
import json
import os
import secrets
import re
import time
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field
from . import config
from .browser import BrowserWorker, DemoError, device_location, has_login_credentials
from .browser_pool import WarmBrowser
from .planner import FEATURES, declined, warm_up, write_request, USAGE
from .project import PROJECT
from .conversation_engine import ConversationEngine, Decision
from .conversation_store import ConversationStore
from .semantic_knowledge import SemanticKnowledge
from .screens import Screens
from .qualification import Facts, qualify
from .voice import VoiceCache, warm_phrases
from .lead_browser import walkthrough
from .qualify import EMAIL, PHONE, EXCLUDED_KINDS, qualify_session, rules_extract, transcript_of
from . import handoff as handoffs
from fastapi.responses import JSONResponse
from . import docs
from . import transport, usage, recovery

READ_ONLY=("I can't do that here. Only the confirmed Add Lead flow can save a new record. I do not delete, edit existing records, send, upload, export, assign or call. "
    "I can show you where it is done and how it works; for example, ask \"how do I delete a lead?\"")
# Optional filler spoken while a slow answer is prepared. Off by default: hearing the same phrase
# before every reply sounds robotic. BEACON_VOICE_ACK=1 enables it, at most once per session.
ACKS={'question':'Let me check that for you.','action':'Sure, one moment.'}
VOICE_ACK=os.getenv('BEACON_VOICE_ACK','0')=='1'
ACK_AFTER=float(os.getenv('ACK_AFTER_MS','2500'))/1000
WELCOME='Welcome to Beacon! I can answer your questions about Leadrat and show you how it works. What would you like to explore?'

# A widget polls several times per second; one that has been silent this long was closed or crashed.
ABANDONED_AFTER=120
TAB_CLOSE_GRACE=10
LOGIN_HELP=('The hidden demo browser is not signed in to the test CRM. Operator: run .\\login.ps1 once, '
    'or start Beacon with test credentials. This screen updates automatically after sign-in.')

def speech_parts(text):
    # Short clips reduce first-audio synthesis time and enable parallel lookahead.
    parts=[]
    for sentence in re.split(r'(?<=[.!?])\s+',text.strip()):
        if parts and len(parts[-1])+len(sentence)<200:parts[-1]+=' '+sentence
        elif sentence:parts.append(sentence)
    parts=parts or [text]
    # The first clip decides time-to-first-audio: keep it to ~90 characters, split at a comma or space.
    first=parts[0]
    if len(first)>90:
        cut=max(first.rfind(', ',40,90),first.rfind(' ',40,90))
        if cut>0:parts=[first[:cut+1].strip(),first[cut+1:].strip()]+parts[1:]
    return parts

@dataclass
class Session:
    id:str=field(default_factory=lambda:secrets.token_urlsafe(18))
    token:str=field(default_factory=lambda:secrets.token_urlsafe(32))
    created:float=field(default_factory=time.monotonic)
    touched:float=field(default_factory=time.monotonic)
    seen:float=field(default_factory=time.monotonic)
    client_id:str=''
    leaving_deadline:float|None=None
    closing:bool=False
    last_completed:float=field(default_factory=time.monotonic)
    status:str='starting'
    messages:list=field(default_factory=list)
    steps:list=field(default_factory=list)
    last_error:str|None=None
    last_feature:str|None=None
    opted_out:bool=False
    shown:set=field(default_factory=set)
    # The feature Beacon suggested in its last follow-up, so a bare "yes" can run it.
    offer:str|None=None
    lead_draft:dict|None=None
    worker:BrowserWorker=field(default_factory=BrowserWorker)
    task:asyncio.Task|None=None
    boot:asyncio.Task|None=None
    relogin:asyncio.Task|None=None
    refresh_task:asyncio.Task|None=None
    last_turn:float=0
    last_turn_ms:int|None=None
    # Per-turn stage timings (ms since the turn was received); aggregate numbers only, no transcript.
    timings:list=field(default_factory=list)
    turn_started:float=0
    auth_checked:float=0
    auth_lost:float|None=None
    voice_enabled:bool=False
    voice_cache:VoiceCache=field(default_factory=VoiceCache)
    qual:dict|None=None
    qual_task:asyncio.Task|None=None
    handoff_status:str='not_requested'
    discovery_asked:list=field(default_factory=list)
    pending_discovery:str|None=None
    discovery_answers:dict=field(default_factory=dict)
    closed_politely:bool=False
    accepted_turns:dict=field(default_factory=dict)
    last_decision:dict|None=None
    fact_evidence:dict=field(default_factory=dict)
    customer_revision:int=0
    discovery_misses:dict=field(default_factory=dict)
    # Business questions already raised again after a product answer (each is re-asked at most once).
    reasked:set=field(default_factory=set)
    acknowledged:bool=False
    qual_dirty:bool=False
    # The visitor said they were finished; a repeated "nothing" gets a short reply, not the goodbye again.
    finished:bool=False
    # The CRM page last shown from the screen map, so "isme kya hota hai" refers to it.
    last_location:dict|None=None
    recovery_lock:asyncio.Lock=field(default_factory=asyncio.Lock)
    recovery_attempts:int=0
    recovery_checked:float=0
    speech_key_issued:float=0
    registration_status:str='needed'
    registration_accepted:bool=False
    registration_error:str|None=None
    registration_profile:dict|None=None
    registration_task:asyncio.Task|None=None
    registration_lock:asyncio.Lock=field(default_factory=asyncio.Lock)
    registration_blocked_phones:set=field(default_factory=set)
    def __post_init__(self):
        self.voice_cache.reference=self.id
    def say(self,text,kind=None):
        # One chat bubble per reply; voice fetches its short parts separately.
        parts=speech_parts(text)
        message_id=secrets.token_urlsafe(12)
        self.messages.append({'id':message_id,'role':'assistant','text':text,'parts':parts,**({'kind':kind} if kind else {})})
        if self.timings and kind is None and 'answer_reply_ms' not in self.timings[-1]:
            self.timings[-1]['answer_reply_ms']=round((time.monotonic()-self.turn_started)*1000)
        if self.timings and 'first_reply_ms' not in self.timings[-1]:
            self.timings[-1].update(first_reply_ms=round((time.monotonic()-self.turn_started)*1000),first_message_id=message_id,first_part_hash=hashlib.sha256(parts[0][:3000].encode()).hexdigest())
        if self.voice_enabled:
            for part in parts:self.voice_cache.prepare(part)
        self.messages=self.messages[-80:]
    def qual_view(self):
        if self.qual:return {**accepted_qualification(self,self.qual),'scorer':self.qual['source'],'fallback_attempts':self.qual['attempts']}
        from slm.labels import Extraction,complete
        pending=accepted_qualification(self,{'source':'pending','qualification':complete(Extraction()).model_dump()})
        return {**pending,**qualify(Facts(),declined=self.opted_out)}
    def snapshot(self):
        from .quick_replies import for_question
        problem=getattr(self.worker,'login_problem',None)
        return {'id':self.id,'status':self.status,'busy':bool(self.task and not self.task.done()),'messages':self.messages,
          'steps':self.steps,'qualification':self.qual_view(),'handoff_status':self.handoff_status,'last_error':self.last_error,'product_areas_shown':sorted(self.shown),
          'speech_provider':config.STT_PROVIDER,'tts_provider':config.TTS_PROVIDER,
          'registration_required':os.getenv('BEACON_REQUIRE_VISITOR_DETAILS','1')=='1',
          'registration_status':self.registration_status,
          'registration_accepted':self.registration_accepted,
          'registration_error':self.registration_error,
          'quick_replies':for_question(self.pending_discovery) if not (self.opted_out or self.finished or self.lead_draft) else None,
          'registration_blocked_phones':sorted(self.registration_blocked_phones),
          'login_help':(LOGIN_HELP+(' Last attempt: '+problem if problem else '')) if self.status=='login_required' else None}

sessions:dict[str,Session]={}
create_lock=asyncio.Lock()
background:set[asyncio.Task]=set()
registration_jobs:set[asyncio.Task]=set()
teardowns:set[asyncio.Task]=set()
browser_pool=WarmBrowser()
conversation_store=None
knowledge=SemanticKnowledge(project=PROJECT['id'],directory=PROJECT['knowledge_dir'])
screens=Screens()
engine=ConversationEngine(FEATURES,[],knowledge,project=PROJECT['id'],screens=screens)

def spawn(coroutine):
    # asyncio keeps only weak references to tasks; hold fire-and-forget work until it finishes.
    task=asyncio.create_task(coroutine);background.add(task);task.add_done_callback(background.discard)

async def close(s):
    if s.closing:return
    s.closing=True
    # Closing the demo must not cancel an accepted backend lead capture.
    for task in [s.task,s.boot,s.relogin,s.qual_task,s.refresh_task]:
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):await task
    s.voice_cache.close()
    s.messages.clear();s.steps.clear();sessions.pop(s.id,None)
    # The next visitor's browser starts preparing now. Saving this one's login and shutting Chrome
    # down takes seconds; the visitor closing the demo does not wait for it.
    if not sessions:browser_pool.prime()
    worker=s.worker
    async def shut_down():
        with suppress(Exception):await worker.close()
    task=asyncio.create_task(shut_down());teardowns.add(task);task.add_done_callback(teardowns.discard)

async def cleanup():
    while True:
        await asyncio.sleep(15)
        now=time.monotonic()
        for s in list(sessions.values()):
            if session_expired(s,now):await close(s)

def session_expired(s,now):
    working=any(task and not task.done() for task in (s.task,s.boot,s.relogin,s.registration_task))
    return (s.leaving_deadline is not None and now>=s.leaving_deadline) or now-s.seen>ABANDONED_AFTER or (now-s.touched>900 and not working)

@asynccontextmanager
async def lifespan(app):
    global conversation_store
    await transport.start()
    conversation_store=ConversationStore()
    await conversation_store.start()
    engine.store=conversation_store;knowledge.store=conversation_store
    engine.topics=sorted({c['module'] for c in docs.load(PROJECT['knowledge_dir'])})
    handoffs.prune()  # retention: drop handoff records older than HANDOFF_RETENTION_DAYS
    tasks=[asyncio.create_task(cleanup()),asyncio.create_task(warm_up())]
    async def warm_search():
        try:
            await knowledge.warm()
            await screens.prepare(knowledge.model)
        except Exception as exc:print('Semantic knowledge preparation failed:',type(exc).__name__,flush=True)
    # Loading the search model takes ~9 s; do it at start-up, not during the first visitor question.
    if os.getenv('BEACON_WARM_KNOWLEDGE','1')=='1':tasks.append(asyncio.create_task(warm_search()))
    # The welcome and follow-up questions then play without waiting for speech synthesis.
    if os.getenv('BEACON_WARM_VOICE','1')=='1':tasks.append(asyncio.create_task(warm_phrases(fixed_phrases())))
    if config.PROVIDER=='local' and __import__('os').getenv('BEACON_START_LOCAL_MODEL')=='1':
        async def start_model():
            from slm.local_runtime import ensure_local_model
            try:await asyncio.to_thread(ensure_local_model)
            except Exception as exc:print('Local model startup failed:',str(exc),flush=True)
        tasks.append(asyncio.create_task(start_model()))
    if config.PROVIDER=='local' and config.PLANNER_BACKEND=='llamacpp' and os.getenv('BEACON_START_LOCAL_MODEL')=='1':
        async def start_planner():
            from slm.planner_runtime import ensure_planner
            try:await asyncio.to_thread(ensure_planner)
            except Exception as exc:print('Conversation model startup failed:',str(exc),flush=True)
        tasks.append(asyncio.create_task(start_planner()))
    # Sign-in needs the device location; read it before the first visitor waits for it.
    if config.LOCAL_DEVICE_LOCATION and has_login_credentials():tasks.append(asyncio.create_task(device_location()))
    browser_pool.enabled=__import__('os').getenv('BEACON_PREWARM_BROWSER')=='1'
    browser_pool.prime()
    yield
    await browser_pool.close()
    for task in tasks:task.cancel()
    for task in tasks:
        with suppress(BaseException):await task
    for s in list(sessions.values()):await close(s)
    if teardowns:await asyncio.wait(list(teardowns),timeout=10)
    if registration_jobs:
        _,pending=await asyncio.wait(list(registration_jobs),timeout=30)
        for task in pending:task.cancel()
        if pending:await asyncio.gather(*pending,return_exceptions=True)
    await conversation_store.close();conversation_store=None;engine.store=None;knowledge.store=None
    await transport.close()

app=FastAPI(title='Beacon standalone demo backend',lifespan=lifespan,docs_url='/api/docs',redoc_url=None)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','testserver'])

@app.middleware('http')
async def security(request:Request,call_next):
    origin=request.headers.get('origin')
    if origin and origin not in config.ORIGINS:return Response('Origin is not registered',status_code=403)
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self' wss://stt-rt.soniox.com; frame-ancestors "+' '.join(sorted(config.ORIGINS))+';'
    return response

class Create(BaseModel):
    model_config=ConfigDict(extra='forbid')
    parent_origin:str=Field(max_length=200)
    voice:bool=False
class Turn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    message:str=Field(min_length=1,max_length=2000)
    # The visitor spoke or typed over a running demonstration: stop it and do the new request.
    interrupt:bool=False
    request_id:str|None=Field(default=None,min_length=8,max_length=80,pattern=r'^[A-Za-z0-9_-]+$')

def owned(id,request,touch=False):
    s=sessions.get(id)
    if not s or not secrets.compare_digest(request.headers.get('x-beacon-token',''),s.token):raise HTTPException(404,'Session not found')
    s.seen=time.monotonic()
    if touch:s.touched=s.seen
    return s

async def boot(s):
    try:
        if browser_pool.enabled:s.worker=await browser_pool.take()
        else:await s.worker.start()
        # Browser events wake recovery immediately; HTTP polling remains a fallback.
        def wake_recovery():
            if s.status not in {'ready','login_required','error'}:return
            if s.refresh_task and not s.refresh_task.done():return
            s.refresh_task=asyncio.create_task(refresh_status(s,immediate=True))
        s.worker.on_failure=wake_recovery
        if await s.worker.signed_in():
            s.status='ready'
        else:
            s.status='login_required'
            s.say('The demo browser is not signed in to the test CRM yet. You can still ask about the supported features, and the live screen will appear here once the operator signs in.')
    except asyncio.CancelledError:raise
    except Exception:
        s.status='error';s.last_error='The demo browser could not start or reach the CRM. Check that Google Chrome is installed and CRM_URL is reachable, then end this session and retry.'

async def relogin(s):
    await recovery.restore(s)

async def refresh_status(s,immediate=False):
    """Debounced sign-in state: a navigation or a transient read error must not blank the screen."""
    if s.status not in {'login_required','ready','error'}:return
    now=time.monotonic()
    # Actions own the page while they run; a sign-in attempt owns it too.
    if (not immediate and now-s.auth_checked<0.8) or (s.task and not s.task.done()) or (s.relogin and not s.relogin.done()):return
    s.auth_checked=now
    can_recover=s.recovery_attempts<recovery.MAX_ATTEMPTS and now-s.recovery_checked>=min(2**s.recovery_attempts,8)
    if not s.worker.alive() or s.status=='error':
        if can_recover:s.relogin=asyncio.create_task(recovery.restore(s,force=True))
        return
    if s.status=='login_required' and await s.worker.adopt_saved_login():
        try:
            if hasattr(s.worker,'restore_checkpoint'):await s.worker.restore_checkpoint()
        except Exception:
            s.status='error';s.last_error='Signed in, but the previous demo has not been restored yet.';return
        s.status='ready';s.auth_lost=None;s.last_error=None;s.recovery_attempts=0
        s.say('The operator has signed in. The test CRM is ready; ask me to show Leads, Projects, Tasks or another feature.')
        return
    if s.status=='login_required' and can_recover and has_login_credentials():
        s.relogin=asyncio.create_task(relogin(s));return
    auth=await s.worker.authenticated()
    if auth is None:return
    if auth:
        s.auth_lost=None
        if s.status=='login_required':
            s.status='ready'
        return
    s.auth_lost=s.auth_lost or now
    if s.status=='ready' and (immediate or now-s.auth_lost>0.8):
        s.status='login_required'
        if has_login_credentials():
            s.relogin=asyncio.create_task(relogin(s))
        else:s.say('The CRM sign-in expired, so the live screen is paused until the operator signs in again.')

@app.get('/api/health')
async def health():
    if config.PROVIDER=='deepseek':
        # Hosted conversation and qualification model; the key itself is never reported.
        return {'status':'ok','provider':'deepseek','model':config.DEEPSEEK_MODEL,'model_available':bool(config.DEEPSEEK_API_KEY),
          'qualification_available':bool(config.DEEPSEEK_API_KEY),'qualification':config.DEEPSEEK_MODEL,
          'trained_adapter_active':False,'adapter_release':None,'sandbox_confirmed':config.SANDBOX_CONFIRMED,'api_usage':USAGE,
          'screen_transport':'authenticated_jpeg_polling','demo_browser':'hidden' if config.HEADLESS else 'visible_window',
          'saved_login':config.BROWSER_STATE.is_file(),'login_credentials_in_memory':has_login_credentials(),
          'speech':config.TTS_PROVIDER,'external_llm_calls':True,'capacity':1,
          'conversation_engine':'planner-v1','conversation_model':config.DEEPSEEK_MODEL,
          'conversation_database':conversation_store.backend if conversation_store else 'not_started',
          'knowledge_ready':knowledge.ready,'knowledge_error':knowledge.error,'screen_index_ready':screens.ready}
    local_details={};planner_available=False;adapter_active=False;adapter_release=None
    async with httpx.AsyncClient(timeout=2) as client:
        if os.getenv('QUAL_SLM_URL') and os.getenv('QUAL_SLM_MODEL') and config.LOCAL_MODEL_URL!=config.PLANNER_MODEL_URL:
            try:
                r=await client.get(config.LOCAL_MODEL_URL+'/health');r.raise_for_status();local_details=r.json()
            except (httpx.HTTPError,ValueError):pass
        try:
            from .local_model import request_headers
            r=await client.get(config.PLANNER_MODEL_URL+'/v1/models',headers=request_headers());r.raise_for_status()
            planner_available=config.PLANNER_MODEL in [m['id'] for m in r.json()['data']]
            if config.PLANNER_BACKEND=='llamacpp':
                from slm.planner_runtime import active_release,verify_identity
                release=active_release()
                if release:
                    props=await client.get(config.PLANNER_MODEL_URL+'/props',headers=request_headers());props.raise_for_status()
                    adapters=await client.get(config.PLANNER_MODEL_URL+'/lora-adapters',headers=request_headers());adapters.raise_for_status()
                    verify_identity([m['id'] for m in r.json()['data']],props.json(),adapters.json(),release)
                    adapter_active=True;adapter_release=release['release_id']
                    if os.getenv('QUAL_SLM_URL','').rstrip('/')==config.PLANNER_MODEL_URL+'/v1' and os.getenv('QUAL_SLM_MODEL')==release['model_alias']:
                        local_details={'ready':True,'qualification_model':release['model_alias'],'weights_sha256':release['weights_sha256']}
        except RuntimeError:planner_available=False
        except (httpx.HTTPError,ValueError,KeyError,OSError):planner_available=False
    return {'status':'ok','provider':'local','model':config.PLANNER_MODEL,
      'model_available':planner_available,'qualification_available':bool(local_details.get('ready')),
      'trained_adapter_active':adapter_active,'adapter_release':adapter_release,
      'sandbox_confirmed':config.SANDBOX_CONFIRMED,'api_usage':USAGE,
      'screen_transport':'authenticated_jpeg_polling','demo_browser':'hidden' if config.HEADLESS else 'visible_window',
      'saved_login':config.BROWSER_STATE.is_file(),'login_credentials_in_memory':has_login_credentials(),
      'speech':config.TTS_PROVIDER,'qualification':local_details.get('qualification_model','unavailable'),
      'qualification_weights_sha256':local_details.get('weights_sha256'),'external_llm_calls':False,'capacity':1,
      'conversation_engine':'langgraph-context-v1','conversation_model':config.PLANNER_MODEL,
      'conversation_database':conversation_store.backend if conversation_store else 'not_started',
      'knowledge_ready':knowledge.ready,'knowledge_error':knowledge.error}

@app.post('/api/sessions',status_code=201)
async def create(body:Create,request:Request):
    if body.parent_origin not in config.ORIGINS:raise HTTPException(403,'Website origin is not registered')
    async with create_lock:
        for old in list(sessions.values()):
            # A closed tab or crashed page stops polling; reclaim its browser instead of blocking for 15 minutes.
            if time.monotonic()-old.seen>ABANDONED_AFTER:await close(old)
        if sessions:raise HTTPException(409,'One demo is already active. End it before starting another.')
        s=Session(voice_enabled=body.voice,client_id=request.headers.get('x-beacon-client','')[:80]);sessions[s.id]=s
        # The local model unloads after 30 idle minutes; reload it while the browser boots.
        spawn(warm_up())
        s.say(WELCOME)
        s.boot=asyncio.create_task(boot(s))
        # A prepared browser can be handed over immediately, without a starting-state poll.
        if browser_pool.ready():
            # Even a preloaded browser can stall checking CRM authentication.
            # Return ownership promptly so a lost POST cannot strand a session.
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(s.boot),timeout=0.25)
    return {**s.snapshot(),'token':s.token,'capabilities':[{'id':f['id'],'title':f['title']} for f in FEATURES.values()], 'message':s.messages[-1]['text']}

@app.get('/api/sessions/{id}')
async def state(id:str,request:Request):
    s=owned(id,request)
    if request.headers.get('x-beacon-attach')=='1':
        s.client_id=request.headers.get('x-beacon-client','')[:80]
        s.leaving_deadline=None
    # A transient page error must never end the visitor's session.
    if not s.refresh_task or s.refresh_task.done():
        async def refresh():
            with suppress(Exception):await refresh_status(s)
        s.refresh_task=asyncio.create_task(refresh())
    body=json.dumps(jsonable_encoder(s.snapshot()),ensure_ascii=False,separators=(',',':')).encode()
    return conditional(request,body,'application/json')

def conditional(request,body,media_type):
    """Polls repeat several times a second; what the widget already has is answered with 304 and no body."""
    tag='"'+hashlib.blake2b(body,digest_size=12).hexdigest()+'"'
    if request.headers.get('if-none-match')==tag:return Response(status_code=304,headers={'ETag':tag})
    return Response(body,media_type=media_type,headers={'ETag':tag})

@app.get('/api/sessions/{id}/screen')
async def screen(id:str,request:Request):
    s=owned(id,request)
    if s.status!='ready':return Response(status_code=204)
    try:
        frame=await s.worker.screenshot()
        return conditional(request,frame,'image/jpeg') if frame else Response(status_code=204)
    except Exception:return Response(status_code=204)

def conversation_context(s,message):
    messages=s.messages
    # The current turn is supplied separately; duplicating it in history can
    # make a short answer appear to answer itself instead of the last question.
    if messages and messages[-1]['role']=='user' and messages[-1]['text']==message:
        messages=messages[:-1]
    # The registration record (name, email, phone) is kept for lead scoring, not sent with every question.
    history=[{'role':m['role'],'text':m['text'][:240]} for m in messages
             if m.get('kind') not in {'ack','lead_creation','customer_registration'}][-8:]
    return dict(session_id=s.id,message=message,history=history,customer=s.discovery_answers,
        pending_question=s.pending_discovery,last_feature=s.last_feature,last_offer=s.offer,
        last_location=s.last_location)


async def execute(s,message):
    usage_token=usage.session_id.set(s.id)
    started=time.monotonic();ack=None;needs_qualification=False;demo=None
    lead_turn=bool(s.lead_draft);message_start=len(s.messages)
    try:
        # Form values/confirmation are validation, not product intent routing.
        if s.lead_draft:
            from .lead_creation import handle
            if await handle(s,message,engine.completion):return
            # The visitor asked something else mid-form and left it: this is an ordinary turn now.
            lead_turn=bool(s.lead_draft)
        if s.voice_enabled and VOICE_ACK and not s.acknowledged:
            count=len(s.messages)
            async def acknowledge():
                await asyncio.sleep(ACK_AFTER)
                if len(s.messages)==count:s.acknowledged=True;s.say(ACKS['question'],kind='ack')
            ack=asyncio.create_task(acknowledge())
        def on_decision(decision,location=None):
            # Open the requested screen while the answer is still being written,
            # so the live view changes within seconds instead of after the text.
            nonlocal demo
            d=Decision.model_validate(decision)
            if d.kind!='product' or not d.demo or d.change_request:return
            if location:
                step={'title':location['page'],'status':'running','detail':'Opening the CRM screen for this question.'};s.steps.append(step)
                demo=(step,asyncio.create_task(recovery.read_action(s,lambda:s.worker.open_location(location))))
                return
            if d.feature not in FEATURES:return
            f=FEATURES[d.feature]
            step={'title':f['title'],'status':'running','detail':'Opening the requested CRM screen.'};s.steps.append(step)
            demo=(step,asyncio.create_task(recovery.read_action(s,lambda:s.worker.open_module(f))))
        def on_draft(text):
            # Synthesise the opening of a drafted answer while it is checked against its sources.
            # Only a checked answer is said, but by then its first audio is already prepared.
            if s.voice_enabled:
                for part in speech_parts(text)[:2]:s.voice_cache.prepare(part)
        outcome=await engine.decide(on_decision=on_decision,on_draft=on_draft,**conversation_context(s,message))
        d=Decision.model_validate(outcome['decision']);s.last_decision=d.model_dump()
        if s.messages and s.messages[-1]['role']=='user' and s.messages[-1]['text']==message:
            s.messages[-1]['kind']='customer_answer' if d.kind=='customer' else 'product_question' if d.kind=='product' else 'unverified_input'
        if s.timings:s.timings[-1].update(plan_ready_ms=round((time.monotonic()-started)*1000),plan_source='langgraph_context')
        # The model decides what the visitor meant. Only when it could not read the message at all do these
        # fixed checks still honour a contact refusal or refuse a data-change command.
        unread=bool(outcome.get('error'))
        if d.kind=='decline' or (unread and declined(message)):
            s.opted_out=True;s.discovery_answers['consent']=False;s.pending_discovery=None
            s.customer_revision+=1
            needs_qualification=True
            s.say("Understood, I won't ask for your contact details or arrange a follow-up. Feel free to keep exploring.");return
        if d.change_request or (unread and write_request(message)):
            s.steps.append({'title':'Requested CRM change','status':'blocked','detail':READ_ONLY})
            s.say(READ_ONLY);return
        if d.kind in {'stop','done'}:
            # A running demo was already interrupted by this message; what remains is the visitor saying
            # they are finished. No further questions or offers until they ask something new.
            s.offer=None;s.pending_discovery=None
            if s.finished:s.say("Sure, I'm here if you need anything else.");return
            s.finished=True
            contacted=s.discovery_answers.get('consent') is True and s.discovery_answers.get('contact') and not s.opted_out
            s.say('Thanks for exploring Leadrat! '+('The team will reach out on the details you shared. ' if contacted else '')
                  +'You can close this window now, or ask me anything else whenever you like.');return
        s.finished=False
        if d.kind=='repeat':
            previous=next((m['text'] for m in reversed(s.messages) if m['role']=='assistant' and not m.get('kind')),None)
            s.say(previous or 'What would you like me to explain?');return
        if d.kind in {'clarify','chat'}:
            s.say(d.reply or 'Which feature would you like to explore?');return
        if d.kind=='customer':
            pending=s.pending_discovery
            if not d.updates and not d.skip:
                if pending:s.discovery_misses[pending]=s.discovery_misses.get(pending,0)+1
                s.say("Sorry, I didn't quite get that. Could you put it another way? Your details have not changed.")
                return
            if record_facts(s,d,pending)=='invalid_contact':
                s.say("That doesn't look like an email address or phone number. Could you share one, or just say skip?");return
            needs_qualification=bool(d.updates)
            if d.skip:s.pending_discovery=None
            if s.discovery_answers.get('consent') is True and not s.discovery_answers.get('contact'):
                s.pending_discovery='contact'
            if any(u.field=='contact' for u in d.updates):
                s.say(SAVED_CONTACT,kind='customer_ack')
                if s.pending_discovery in {'contact','consent'}:s.pending_discovery=None
            else:
                acknowledgements=[text for text in map(reaction,d.updates) if text]
                s.say(' '.join(acknowledgements) or ("No problem, let's skip that one." if d.skip else NOTED),kind='customer_ack')
            if s.pending_discovery not in {None,'contact','consent'} and s.discovery_misses.get(s.pending_discovery):
                # Already asked twice: move on instead of repeating the same question.
                s.pending_discovery=None
            if s.pending_discovery:
                # The reply answered something else; ask the open question again, once.
                s.discovery_misses[s.pending_discovery]=s.discovery_misses.get(s.pending_discovery,0)+1
                question=discovery_question(s,s.pending_discovery)
                if s.pending_discovery=='contact':question='Which email or phone number should the team use?'
                if question:s.say(question)
            else:
                discover(s)
                if not s.pending_discovery:follow_up(s)
            return
        # Product answer and action consume the very same validated decision.
        if d.updates and record_facts(s,d,s.pending_discovery)!='invalid_contact':needs_qualification=True
        s.offer=None
        answer=outcome['answer'];s.say(answer['text'],kind='product_answer')
        if d.feature=='unknown':
            location=outcome.get('location')
            if location and demo:
                # A page or section located from the CRM's own screen map.
                step,opening=demo;demo=None
                result=await opening
                step['status']='verified';step['detail']=result;s.shown.add(location['page'])
                s.last_location={k:location.get(k) for k in ('id','path','page','section')}
                s.say(result,kind='product_answer')
            elif d.demo and answer.get('demo_requested'):
                s.say("I can explain this, but I couldn't find a matching screen in this CRM to show you.",kind='product_answer')
            next_question(s);return
        f=FEATURES[d.feature];s.last_feature=d.feature;s.last_location=None
        if not d.demo:next_question(s);return
        s.worker.notify=s.say
        if not demo:on_decision(d.model_dump())
        step,opening=demo;demo=None
        result=await opening
        step['status']='verified';step['detail']=result;s.shown.add(f['module'])
        if f['workspace']:
            s.shown.add(f['id'])
            s.say(workspace_opened(f),kind='product_answer')
        else:
            step={'title':f['title']+' controls','status':'running','detail':'Checking the requested controls.'};s.steps.append(step)
            result=await recovery.read_action(s,lambda:walkthrough(s.worker,f))
            overview_only='has not been opened or executed' in result or result.startswith('Email prerequisite:')
            step['status']='overview_only' if overview_only else 'verified';step['detail']=result
            if not overview_only:s.shown.add(f['id'])
            s.say(result,kind='product_answer')
        if f['id']=='add_lead':
            lead_turn=True
            from .lead_creation import begin
            await begin(s);return
        next_question(s)
    except asyncio.CancelledError:
        for step in s.steps:
            if step['status']=='running':step['status']='stopped';step['detail']='Stopped by the visitor.'
        raise
    except DemoError as exc:
        s.last_error=str(exc);s.say(str(exc))
        for step in s.steps:
            if step['status']=='running':step['status']='failed';step['detail']=str(exc)
    except Exception as exc:
        s.last_error='I could not complete this request. Please try again.'
        s.say(s.last_error)
        print('Conversation execution failed:',type(exc).__name__,flush=True)
        for step in s.steps:
            if step['status']=='running':step['status']='failed';step['detail']=s.last_error
    finally:
        if ack and not ack.done():ack.cancel()
        if demo:
            # The answer failed or was interrupted before the early screen change was awaited.
            step,opening=demo
            if not opening.done():opening.cancel()
            opening.add_done_callback(lambda t:t.cancelled() or t.exception())
            if step['status']=='running':step['status']='stopped';step['detail']='Not completed.'
        s.last_completed=time.monotonic()
        s.last_turn_ms=round((time.monotonic()-started)*1000)
        if lead_turn:
            for m in s.messages[message_start:]:m['kind']='lead_creation'
            if message_start and s.messages[message_start-1]['role']=='user':s.messages[message_start-1]['kind']='lead_creation'
        if engine.store:
            try:
                state=conversation_context(s,message)
                state.update(decision=s.last_decision,steps=s.steps,fact_evidence=s.fact_evidence,
                    last_turn_ms=s.last_turn_ms,handoff_status=s.handoff_status,opted_out=s.opted_out)
                await engine.store.save(PROJECT['id'],s.id,state)
            except Exception as exc:print('Conversation persistence failed:',type(exc).__name__,flush=True)
        if needs_qualification:s.qual_dirty=True
        if s.qual_dirty and not lead_turn:
            if s.qual_task and not s.qual_task.done():s.qual_task.cancel()
            async def after_pause():
                # Do not start a full GPU extraction for every short reply
                # while the next interactive turn is using the CPU planner.
                # Accepted facts are already visible in the preliminary JSON.
                idle=0.6 if not s.pending_discovery else 8
                await asyncio.sleep(idle)
                while (s.task and not s.task.done()) or time.monotonic()-s.last_completed<idle:
                    await asyncio.sleep(0.2)
                await requalify(s)
                s.qual_dirty=False
            s.qual_task=asyncio.create_task(after_pause())
        usage.session_id.reset(usage_token)

@app.post('/api/sessions/{id}/turn',status_code=202)
async def turn(id:str,body:Turn,request:Request):
    s=owned(id,request,touch=True)
    if os.getenv('BEACON_REQUIRE_VISITOR_DETAILS','1')=='1' and not (s.registration_accepted or s.registration_status=='created'):
        raise HTTPException(428,'Please complete the details form before starting the conversation.')
    message=body.message.strip()
    if not message:raise HTTPException(422,'Enter a question')
    message_hash=hashlib.sha256(message.encode()).hexdigest()
    if body.request_id in s.accepted_turns:
        if s.accepted_turns[body.request_id]!=message_hash:raise HTTPException(409,detail={'code':'request_conflict','message':'Request ID was already used for a different question'})
        return {'accepted':True,'duplicate':True}
    if s.relogin and not s.relogin.done():raise HTTPException(409,detail={'code':'crm_reconnecting','message':'The CRM is reconnecting. Your question will continue after sign-in.'})
    if s.task and not s.task.done() and not body.interrupt:raise HTTPException(409,'A demonstration is running. Stop it first to change the request.')
    if time.monotonic()-s.last_turn<0.5:raise HTTPException(429,'Please wait briefly before another request')
    if s.task and not s.task.done():
        # Cancellation marks running steps as stopped; nothing half-done is claimed as verified.
        s.task.cancel()
        with suppress(asyncio.CancelledError):await s.task
    if s.qual_task and not s.qual_task.done() and s.handoff_status!='pending':
        # Lead scoring shares the single local model slot. A visitor waiting for a reply comes
        # first; the scoring is marked outstanding and runs again after this turn.
        s.qual_task.cancel();s.qual_dirty=True
    s.last_turn=time.monotonic();s.last_error=None;s.steps=[]
    s.turn_started=s.last_turn;s.timings=(s.timings+[{'turn':len(s.timings)+1}])[-200:]
    s.messages.append({'id':secrets.token_urlsafe(12),'role':'user','text':message})
    if body.request_id:
        s.accepted_turns[body.request_id]=message_hash
        if len(s.accepted_turns)>200:s.accepted_turns.pop(next(iter(s.accepted_turns)))
    s.task=asyncio.create_task(execute(s,message))
    return {'accepted':True}

@app.get('/api/sessions/{id}/timings')
async def timings(id:str,request:Request):
    s=owned(id,request)
    rows=[]
    for t in s.timings:
        row={k:v for k,v in t.items() if k not in {'first_part_hash'}}
        synth=s.voice_cache.timings.get(t.get('first_part_hash'))
        if synth is not None:row['first_tts_ms']=synth
        rows.append(row)
    return {'turns':rows}

@app.post('/api/sessions/{id}/stop')
async def stop(id:str,request:Request):
    s=owned(id,request,touch=True)
    if s.task and not s.task.done():
        s.task.cancel()
        with suppress(asyncio.CancelledError):await s.task
        s.say(STOPPED)
    return {'status':'stopped'}

STOPPED="Okay, I've stopped the walkthrough."

@app.delete('/api/sessions/{id}',status_code=204)
async def end(id:str,request:Request):
    await close(owned(id,request));return Response(status_code=204)

@app.post('/api/sessions/{id}/detach',status_code=204)
async def detach(id:str,request:Request):
    s=owned(id,request)
    # A delayed unload from the old document cannot close a refreshed document.
    if request.headers.get('x-beacon-client','')!=s.client_id:return Response(status_code=204)
    deadline=time.monotonic()+TAB_CLOSE_GRACE
    s.leaving_deadline=deadline
    async def expire_departed_tab():
        await asyncio.sleep(TAB_CLOSE_GRACE)
        if sessions.get(id) is s and s.leaving_deadline==deadline:
            await close(s)
    spawn(expire_departed_tab())
    return Response(status_code=204)

class VoicePreference(BaseModel):
    enabled:bool

@app.post('/api/sessions/{id}/voice')
async def voice_preference(id:str,body:VoicePreference,request:Request):
    s=owned(id,request);s.voice_enabled=body.enabled
    if not body.enabled:s.voice_cache.close()
    else:
        if VOICE_ACK:
            for text in ACKS.values():s.voice_cache.prepare(text)
    return {'enabled':body.enabled}

@app.get('/api/sessions/{id}/speech')
async def speech(id:str,request:Request,message_id:str|None=None,message_index:int|None=None,part:int=0,stream:bool=False):
    s=owned(id,request)
    message=next((m for m in s.messages if m.get('id')==message_id),None) if message_id else (
        s.messages[message_index] if message_index is not None and 0<=message_index<len(s.messages) else None)
    if not message or message['role']!='assistant':raise HTTPException(404,'Assistant message not found')
    parts=message.get('parts') or [message['text']]
    if not 0<=part<len(parts):raise HTTPException(404,'Speech part not found')
    try:
        if stream and config.TTS_PROVIDER=='edge':
            chunks=s.voice_cache.stream(parts[part])
            # Check first audio before sending HTTP success; later failures terminate the stream.
            first=await anext(chunks)
            async def body():
                try:
                    yield first
                    async for chunk in chunks:yield chunk
                finally:await chunks.aclose()
            return StreamingResponse(body(),media_type='audio/mpeg',headers={
                'Cache-Control':'no-store','X-Accel-Buffering':'no'})
        audio=await asyncio.shield(s.voice_cache.prepare(parts[part]))
        return Response(audio,media_type='audio/mpeg')
    except (Exception,asyncio.CancelledError):raise HTTPException(503,'Voice is temporarily unavailable. You can still read and type.')

@app.post('/api/sessions/{id}/speech-key')
async def speech_key(id:str,request:Request):
    s=owned(id,request,touch=True)
    if time.monotonic()-s.speech_key_issued<5:raise HTTPException(429,'Please wait before restarting the microphone.')
    from .soniox import temporary_key
    s.speech_key_issued=time.monotonic()
    try:return await temporary_key(s.id)
    except ValueError:raise HTTPException(503,'Soniox is not configured yet. You can still type.')
    except Exception:raise HTTPException(503,'Speech connection is unavailable. Please try again.')

from .registration import Visitor

def registration_welcome(name,queued=False):
    """Beacon's reply once the details form is accepted (not a claim that the CRM has saved them)."""
    first=(name.split() or [''])[0]
    # "ABID" or "abid" from the form reads as "Abid"; mixed case such as "McKay" is kept.
    if first.isupper() or first.islower():first=first[:1].upper()+first[1:].lower()
    thanks=f'Thanks, {first}!' if first else 'Thank you!'
    return thanks+(' Let me take you to your question now.' if queued else
                   ' What would you like to explore first? Ask me anything, or pick one of the suggestions.')

@app.post('/api/sessions/{id}/visitor',status_code=202)
async def visitor(id:str,body:Visitor,request:Request,queued:bool=False):
    s=owned(id,request,touch=True)
    async with s.registration_lock:
        if s.registration_status in {'saving','created'}:
            return {'status':s.registration_status,'accepted':s.registration_accepted or s.registration_status=='created'}
        if body.phone in s.registration_blocked_phones:
            s.registration_status='review_required'
            s.registration_error='We couldn’t confirm the registration for this number. Use a different number, or contact support for help.'
            return {'status':'review_required','accepted':s.registration_accepted}
        from .registration import register,remember_details
        # Validate the normalized phone locally; no remote API call blocks this acknowledgement.
        from .registration_api import payload,RegistrationRejected
        try:payload(body)
        except RegistrationRejected as exc:raise HTTPException(422,str(exc)) from exc
        s.registration_error=None
        s.registration_status='saving'
        s.registration_accepted=True
        remember_details(s,body)
        async def capture():
            try:await register(s,body)
            except asyncio.CancelledError:raise
            except Exception:
                s.registration_status='failed'
                s.registration_error='We couldn’t save your details. Please try again.'
        s.registration_task=asyncio.create_task(capture())
        registration_jobs.add(s.registration_task)
        s.registration_task.add_done_callback(registration_jobs.discard)
        # The visitor just finished the form: answer them instead of leaving the chat silent.
        s.say(registration_welcome(body.name,queued))
    return {'status':'saving','accepted':True}

# Discovery: short questions, one per turn, only about what is still unknown, then the contact question.
DISCOVERY=[('organisation.type','So I can tailor the demo, are you a brokerage, a developer or a channel partner?'),
    ('organisation.agents','How many people are on your sales team?'),
    ('monthly_leads','Roughly how many new leads do you get in a month?'),
    # Ask what they use before what hurts, so a tool name is never mistaken for the problem.
    ('process','What do you use to manage leads today: Excel, WhatsApp or another CRM?'),
    ('pain_points','What is the biggest problem with how you handle leads today?'),
    ('influence','Would you be the one deciding on a CRM, or evaluating it for someone else?'),
    ('next_step','When would you want a new CRM running: within the next month, or later?')]

TEXT_FACTS={'pain_points','process','influence','next_step'}
def discovery_question(s,path):
    return dict(DISCOVERY).get(path)

# Spoken reactions to the visitor's answers. Each fact gets its own natural lead-in instead of the same
# "Got it" every time; the wording is built only from validated values, never from free model prose.
NOTED="Thanks, I've noted that."
BUSINESS_TYPES={'developer':"Great, so you're a developer.",'brokerage':'Great, so you run a brokerage.',
    'channel_partner':"Nice, so you're a channel partner.",'other_real_estate':"Thanks, that's helpful.",
    'unrelated':'Thanks for letting me know.'}
LEAD_INS={'process':'Okay, so','pain_points':'I see, so','influence':'Good to know,','next_step':'Perfect, so'}

def reaction(update):
    if update.field=='organisation.type':return BUSINESS_TYPES.get(update.value,"Thanks, that's helpful.")
    if update.field=='organisation.agents':return f'Okay, a team of {count_description(update)}.'
    if update.field=='monthly_leads':return f"Thanks, that's {count_description(update)} new leads a month."
    if update.field in TEXT_FACTS:return restated(update)
    return ''

def restated(update):
    """Acknowledge a free-text answer in the model's words, whatever the visitor's spelling."""
    summary=' '.join(update.summary.split()).rstrip('.')
    if summary.casefold().startswith('you ') and len(summary)<=110:return LEAD_INS.get(update.field,'Okay, so')+' '+summary+'.'
    return NOTED

def reask(question):
    """An unanswered question raised again in passing after an answer, the way a person would."""
    question=question.removeprefix('So I can tailor the demo, ')
    return 'By the way, '+question[:1].lower()+question[1:]

def workspace_opened(feature):
    return "I've opened the "+feature['title']+' for you.'

def count_description(update):
    value=f'{update.value:,}'
    return {'exact':value,'approximate':'about '+value,'at_least':value+'+',
            'more_than':'more than '+value,'at_most':'at most '+value,'less_than':'fewer than '+value}[update.relation]

def record_facts(s,d,pending):
    """Save the facts in a validated plan. Returns 'invalid_contact' when a contact quote holds no email or phone."""
    if any(u.field=='contact' and not (re.search(EMAIL,u.evidence) or re.search(PHONE,u.evidence)) for u in d.updates):
        return 'invalid_contact'
    for u in d.updates:
        s.discovery_answers[u.field]=u.value
        s.fact_evidence[u.field]={'quote':u.evidence,'message_id':s.messages[-1]['id'] if s.messages else None}
        if u.field in {'organisation.agents','monthly_leads'}:
            s.discovery_answers[u.field+'.relation']=u.relation
            s.fact_evidence[u.field]['relation']=u.relation
        if u.field==pending:s.pending_discovery=None
        if u.field=='consent' and u.value is False:s.opted_out=True
    if pending=='consent' and any(u.field=='contact' for u in d.updates) and 'consent' not in s.discovery_answers:
        # We asked "Would you like someone to contact you? If yes, share an email or phone number";
        # sharing one in reply is that yes.
        s.discovery_answers['consent']=True
        s.fact_evidence['consent']=s.fact_evidence['contact']
    if d.updates:s.customer_revision+=1
    return None

def known(q,path):
    value=q
    for part in path.split('.'):value=value.get(part) if isinstance(value,dict) else None
    return value not in (None,'unknown',{'min':None,'max':None})

SAVED_CONTACT="Thank you, I've noted your contact details."
# What a visitor usually wants after each screen; the first one not yet shown is suggested.
NEXT_STEPS={'leads':['add_lead','status','site_visit'],'add_lead':['status','site_visit'],'status':['site_visit','meeting'],
    'site_visit':['notes','projects'],'meeting':['notes','tasks'],'projects':['properties','leads'],'properties':['matching','projects'],
    'tasks':['dashboard','leads'],'dashboard':['leads','tasks']}
DEFAULT_STEPS=['leads','add_lead','status','site_visit','projects','tasks','dashboard']

def next_question(s):
    """Every product answer ends by moving the conversation on: the open business question, else the
    next one, else a concrete next demo the visitor can accept with a plain yes."""
    pending=s.pending_discovery
    if pending:
        question=discovery_question(s,pending)
        # Raised again once, in passing. After that the answer chips stay on screen and the visitor
        # leads; repeating the same question after every answer sounds like a form, not a person.
        if question and pending not in s.reasked:
            s.reasked.add(pending);s.say(reask(question));return
        follow_up(s);return
    discover(s)
    if not s.pending_discovery:follow_up(s)

def follow_up(s):
    """Close the turn with one concrete next step the visitor can accept with a plain yes."""
    options=NEXT_STEPS.get(s.last_feature,[])+DEFAULT_STEPS
    nxt=next((o for o in options if o in FEATURES and o!=s.last_feature and o not in s.shown),None)
    if not nxt:
        s.say(NOTHING_NEXT);return
    s.offer=nxt
    s.say(offer_text(nxt))

NOTHING_NEXT='What else would you like to see?'
def offer_text(feature):
    title=FEATURES[feature]['title']
    what='how to '+title[0].lower()+title[1:] if title.split()[0] in {'Add','Change','Schedule','Reassign','Edit','Find','Export','Complete','Manage'} else 'the '+title
    return f'Would you like to see {what} next? Or ask me anything else.'

def fixed_phrases():
    """Every sentence Beacon says word for word, split the way it is spoken (see speech_parts)."""
    offered={o for steps in NEXT_STEPS.values() for o in steps}|set(DEFAULT_STEPS)
    texts=[WELCOME,NOTHING_NEXT,SAVED_CONTACT,CONTACT_QUESTION,STOPPED,
           *(question for _,question in DISCOVERY),*(reask(question) for _,question in DISCOVERY),
           *(offer_text(f) for f in sorted(offered) if f in FEATURES),
           *(workspace_opened(f) for f in FEATURES.values() if f['workspace'])]
    return [part for text in texts for part in speech_parts(text)]

def discover(s):
    if s.opted_out or s.pending_discovery:return
    q=(s.qual or {}).get('qualification') or rules_extract(transcript_of(s.messages)).model_dump()
    # Every unknown fact is needed to score the lead, so each is asked once unless the visitor already said it.
    for path,question in DISCOVERY:
        if path not in s.discovery_asked and path not in s.discovery_answers and not known(q,path):
            s.discovery_asked.append(path);s.pending_discovery=path;s.say(discovery_question(s,path));return
    # The contact question closes discovery.
    if not q.get('consent') and 'consent' not in s.discovery_asked:
        s.discovery_asked.append('consent')
        s.pending_discovery='consent'
        s.say(CONTACT_QUESTION)

CONTACT_QUESTION='Would you like someone from Leadrat to contact you? If yes, share an email or phone number.'

def accepted_qualification(s,result):
    # The trained extractor cannot overwrite the visitor's accepted corrections
    # or grant contact permission which the conversation never recorded.
    from slm.labels import Qualification,Range
    from slm.prompting import rescore
    q=Qualification.model_validate(result['qualification'])
    answers=s.discovery_answers
    org=q.organisation.model_copy(update={'type':answers.get('organisation.type','unknown'),
                                          'agents':answers.get('organisation.agents')})
    count_details={}
    for field in ('organisation.agents','monthly_leads'):
        if field in answers and answers.get(field+'.relation','exact')!='exact':
            count_details[field]={'value':answers[field],'relation':answers[field+'.relation'],
                                  'evidence':s.fact_evidence.get(field,{}).get('quote','')}
    if 'organisation.agents' in count_details:org=org.model_copy(update={'agents':None})
    changes={'organisation':org,'consent':answers.get('consent') is True and not s.opted_out}
    changes['count_details']=count_details
    count=answers.get('monthly_leads')
    relation=answers.get('monthly_leads.relation','exact')
    changes['monthly_leads']=(Range(min=count,max=count) if relation=='exact' else
        Range(min=count) if relation=='at_least' else Range(min=count+1) if relation=='more_than' and count is not None else
        Range(max=count) if relation=='at_most' else Range(max=max(0,count-1)) if relation=='less_than' and count is not None else Range())
    for key in ('process','influence','next_step'):
        if key not in answers:changes[key]='unknown'
    # Preserve the visitor's latest accepted problem, even when the extractor
    # used an earlier tool-name reply as the problem or fell back to rules.
    changes['pain_points']=[answers['pain_points']] if answers.get('pain_points') else None
    if not answers.get('contact'):
        changes['contact']=q.contact.model_copy(update={'email':None,'phone':None})
    if s.opted_out:changes['next_step']='declined'
    messages=[m for m in s.messages if m.get('kind') not in EXCLUDED_KINDS]
    turn_ids={m.get('id'):i+1 for i,m in enumerate(messages) if m['role']=='user' and m.get('id')}
    evidence=dict(q.evidence)
    profile=s.registration_profile
    if answers.get('contact') and profile and s.fact_evidence.get('contact',{}).get('message_id')==profile['message_id']:
        changes['contact']=q.contact.model_copy(update={k:profile[k] for k in ('name','email','phone')})
        tid=turn_ids.get(profile['message_id'])
        if tid:
            for key in ('name','email','phone'):evidence['contact.'+key]=[tid]
    missing_evidence=False
    for key in ('organisation.type','organisation.agents','monthly_leads','pain_points','consent'):
        if key not in answers:continue
        tid=turn_ids.get(s.fact_evidence.get(key,{}).get('message_id'))
        if tid:evidence[key]=[tid]
        else:evidence.pop(key,None);missing_evidence=True
    changes['evidence']=evidence
    q=rescore(q.model_copy(update=changes)).model_copy(update={'count_details':count_details})
    if (result['source']!='slm' or missing_evidence) and q.route!='graceful_close':q=q.model_copy(update={'route':'human_review'})
    return q.model_dump()

async def requalify(s):
    revision=s.customer_revision
    result=await qualify_session(list(s.messages))
    if s.id not in sessions or s.customer_revision!=revision:return
    result['qualification']=accepted_qualification(s,result)
    s.qual=result;q=result['qualification']
    show_handoff(s,result)
    if not s.opted_out and handoffs.eligible(q) and s.handoff_status=='not_requested':
        s.handoff_status='pending'
        s.handoff_status=await handoffs.deliver(handoffs.brief(s.id,q,s.shown))
        s.say("All done, I've shared your details with the Leadrat team. Someone will be in touch soon." if s.handoff_status=='delivered'
              else "I couldn't send your details to the team just now. Please use the contact option on the website.")
    elif q['route']=='graceful_close' and not s.closed_politely and not s.opted_out and q.get('icp_score') is not None:
        s.closed_politely=True
        s.say("Thanks for exploring Leadrat. It may not be the right fit for your business just now, but you're welcome to keep looking around.")

def show_handoff(s,result):
    """Development aid: print what the sales team would receive after each turn (BEACON_PRINT_HANDOFF=0 turns it off)."""
    if os.getenv('BEACON_PRINT_HANDOFF','0')=='0':return
    q=result['qualification']
    contact='yes' if q['contact'].get('email') or q['contact'].get('phone') else 'no'
    why=('already sent' if s.handoff_status!='not_requested' else 'visitor opted out' if s.opted_out
         else 'sending now' if handoffs.eligible(q) else f"not sent: route={q['route']}, consent={bool(q.get('consent'))}, contact={contact}")
    print(f"\n=== Sales handoff JSON (session {s.id[:8]}, extracted by {result['source']}; {why}) ===",flush=True)
    print(json.dumps(handoffs.brief(s.id,q,s.shown),indent=2,ensure_ascii=False),flush=True)

@app.post('/mock-crm/handoff')
async def mock_crm(request:Request):
    # Stand-in for a CRM webhook: records each handoff_id once.
    status,body=handoffs.receive(await request.json())
    return JSONResponse(body,status_code=status)

@app.get('/vendor/intl-tel-input/{filename:path}')
async def phone_assets(filename:str):
    if filename not in {'js/intlTelInput.min.js','js/utils.js','css/intlTelInput.css','img/flags.webp','img/flags@2x.webp'}:
        raise HTTPException(404)
    path=config.ROOT/'web/vendor/intl-tel-input'/filename
    if not path.is_file():raise HTTPException(404)
    return FileResponse(path)

@app.get('/vendor/noise-suppressor/{filename:path}')
async def noise_assets(filename:str):
    if filename not in {'index.js','rnnoise/workletProcessor.js','rnnoise.wasm','rnnoise_simd.wasm'}:raise HTTPException(404)
    path=config.ROOT/'web/vendor/noise-suppressor'/filename
    if not path.is_file():raise HTTPException(404)
    return FileResponse(path,media_type='application/wasm' if filename.endswith('.wasm') else 'text/javascript')

@app.get('/{filename}')
async def static(filename:str):
    if filename not in {'index.html','widget.html','widget.js','widget.css','widget-client.js','soniox-input.js','microphone-filter.js','visitor-phone.js','index.css','index.js'}:raise HTTPException(404)
    path=config.ROOT/'web'/filename
    if not path.is_file():raise HTTPException(404)
    return FileResponse(path)

@app.get('/')
async def root():return FileResponse(config.ROOT/'web/index.html')
