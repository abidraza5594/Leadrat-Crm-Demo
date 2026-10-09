import asyncio
import json
import os
import secrets
import re
import time
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
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
from .qualification import Facts, qualify
from .voice import VoiceCache
from .lead_browser import walkthrough
from .qualify import EMAIL, PHONE, EXCLUDED_KINDS, qualify_session, rules_extract, transcript_of
from . import handoff as handoffs
from fastapi.responses import JSONResponse
from . import docs

READ_ONLY=("I can't do that here. Only the confirmed Add Lead flow can save a new record. I do not delete, edit existing records, send, upload, export, assign or call. "
    "I can show you where it is done and how it works; for example, ask \"how do I delete a lead?\"")
# Optional filler spoken while a slow answer is prepared. Off by default: hearing the same phrase
# before every reply sounds robotic. BEACON_VOICE_ACK=1 enables it, at most once per session.
ACKS={'question':'Let me check that for you.','action':'Sure, one moment.'}
VOICE_ACK=os.getenv('BEACON_VOICE_ACK','0')=='1'
ACK_AFTER=float(os.getenv('ACK_AFTER_MS','2500'))/1000

# A widget polls several times per second; one that has been silent this long was closed or crashed.
ABANDONED_AFTER=30
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
    acknowledged:bool=False
    qual_dirty:bool=False
    # The visitor said they were finished; a repeated "nothing" gets a short reply, not the goodbye again.
    finished:bool=False
    def say(self,text,kind=None):
        # One chat bubble per reply; voice fetches its short parts separately.
        parts=speech_parts(text)
        message_id=secrets.token_urlsafe(12)
        self.messages.append({'id':message_id,'role':'assistant','text':text,'parts':parts,**({'kind':kind} if kind else {})})
        if self.timings and kind is None and 'answer_reply_ms' not in self.timings[-1]:
            self.timings[-1]['answer_reply_ms']=round((time.monotonic()-self.turn_started)*1000)
        if self.timings and 'first_reply_ms' not in self.timings[-1]:
            self.timings[-1].update(first_reply_ms=round((time.monotonic()-self.turn_started)*1000),first_message_id=message_id,first_part_hash=__import__('hashlib').sha256(parts[0][:3000].encode()).hexdigest())
        if self.voice_enabled:
            for part in parts:self.voice_cache.prepare(part)
        self.messages=self.messages[-80:]
    def qual_view(self):
        if self.qual:return {**accepted_qualification(self,self.qual),'scorer':self.qual['source'],'fallback_attempts':self.qual['attempts']}
        from slm.labels import Extraction,complete
        pending=accepted_qualification(self,{'source':'pending','qualification':complete(Extraction()).model_dump()})
        return {**pending,**qualify(Facts(),declined=self.opted_out)}
    def snapshot(self):
        problem=getattr(self.worker,'login_problem',None)
        return {'id':self.id,'status':self.status,'busy':bool(self.task and not self.task.done()),'messages':self.messages,
          'steps':self.steps,'qualification':self.qual_view(),'handoff_status':self.handoff_status,'last_error':self.last_error,'product_areas_shown':sorted(self.shown),
          'login_help':(LOGIN_HELP+(' Last attempt: '+problem if problem else '')) if self.status=='login_required' else None}

sessions:dict[str,Session]={}
create_lock=asyncio.Lock()
background:set[asyncio.Task]=set()
browser_pool=WarmBrowser()
conversation_store=None
knowledge=SemanticKnowledge(project=PROJECT['id'],directory=PROJECT['knowledge_dir'])
engine=ConversationEngine(FEATURES,[],knowledge,project=PROJECT['id'])

def spawn(coroutine):
    # asyncio keeps only weak references to tasks; hold fire-and-forget work until it finishes.
    task=asyncio.create_task(coroutine);background.add(task);task.add_done_callback(background.discard)

async def close(s):
    for task in [s.task,s.boot,s.relogin,s.qual_task,s.refresh_task]:
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):await task
    with suppress(Exception):await s.worker.close()
    s.voice_cache.close()
    s.messages.clear();s.steps.clear();sessions.pop(s.id,None)
    if not sessions:browser_pool.prime()

