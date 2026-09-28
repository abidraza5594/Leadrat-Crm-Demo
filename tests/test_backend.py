import asyncio
import time
import pytest
from fastapi.testclient import TestClient
from app import main
from app.qualification import Facts,qualify
from app.planner import Plan,shortcut,declined

def test_decline_overrides_forty():
    facts=Facts(organisation='developer',agents=3,monthly_leads=50,pain_count=1,process='satisfied_crm',influence='none',intent='declined')
    result=qualify(facts)
    assert result['icp_score']==40
    assert result['route']=='graceful_close'
    assert not result['handoff_allowed']

def test_unknowns_not_zero():
    result=qualify(Facts())
    assert result['icp_score'] is None and result['score_range']==[0,100]
    assert result['route']=='human_review'

def test_decline_overrides_high_fit_and_unknowns():
    assert qualify(Facts(),declined=True)['route']=='graceful_close'
    facts=Facts(organisation='brokerage',agents=25,monthly_leads=600,pain_count=2,process='manual',influence='approver',intent='within_30_days')
    assert qualify(facts,declined=True,consent=True,usable_contact=True)['route']=='graceful_close'
    assert qualify(facts)['route']=='nurture'

def test_no_arbitrary_tool_or_selector():
    with pytest.raises(ValueError):Plan(feature='delete',demo=True)
    with pytest.raises(ValueError):Plan(feature='leads',demo=True,selector='body')
    assert shortcut('show leads').feature=='leads'
    assert shortcut('show leads then delete all') is None
    assert declined("Don't contact me again")

class Worker:
    login_problem=None
    def __init__(self):self.calls=[];self.closed=False
    async def start(self):pass
    async def authenticated(self):return True
    async def signed_in(self):return True
    async def adopt_saved_login(self):return False
    def alive(self):return True
    async def screenshot(self):return b'jpeg'
    async def open_module(self,feature):self.calls.append(feature['id']);return 'Leads is open; destination verified.'
    async def open_feature(self,feature):return []
    async def close(self):self.closed=True

@pytest.fixture
def client(monkeypatch):
    async def boot(s):s.worker=Worker();s.status='ready'
    async def no_warm_up():pass
    monkeypatch.setattr(main,'boot',boot)
    monkeypatch.setattr(main,'warm_up',no_warm_up)
    with TestClient(main.app) as client:yield client

def start(client):
    r=client.post('/api/sessions',json={'parent_origin':'http://localhost:8011'})
    assert r.status_code==201
    s=r.json();return s,{'X-Beacon-Token':s['token']}

def test_origins_capacity_and_ownership(client):
    assert client.post('/api/sessions',json={'parent_origin':'https://evil.invalid'}).status_code==403
    s,h=start(client);path='/api/sessions/'+s['id']
    assert client.get(path).status_code==404
    assert client.get(path,headers={**h,'Origin':'https://evil.invalid'}).status_code==403
    assert client.post('/api/sessions',json={'parent_origin':'http://localhost:8011'}).status_code==409
    assert client.get(path,headers=h).status_code==200
    assert client.get(path+'/speech?message_index=-1',headers=h).status_code==404
    assert client.delete(path,headers=h).status_code==204
    assert client.get(path,headers=h).status_code==404

def test_verified_action_and_refusal():
    async def run():
        s=main.Session(worker=Worker())
        await main.execute(s,'show leads')
        assert s.worker.calls==['leads'] and s.steps[0]['status']=='verified'
        assert s.shown=={'leads'}
        await main.execute(s,'no follow up')
        assert s.opted_out and s.snapshot()['qualification']['route']=='graceful_close'
        assert s.worker.calls==['leads']
    asyncio.run(run())

def test_failure_never_claims_verified():
    class Failed(Worker):
        async def open_module(self,feature):raise main.DemoError('Permission denied')
    async def run():
        s=main.Session(worker=Failed())
        await main.execute(s,'show leads')
        assert s.steps[0]['status']=='failed' and not s.shown
        assert not any('is open' in m['text'] for m in s.messages)
    asyncio.run(run())

