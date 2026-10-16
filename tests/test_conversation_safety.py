import asyncio
import pytest
from app import main
from app.conversation_engine import validate_decision
from app.project import FEATURES
from slm.labels import Extraction,complete

def test_product_interruption_preserves_business_question(isolated_conversation_model):
    class Worker:
        async def open_module(self,f):return 'Verified'
    async def run():
        s=main.Session(worker=Worker(),pending_discovery='monthly_leads')
        await main.execute(s,'show leads')
        assert s.pending_discovery=='monthly_leads'
        assert s.messages[-1]['text'].startswith('By the way,')
        assert 'leads' in s.shown
    asyncio.run(run())

def test_empty_extraction_does_not_acknowledge_saved_facts(isolated_conversation_model):
    isolated_conversation_model['perhaps']={'kind':'customer','updates':[]}
    async def run():
        s=main.Session(pending_discovery='monthly_leads')
        await main.execute(s,'perhaps')
        assert s.pending_discovery=='monthly_leads' and not s.discovery_answers
        assert 'not changed' in s.messages[-1]['text']
    asyncio.run(run())

def test_current_message_is_not_duplicated_in_history():
    s=main.Session();s.say('How many people?')
    s.messages.append({'id':'u1','role':'user','text':'17'})
    context=main.conversation_context(s,'17')
    assert context['message']=='17' and len(context['history'])==1

def test_crm_answer_cannot_become_developer_fact():
    with pytest.raises(ValueError):
        validate_decision({'kind':'customer','updates':[{'field':'organisation.type','value':'developer','evidence':'another CRM'}]},
                          {'message':'another CRM'},FEATURES,[])

def test_old_extraction_cannot_overwrite_new_customer_details(monkeypatch):
    async def run():
        s=main.Session();main.sessions[s.id]=s
        async def extraction(messages):
            s.customer_revision+=1
            return {'qualification':complete(Extraction()).model_dump(),'source':'slm','attempts':[]}
        monkeypatch.setattr(main,'qualify_session',extraction)
        try:await main.requalify(s);assert s.qual is None
        finally:main.sessions.pop(s.id,None)
    asyncio.run(run())

def test_model_cannot_grant_unrecorded_contact_permission(monkeypatch):
    async def run():
        s=main.Session(discovery_answers={'organisation.agents':23,'monthly_leads':20000})
        main.sessions[s.id]=s
        async def extraction(messages):return {'qualification':complete(Extraction(consent=True)).model_dump(),'source':'slm','attempts':[]}
        monkeypatch.setattr(main,'qualify_session',extraction)
        monkeypatch.setenv('BEACON_PRINT_HANDOFF','0')
        try:
            await main.requalify(s)
            q=s.qual['qualification']
            assert q['consent'] is False and q['organisation']['agents']==23
            assert q['monthly_leads']=={'min':20000,'max':20000}
            assert s.handoff_status=='not_requested'
        finally:main.sessions.pop(s.id,None)
    asyncio.run(run())

def test_product_examples_are_not_sent_as_customer_facts():
    from app.qualify import transcript_of
    rows=[{'role':'user','kind':'product_question','text':'Suppose a developer has 900 agents; how would your CRM help?'},
          {'role':'assistant','kind':'product_answer','text':'Example companies may have 500 agents.'},
          {'role':'assistant','kind':'customer_ack','text':'Thanks for your answer.'},
          {'role':'assistant','text':'How many people are on your sales team?'},
          {'role':'user','kind':'customer_answer','text':'12'}]
    turns=transcript_of(rows)
    assert len(turns)==2 and '900' not in str(turns)


def test_accepted_problem_replaces_earlier_tool_name_in_fallback():
    s=main.Session(discovery_answers={'pain_points':'We miss follow-ups'})
    s.messages=[{'id':'u1','role':'user','text':'We miss follow-ups','kind':'customer_answer'}]
    s.fact_evidence={'pain_points':{'message_id':'u1','quote':'We miss follow-ups'}}
    result={'source':'rules','qualification':complete(Extraction(pain_points=['excels'])).model_dump()}
    q=main.accepted_qualification(s,result)
    assert q['pain_points']==['We miss follow-ups'] and q['evidence']['pain_points']==[1]
    assert q['route']=='human_review'

def test_unaccepted_model_facts_do_not_reach_sales_json():
    from slm.labels import Organisation,Range
    s=main.Session()
    result={'source':'slm','qualification':complete(Extraction(
        organisation=Organisation(type='developer',agents=900),monthly_leads=Range(min=100000,max=100000))).model_dump()}
    q=main.accepted_qualification(s,result)
    assert q['organisation']['type']=='unknown' and q['organisation']['agents'] is None
    assert q['monthly_leads']=={'min':None,'max':None} and q['route']=='human_review'


def test_refusal_clears_pending_contact_question():
    async def run():
        s=main.Session(pending_discovery='consent')
        await main.execute(s,'Do not contact me')
        assert s.opted_out and s.pending_discovery is None
        assert s.discovery_answers['consent'] is False
    asyncio.run(run())


def test_browser_cleanup_survives_expired_page_and_failed_close():
    from app.browser import BrowserWorker
    calls=[]
    class Resource:
        def __init__(self,name):self.name=name
        async def close(self):
            calls.append(self.name)
            if self.name=='context':raise RuntimeError('Page already closed')
        async def stop(self):calls.append(self.name)
    async def run():
        worker=BrowserWorker()
        worker.context=Resource('context');worker.browser=Resource('browser');worker.pw=Resource('driver')
        async def expired():raise RuntimeError('Disconnected page')
        worker.authenticated=expired
        await worker.close()
        assert calls==['context','browser','driver']
        assert worker.context is worker.browser is worker.pw is None
    asyncio.run(run())