async def cleanup():
    while True:
        await asyncio.sleep(15)
        now=time.monotonic()
        for s in list(sessions.values()):
            if now-s.created>1800 or now-s.touched>900:await close(s)

@asynccontextmanager
async def lifespan(app):
    global conversation_store
    conversation_store=ConversationStore()
    await conversation_store.start()
    engine.store=conversation_store;knowledge.store=conversation_store
    engine.topics=sorted({c['module'] for c in docs.load(PROJECT['knowledge_dir'])})
    handoffs.prune()  # retention: drop handoff records older than HANDOFF_RETENTION_DAYS
    tasks=[asyncio.create_task(cleanup()),asyncio.create_task(warm_up())]
    async def warm_search():
        try:await knowledge.warm()
        except Exception as exc:print('Semantic knowledge preparation failed:',type(exc).__name__,flush=True)
    # Loading the search model takes ~9 s; do it at start-up, not during the first visitor question.
    if os.getenv('BEACON_WARM_KNOWLEDGE','1')=='1':tasks.append(asyncio.create_task(warm_search()))
    if config.PROVIDER=='local' and __import__('os').getenv('BEACON_START_LOCAL_MODEL')=='1':
        async def start_model():
            from slm.local_runtime import ensure_local_model
            try:await asyncio.to_thread(ensure_local_model)
            except Exception as exc:print('Local model startup failed:',str(exc),flush=True)
        tasks.append(asyncio.create_task(start_model()))
    if config.PLANNER_BACKEND=='llamacpp' and os.getenv('BEACON_START_LOCAL_MODEL')=='1':
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
    await conversation_store.close();conversation_store=None;engine.store=None;knowledge.store=None

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
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors "+' '.join(sorted(config.ORIGINS))+';'
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
        if await s.worker.signed_in():
            s.status='ready';s.say('The test CRM is ready. Ask me to show Leads, Projects, Tasks or another available feature.')
        else:
            s.status='login_required'
            s.say('The demo browser is not signed in to the test CRM yet. You can still ask about the supported features, and the live screen will appear here once the operator signs in.')
    except asyncio.CancelledError:raise
    except Exception:
        s.status='error';s.last_error='The demo browser could not start or reach the CRM. Check that Google Chrome is installed and CRM_URL is reachable, then end this session and retry.'

async def relogin(s):
    if await s.worker.login():
        s.status='ready';s.auth_lost=None
        s.say('I signed the demo browser in again. The live screen is back.')

async def refresh_status(s):
    """Debounced sign-in state: a navigation or a transient read error must not blank the screen."""
    if s.status not in {'login_required','ready'}:return
    if not s.worker.alive():
        s.status='error';s.last_error='The demo browser has closed. End this session and start again.';return
    now=time.monotonic()
    # Actions own the page while they run; a sign-in attempt owns it too.
    if now-s.auth_checked<0.8 or (s.task and not s.task.done()) or (s.relogin and not s.relogin.done()):return
    s.auth_checked=now
    if s.status=='login_required' and await s.worker.adopt_saved_login():
        s.status='ready';s.auth_lost=None
        s.say('The operator has signed in. The test CRM is ready; ask me to show Leads, Projects, Tasks or another feature.')
        return
    auth=await s.worker.authenticated()
    if auth is None:return
    if auth:
        s.auth_lost=None
        if s.status=='login_required':
            s.status='ready';s.say('The test CRM is ready. Ask me to show Leads, Projects, Tasks or another available feature.')
        return
    s.auth_lost=s.auth_lost or now
    if s.status=='ready' and now-s.auth_lost>4:
        s.status='login_required'
        if has_login_credentials():
            s.say('The CRM sign-in expired. I am signing the demo browser in again.')
            s.relogin=asyncio.create_task(relogin(s))
        else:s.say('The CRM sign-in expired, so the live screen is paused until the operator signs in again.')

