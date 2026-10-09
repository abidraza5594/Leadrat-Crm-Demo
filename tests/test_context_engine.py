import asyncio
import json
import pytest
from app import main
from app.conversation_engine import Decision,validate_decision
from app.project import FEATURES
from app.conversation_store import ConversationStore


@pytest.mark.parametrize('question',['how to manage lead in your CRM','explain to we can manage lead','lead manage kaise karte hai'])
def test_answer_and_demo_use_one_decision(question,isolated_conversation_model):
    isolated_conversation_model[question]={'kind':'product','feature':'leads','topic':'Data Management','demo':True}
    class Worker:
        async def open_module(self,f):assert f['id']=='leads';return 'Leads workspace verified'
    async def run():
        s=main.Session(worker=Worker(),discovery_answers={'organisation.type':'developer','organisation.agents':300,'monthly_leads':100000})
        await main.execute(s,question)
        assert s.last_decision['topic']=='Lead Management'
        assert s.steps[-1]['status']=='verified'
        assert 'Manage enquiries' in s.messages[0]['text']
        assert not any('bulk prospect' in m['text'] for m in s.messages)
    asyncio.run(run())


def test_context_contains_pending_question_history_offer_and_facts(monkeypatch):
    async def run():
        seen=[]
        async def complete(messages,schema,**kwargs):
            seen.append(messages)
            return {'kind':'customer','updates':[{'field':'monthly_leads','value':100000,'evidence':'100k'}],'reply':'Got it — 100,000 leads per month.'}
        monkeypatch.setattr(main.engine,'completion',complete)
        s=main.Session(pending_discovery='monthly_leads',last_feature='leads',offer='status',discovery_answers={'organisation.agents':300})
        s.say('Roughly how many new leads do you get in a month?')
        await main.execute(s,'100k')
        assert 'Roughly how many' in seen[0][-1]['content']
        context=main.conversation_context(s,'100k')
        assert context['customer']['organisation.agents']==300 and context['last_offer']=='status'
        assert s.discovery_answers['monthly_leads']==100000 and not s.steps
        if s.qual_task:s.qual_task.cancel()
    asyncio.run(run())


@pytest.mark.parametrize('raw',[
    {'kind':'product','feature':'run_javascript','demo':True},
    {'kind':'product','feature':'leads','demo':'false'},
    {'kind':'customer','updates':[{'field':'organisation.agents','value':300,'evidence':'I have 300 people'}]},
    {'kind':'customer','updates':[{'field':'monthly_leads','value':-5,'evidence':'-5'}]},
    {'kind':'customer','updates':[{'field':'consent','value':'yes','evidence':'yes'}]},
])
def test_invalid_model_output_never_executes_or_guesses(monkeypatch,raw):
    async def complete(*args,**kwargs):return raw
    monkeypatch.setattr(main.engine,'completion',complete)
    async def run():
        s=main.Session()
        await main.execute(s,'-5 yes show leads')
        assert not s.steps and not s.discovery_answers and s.last_decision['kind']=='clarify'
    asyncio.run(run())


def test_model_outage_does_not_keyword_route(monkeypatch):
    async def down(*args,**kwargs):raise TimeoutError()
    monkeypatch.setattr(main.engine,'completion',down)
    async def run():
        s=main.Session();await main.execute(s,'show leads')
        assert not s.steps and s.last_decision['kind']=='clarify'
        assert 'try again shortly' in s.messages[-1]['text']
        assert 'which feature' not in s.messages[-1]['text']
    asyncio.run(run())


def test_correction_does_not_consume_unrelated_pending_question(isolated_conversation_model):
    text='actually 60 agents'
    isolated_conversation_model[text]={'kind':'customer','updates':[{'field':'organisation.agents','value':60,'evidence':'60'}],'reply':'Thanks, 60 people on your team.'}
    async def run():
        s=main.Session(pending_discovery='monthly_leads',discovery_answers={'organisation.agents':50})
        await main.execute(s,text)
        assert s.discovery_answers['organisation.agents']==60 and s.pending_discovery=='monthly_leads' and not s.steps
        if s.qual_task:s.qual_task.cancel()
    asyncio.run(run())


def test_explanation_only_does_not_open_screen(isolated_conversation_model):
    text='only explain lead management, do not open anything'
    isolated_conversation_model[text]={'kind':'product','feature':'leads','topic':'Lead Management','demo':False}
    async def run():
        s=main.Session();await main.execute(s,text)
        assert not s.steps and 'Leads workspace' in s.messages[0]['text']
    asyncio.run(run())


def test_durable_storage_is_scoped_by_project_and_session(tmp_path):
    async def run():
        path=tmp_path/'memory.db';store=ConversationStore(dsn='',path=path);await store.start()
        await store.save('leadrat','visitor-a',{'customer':{'monthly_leads':100000}})
        assert await store.load('other','visitor-a')=={} and await store.load('leadrat','visitor-b')=={}
        await store.close();store=ConversationStore(dsn='',path=path);await store.start()
        assert (await store.load('leadrat','visitor-a'))['customer']['monthly_leads']==100000
        await store.close()
    asyncio.run(run())


def test_wrong_topic_search_cannot_override_capability_answer(monkeypatch):
    async def irrelevant(*args):return [(0.99,{'id':9,'module':'Data Management','text':'Bulk prospects'})]
    monkeypatch.setattr(main.knowledge,'retrieve',irrelevant)
    result=asyncio.run(main.knowledge.answer('manage leads',Decision(kind='product',feature='leads',topic='Lead Management',demo=True),FEATURES))
    assert 'Bulk prospects' not in result['text'] and result['grounded']
