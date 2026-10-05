import asyncio
import pytest
from app import main
from app.qualify import rules_extract,transcript_of

@pytest.mark.parametrize('reply,expected',[
 ('20k',20000),('20 K',20000),('1.5k',1500),('20,000',20000),('1 lakh',100000),
 ('2 lakhs',200000),('1,00,000',100000),('2.5 million',2500000),('fifty',50),('twenty-five',25),
 ('we get around 20k leads per month',20000),('0',0)])
@pytest.mark.parametrize('field',['monthly_leads','organisation.agents'])
def test_count_reply_categories(reply,expected,field):
 s=main.Session(pending_discovery=field,last_feature='site_visit')
 assert main.accept_discovery_reply(s,reply)
 assert s.discovery_answers[field]==expected and s.last_feature=='site_visit'

@pytest.mark.parametrize('reply',['yes','no','haan','nahi','ok','20-30k','20,00','-5'])
def test_unclear_count_does_not_move_or_consume_question(reply):
 s=main.Session(pending_discovery='monthly_leads',last_feature='site_visit')
 assert main.accept_discovery_reply(s,reply)
 main.discover(s)
 assert s.pending_discovery=='monthly_leads' and not s.discovery_answers

@pytest.mark.parametrize('reply',['skip','not sure',"don't know",'pata nahi','later'])
def test_skip_unknown(reply):
 s=main.Session(pending_discovery='monthly_leads',discovery_asked=['monthly_leads'])
 assert main.accept_discovery_reply(s,reply)
 assert not s.pending_discovery and not s.discovery_answers

@pytest.mark.parametrize('reply',['developer','i am developer',"I'm a developer",'main developer hu','we are builders','channel partner'])
def test_business_replies(reply):
 s=main.Session(pending_discovery='organisation.type')
 assert main.accept_discovery_reply(s,reply)
 assert s.discovery_answers['organisation.type']

@pytest.mark.parametrize('reply',['show leads','show projects','how do I change status?','open site visit','delete all leads'])
def test_new_request_not_swallowed(reply):
 s=main.Session(pending_discovery='monthly_leads')
 assert not main.accept_discovery_reply(s,reply)

@pytest.mark.parametrize('reply',['no','nahi','no thanks'])
def test_declined_consent(reply):
 s=main.Session(pending_discovery='consent')
 assert main.accept_discovery_reply(s,reply) and s.opted_out
 assert s.discovery_answers['consent'] is False

def test_explicit_correction_does_not_answer_wrong_question():
 s=main.Session(pending_discovery='monthly_leads',discovery_answers={'organisation.agents':50})
 assert main.accept_discovery_reply(s,'actually 60 agents')
 assert s.discovery_answers=={'organisation.agents':60}
 assert s.pending_discovery=='monthly_leads'

def test_count_context_in_sales_fallback():
 rows=[{'role':'assistant','text':'How many people are on your sales team?'},{'role':'user','text':'50'},
 {'role':'assistant','text':'Roughly how many new leads do you get in a month?'},{'role':'user','text':'20k'}]
 q=rules_extract(transcript_of(rows))
 assert q.organisation.agents==50 and q.monthly_leads.min==20000
 assert q.evidence['monthly_leads']==[4]

def test_assistant_number_does_not_become_customer_fact():
 q=rules_extract(transcript_of([{'role':'assistant','text':'Our sample has 20k leads'},{'role':'user','text':'ok'}]))
 assert q.monthly_leads.min is None

@pytest.mark.parametrize('text,n',[('20k leads',20000),('20,000 leads',20000),('1 lakh leads',100000)])
def test_explicit_sales_counts(text,n):
 q=rules_extract(transcript_of([{'role':'user','text':text}]))
 assert q.monthly_leads.min==n

@pytest.mark.parametrize('text,expected',[('twenty thousand',20000),('two lakh',200000),('one million',1000000)])
def test_spoken_counts(text,expected):
 from app.conversation_numbers import count_reply
 assert count_reply(text)==expected

@pytest.mark.parametrize('text',['show it','show this','demo this','ye dikhao','iska demo dikhao'])
def test_followup_demo_uses_previous_feature(text):
 from app.planner import plan
 p,_=asyncio.run(plan(text,'site_visit'))
 assert p.feature=='site_visit' and p.demo

def test_repeat_preserves_pending_question():
 async def check():
  s=main.Session(pending_discovery='monthly_leads')
  s.say('Roughly how many new leads do you get in a month?')
  await main.execute(s,'repeat')
  assert s.messages[-1]['text']=='Roughly how many new leads do you get in a month?'
  assert s.pending_discovery=='monthly_leads' and not s.steps
  if s.qual_task:s.qual_task.cancel()
 asyncio.run(check())