@app.get('/api/health')
async def health():
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
async def create(body:Create):
    if body.parent_origin not in config.ORIGINS:raise HTTPException(403,'Website origin is not registered')
    async with create_lock:
        for old in list(sessions.values()):
            # A closed tab or crashed page stops polling; reclaim its browser instead of blocking for 15 minutes.
            if time.monotonic()-old.seen>ABANDONED_AFTER:await close(old)
        if sessions:raise HTTPException(409,'One demo is already active. End it before starting another.')
        s=Session(voice_enabled=body.voice);sessions[s.id]=s
        # The local model unloads after 30 idle minutes; reload it while the browser boots.
        spawn(warm_up())
        s.say('Welcome to Beacon. I can explain the verified feature catalogue and demonstrate supported screens in the test CRM.')
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
    # A transient page error must never end the visitor's session.
    if not s.refresh_task or s.refresh_task.done():
        async def refresh():
            with suppress(Exception):await refresh_status(s)
        s.refresh_task=asyncio.create_task(refresh())
    return s.snapshot()

@app.get('/api/sessions/{id}/screen')
async def screen(id:str,request:Request):
    s=owned(id,request)
    if s.status!='ready':return Response(status_code=204)
    try:
        frame=await s.worker.screenshot()
        return Response(frame,media_type='image/jpeg') if frame else Response(status_code=204)
    except Exception:return Response(status_code=204)

def conversation_context(s,message):
    messages=s.messages
    # The current turn is supplied separately; duplicating it in history can
    # make a short answer appear to answer itself instead of the last question.
    if messages and messages[-1]['role']=='user' and messages[-1]['text']==message:
        messages=messages[:-1]
    history=[{'role':m['role'],'text':m['text'][:240]} for m in messages
             if m.get('kind') not in {'ack','lead_creation'}][-8:]
    return dict(session_id=s.id,message=message,history=history,customer=s.discovery_answers,
        pending_question=s.pending_discovery,last_feature=s.last_feature,last_offer=s.offer)


