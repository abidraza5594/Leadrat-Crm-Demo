import asyncio
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
from .planner import FEATURES, plan, declined, small_talk, warm_up, write_request, USAGE
from .qualification import Facts, qualify
from .voice import VoiceCache
from .lead_browser import walkthrough
from .qualify import qualify_session, rules_extract, transcript_of
from . import handoff as handoffs
from fastapi.responses import JSONResponse
from . import docs

READ_ONLY=("I can't do that here. This demo is read-only: I never delete, edit, save, send, upload, export, assign or call anything. "
    "I can show you where it is done and how it works; for example, ask \"how do I delete a lead?\"")
# Spoken the moment a turn starts so the visitor hears Beacon within a second while the answer is prepared.
# Voice only (no chat bubble); synthesised once per session in advance. Reported separately in eval/latency.py.
ACKS={'question':'Let me check that for you.','action':'Sure, one moment.'}
ACK_AFTER=float(__import__('os').getenv('ACK_AFTER_MS','700'))/1000
QUESTION=re.compile(r"\b(how|why|what|where|when|which|who|can i|could i|does|do i|is it|are there|kya|kaise|kyu|kyun|kaha|kahan|batao|bataiye|explain)\b|\?\s*$",re.I)

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
    status:str='starting'
    messages:list=field(default_factory=list)
    steps:list=field(default_factory=list)
    last_error:str|None=None
    last_feature:str|None=None
    opted_out:bool=False
    shown:set=field(default_factory=set)
    worker:BrowserWorker=field(default_factory=BrowserWorker)
    task:asyncio.Task|None=None
    boot:asyncio.Task|None=None
    relogin:asyncio.Task|None=None
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
        if self.qual:return {**self.qual['qualification'],'scorer':self.qual['source'],'fallback_attempts':self.qual['attempts']}
        return qualify(Facts(),declined=self.opted_out)
    def snapshot(self):
        problem=getattr(self.worker,'login_problem',None)
        return {'id':self.id,'status':self.status,'busy':bool(self.task and not self.task.done()),'messages':self.messages,
          'steps':self.steps,'qualification':self.qual_view(),'handoff_status':self.handoff_status,'last_error':self.last_error,'product_areas_shown':sorted(self.shown),
          'login_help':(LOGIN_HELP+(' Last attempt: '+problem if problem else '')) if self.status=='login_required' else None}

sessions:dict[str,Session]={}
create_lock=asyncio.Lock()
background:set[asyncio.Task]=set()

def spawn(coroutine):
    # asyncio keeps only weak references to tasks; hold fire-and-forget work until it finishes.
    task=asyncio.create_task(coroutine);background.add(task);task.add_done_callback(background.discard)

async def close(s):
    for task in [s.task,s.boot,s.relogin,s.qual_task]:
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):await task
    with suppress(Exception):await s.worker.close()
    s.voice_cache.close()
    s.messages.clear();s.steps.clear();sessions.pop(s.id,None)

async def cleanup():
    while True:
        await asyncio.sleep(15)
        now=time.monotonic()
        for s in list(sessions.values()):
            if now-s.created>1800 or now-s.touched>900:await close(s)

@asynccontextmanager
async def lifespan(app):
    handoffs.prune()  # retention: drop handoff records older than HANDOFF_RETENTION_DAYS
    tasks=[asyncio.create_task(cleanup()),asyncio.create_task(warm_up())]
    # Sign-in needs the device location; read it before the first visitor waits for it.
    if config.LOCAL_DEVICE_LOCATION and has_login_credentials():tasks.append(asyncio.create_task(device_location()))
    yield
    for task in tasks:task.cancel()
    for task in tasks:
        with suppress(BaseException):await task
    for s in list(sessions.values()):await close(s)

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
        await s.worker.start()
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
    model_available=False
    local_details={}
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            data=(await client.get(config.OLLAMA_URL+'/api/tags')).json()
            model_available=config.MODEL in [m['name'] for m in data.get('models',[])]
    except Exception:pass
    if config.PROVIDER=='openai':
        import os
        model_available=bool(os.getenv('OPENAI_API_KEY'))
    if config.PROVIDER=='local':
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response=await client.get(config.LOCAL_MODEL_URL+'/health');response.raise_for_status()
                local_details=response.json();model_available=bool(local_details.get('ready'))
        except Exception:model_available=False
    return {'status':'ok','provider':config.PROVIDER,'model':config.LOCAL_CHAT_MODEL if config.PROVIDER=='local' else config.OPENAI_MODEL if config.PROVIDER=='openai' else config.MODEL,'model_available':model_available,'sandbox_confirmed':config.SANDBOX_CONFIRMED,
      'reasoning_effort':'low' if config.PROVIDER=='openai' else None,'api_usage':USAGE,
      'screen_transport':'authenticated_jpeg_polling','demo_browser':'hidden' if config.HEADLESS else 'visible_window',
      'saved_login':config.BROWSER_STATE.is_file(),'login_credentials_in_memory':has_login_credentials(),
      'speech':config.TTS_PROVIDER,'qualification':local_details.get('qualification_model','configured_fallback_ladder'),
      'qualification_weights_sha256':local_details.get('weights_sha256'),'external_llm_calls':config.PROVIDER=='openai','capacity':1}

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
    return {**s.snapshot(),'token':s.token,'capabilities':[{'id':f['id'],'title':f['title']} for f in FEATURES.values()], 'message':s.messages[-1]['text']}

