import asyncio
from types import SimpleNamespace
import pytest
from app.browser_pool import WarmBrowser


class Worker:
    def __init__(self):self.started=0;self.closed=False;self.saved=None;self.dead=False
    async def start(self):self.started+=1
    def alive(self):return not self.dead
    async def save_state(self):pass
    async def close(self,save=True):self.closed=True;self.saved=save


def test_dead_idle_browser_is_replaced_instead_of_handed_out():
    async def run():
        workers=[]
        def factory():workers.append(Worker());return workers[-1]
        pool=WarmBrowser(factory);pool.enabled=True;pool.prime()
        await pool.task;workers[0].dead=True
        assert not pool.ready()
        worker=await pool.take()
        assert worker is workers[1] and worker.started==1
        await asyncio.sleep(0)
        assert workers[0].closed and workers[0].saved is False
        await worker.close();await pool.close()
    asyncio.run(run())


def test_stale_idle_browser_is_swapped_in_background_without_a_gap():
    async def run():
        workers=[];release=asyncio.Event()
        class Slow(Worker):
            async def start(self):
                if workers.index(self):await release.wait()
                self.started+=1
        def factory():workers.append(Slow());return workers[-1]
        pool=WarmBrowser(factory,refresh_after=0,check_every=0.01);pool.enabled=True;pool.prime()
        await pool.task
        while len(workers)<2:await asyncio.sleep(0.01)
        # While the replacement starts, the visitor-facing browser stays ready.
        assert pool.ready() and pool.task.result() is workers[0]
        release.set()
        while pool.task.result() is workers[0]:await asyncio.sleep(0.01)
        assert pool.task.result() is workers[1]
        while not workers[0].closed:await asyncio.sleep(0.01)
        assert workers[0].saved is False  # the replacement already holds the newest login
        await pool.close()
        assert all(w.closed for w in workers)
    asyncio.run(run())


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
        request=SimpleNamespace(headers={})
        snapshot=await asyncio.wait_for(main.create(main.Create(parent_origin=next(iter(main.config.ORIGINS))),request),1)
        session=main.sessions[snapshot['id']]
        assert snapshot['token']==session.token and not session.boot.done()
        release.set();await session.boot
        assert session.status=='ready'
        await main.close(session)
    asyncio.run(run())