def test_answers_get_varied_natural_reactions_and_a_question_is_raised_again_only_once(isolated_conversation_model):
    """Live report: every answer began with the same "Got it —", and the business-type question was
    repeated word for word ("And to continue: To tailor the demo: ...") after every product answer."""
    from app.conversation_engine import CountUpdate,OrganisationUpdate,TextUpdate
    reactions=[main.reaction(OrganisationUpdate(field='organisation.type',value='developer',evidence='developer')),
        main.reaction(CountUpdate(field='organisation.agents',value=25,evidence='25')),
        main.reaction(CountUpdate(field='monthly_leads',value=500,evidence='500')),
        main.reaction(TextUpdate(field='process',value='WhatsApp',evidence='WhatsApp',summary='you manage leads on WhatsApp')),
        main.reaction(TextUpdate(field='next_step',value='now',evidence='now',summary='you want a new CRM running now'))]
    assert reactions==["Great, so you're a developer.",'Okay, a team of 25.',"Thanks, that's 500 new leads a month.",
                       'Okay, so you manage leads on WhatsApp.','Perfect, so you want a new CRM running now.']
    assert not any('Got it' in r for r in reactions) and len({r.split()[0] for r in reactions})>=4
    class Worker:
        async def open_module(self,f):return 'Verified'
    async def run():
        s=main.Session(worker=Worker(),pending_discovery='organisation.type')
        await main.execute(s,'show leads')
        assert s.messages[-1]['text']=='By the way, are you a brokerage, a developer or a channel partner?'
        await main.execute(s,'show tasks')
        # Asked once already: offer a next step instead; the answer chips stay available.
        assert s.pending_discovery=='organisation.type' and s.messages[-1]['text'].startswith('Would you like to see ')
        assert sum('brokerage, a developer' in m['text'] for m in s.messages)==1
        assert all('Got it' not in m['text'] and 'is open.' not in m['text'] for m in s.messages)
    asyncio.run(run())

def test_acknowledgement_never_echoes_raw_reply_without_a_restatement():
    from app.conversation_engine import TextUpdate
    assert main.restated(TextUpdate(field='process',value='i am not usting any tools',evidence='i am not usting any tools'))==main.NOTED

def test_early_screen_opening_runs_before_the_answer_is_written(isolated_conversation_model,monkeypatch):
    order=[]
    class Worker:
        async def open_module(self,f):order.append('open');return 'Verified'
    original=main.knowledge.answer
    async def answer(*args,**kwargs):
        await asyncio.sleep(0.05);order.append('answer');return await original(*args,**kwargs)
    monkeypatch.setattr(main.knowledge,'answer',answer)
    async def run():
        s=main.Session(worker=Worker())
        await main.execute(s,'show leads')
        assert order==['open','answer'] and s.steps[0]['status']=='verified'
    asyncio.run(run())


@pytest.mark.parametrize('decision',[{'kind':'product','feature':'unknown','topic':'Global Config','demo':False},
    {'kind':'product','feature':'unknown','topic':'Offplan','demo':True},{'kind':'product','feature':'leads','topic':'Lead Management','demo':False}])
def test_every_product_answer_ends_with_a_follow_up_question(isolated_conversation_model,decision):
    """Live report: after an explanation without a screen, Beacon stopped and asked nothing."""
    isolated_conversation_model['tell me more']=decision
    async def run():
        s=main.Session(pending_discovery='organisation.type')
        await main.execute(s,'tell me more')
        assert s.messages[-1]['text']=='By the way, are you a brokerage, a developer or a channel partner?'
        s=main.Session(discovery_asked=[p for p,_ in main.DISCOVERY]+['consent'])
        await main.execute(s,'tell me more')
        assert s.messages[-1]['text'].startswith('Would you like to see ')
    asyncio.run(run())

def test_sharing_a_number_after_the_contact_question_is_permission(isolated_conversation_model):
    """Live report: a phone number given in reply to "Would you like someone to contact you? If yes, share..."
    was saved without consent, so the sales handoff was never sent."""
    isolated_conversation_model['8103829424']={'kind':'customer','updates':[{'field':'contact','value':True,'evidence':'8103829424'}]}
    async def run():
        s=main.Session(pending_discovery='consent')
        s.messages.append({'id':'u1','role':'user','text':'8103829424'})
        await main.execute(s,'8103829424')
        assert s.discovery_answers['consent'] is True and s.discovery_answers['contact'] is True
        assert s.fact_evidence['consent']['message_id']=='u1' and s.pending_discovery not in {'consent','contact'}
        if s.qual_task:s.qual_task.cancel()
    asyncio.run(run())

def test_finishing_stops_questions_and_offers(isolated_conversation_model):
    isolated_conversation_model['no thanks']={'kind':'stop'}
    async def run():
        s=main.Session(offer='notes',discovery_answers={'consent':True,'contact':True})
        await main.execute(s,'no thanks')
        assert s.offer is None and s.pending_discovery is None and len(s.messages)==1
        assert 'The team will reach out' in s.messages[0]['text'] and not s.messages[0]['text'].rstrip().endswith('next?')
        await main.execute(s,'no thanks')
        assert s.messages[-1]['text']=="Sure, I'm here if you need anything else."
    asyncio.run(run())

