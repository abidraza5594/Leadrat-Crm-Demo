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

def test_last_answer_moves_conversation_on_without_repeating_screen_note(monkeypatch):
 async def forbidden(*args):raise AssertionError('A discovery reply must not plan a demo')
 monkeypatch.setattr(main,'plan',forbidden)
 async def check():
  s=main.Session(last_feature='leads')
  main.discover(s)
  for text in ['developer','23','20k','excels']:await main.execute(s,text)
  replies=[m['text'] for m in s.messages if m['role']=='assistant']
  assert s.discovery_answers['process']=='Excel'
  # Excel already answers "what do you use", so that question is skipped.
  assert s.pending_discovery=='influence'
  for text in ['i decide','next month']:await main.execute(s,text)
  replies=[m['text'] for m in s.messages if m['role']=='assistant']
  assert not any('screen open' in r for r in replies)
  assert s.pending_discovery=='consent' and replies[-1].startswith('Would you like someone from Leadrat')
  await main.execute(s,'no')
  assert s.messages[-1]['text'].startswith('Shall I show you how to add a lead') and s.offer=='add_lead'
  if s.qual_task:s.qual_task.cancel()
 asyncio.run(check())

def test_yes_to_follow_up_runs_offered_demo(monkeypatch):
 async def forbidden(*args):raise AssertionError('An accepted offer needs no planning')
 async def opened(f):return f['title']+' opened.'
 async def walked(worker,f):return f['title']+' controls shown.'
 monkeypatch.setattr(main,'plan',forbidden);monkeypatch.setattr(main,'walkthrough',walked)
 async def check():
  s=main.Session(offer='add_lead',opted_out=True);s.worker.open_module=opened
  await main.execute(s,'haan')
  assert s.last_feature=='add_lead' and 'Add a lead controls shown.' in [m['text'] for m in s.messages]
  if s.qual_task:s.qual_task.cancel()
 asyncio.run(check())

def test_contact_reply_after_consent_is_captured_not_planned(monkeypatch):
 async def forbidden(*args):raise AssertionError('A contact reply must not plan a demo')
 monkeypatch.setattr(main,'plan',forbidden)
 async def check():
  s=main.Session(pending_discovery='consent',discovery_asked=['consent'])
  await main.execute(s,'yes')
  assert s.pending_discovery=='contact'
  await main.execute(s,'my name is Rohan, rohan@acme.example.com')
  assert s.discovery_answers['contact'] is True and s.messages[0]['text']==main.SAVED_CONTACT or main.SAVED_CONTACT in [m['text'] for m in s.messages]
  if s.qual_task:s.qual_task.cancel()
 asyncio.run(check())

def test_rules_extract_reads_discovery_answers():
 from app.qualify import rules_extract
 turns=[{'speaker':'beacon','turn_id':1,'text':'What is the biggest problem with how you handle leads today?'},
  {'speaker':'visitor','turn_id':2,'text':'excels'},
  {'speaker':'beacon','turn_id':3,'text':'Would you like someone from Leadrat to contact you? If yes, share an email or phone number.'},
  {'speaker':'visitor','turn_id':4,'text':'yes'},
  {'speaker':'beacon','turn_id':5,'text':'Would you be the one deciding on a CRM, or evaluating it for someone else?'},
  {'speaker':'visitor','turn_id':6,'text':'i decide'},
  {'speaker':'beacon','turn_id':7,'text':'When would you want a new CRM running: within the next month, or later?'},
  {'speaker':'visitor','turn_id':8,'text':'next month'}]
 x=rules_extract(turns)
 assert x.pain_points==['excels'] and x.current_tooling==['Excel'] and x.process=='manual' and x.consent is True
 assert x.influence=='approver' and x.next_step=='within_30_days'

def test_product_question_is_not_a_discovery_answer():
 s=main.Session(pending_discovery='organisation.agents')
 assert not main.accept_discovery_reply(s,'show 30 leads')
 assert not main.accept_discovery_reply(s,'how many agents can use this?')
 assert not s.discovery_answers

def test_bare_number_without_pending_question_is_not_assumed():
 s=main.Session()
 assert not main.accept_discovery_reply(s,'30')

def test_direct_answers_override_model_misreading():
 from app.qualify import anchor
 from slm.labels import Extraction
 turns=[{'speaker':'beacon','turn_id':1,'text':'When would you want a new CRM running: within the next month, or later?'},
  {'speaker':'visitor','turn_id':2,'text':'next month'},
  {'speaker':'beacon','turn_id':3,'text':'What is the biggest problem with how you handle leads today?'},
  {'speaker':'visitor','turn_id':4,'text':'excels'}]
 model=Extraction(next_step='later',pain_points=[],organisation={'type':'developer','agents':23})
 x=anchor(model,turns)
 assert x.next_step=='within_30_days' and x.pain_points==['excels'] and x.process=='manual'
 assert x.organisation.type=='developer' and x.organisation.agents==23