async def execute(s,message):
    started=time.monotonic();ack=None;needs_qualification=False;demo=None
    lead_turn=bool(s.lead_draft);message_start=len(s.messages)
    try:
        # Form values/confirmation are validation, not product intent routing.
        if s.lead_draft:
            from .lead_creation import handle
            if await handle(s,message):return
        if declined(message):
            s.opted_out=True;s.discovery_answers['consent']=False;s.pending_discovery=None
            s.customer_revision+=1
            needs_qualification=True
            s.say('Understood. I will not request contact details or send a follow-up. You can continue exploring the product.')
            return
        if write_request(message):
            s.steps.append({'title':'Requested CRM change','status':'blocked','detail':READ_ONLY})
            s.say(READ_ONLY);return
        if s.voice_enabled and VOICE_ACK and not s.acknowledged:
            count=len(s.messages)
            async def acknowledge():
                await asyncio.sleep(ACK_AFTER)
                if len(s.messages)==count:s.acknowledged=True;s.say(ACKS['question'],kind='ack')
            ack=asyncio.create_task(acknowledge())
        def on_decision(decision):
            # Open the requested screen while the answer is still being written,
            # so the live view changes within seconds instead of after the text.
            nonlocal demo
            d=Decision.model_validate(decision)
            if d.kind!='product' or not d.demo or d.feature not in FEATURES:return
            f=FEATURES[d.feature]
            step={'title':f['title'],'status':'running','detail':'Opening the requested CRM screen.'};s.steps.append(step)
            demo=(step,asyncio.create_task(s.worker.open_module(f)))
        outcome=await engine.decide(on_decision=on_decision,**conversation_context(s,message))
        d=Decision.model_validate(outcome['decision']);s.last_decision=d.model_dump()
        if s.messages and s.messages[-1]['role']=='user' and s.messages[-1]['text']==message:
            s.messages[-1]['kind']='customer_answer' if d.kind=='customer' else 'product_question' if d.kind=='product' else 'unverified_input'
        if s.timings:s.timings[-1].update(plan_ready_ms=round((time.monotonic()-started)*1000),plan_source='langgraph_context')
        if d.kind=='decline':
            s.opted_out=True;s.discovery_answers['consent']=False;s.pending_discovery=None
            s.customer_revision+=1
            needs_qualification=True
            s.say('Understood. I will not request contact details or arrange a follow-up.');return
        if d.kind in {'stop','done'}:
            # A running demo was already interrupted by this message; what remains is the visitor saying
            # they are finished. No further questions or offers until they ask something new.
            s.offer=None;s.pending_discovery=None
            if s.finished:s.say('Sure. I am here if you need anything else.');return
            s.finished=True
            contacted=s.discovery_answers.get('consent') is True and s.discovery_answers.get('contact') and not s.opted_out
            s.say('Thank you for exploring Leadrat. '+('The team will contact you on the details you shared. ' if contacted else '')
                  +'You can close this window now, or ask me anything else whenever you like.');return
        s.finished=False
        if d.kind=='repeat':
            previous=next((m['text'] for m in reversed(s.messages) if m['role']=='assistant' and not m.get('kind')),None)
            s.say(previous or 'What would you like me to explain?');return
        if d.kind in {'clarify','chat'}:
            s.say(d.reply or 'Which feature would you like to explore?');return
        if d.kind=='customer':
            pending=s.pending_discovery
            d.updates=answer_pending(s,pending,message,d)
            if not d.updates and not d.skip:
                if pending:s.discovery_misses[pending]=s.discovery_misses.get(pending,0)+1
                s.say('Could you clarify that answer? I have not changed your details.')
                return
            for u in d.updates:
                if u.field=='contact' and not (re.search(EMAIL,u.evidence) or re.search(PHONE,u.evidence)):
                    s.say('Please share a valid email address or phone number, or say skip.');return
                s.discovery_answers[u.field]=u.value
                s.fact_evidence[u.field]={'quote':u.evidence,'message_id':s.messages[-1]['id'] if s.messages else None}
                if u.field==pending:s.pending_discovery=None
                if u.field=='consent' and u.value is False:s.opted_out=True
            if pending=='consent' and any(u.field=='contact' for u in d.updates) and 'consent' not in s.discovery_answers:
                # We asked "Would you like someone to contact you? If yes, share an email or phone number";
                # sharing one in reply is that yes.
                s.discovery_answers['consent']=True
                s.fact_evidence['consent']=s.fact_evidence['contact']
            needs_qualification=bool(d.updates)
            if d.updates:s.customer_revision+=1
            if d.skip:s.pending_discovery=None
            if s.discovery_answers.get('consent') is True and not s.discovery_answers.get('contact'):
                s.pending_discovery='contact'
            if any(u.field=='contact' for u in d.updates):
                s.say(SAVED_CONTACT,kind='customer_ack')
                if s.pending_discovery in {'contact','consent'}:s.pending_discovery=None
            else:
                acknowledgements=[]
                for u in d.updates:
                    if u.field=='organisation.type':acknowledgements.append('Got it — '+str(u.value)+'.')
                    elif u.field=='organisation.agents':acknowledgements.append(f'Got it — {u.value:,} people on your sales team.')
                    elif u.field=='monthly_leads':acknowledgements.append(f'Got it — approximately {u.value:,} new leads per month.')
                    elif u.field in TEXT_FACTS:acknowledgements.append(restated(u))
                s.say(' '.join(acknowledgements) or ('No problem, we can skip that.' if d.skip else 'Thanks, I have noted that.'),kind='customer_ack')
            if s.pending_discovery not in {None,'contact','consent'} and s.discovery_misses.get(s.pending_discovery):
                # Already asked twice: move on instead of repeating the same question.
                s.pending_discovery=None
            if s.pending_discovery:
                # The reply answered something else; ask the open question again, once.
                s.discovery_misses[s.pending_discovery]=s.discovery_misses.get(s.pending_discovery,0)+1
                question=discovery_question(s,s.pending_discovery)
                if s.pending_discovery=='contact':question='Please share the email or phone number the team should use.'
                if question:s.say(question)
            else:
                discover(s)
                if not s.pending_discovery:follow_up(s)
            return
        # Product answer and action consume the very same validated decision.
        s.offer=None
        answer=outcome['answer'];s.say(answer['text'],kind='product_answer')
        if d.feature=='unknown':
            # Routing missed (for example an unusual spelling), yet the answer is grounded in one module:
            # show that module's screen instead of leaving the live view where it was.
            grounded=workspace_for(answer) if d.demo and answer.get('grounded') else None
            if not grounded:
                if d.demo and answer.get('demo_requested'):s.say('I can explain this, but its screen walkthrough is not available here.',kind='product_answer')
                next_question(s);return
            d=d.model_copy(update={'feature':grounded,'topic':FEATURES[grounded]['knowledge_topics'][0]});s.last_decision=d.model_dump()
        f=FEATURES[d.feature];s.last_feature=d.feature
        if not d.demo:next_question(s);return
        s.worker.notify=s.say
        if not demo:on_decision(d.model_dump())
        step,opening=demo;demo=None
        result=await opening
        step['status']='verified';step['detail']=result;s.shown.add(f['module'])
        if f['workspace']:
            s.shown.add(f['id'])
            s.say('The '+f['title']+' is open.',kind='product_answer')
        else:
            step={'title':f['title']+' controls','status':'running','detail':'Checking the requested controls.'};s.steps.append(step)
            result=await walkthrough(s.worker,f)
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

