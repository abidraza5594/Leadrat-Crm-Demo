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
