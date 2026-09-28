import asyncio
import httpx
import pytest
from app import planner
from app.planner import Plan, small_talk, shortcut, explanation_only, keyword_match

@pytest.mark.parametrize('text',['hi','Hii!','hello beacon','Namaste','good morning'])
def test_greetings_need_no_model(text):
    assert small_talk(text).startswith('Hello!')

def test_thanks_and_help():
    assert 'welcome' in small_talk('thank you')
    assert 'Leads' in small_talk('what can you do?')
    assert small_talk('show leads') is None

@pytest.mark.parametrize('question,expected',[
 ('lead ka status kaise badalna hai','status'),('lead me note kaise add kare','notes'),
 ('naya lead banao','add_lead'),('mujhe whatsapp dikhao','whatsapp'),('add lead','add_lead')])
def test_hinglish_shortcuts(question,expected):
    assert shortcut(question).feature==expected

def test_show_by_default_unless_explanation_only(monkeypatch):
    async def model(message,previous):return Plan(feature='projects',demo=False),'ollama'
    monkeypatch.setattr(planner,'classify',model)
    assert asyncio.run(planner.plan('where do i see my projects',None))[0].demo is True
    assert asyncio.run(planner.plan('just explain projects, do not open anything',None))[0].demo is False
    assert explanation_only('sirf batao, mat dikhao')

def test_model_outage_uses_reviewed_keywords_only(monkeypatch):
    async def down(message,previous):raise httpx.ConnectError('offline')
    monkeypatch.setattr(planner,'classify',down)
    result,source=asyncio.run(planner.plan('where can I see the projects list',None))
    assert result.feature=='projects' and source=='keyword_fallback'
    with pytest.raises(httpx.HTTPError):asyncio.run(planner.plan('file my income tax',None))
    assert keyword_match('payroll for employees') is None

@pytest.mark.parametrize('spoken,expected',[
 ('लीड का स्टेटस कैसे बदलें','status'),('लीड में नोट कैसे ऐड करें','notes'),('मुझे व्हाट्सएप दिखाओ','whatsapp'),('नया लीड बनाओ','add_lead')])
def test_hindi_speech_uses_reviewed_shortcuts(spoken,expected):
    result,source=asyncio.run(planner.plan(spoken,None))
    assert result.feature==expected and source=='reviewed_shortcut'

def test_hindi_greeting_and_opt_out():
    assert small_talk('नमस्ते।').startswith('Hello!')
    assert planner.declined('मुझे संपर्क मत करो')