@app.post('/api/sessions/{id}/turn',status_code=202)
async def turn(id:str,body:Turn,request:Request):
    s=owned(id,request,touch=True)
    message=body.message.strip()
    if not message:raise HTTPException(422,'Enter a question')
    message_hash=__import__('hashlib').sha256(message.encode()).hexdigest()
    if body.request_id in s.accepted_turns:
        if s.accepted_turns[body.request_id]!=message_hash:raise HTTPException(409,'Request ID was already used for a different question')
        return {'accepted':True,'duplicate':True}
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
        s.say('The demonstration has stopped.')
    return {'status':'stopped'}

@app.delete('/api/sessions/{id}',status_code=204)
async def end(id:str,request:Request):
    await close(owned(id,request));return Response(status_code=204)

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
async def speech(id:str,request:Request,message_id:str|None=None,message_index:int|None=None,part:int=0):
    s=owned(id,request)
    message=next((m for m in s.messages if m.get('id')==message_id),None) if message_id else (
        s.messages[message_index] if message_index is not None and 0<=message_index<len(s.messages) else None)
    if not message or message['role']!='assistant':raise HTTPException(404,'Assistant message not found')
    parts=message.get('parts') or [message['text']]
    if not 0<=part<len(parts):raise HTTPException(404,'Speech part not found')
    try:
        audio=await asyncio.shield(s.voice_cache.prepare(parts[part]))
        return Response(audio,media_type='audio/mpeg')
    except (Exception,asyncio.CancelledError):raise HTTPException(503,'Voice is unavailable. Use browser voice.')

