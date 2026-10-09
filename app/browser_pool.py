"""One fresh preloaded CRM browser; used sessions are never handed to another visitor."""
import asyncio
from contextlib import suppress
from .browser import BrowserWorker


class WarmBrowser:
    def __init__(self,factory=BrowserWorker):
        self.factory=factory;self.task=None;self.enabled=False

    async def _prepare(self):
        worker=self.factory()
        try:
            await worker.start()
            return worker
        except BaseException:
            with suppress(Exception):await worker.close()
            raise

    def prime(self):
        if self.enabled and self.task is None:
            self.task=asyncio.create_task(self._prepare())
            self.task.add_done_callback(lambda t:None if t.cancelled() else t.exception())

    def ready(self):
        return bool(self.task and self.task.done() and not self.task.cancelled() and self.task.exception() is None)

    async def take(self):
        task,self.task=self.task,None
        if task is None:return await self._prepare()
        # A failed idle warm-up must not poison the next visitor's startup.
        if task.done() and (task.cancelled() or task.exception() is not None):
            return await self._prepare()
        return await task

    async def close(self):
        self.enabled=False
        task,self.task=self.task,None
        if task is None:return
        if not task.done():task.cancel()
        try:worker=await task
        except BaseException:return
        with suppress(Exception):await worker.close()
