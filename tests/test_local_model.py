import asyncio
import json
from app import planner, docs, qualify, local_model
from slm.prompting import SYSTEM


def test_local_docs_require_boolean_support(monkeypatch):
    monkeypatch.setattr(docs.config,'PROVIDER','local')
    async def complete(*args,**kwargs):return {'supported':'false','answer':'Invented','excerpts_used':[1]}
    monkeypatch.setattr(local_model,'complete',complete)
    evidence=[(10,1,{'module':'Tasks','section':'Tasks','text':'View your tasks.'})]
    try:asyncio.run(docs.compose('tasks',evidence))
    except ValueError:pass
    else:raise AssertionError('String false must not become true')

def test_latest_adapter_receives_training_prompt(monkeypatch):
    monkeypatch.setenv('QUAL_SLM_URL','http://local.invalid/v1')
    monkeypatch.setenv('QUAL_SLM_MODEL','beacon-v4')
    monkeypatch.setenv('QUAL_SLM_FORMAT','full')
    row=json.loads(open('slm/data/v3/test.jsonl',encoding='utf8').readline())
    async def chat(url,model,msgs,headers=None):
        assert msgs[0]['content']==SYSTEM
        return json.dumps(row['target'])
    monkeypatch.setattr(qualify,'_chat',chat)
    turns=[{'role':'user' if t['speaker']=='visitor' else 'assistant','text':t['text']} for t in row['transcript']]
    result=asyncio.run(qualify.qualify_session(turns))
    assert result['source']=='slm'

def test_handbook_does_not_invent_portal_names_or_support_hours(monkeypatch):
    monkeypatch.setenv('DOCS_ANSWER','extractive')
    for question in ['Which property portals in India does Leadrat publish to?', 'What are your customer support hours?']:
        assert asyncio.run(docs.answer(question))['grounded'] is False

def test_explicit_name_correction_and_withdrawal_override_model():
    import time
    from slm.labels import Extraction, complete
    q=complete(Extraction(role='Ravi',seniority='owner'))
    turns=[{'speaker':'beacon','turn_id':1,'text':'My name is Fake.'},
           {'speaker':'visitor','turn_id':2,'text':'My name is Ravi. We are a brokerage.'},
           {'speaker':'visitor','turn_id':3,'text':'Correction: my name is Neha.'}]
    result=qualify._done(q,'slm',[],time.monotonic(),turns)['qualification']
    assert result['contact']['name']=='Neha' and result['seniority']=='unknown'
    turns.append({'speaker':'visitor','turn_id':4,'text':'Forget my name.'})
    result=qualify._done(q,'slm',[],time.monotonic(),turns)['qualification']
    assert result['contact']['name'] is None
    result=qualify._done(q,'slm',[],time.monotonic(),[{'speaker':'visitor','turn_id':1,'text':'My name is Ravi. Forget my name.'}])['qualification']
    assert result['contact']['name'] is None

def test_personal_name_is_not_a_job_title():
    import time
    from slm.labels import Extraction, complete
    q=complete(Extraction(role='Ravi',seniority='owner'))
    result=qualify._done(q,'slm',[],time.monotonic(),[{'speaker':'visitor','turn_id':1,'text':'My name is Ravi. We have 12 agents.'}])['qualification']
    assert result['contact']['name']=='Ravi' and result['role'] is None and result['seniority']=='unknown'


def test_real_estate_developer_does_not_imply_employee_seniority():
    import time
    from slm.labels import Extraction,complete
    q=complete(Extraction(role='developer',seniority='individual_contributor'))
    result=qualify._done(q,'slm',[],time.monotonic(),[{'speaker':'visitor','turn_id':1,'text':'I am a developer.'}])['qualification']
    assert result['seniority']=='unknown' and 'seniority' not in result['evidence']
    stated=qualify._done(q,'slm',[],time.monotonic(),[{'speaker':'visitor','turn_id':1,'text':'I am a sales agent.'}])['qualification']
    assert stated['seniority']=='individual_contributor'

def test_absent_permission_is_not_an_explicit_decline():
    import time
    from slm.labels import Extraction, complete
    q=complete(Extraction(next_step='declined',consent=True))
    result=qualify._done(q,'slm',[],time.monotonic(),[{'speaker':'visitor','turn_id':1,'text':'I have not agreed to sales contact.'}])['qualification']
    assert result['next_step']=='unknown' and result['consent'] is False and result['route']=='human_review'

def test_explicit_customer_timing_contact_withdrawal_and_hinglish_name():
    import time
    from slm.labels import Extraction, complete
    q=complete(Extraction(next_step='within_30_days',consent=True,contact={'email':'asha@example.com'}))
    turns=[{'speaker':'visitor','turn_id':1,'text':'Mera naam Ravi hai. I want a demo in three months.'},
           {'speaker':'visitor','turn_id':2,'text':'That email belongs to someone else. Remove it.'}]
    result=qualify._done(q,'slm',[],time.monotonic(),turns)['qualification']
    assert result['next_step']=='later' and result['contact']['email'] is None and result['contact']['name']=='Ravi'
    assert result['route']!='sales_handoff'

def test_company_duration_does_not_set_demo_timing():
    import time
    from slm.labels import Extraction,complete
    q=complete(Extraction(next_step='unknown'))
    result=qualify._done(q,'slm',[],time.monotonic(),[{'speaker':'visitor','turn_id':1,'text':'We have been operating for three months.'}])['qualification']
    assert result['next_step']=='unknown'


def test_generation_deadline_does_not_repeat_long_request_or_claim_trained_result(monkeypatch):
    import httpx
    monkeypatch.setenv('QUAL_SLM_URL','http://local.invalid/v1')
    monkeypatch.setenv('QUAL_SLM_MODEL','beacon-v4')
    attempts=[]
    async def expired(*args,**kwargs):
        attempts.append(1)
        response=httpx.Response(504,request=httpx.Request('POST','http://local.invalid/v1/chat/completions'))
        response.raise_for_status()
    monkeypatch.setattr(qualify,'_chat',expired)
    result=asyncio.run(qualify.qualify_session([{'role':'user','text':'We are a developer with 30 agents.'}]))
    assert len(attempts)==1 and result['source']=='rules'
    assert result['qualification']['route']=='human_review'