@app.get('/api/sessions/{id}')
async def state(id:str,request:Request):
    s=owned(id,request)
    # A transient page error must never end the visitor's session.
    with suppress(Exception):await refresh_status(s)
    return s.snapshot()

@app.get('/api/sessions/{id}/screen')
async def screen(id:str,request:Request):
    s=owned(id,request)
    if s.status!='ready':return Response(status_code=204)
    try:
        frame=await s.worker.screenshot()
        return Response(frame,media_type='image/jpeg') if frame else Response(status_code=204)
    except Exception:return Response(status_code=204)

async def execute(s,message):
    started=time.monotonic();answered=False;handbook=None;ack=None
    try:
        if declined(message):
            s.opted_out=True
            s.say('Understood. I will not request contact details or send a follow-up or handoff. Thank you for exploring Leadrat.')
            return
        if write_request(message):
            # Enforced before planning: no model output or browser action can turn this into a write.
            s.steps.append({'title':'Requested CRM change','status':'blocked','detail':'Read-only demo: delete, edit, save, send, upload, export, assign and call are not permitted.'})
            s.say(READ_ONLY)
            return
        if message.strip().lower().rstrip('.!') in {'repeat','repeat that','say that again','dobara batao'}:
            previous=next((m['text'] for m in reversed(s.messages) if m['role']=='assistant' and not m.get('kind')),None)
            s.say(previous or 'Please name the feature you would like me to explain.')
            return
        if accept_discovery_reply(s,message):
            discover(s)
            return
        from .conversation_numbers import count_reply
        if count_reply(message) is not None or re.fullmatch(r'(?:yes|yeah|yep|no|nope|haan|han|nahi|nahin)',message.strip(),re.I):
            s.say('Please tell me what you mean, or name the feature you would like to see. I will keep the current screen open.')
            return
        # An unrelated product request supersedes a pending discovery question.
        # A later bare number must not silently answer an old question.
        s.pending_discovery=None
        reply=small_talk(message)
        if reply:
            s.say(reply)
            return
        if s.voice_enabled:
            # Only when the answer is slow: an acknowledgement ahead of a ready answer would delay it.
            turn_messages=len(s.messages)
            async def acknowledge():
                await asyncio.sleep(ACK_AFTER)
                if len(s.messages)==turn_messages:s.say(ACKS['question' if QUESTION.search(message) else 'action'],kind='ack')
            ack=asyncio.create_task(acknowledge())
        # The handbook answer does not depend on the plan: start it now so the two model calls overlap.
        handbook=asyncio.create_task(docs.answer(message)) if QUESTION.search(message) else None
        selected,source=await plan(message,s.last_feature)
        if s.timings:s.timings[-1].update(plan_ms=round((time.monotonic()-s.turn_started)*1000),plan_source=source)
        if selected.feature=='unknown':
            # Not a screen Beacon can show: answer from the company handbook, or say it does not know.
            s.say((await (handbook or docs.answer(message)))['text'])
            s.say('This specific screen walkthrough is not available in the current demo. The live view remains on the previous screen.')
            return
        f=FEATURES[selected.feature];s.last_feature=f['id']
        s.worker.notify=s.say
        # Questions get an answer from the handbook when it has one; the reviewed catalogue text is the fallback.
        grounded=await handbook if handbook else await docs.answer(message) if not selected.demo else None
        answered=bool(grounded and grounded['grounded'])
        if not selected.demo:
            s.say(grounded['text'] if grounded and grounded['grounded'] else ' '.join(f['facts']));return
        step={'title':f['title'],'status':'running','detail':'Checking the visible CRM navigation.'}
        s.steps.append(step)
        # Answer the question from the handbook first; the screen then shows where it happens.
        s.say(grounded['text'] if answered else f['facts'][0])
        result=await s.worker.open_module(f)
        step['status']='verified';step['detail']=result
        s.shown.add(f['module'])
        if f['id'] in {'leads','projects','tasks','properties','dashboard'}:
            s.say('The '+f['title']+' is open. This shows the workspace; the complete procedure described in the answer has not been demonstrated.')
        if f['id'] not in {'leads','projects','tasks','properties','dashboard'}:
            step={'title':f['title']+' controls','status':'running','detail':'Checking the requested controls.'}
            s.steps.append(step)
            result=await walkthrough(s.worker,f)
            overview_only='has not been opened or executed' in result or result.startswith('Email prerequisite:')
            step['status']='overview_only' if overview_only else 'verified';step['detail']=result
            if not overview_only:s.shown.add(f['id'])
            s.say(result)
        if not answered:s.say(f['facts'][1])
        discover(s)
    except asyncio.CancelledError:
        for step in s.steps:
            if step['status']=='running':step['status']='stopped';step['detail']='Stopped by the visitor.'
        raise
    except DemoError as exc:
        s.last_error=str(exc);s.say(str(exc))
        # A handbook answer already covers the procedure when the screen cannot be shown.
        if s.last_feature in FEATURES and not answered:s.say('Here is the procedure: '+FEATURES[s.last_feature]['facts'][1])
        for step in s.steps:
            if step['status']=='running':step['status']='failed';step['detail']=str(exc)
    except (httpx.HTTPError,ValueError,KeyError):
        s.last_error='The planner did not return a valid plan within its time limit or the provider rejected the request. No model-generated action was run.'
        s.say('I could not interpret that request right now. Try a shorter question such as “Show leads” or “How to change lead status”.')
    except Exception:
        s.last_error='The expected CRM control or screen could not be verified. The action stopped; no alternate control was clicked.'
        s.say(s.last_error)
        for step in s.steps:
            if step['status']=='running':step['status']='failed';step['detail']=s.last_error
    finally:
        if handbook and not handbook.done():handbook.cancel()
        if ack and not ack.done():ack.cancel()
        # Only aggregate timing; no transcript or records written to logs.
        s.last_turn_ms=round((time.monotonic()-started)*1000)
        # Exact handbook questions contain no new customer facts. Preserve any
        # ongoing extraction instead of queueing another expensive GPU request.
        from .handbook_faq import lookup
        if not lookup(message):
            if s.qual_task and not s.qual_task.done():s.qual_task.cancel()
            s.qual_task=asyncio.create_task(requalify(s))

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

