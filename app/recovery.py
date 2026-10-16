"""Recover CRM authentication and replay only read-only navigation, never Save."""
import asyncio
import time
import httpx
from playwright.async_api import TimeoutError as BrowserTimeout, Error as BrowserError
from .browser import DemoError, has_login_credentials

RECOVERY_TIMEOUT=45
MAX_ATTEMPTS=3

def transient(exc):
    return isinstance(exc,(TimeoutError,BrowserTimeout,httpx.TransportError)) or (
        isinstance(exc,BrowserError) and any(code in str(exc) for code in (
            'net::ERR_CONNECTION','net::ERR_NETWORK','net::ERR_INTERNET_DISCONNECTED','Target page, context or browser has been closed')))

async def restore(s,force=False):
    async with s.recovery_lock:
        alive=not hasattr(s.worker,'alive') or s.worker.alive()
        if alive and await s.worker.signed_in() and not force:return True
        if s.recovery_attempts>=MAX_ATTEMPTS:
            s.last_error='The CRM is still unavailable. Please try again shortly.'
            return False
        s.recovery_attempts+=1;s.recovery_checked=time.monotonic()
        s.status='reconnecting'
        s.say('Reconnecting the CRM. I will return to your demo.')
        started=time.monotonic()
        signed_in_again=False
        try:
            async with asyncio.timeout(RECOVERY_TIMEOUT):
                if not alive:
                    await s.worker.reopen()
                if not await s.worker.signed_in():
                    if not has_login_credentials() or not await s.worker.login():
                        s.status='login_required'
                        s.last_error='Automatic CRM sign-in needs valid saved credentials. Your conversation is still here.'
                        return False
                    signed_in_again=True
                if hasattr(s.worker,'restore_checkpoint'):await s.worker.restore_checkpoint()
                if s.lead_draft and s.lead_draft.get('phase')=='review':
                    from .lead_creation import prepare
                    await prepare(s.worker,s.lead_draft)
                    s.lead_draft['signature']=await s.worker.form_signature()
                if hasattr(s.worker,'remember_checkpoint'):await s.worker.remember_checkpoint()
                if hasattr(s.worker,'failure_event'):s.worker.failure_event.clear()
            s.status='ready';s.auth_lost=None;s.last_error=None
            s.recovery_attempts=0
            s.say(('Signed in again. ' if signed_in_again else '')+'Your previous demo is restored.')
            if s.timings:s.timings[-1]['crm_recovery_ms']=round((time.monotonic()-started)*1000)
            return True
        except asyncio.CancelledError:
            s.status='login_required'
            raise
        except Exception:
            s.status='error'
            s.last_error='The previous demo could not be restored yet. Your conversation is preserved.'
            return False

async def read_action(s, action):
    # Calls to this helper are restricted to navigation / unsaved walkthroughs.
    if (hasattr(s.worker,'alive') and not s.worker.alive()) or (hasattr(s.worker,'signed_in') and not await s.worker.signed_in()):
        if not await restore(s):raise DemoError(s.last_error)
    async def run_read():
        event=getattr(s.worker,'failure_event',None)
        if event is None:return await action()
        operation=asyncio.create_task(action())
        failed=asyncio.create_task(event.wait())
        try:
            done,_=await asyncio.wait((operation,failed),return_when=asyncio.FIRST_COMPLETED)
            if operation in done:return await operation
            raise TimeoutError('CRM connection interrupted during read-only navigation.')
        finally:
            for task in (operation,failed):
                if not task.done():task.cancel()
            await asyncio.gather(operation,failed,return_exceptions=True)
    try: result=await run_read()
    except asyncio.CancelledError:raise
    except Exception as exc:
        dead=hasattr(s.worker,'alive') and not s.worker.alive()
        logged_out=hasattr(s.worker,'signed_in') and not await s.worker.signed_in()
        if not (dead or logged_out or transient(exc)):raise
        if not await restore(s,force=True):raise DemoError(s.last_error)
        result=await run_read()  # One bounded retry of a read-only action; never a Save.
    if hasattr(s.worker,'remember_checkpoint'):await s.worker.remember_checkpoint()
    return result
