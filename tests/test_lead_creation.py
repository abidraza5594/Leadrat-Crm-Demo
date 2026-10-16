import asyncio
from app import main,lead_creation
from app.qualify import transcript_of

class Worker:
 async def signed_in(self):return True
 async def form_signature(self):return 'unchanged'

def test_creation_requires_review_and_never_retries_uncertain_save(monkeypatch):
 calls=[]
 async def prepare(worker,d):return 'Source: Direct.'
 async def uncertain(worker,d):calls.append(dict(d));raise TimeoutError()
 monkeypatch.setattr(lead_creation,'prepare',prepare)
 monkeypatch.setattr(lead_creation,'save',uncertain)
 async def run():
  s=main.Session(worker=Worker());await lead_creation.begin(s)
  for msg in ['Test Person','+12025550123','skip']:
   assert await lead_creation.handle(s,msg)
  assert not calls and s.lead_draft['phase']=='review'
  await lead_creation.handle(s,'maybe');assert not calls
  await lead_creation.handle(s,'confirm create');assert len(calls)==1
  await lead_creation.handle(s,'confirm create');assert len(calls)==1
  assert s.lead_draft['phase']=='submitted'
 asyncio.run(run())

def test_changed_form_requires_new_review(monkeypatch):
 async def no_save(*args):raise AssertionError('Must not save changed form')
 monkeypatch.setattr(lead_creation,'save',no_save)
 async def run():
  s=main.Session(worker=Worker(),lead_draft={'phase':'review','signature':'different'})
  await lead_creation.handle(s,'yes')
  assert s.lead_draft['phase']=='review' and 'form changed' in s.messages[-1]['text']
 asyncio.run(run())

def test_creation_data_is_not_sales_qualification_identity():
 async def run():
  s=main.Session(worker=Worker());await lead_creation.begin(s)
  s.messages.append({'role':'user','text':'Test Person'})
  await main.execute(s,'Test Person')
  assert all(t['text']!='Test Person' for t in transcript_of(s.messages))
  assert s.qual_task is None
 asyncio.run(run())

def test_cancel_and_invalid_phone_never_save():
 async def run():
  s=main.Session(worker=Worker(),lead_draft={'phase':'phone','name':'Test'})
  await lead_creation.handle(s,'12345')
  assert s.lead_draft['phase']=='phone'
  await lead_creation.handle(s,'cancel');assert s.lead_draft is None
 asyncio.run(run())

def test_a_question_mid_form_leaves_the_unsaved_lead_and_is_answered(isolated_conversation_model):
 """Live report: during Add Lead, "Explain lead sources" was taken as the customer's name, and
 "explain me every thin in global config" was rejected as a phone number."""
 assert not lead_creation.aside('Rahul Sharma','name') and not lead_creation.aside('Can Yilmaz','name')
 assert not lead_creation.aside('+91 98765 43210','phone') and not lead_creation.aside('rahul@example.com','email')
 for text,phase in [('Explain lead sources','name'),('explain me every thin in global config','phone'),
                    ('what is a lead source?','email'),('lead source kya hai','name')]:
  assert lead_creation.aside(text,phase),text
 isolated_conversation_model['Explain lead sources']={'kind':'product','feature':'lead_sources','topic':'Lead Management','demo':False}
 async def run():
  s=main.Session(worker=Worker(),pending_discovery='pain_points');await lead_creation.begin(s)
  s.messages.append({'id':'u1','role':'user','text':'Explain lead sources'})
  await main.execute(s,'Explain lead sources')
  texts=[m['text'] for m in s.messages]
  assert s.lead_draft is None and "Sure, let's leave the new lead for now. Nothing has been saved." in texts
  assert not any(t.startswith('What is their phone number') for t in texts)
  assert any(m.get('kind')=='product_answer' for m in s.messages)
  # The business question that was open before Add Lead comes back once, in passing.
  assert s.pending_discovery=='pain_points' and s.messages[-1]['text'].startswith('By the way, what is the biggest problem')
  if s.qual_task:s.qual_task.cancel();await asyncio.gather(s.qual_task,return_exceptions=True)
 asyncio.run(run())
