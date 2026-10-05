import asyncio
from app import main,planner,docs

def test_site_visit_typo_uses_same_answer_and_plan():
 async def check():
  for text in ['how to do siteviste schedule','i want sitevisite','how to schedule site visit']:
   p,_=await planner.plan(text,None)
   a=await docs.answer(text)
   assert p.feature=='site_visit' and p.demo
   assert 'Schedule Site Visit' in a['text'] and 'Clock In' not in a['text']
 asyncio.run(check())

def test_discovery_replies_do_not_plan_or_move_screen(monkeypatch):
 async def forbidden(*args):raise AssertionError('A discovery reply must not plan a demo')
 monkeypatch.setattr(main,'plan',forbidden)
 async def check():
  s=main.Session(last_feature='site_visit')
  main.discover(s)
  assert s.pending_discovery=='organisation.type'
  await main.execute(s,'channel partner')
  assert s.pending_discovery=='organisation.agents'
  await main.execute(s,'30')
  assert s.discovery_answers=={'organisation.type':'channel partner','organisation.agents':30}
  assert s.last_feature=='site_visit' and not s.steps
  assert s.pending_discovery=='monthly_leads'
  assert not any("don't know" in m['text'] for m in s.messages)
  if s.qual_task:s.qual_task.cancel()
 asyncio.run(check())

def test_product_question_is_not_a_discovery_answer():
 s=main.Session(pending_discovery='organisation.agents')
 assert not main.accept_discovery_reply(s,'show 30 leads')
 assert not main.accept_discovery_reply(s,'how many agents can use this?')
 assert not s.discovery_answers

def test_bare_number_without_pending_question_is_not_assumed():
 s=main.Session()
 assert not main.accept_discovery_reply(s,'30')
