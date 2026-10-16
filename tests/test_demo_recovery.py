import asyncio
import time
import pytest
from app import main,recovery

class Worker:
    def __init__(self):
        self.live=True;self.auth=True;self.logins=0;self.reopens=0;self.restores=0
        self.checkpoint={'page':'leads','record':'same-lead','tab':'Status'};self.screen=self.checkpoint.copy()
    def alive(self):return self.live
    async def signed_in(self):return self.auth
    async def authenticated(self):return self.auth
    async def adopt_saved_login(self):return False
    async def login(self):self.auth=True;self.logins+=1;return True
    async def reopen(self):self.live=True;self.auth=True;self.reopens+=1;self.screen={'page':'home'}
    async def restore_checkpoint(self):self.screen=self.checkpoint.copy();self.restores+=1
    async def remember_checkpoint(self):self.checkpoint=self.screen.copy()

def test_timeout_restores_same_record_then_continues_once():
    async def run():
        s=main.Session(worker=Worker());calls=[]
        async def action():
            calls.append(s.worker.screen.copy())
            if len(calls)==1:s.worker.screen={'page':'partial'};raise TimeoutError()
            assert s.worker.screen['record']=='same-lead'
            s.worker.screen['tab']='Notes';return 'Notes open'
        assert await recovery.read_action(s,action)=='Notes open'
        assert len(calls)==2 and s.worker.restores==1 and s.worker.logins==0
        assert s.worker.checkpoint['tab']=='Notes'
    asyncio.run(run())

def test_crashed_browser_keeps_conversation_and_checkpoint():
    async def run():
        s=main.Session(worker=Worker());s.worker.live=False;s.worker.auth=False;s.messages=[{'text':'existing conversation'}]
        assert await recovery.read_action(s,lambda:asyncio.sleep(0,result=s.worker.screen))==s.worker.checkpoint
        assert s.worker.reopens==1 and s.worker.restores==1
        assert s.messages[0]['text']=='existing conversation' and s.status=='ready'
    asyncio.run(run())

def test_recovery_timeout_is_bounded_and_does_not_claim_success(monkeypatch):
    monkeypatch.setattr(recovery,'RECOVERY_TIMEOUT',.01)
    async def run():
        s=main.Session(worker=Worker())
        async def stuck():await asyncio.Event().wait()
        s.worker.restore_checkpoint=stuck
        assert not await recovery.restore(s,force=True)
        assert s.status=='error' and not any('restored.' in m['text'] for m in s.messages)
    asyncio.run(run())

def test_failed_recovery_does_not_retry_forever(monkeypatch):
    monkeypatch.setattr(recovery,'has_login_credentials',lambda:True)
    async def run():
        s=main.Session(worker=Worker());s.worker.auth=False
        async def bad_login():s.worker.logins+=1;return False
        s.worker.login=bad_login
        for _ in range(5):assert not await recovery.restore(s)
        assert s.worker.logins==3
    asyncio.run(run())

def test_second_timeout_does_not_loop():
    async def run():
        s=main.Session(worker=Worker());calls=[]
        async def action():calls.append(1);raise TimeoutError()
        with pytest.raises(TimeoutError):await recovery.read_action(s,action)
        assert len(calls)==2 and s.worker.restores==1
    asyncio.run(run())

def test_active_demo_not_expired_by_absolute_age_or_inflight_work():
    async def run():
        s=main.Session();now=time.monotonic();s.created=now-3600
        assert not main.session_expired(s,now)
        s.touched=now-1000
        assert main.session_expired(s,now)
        s.task=asyncio.create_task(asyncio.sleep(10))
        assert not main.session_expired(s,now)
        s.task.cancel()
        await asyncio.gather(s.task,return_exceptions=True)
    asyncio.run(run())

def test_background_crash_recovery_starts_without_action():
    async def run():
        s=main.Session(worker=Worker());s.status='ready';s.worker.live=False
        await main.refresh_status(s);assert s.relogin
        await s.relogin
        assert s.status=='ready' and s.worker.screen==s.worker.checkpoint
    asyncio.run(run())


def test_login_event_interrupts_pending_read_without_waiting_for_its_timeout(monkeypatch):
    monkeypatch.setattr(recovery,'has_login_credentials',lambda:True)
    async def run():
        w=Worker();w.failure_event=asyncio.Event();s=main.Session(worker=w)
        calls=0;cancelled=asyncio.Event()
        async def read():
            nonlocal calls
            calls+=1
            if calls==1:
                w.auth=False;w.failure_event.set()
                try:await asyncio.Event().wait()
                finally:cancelled.set()
            return 'resumed'
        assert await asyncio.wait_for(recovery.read_action(s,read),.5)=='resumed'
        assert cancelled.is_set() and calls==2 and w.logins==1
        assert not w.failure_event.is_set()
    asyncio.run(run())


def test_cancelling_read_cleans_up_action_and_does_not_recover():
    async def run():
        w=Worker();w.failure_event=asyncio.Event();s=main.Session(worker=w)
        started=asyncio.Event();cancelled=asyncio.Event()
        async def read():
            started.set()
            try:await asyncio.Event().wait()
            finally:cancelled.set()
        task=asyncio.create_task(recovery.read_action(s,read));await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert cancelled.is_set() and w.restores==0
    asyncio.run(run())


def test_confirmed_login_event_bypasses_poll_debounce(monkeypatch):
    monkeypatch.setattr(main,'has_login_credentials',lambda:True)
    monkeypatch.setattr(recovery,'has_login_credentials',lambda:True)
    async def run():
        s=main.Session(worker=Worker());s.status='ready';s.worker.auth=False
        s.auth_checked=time.monotonic()
        await main.refresh_status(s,immediate=True)
        assert s.relogin is not None
        await s.relogin
        assert s.status=='ready' and s.worker.logins==1
    asyncio.run(run())


def test_browser_crash_is_detected_even_when_page_is_not_closed():
    from app.browser import BrowserWorker
    from types import SimpleNamespace
    w=BrowserWorker();w.page=SimpleNamespace(is_closed=lambda:False)
    w.browser=SimpleNamespace(is_connected=lambda:True);notifications=[]
    w.on_failure=lambda:notifications.append(True)
    assert w.alive()
    w.page_crashed()
    assert not w.alive() and w.failure_event.is_set() and notifications==[True]
    w.closed=True;w.signal_failure()
    assert notifications==[True]