# Discovery: 2–4 short questions, one per turn, only about what is still unknown.
DISCOVERY=[('organisation.type','To tailor the demo: are you a brokerage, a developer or a channel partner?'),
    ('organisation.agents','How many people are on your sales team?'),
    ('monthly_leads','Roughly how many new leads do you get in a month?'),
    ('pain_points','What is the biggest problem with how you handle leads today?'),
    ('process','What do you use to manage leads today: Excel, WhatsApp or another CRM?'),
    ('influence','Would you be the one deciding on a CRM, or evaluating it for someone else?')]

def known(q,path):
    value=q
    for part in path.split('.'):value=value.get(part) if isinstance(value,dict) else None
    return value not in (None,'unknown',{'min':None,'max':None})

def discover(s):
    if s.opted_out or s.pending_discovery or len(s.discovery_asked)>=4:return
    q=(s.qual or {}).get('qualification') or rules_extract(transcript_of(s.messages)).model_dump()
    for path,question in DISCOVERY:
        if path not in s.discovery_asked and path not in s.discovery_answers and not known(q,path):
            s.discovery_asked.append(path);s.pending_discovery=path;s.say(question);return
    if not q.get('consent') and 'consent' not in s.discovery_asked and len(s.discovery_asked)<4:
        s.discovery_asked.append('consent')
        s.pending_discovery='consent'
        s.say('Would you like someone from Leadrat to contact you? If yes, share an email or phone number.')

