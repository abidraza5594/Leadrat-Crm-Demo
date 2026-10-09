import asyncio,time
from types import SimpleNamespace
from app import main

def test_slow_crm_refresh_does_not_block_session_poll(monkeypatch):
 async def slow(s):await asyncio.sleep(60)
 monkeypatch.setattr(main,'refresh_status',slow)
 async def run():
  s=main.Session(status='ready');main.sessions[s.id]=s
  req=SimpleNamespace(headers={'x-beacon-token':s.token})
  try:
   result=await asyncio.wait_for(main.state(s.id,req),0.25)
   first=s.refresh_task
   assert result['status']=='ready'
   await main.state(s.id,req)
   assert s.refresh_task is first
  finally:
   s.refresh_task.cancel();main.sessions.pop(s.id,None)
 asyncio.run(run())
