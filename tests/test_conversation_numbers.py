import pytest
from app.conversation_numbers import count_reply

@pytest.mark.parametrize('text,expected',[
 ('20k',20000),('20K',20000),('1.5k',1500),('20,000',20000),
 ('1 lakh',100000),('1,00,000',100000),('we get around 20k leads per month',20000),
 ('50',50),('0',0),('2 million',2000000),('20k/month',20000),
 ('show 20k leads',None),('20-30k',None),('20,00',None),('-30',None),('1.5',None)])
def test_count_formats(text,expected):
 assert count_reply(text)==expected

def test_developer_team_and_monthly_volume_conversation(monkeypatch):
 import asyncio
 from app import main
 async def forbidden(*args):raise AssertionError('Discovery response reached demo planner')
 monkeypatch.setattr(main,'plan',forbidden)
 async def check():
  s=main.Session(last_feature='leads');main.discover(s)
  for text in ['i am developer','50','20k']:
   await main.execute(s,text)
  assert s.discovery_answers=={'organisation.type':'developer','organisation.agents':50,'monthly_leads':20000}
  assert s.last_feature=='leads' and not s.steps
  assert any('20,000 new leads per month' in m['text'] for m in s.messages)
  assert s.pending_discovery=='pain_points'
  if s.qual_task:s.qual_task.cancel()
 asyncio.run(check())

def test_ambiguous_count_keeps_same_question():
 from app import main
 s=main.Session(pending_discovery='monthly_leads',discovery_asked=['monthly_leads'])
 assert main.accept_discovery_reply(s,'20-30k')
 main.discover(s)
 assert s.pending_discovery=='monthly_leads' and not s.discovery_answers