# Discovery: short questions, one per turn, only about what is still unknown, then the contact question.
DISCOVERY=[('organisation.type','To tailor the demo: are you a brokerage, a developer or a channel partner?'),
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

def restated(update):
    """Acknowledge a free-text answer in the model's words, whatever the visitor's spelling."""
    summary=' '.join(update.summary.split()).rstrip('.')
    if summary.casefold().startswith('you ') and len(summary)<=110:return 'Got it — '+summary+'.'
    return 'Got it, I have noted that.'

def answer_pending(s,pending,message,d):
    """A reply to our open text question is kept as its answer instead of being re-asked in a loop.

    The first reply that does not answer the open question is handled normally and the question
    is asked once more; the next reply is taken as the visitor's answer to it."""
    updates=list(d.updates)
    if pending in TEXT_FACTS and not any(u.field==pending for u in updates):
        # A text answer for a question we have not asked yet cannot be a correction: it answers this one.
        updates=[u.model_copy(update={'field':pending}) if u.field in TEXT_FACTS and u.field not in s.discovery_asked else u for u in updates]
    if pending not in TEXT_FACTS or d.skip or any(u.field==pending for u in updates):return updates
    # The model judged this message to be the visitor's answer; with nothing extracted, their own
    # words answer the open question. A reply about another subject is applied, and the open
    # question asked once more before the next reply is taken as its answer.
    if updates and not s.discovery_misses.get(pending):return updates
    from .conversation_engine import TextUpdate
    text=message.strip()[:500]
    return [u for u in updates if u.field not in TEXT_FACTS]+[TextUpdate(field=pending,value=text,evidence=text)]

def known(q,path):
    value=q
    for part in path.split('.'):value=value.get(part) if isinstance(value,dict) else None
    return value not in (None,'unknown',{'min':None,'max':None})

SAVED_CONTACT='Thank you, I have noted your contact details.'
# What a visitor usually wants after each screen; the first one not yet shown is suggested.
NEXT_STEPS={'leads':['add_lead','status','site_visit'],'add_lead':['status','site_visit'],'status':['site_visit','meeting'],
    'site_visit':['notes','projects'],'meeting':['notes','tasks'],'projects':['properties','leads'],'properties':['matching','projects'],
    'tasks':['dashboard','leads'],'dashboard':['leads','tasks']}
DEFAULT_STEPS=['leads','add_lead','status','site_visit','projects','tasks','dashboard']

NOT_MODULES={None,'unknown','Handbook scope','Handbook guidance','Handbook overview'}

def workspace_for(answer):
    """The screen of the single handbook module an answer's evidence comes from, if it has one."""
    modules={source.get('module') for source in answer.get('sources',[])}-NOT_MODULES
    if len(modules)!=1:return None
    topic=modules.pop()
    return next((key for key,f in FEATURES.items() if f['workspace'] and f['knowledge_topics'][0]==topic),None)

def next_question(s):
    """Every product answer ends by moving the conversation on: the open business question, else the
    next one, else a concrete next demo the visitor can accept with a plain yes."""
    if s.pending_discovery:
        question=discovery_question(s,s.pending_discovery)
        if question:s.say('And to continue: '+question)
    else:discover(s)
    if not s.pending_discovery:follow_up(s)

def follow_up(s):
    """Close the turn with one concrete next step the visitor can accept with a plain yes."""
    options=NEXT_STEPS.get(s.last_feature,[])+DEFAULT_STEPS
    nxt=next((o for o in options if o in FEATURES and o!=s.last_feature and o not in s.shown),None)
    if not nxt:
        s.say('What else would you like to see?');return
    title=FEATURES[nxt]['title']
    what='how to '+title[0].lower()+title[1:] if title.split()[0] in {'Add','Change','Schedule','Reassign','Edit','Find','Export','Complete','Manage'} else 'the '+title
    s.offer=nxt
    s.say(f'Shall I show you {what} next? Or ask me about anything else.')

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
        s.say('Would you like someone from Leadrat to contact you? If yes, share an email or phone number.')

def accepted_qualification(s,result):
    # The trained extractor cannot overwrite the visitor's accepted corrections
    # or grant contact permission which the conversation never recorded.
    from slm.labels import Qualification,Range
    from slm.prompting import rescore
    q=Qualification.model_validate(result['qualification'])
    answers=s.discovery_answers
    org=q.organisation.model_copy(update={'type':answers.get('organisation.type','unknown'),
                                          'agents':answers.get('organisation.agents')})
    changes={'organisation':org,'consent':answers.get('consent') is True and not s.opted_out}
    count=answers.get('monthly_leads')
    changes['monthly_leads']=Range(min=count,max=count)
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
    missing_evidence=False
    for key in ('organisation.type','organisation.agents','monthly_leads','pain_points','consent'):
        if key not in answers:continue
        tid=turn_ids.get(s.fact_evidence.get(key,{}).get('message_id'))
        if tid:evidence[key]=[tid]
        else:evidence.pop(key,None);missing_evidence=True
    changes['evidence']=evidence
    q=rescore(q.model_copy(update=changes))
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
        s.say('Thank you. I have shared your details with the Leadrat team, and someone will contact you soon.' if s.handoff_status=='delivered'
              else 'I could not send your details to the team just now. Please use the contact option on the website.')
    elif q['route']=='graceful_close' and not s.closed_politely and not s.opted_out and q.get('icp_score') is not None:
        s.closed_politely=True
        s.say('Thank you for exploring Leadrat. It may not be the best fit for your business right now, but you are welcome to keep looking around.')

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

@app.get('/{filename}')
async def static(filename:str):
    if filename not in {'index.html','widget.html','widget.js','widget.css','widget-client.js','index.css','index.js'}:raise HTTPException(404)
    path=config.ROOT/'web'/filename
    if not path.is_file():raise HTTPException(404)
    return FileResponse(path)

@app.get('/')
async def root():return FileResponse(config.ROOT/'web/index.html')
