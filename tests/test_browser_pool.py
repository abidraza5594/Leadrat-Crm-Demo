import asyncio
import pytest
from app.browser_pool import WarmBrowser


class Worker:
    def __init__(self):self.started=0;self.closed=False
    async def start(self):self.started+=1
    async def close(self):self.closed=True


def test_prepared_browser_is_handed_out_once_and_next_visitor_gets_fresh_one():
    async def run():
        pool=WarmBrowser(Worker);pool.enabled=True
        pool.prime();first_task=pool.task;pool.prime()
        assert pool.task is first_task
        await first_task
        assert pool.ready()
        first=await pool.take()
        assert first.started==1 and pool.task is None
        await first.close()
        pool.prime();await pool.task
        second=await pool.take()
        assert second is not first and second.started==1
        await second.close();await pool.close()
    asyncio.run(run())


def test_failed_preparation_cleans_up_and_retries_for_visitor():
    async def run():
        workers=[]
        class Failing(Worker):
            async def start(self):raise RuntimeError('CRM unavailable')
        def factory():
            w=Failing() if not workers else Worker();workers.append(w);return w
        pool=WarmBrowser(factory);pool.enabled=True;pool.prime()
        with pytest.raises(RuntimeError):await pool.task
        assert workers[0].closed and not pool.ready()
        assert await pool.take() is workers[1]
        await workers[1].close();await pool.close()
    asyncio.run(run())


def test_shutdown_cleans_up_in_progress_preparation_and_does_not_restart():
    async def run():
        started=asyncio.Event()
        class Slow(Worker):
            async def start(self):started.set();await asyncio.Event().wait()
        worker=Slow();pool=WarmBrowser(lambda:worker);pool.enabled=True;pool.prime()
        await started.wait();await pool.close();pool.prime()
        assert worker.closed and pool.task is None
    asyncio.run(run())


def test_shutdown_closes_unused_ready_browser():
    async def run():
        worker=Worker();pool=WarmBrowser(lambda:worker);pool.enabled=True;pool.prime()
        await pool.task;await pool.close()
        assert worker.closed
    asyncio.run(run())


def test_ready_browser_with_slow_auth_returns_session_token_without_cancelling_boot(monkeypatch):
    from app import main
    async def run():
        release=asyncio.Event()
        async def slow_boot(s):
            await release.wait();s.status='ready'
        monkeypatch.setattr(main,'sessions',{})
        monkeypatch.setattr(main,'create_lock',asyncio.Lock())
        monkeypatch.setattr(main,'boot',slow_boot)
        monkeypatch.setattr(main.browser_pool,'ready',lambda:True)
        snapshot=await asyncio.wait_for(main.create(main.Create(parent_origin=next(iter(main.config.ORIGINS)))),1)
        session=main.sessions[snapshot['id']]
        assert snapshot['token']==session.token and not session.boot.done()
        release.set();await session.boot
        assert session.status=='ready'
        await main.close(session)
    asyncio.run(run())