def accept_discovery_reply(s,message):
    """Consume a reply to our own question before any product navigation.

    Keep the original transcript for customer extraction. These local values only
    guide the conversation; they are not a substitute for sales qualification.
    """
    pending=s.pending_discovery
    if QUESTION.search(message):return False
    text=message.strip().lower().rstrip('.!')
    from .conversation_numbers import count_reply
    correction=re.fullmatch(r'(?:actually|correction|sorry|actually we have)[, ]+(.+?)\s+(agents|people|team members|leads per month|monthly leads)',text)
    if correction:
        count=count_reply(correction[1])
        if count is not None:
            path='monthly_leads' if 'leads' in correction[2] else 'organisation.agents'
            s.discovery_answers[path]=count
            s.say(f'Thanks for correcting that: {count:,} '+('new leads per month.' if path=='monthly_leads' else 'people on your sales team.'))
            if pending==path:s.pending_discovery=None
            elif pending in dict(DISCOVERY):s.say(dict(DISCOVERY)[pending])
            return True
    if not pending:return False
    # Skips and uncertainty answer the discovery turn, not the feature planner.
    if text in {'skip','skip this','not sure','dont know',"don't know",'pata nahi','later','prefer not to say'}:
        s.pending_discovery=None
        s.say('No problem, we can leave that detail unknown. The current demo stays open.')
        return True
    # An acknowledgement is not an answer to a count or business-type question.
    if pending!='consent' and text in {'yes','yeah','yep','no','nope','haan','han','nahi','nahin','ok','okay'}:
        question=dict(DISCOVERY).get(pending,'Could you share a little more detail?')
        s.say(question+' You can also say skip.')
        return True
    value=None;reply=None
    if pending=='organisation.type':
        match=re.fullmatch(r"(?:(?:i am|i'm|we are|we're|main|hum) (?:(?:a|an) )?)?(channel partners?|brokerage|brokers?|developers?|builders?)(?: (?:hu|hoon|hai|hain))?",text)
        if match:value=match[1];reply=f'Thanks — you are a {value}.'
    elif pending in {'organisation.agents','monthly_leads'}:
        from .conversation_numbers import count_reply
        value=count_reply(text)
        if value is not None:
            reply=(f'Got it — {value:,} people on your sales team.' if pending=='organisation.agents' else f'Got it — approximately {value:,} new leads per month.')
        elif re.fullmatch(r'[\d\s.,+\-/]+[a-z ]*',text):
            s.say('Please give one approximate count, for example 20k or 20,000. I will keep the current demo screen open.')
            return True
    elif pending in {'pain_points','process','influence'}:
        from .planner import shortcut,romanize
        if not re.search(r'\b(show|open|demo|schedule|explain|dikhao|kholo)\b',text) and not shortcut(romanize(text)):
            value=message.strip();reply='Thanks, I have noted that.'
    elif pending=='consent':
        if text in {'yes','yeah','haan','han','yes please'}:
            value=True;reply='You would like a follow-up. Please share the email or phone number the team should use.'
        elif text in {'no','nope','nahi','nahin','no thanks'}:
            value=False;s.opted_out=True;reply='Understood. I will not request contact details or arrange a follow-up.'
    if value is None:return False
    s.discovery_answers[pending]=value;s.pending_discovery=None
    s.say(reply+' I will keep the current demo screen open.')
    return True

async def requalify(s):
    result=await qualify_session(list(s.messages))
    if s.id not in sessions:return
    s.qual=result;q=result['qualification']
    if not s.opted_out and handoffs.eligible(q) and s.handoff_status=='not_requested':
        s.handoff_status='pending'
        s.handoff_status=await handoffs.deliver(handoffs.brief(s.id,q,s.shown))
        s.say('Thank you. I have shared your details with the Leadrat team, and someone will contact you soon.' if s.handoff_status=='delivered'
              else 'I could not hand your details to the team just now; a Leadrat specialist will review this conversation.')
    elif q['route']=='graceful_close' and not s.closed_politely and not s.opted_out and q.get('icp_score') is not None:
        s.closed_politely=True
        s.say('Thank you for exploring Leadrat. It may not be the best fit for your business right now, but you are welcome to keep looking around.')

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
