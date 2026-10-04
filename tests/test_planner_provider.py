import asyncio
import json
import pytest
from app import planner

def test_hosted_budget_and_low_schema(monkeypatch):
    monkeypatch.setattr(planner.config,'PROVIDER','openai')
    monkeypatch.setenv('OPENAI_API_KEY','test-not-a-real-key')
    monkeypatch.setattr(planner,'USAGE',{'requests':0,'input_tokens':0,'output_tokens':0})
    captured={}
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'status':'completed','usage':{'input_tokens':100,'output_tokens':12},'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'feature':'projects','demo':True})}]}]}
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,**kwargs):captured.update(kwargs['json']);return Response()
    monkeypatch.setattr(planner.httpx,'AsyncClient',Client)
    result,_=asyncio.run(planner.plan('Where can I see projects? sample@example.test',None))
    assert result.feature=='projects'
    assert captured['reasoning']=={'effort':'low'} and captured['store'] is False
    assert captured['max_output_tokens']==512
    assert captured['text']['format']['strict'] is True
    assert 'sample@example.test' not in str(captured)
    assert planner.USAGE=={'requests':1,'input_tokens':100,'output_tokens':12}
    monkeypatch.setenv('OPENAI_MAX_TEST_CALLS','1')
    captured.clear()
    # Past the budget no paid request is made; reviewed keywords may still answer.
    result,source=asyncio.run(planner.plan('Take me to projects please',None))
    assert result.feature=='projects' and source=='keyword_fallback' and not captured
    result,source=asyncio.run(planner.plan('Does Leadrat run payroll?',None))
    assert result.feature=='unknown' and not result.demo and not captured
    assert planner.USAGE['requests']==1

def test_shortcuts_do_not_call_paid_provider(monkeypatch):
    monkeypatch.setattr(planner.config,'PROVIDER','openai')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    result,source=asyncio.run(planner.plan('Show projects',None))
    assert result.feature=='projects' and source=='reviewed_shortcut'
