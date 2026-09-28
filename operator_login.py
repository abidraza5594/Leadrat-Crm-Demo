"""Operator-only: sign the hidden demo browser in to the test CRM once.

Opens a visible Chrome window on the CRM login page. Sign in normally, including any
two-factor step. When the CRM opens, the login is saved to .browser/crm-state.json and
the window closes. Each hidden demo browser reuses it, and a session that is already
waiting picks it up automatically. The file holds auth tokens: keep it on this machine.
"""
import asyncio
from contextlib import suppress
from app import config
from app.browser import BrowserWorker, device_location

async def main():
    worker=BrowserWorker()
    print('Opening the CRM login window...')
    await worker.start(headless=False)
    try:
        if await worker.signed_in():
            await worker.save_state()
            print('Signed in. The login is saved for the hidden demo browser:',config.BROWSER_STATE)
            return
        location=await device_location()
        if location:await worker.context.set_geolocation(location)
        print('Sign in to the test CRM in the Chrome window (waiting up to 10 minutes)...')
        for _ in range(1200):
            await asyncio.sleep(0.5)
            if worker.page.is_closed():raise SystemExit('The login window was closed before sign-in finished.')
            if await worker.authenticated():
                await worker.save_state()
                print('Signed in. The login is saved for the hidden demo browser:',config.BROWSER_STATE)
                return
        raise SystemExit('Timed out waiting for sign-in.')
    finally:
        # The operator may already have closed the window.
        with suppress(Exception):await worker.close()

if __name__=='__main__':
    asyncio.run(main())
