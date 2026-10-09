import asyncio
from app import main

def test_product_navigation_does_not_start_sales_extraction(monkeypatch):
 class Worker:
  async def open_module(self,f):return 'Open'
 async def run():
  s=main.Session(worker=Worker())
  for text in ['hi','show leads','thank you']:
   await main.execute(s,text)
   assert s.qual_task is None
 asyncio.run(run())

def test_customer_reply_still_schedules_extraction():
 async def run():
  s=main.Session(pending_discovery='monthly_leads')
  await main.execute(s,'20k')
  assert s.qual_task and not s.qual_task.done()
  assert s.discovery_answers['monthly_leads']==20000
  s.qual_task.cancel()
 asyncio.run(run())

def test_pure_navigation_keeps_existing_qualification_task():
 class Worker:
  async def open_module(self,f):return 'Open'
 async def run():
  s=main.Session(worker=Worker())
  task=asyncio.create_task(asyncio.sleep(10));s.qual_task=task
  await main.execute(s,'show leads')
  assert s.qual_task is task and not task.cancelled()
  task.cancel()
 asyncio.run(run())


def test_extraction_waits_until_interactive_turn_finishes(monkeypatch):
 async def run():
  called=asyncio.Event()
  async def extract(s):called.set()
  monkeypatch.setattr(main,'requalify',extract)
  monkeypatch.setattr(main,'discover',lambda s:None)
  s=main.Session(pending_discovery='monthly_leads')
  await main.execute(s,'20k')
  interactive=asyncio.create_task(asyncio.sleep(10));s.task=interactive
  try:
   await asyncio.sleep(.8)
   assert not called.is_set()
   interactive.cancel()
   try:await interactive
   except asyncio.CancelledError:pass
   s.last_completed=main.time.monotonic()
   await asyncio.wait_for(called.wait(),2)
  finally:
   interactive.cancel()
   if s.qual_task:s.qual_task.cancel()
 asyncio.run(run())