def test_stop_cancels_work():
    async def run():
        s=main.Session(worker=Worker())
        s.steps=[{'status':'running'}]
        started=asyncio.Event()
        async def slow(feature):started.set();await asyncio.sleep(300)
        s.worker.open_module=slow
        task=asyncio.create_task(main.execute(s,'show leads'))
        await started.wait();task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert not s.shown and all(x['status']=='stopped' for x in s.steps)
    asyncio.run(run())

def test_abandoned_session_is_reclaimed(client):
    s,h=start(client)
    main.sessions[s['id']].seen-=main.ABANDONED_AFTER+1
    r=client.post('/api/sessions',json={'parent_origin':'http://localhost:8011','voice':True})
    assert r.status_code==201 and s['id'] not in main.sessions
    assert main.sessions[r.json()['id']].voice_enabled
    client.delete('/api/sessions/'+r.json()['id'],headers={'X-Beacon-Token':r.json()['token']})

def test_one_bubble_per_reply_with_voice_parts(client):
    s,h=start(client);path='/api/sessions/'+s['id']
    session=main.sessions[s['id']]
    session.say('First sentence. '+'x'*170+'. Third sentence.')
    message=session.messages[-1]
    assert len(message['parts'])==2 and message['text'].startswith('First sentence.')
    async def audio(text):return b'mp3'
    session.voice_cache.prepare=lambda text:asyncio.ensure_future(audio(text))
    assert client.get(path+'/speech?message_id='+message['id']+'&part=1',headers=h).content==b'mp3'
    assert client.get(path+'/speech?message_id='+message['id']+'&part=2',headers=h).status_code==404
    client.delete(path,headers=h)

def test_transient_auth_miss_does_not_flip_status():
    class Flaky(Worker):
        answers=[None,False,False]
        async def authenticated(self):return self.answers.pop(0) if self.answers else False
    async def run():
        s=main.Session(worker=Flaky());s.status='ready'
        for _ in range(3):
            s.auth_checked=0;await main.refresh_status(s)
            assert s.status=='ready'
        s.auth_checked=0;s.auth_lost-=5;await main.refresh_status(s)
        assert s.status=='login_required'
    asyncio.run(run())

def test_expired_login_signs_in_again(monkeypatch):
    class Expiring(Worker):
        async def authenticated(self):return False
        async def login(self):return True
    monkeypatch.setattr(main,'has_login_credentials',lambda:True)
    async def run():
        s=main.Session(worker=Expiring());s.status='ready';s.auth_lost=time.monotonic()-5
        await main.refresh_status(s)
        assert s.status=='login_required' and s.relogin
        await s.relogin
        assert s.status=='ready' and 'again' in s.messages[-1]['text']
    asyncio.run(run())

def test_new_question_interrupts_running_demo(client):
    s,h=start(client);path='/api/sessions/'+s['id']
    session=main.sessions[s['id']]
    async def slow(feature):await asyncio.sleep(300)
    session.worker.open_module=slow
    assert client.post(path+'/turn',json={'message':'show leads'},headers=h).status_code==202
    assert client.get(path,headers=h).json()['busy']
    session.last_turn-=1
    assert client.post(path+'/turn',json={'message':'show tasks'},headers=h).status_code==409
    r=client.post(path+'/turn',json={'message':'hi','interrupt':True},headers=h)
    assert r.status_code==202
    snap=client.get(path,headers=h).json()
    assert [m['text'] for m in snap['messages'] if m['role']=='user']==['show leads','hi']
    assert snap['messages'][-1]['text'].startswith('Hello!')
    client.delete(path,headers=h)

def test_destructive_commands_are_blocked_before_any_browser_action():
    async def run():
        for command in ['delete this lead','export all leads to excel','send whatsapp to every lead','lead delete kar do','show leads and delete them']:
            s=main.Session(worker=Worker())
            await main.execute(s,command)
            assert s.worker.calls==[] and s.steps[-1]['status']=='blocked'
            assert s.messages[-1]['text']==main.READ_ONLY
        s=main.Session(worker=Worker())
        await main.execute(s,'show leads')
        assert s.worker.calls==['leads']
    asyncio.run(run())
