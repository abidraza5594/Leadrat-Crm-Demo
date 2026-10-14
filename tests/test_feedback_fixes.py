import asyncio
import json
from types import SimpleNamespace
import httpx
import pytest
from pydantic import ValidationError
from app import main, recovery, registration, soniox, transport, config, local_model

class Recoverable:
    def __init__(self):self.connected=False;self.restores=0;self.logins=0;self.checks=0
    async def signed_in(self):return self.connected
    async def login(self):self.logins+=1;self.connected=True;return True
    async def restore_checkpoint(self):self.restores+=1
    async def remember_checkpoint(self):self.checks+=1

def test_recovery_restores_before_retry_and_only_once(monkeypatch):
    monkeypatch.setattr(recovery,'has_login_credentials',lambda:True)
    async def run():
        worker=Recoverable();worker.connected=True;s=main.Session(worker=worker);calls=[]
        async def action():
            calls.append(worker.restores)
            if len(calls)==1:worker.connected=False;raise TimeoutError()
            return 'restored screen'
        assert await recovery.read_action(s,action)=='restored screen'
        assert calls==[0,1] and worker.logins==1 and worker.checks==1
    asyncio.run(run())

def test_no_retry_for_non_auth_error(monkeypatch):
    async def run():
        worker=Recoverable();worker.connected=True;s=main.Session(worker=worker)
        async def bad():raise ValueError('not permitted')
        with pytest.raises(ValueError):await recovery.read_action(s,bad)
        assert worker.logins==0
    asyncio.run(run())

def test_failed_signin_stops_read_action(monkeypatch):
    monkeypatch.setattr(recovery,'has_login_credentials',lambda:False)
    async def run():
        s=main.Session(worker=Recoverable())
        async def forbidden():raise AssertionError('Cannot execute without authentication')
        with pytest.raises(main.DemoError):await recovery.read_action(s,forbidden)
        assert s.status=='login_required'
    asyncio.run(run())

def test_registration_receipt_blocks_duplicate_and_unknown_writes():
    assert registration.receipt('one',claim=True)['status']=='claimed'
    assert registration.receipt('one',claim=True)['status']=='preparing'
    registration.receipt('one','submitted')
    assert registration.receipt('one',claim=True)['status']=='submitted'
    registration.receipt('one','created','record')
    assert registration.receipt('one',claim=True)=={'status':'created','record_id':'record'}
    registration.receipt('two',claim=True);registration.receipt('two','not_submitted')
    assert registration.receipt('two',claim=True)['status']=='claimed'

def test_registration_details_reach_sales_json_without_granting_contact_consent():
    from slm.labels import Extraction,complete
    s=main.Session(worker=Recoverable())
    v=registration.Visitor(name='Demo Visitor',email='demo@example.com',phone='+12025550126')
    registration.remember_details(s,v)
    registration.remember_details(s,v)
    q=main.accepted_qualification(s,{'source':'pending','qualification':complete(Extraction()).model_dump()})
    assert q['contact']=={'name':v.name,'email':v.email,'phone':v.phone}
    assert q['consent'] is False and len(s.messages)==1
    assert q['evidence']['contact.email']==[1]

def test_browser_cleanup_continues_when_context_close_stalls(monkeypatch):
    from app import browser
    monkeypatch.setattr(browser,'CLOSE_TIMEOUT',.01)
    async def run():
        calls=[]
        class Context:
            async def close(self):calls.append('context');await asyncio.Event().wait()
        class Browser:
            async def close(self):calls.append('browser')
        class Driver:
            async def stop(self):calls.append('driver')
        w=browser.BrowserWorker();w.context=Context();w.browser=Browser();w.pw=Driver()
        await asyncio.wait_for(w.close(),.5)
        assert calls==['context','browser','driver'] and w.pw is None
    asyncio.run(run())

@pytest.mark.parametrize('field,value',[('email','not email'),('phone','123'),('phone','8104194184')])
def test_registration_rejects_incomplete_contact(field,value):
    values={'name':'Test Visitor','email':'v@example.invalid','phone':'+12025550123',field:value}
    with pytest.raises(ValidationError):registration.Visitor(**values)

def test_soniox_key_is_scoped_single_use_and_session_bound(monkeypatch):
    monkeypatch.setenv('SONIOX_API_KEY','server-secret')
    def respond(request):
        body=json.loads(request.content)
        assert body['single_use'] and body['max_session_duration_seconds']==120
        assert body['usage_type']=='transcribe_websocket' and body['client_reference_id']=='s1'
        assert request.headers['authorization']=='Bearer server-secret'
        return httpx.Response(201,json={'api_key':'temporary','expires_at':'later'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as c:
            monkeypatch.setattr(transport,'shared',c)
            result=await soniox.temporary_key('s1')
            assert result['api_key']=='temporary' and 'server-secret' not in json.dumps(result)
    asyncio.run(run())

def test_soniox_missing_key_is_explicit(monkeypatch):
    monkeypatch.delenv('SONIOX_API_KEY',raising=False)
    with pytest.raises(ValueError,match='not configured'):soniox.key()

def test_deepseek_usage_records_hidden_calls_without_text(monkeypatch,tmp_path):
    monkeypatch.setattr(config,'PROVIDER','deepseek');monkeypatch.setattr(config,'DEEPSEEK_API_KEY','secret')
    path=tmp_path/'meter.jsonl';monkeypatch.setenv('BEACON_USAGE_FILE',str(path))
    def respond(request):
        return httpx.Response(200,json={'id':'request1','usage':{'prompt_tokens':80,'completion_tokens':10,'prompt_cache_hit_tokens':20},
          'choices':[{'finish_reason':'stop','message':{'content':'{"valid":true}'}}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as c:
            monkeypatch.setattr(transport,'shared',c)
            await local_model.complete([{'role':'system','content':'private customer text'}],{'properties':{'valid':{'type':'boolean'}}})
    asyncio.run(run())
    text=path.read_text();entry=json.loads(text)
    assert entry['usage']['prompt_tokens']==80 and entry['stage']=='verification'
    assert 'private customer text' not in text and 'secret' not in text
