"""Recover CRM authentication and replay only read-only navigation, never Save."""
import asyncio
import time
from .browser import DemoError, has_login_credentials

async def restore(s):
    async with s.recovery_lock:
        if await s.worker.signed_in(): return True
        s.status='reconnecting'
        s.say('Reconnecting the CRM. I will return to your demo.')
        started=time.monotonic()
        try:
            if not has_login_credentials() or not await s.worker.login():
                s.status='login_required'
                s.last_error='Automatic CRM sign-in needs valid saved credentials. Your conversation is still here.'
                return False
            if hasattr(s.worker,'restore_checkpoint'):await s.worker.restore_checkpoint()
            if s.lead_draft and s.lead_draft.get('phase')=='review':
                from .lead_creation import prepare
                await prepare(s.worker,s.lead_draft)
                s.lead_draft['signature']=await s.worker.form_signature()
            s.status='ready';s.auth_lost=None;s.last_error=None
            s.say('Signed in again. Your previous demo is restored.')
            if s.timings:s.timings[-1]['crm_recovery_ms']=round((time.monotonic()-started)*1000)
            return True
        except asyncio.CancelledError:raise
        except Exception:
            s.status='ready' if await s.worker.signed_in() else 'login_required'
            s.last_error='CRM reconnected, but the previous demo step could not be restored. No record was saved again.'
            return False

async def read_action(s, action):
    # Calls to this helper are restricted to navigation / unsaved walkthroughs.
    if hasattr(s.worker,'signed_in') and not await s.worker.signed_in():
        if not await restore(s):raise DemoError(s.last_error)
    try: result=await action()
    except asyncio.CancelledError:raise
    except Exception:
        if not hasattr(s.worker,'signed_in') or await s.worker.signed_in():raise
        if not await restore(s):raise DemoError(s.last_error)
        result=await action()  # One bounded retry, only after confirmed auth loss.
    if hasattr(s.worker,'remember_checkpoint'):await s.worker.remember_checkpoint()
    return result
