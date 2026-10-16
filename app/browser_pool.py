"""One fresh preloaded CRM browser; used sessions are never handed to another visitor."""
import asyncio
import time
from contextlib import suppress
from .browser import BrowserWorker

# An idle browser is replaced in the background before its CRM login can go stale, and at once if it
# crashed, so a visitor never waits for Chrome to start or for the CRM to sign in again.
REFRESH_AFTER=600
CHECK_EVERY=20

def healthy(worker):
    return getattr(worker,'alive',lambda:True)()

class WarmBrowser:
    def __init__(self,factory=BrowserWorker,refresh_after=REFRESH_AFTER,check_every=CHECK_EVERY):
        self.factory=factory;self.task=None;self.enabled=False
        self.refresh_after=refresh_after;self.check_every=check_every
        self.since=0.0;self.keeper=None;self.replacing=None;self.retiring=set()

    async def _prepare(self):
        worker=self.factory()
        try:
            await worker.start()
            if hasattr(worker,'prepare_frame'):await worker.prepare_frame()
            return worker
        except BaseException:
            with suppress(Exception):await worker.close()
            raise

    def _spawn(self):
        task=asyncio.create_task(self._prepare())
        task.add_done_callback(lambda t:None if t.cancelled() else t.exception())
        return task

    def prime(self):
        if self.enabled and self.task is None:
            self.task=self._spawn();self.since=time.monotonic()
        if self.enabled and self.task is not None and (self.keeper is None or self.keeper.done()):
            self.keeper=asyncio.create_task(self._maintain())

    def ready(self):
        task=self.task
        return bool(task and task.done() and not task.cancelled() and task.exception() is None and healthy(task.result()))

    def _retire(self,worker,save=True):
        async def shut():
            with suppress(Exception):
                if save:await worker.close()
                else:await worker.close(save=False)
        task=asyncio.create_task(shut());self.retiring.add(task);task.add_done_callback(self.retiring.discard)

    async def _maintain(self):
        """Replace a crashed or stale idle browser; a visitor arriving meanwhile still gets the old one."""
        while self.enabled and self.task is not None:
            await asyncio.sleep(self.check_every)
            task=self.task
            if task is None or not task.done():continue
            worker=None if task.cancelled() or task.exception() is not None else task.result()
            if worker is not None and healthy(worker) and time.monotonic()-self.since<self.refresh_after:
                # Keep the frame shown first to the next visitor current.
                if hasattr(worker,'prepare_frame'):await worker.prepare_frame()
                continue
            # Persist the login the idle CRM page refreshed, so the replacement starts signed in.
            if worker is not None and healthy(worker) and hasattr(worker,'save_state'):
                with suppress(Exception):await worker.save_state()
            self.replacing=replacement=self._spawn();started=time.monotonic()
            try:await replacement
            except asyncio.CancelledError:raise  # close() shuts down the replacement as well
            except Exception:self.replacing=None;continue
            self.replacing=None
            if self.task is task:
                self.task=replacement;self.since=started
                if worker is not None:self._retire(worker,save=False)
            else:
                # Handed to a visitor meanwhile; the next one is prepared when that session ends.
                self._retire(replacement.result())

    async def take(self):
        task,self.task=self.task,None
        if task is None:return await self._prepare()
        # A failed idle warm-up must not poison the next visitor's startup.
        if task.done() and (task.cancelled() or task.exception() is not None):
            return await self._prepare()
        worker=await task
        if not healthy(worker):
            self._retire(worker,save=False)
            return await self._prepare()
        return worker

    async def close(self):
        self.enabled=False
        keeper,self.keeper=self.keeper,None
        if keeper and not keeper.done():
            keeper.cancel()
            with suppress(BaseException):await keeper
        for task in (self.task,self.replacing):
            if task is None:continue
            if not task.done():task.cancel()
            try:worker=await task
            except BaseException:continue
            with suppress(Exception):await worker.close()
        self.task=self.replacing=None
        if self.retiring:await asyncio.wait(list(self.retiring),timeout=10)
