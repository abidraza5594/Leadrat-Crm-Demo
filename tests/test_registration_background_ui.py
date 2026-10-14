"""Real widget with delayed backend acknowledgement/save; no external CRM writes."""
import asyncio
import json
import mimetypes
from pathlib import Path
from playwright.async_api import async_playwright


def test_form_hides_before_ack_demo_runs_during_save_and_failure_can_be_corrected():
    async def run():
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(channel='chrome',headless=True)
            page=await browser.new_page()
            await page.add_init_script("localStorage.setItem('beacon.voice','off')")
            received=asyncio.Event();ack=asyncio.Event();turns=[];posts=[]
            state={'id':'1','token':'test','status':'ready','busy':False,'messages':[],
                   'steps':[],'registration_required':True,'registration_status':'needed',
                   'registration_accepted':False,'registration_error':None}
            async def route(r):
                path=r.request.url.split('http://localhost:9876')[-1].split('?')[0]
                if path.startswith('/api/'):
                    if path.endswith('/screen') or r.request.method=='DELETE':
                        await r.fulfill(status=204);return
                    if path.endswith('/visitor'):
                        posts.append(r.request.post_data_json);received.set();await ack.wait()
                        state.update(registration_status='saving',registration_accepted=True,registration_error=None)
                        await r.fulfill(status=202,json={'status':'saving','accepted':True});return
                    if path.endswith('/turn'):
                        turns.append(r.request.post_data_json['message'])
                        await r.fulfill(status=202,json={'accepted':True});return
                    await r.fulfill(json=state);return
                f=Path('web')/path.lstrip('/')
                await r.fulfill(content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream',body=f.read_bytes())
            await page.route('http://localhost:9876/**',route)
            try:
                await page.goto('http://localhost:9876/widget.html')
                await page.locator('#message').fill('Show leads')
                await page.locator('#send').click()
                await page.locator('#visitor-form').wait_for(state='visible')
                await page.locator('[name=name]').fill('Visitor QA')
                await page.locator('[name=email]').fill('qa@example.invalid')
                await page.locator('#visitor-phone').fill('9876543210')
                await page.locator('#visitor-form button[type=submit]').click()
                await asyncio.wait_for(received.wait(),3)
                assert not ack.is_set() and await page.locator('#visitor-form').is_hidden()
                assert await page.locator('#registration-notice').is_hidden()
                ack.set()
                for _ in range(30):
                    if turns:break
                    await asyncio.sleep(.05)
                assert turns==['Show leads'] and state['registration_status']=='saving'
                assert await page.locator('#registration-notice').is_hidden()
                assert await page.locator('#registration-notice-text').text_content()==''
                state.update(registration_status='failed',registration_error='Please update your phone number.')
                await page.locator('#registration-retry').wait_for(state='visible')
                assert await page.locator('#visitor-form').is_hidden()
                await page.locator('#registration-retry').click()
                assert await page.locator('[name=name]').input_value()=='Visitor QA'
                assert await page.locator('[name=email]').input_value()=='qa@example.invalid'
                await page.locator('#visitor-phone').fill('9876543211')
                assert await page.locator('#visitor-form button[type=submit]').is_enabled()
                await page.locator('#visitor-form button[type=submit]').click()
                await page.locator('#visitor-form').wait_for(state='hidden')
                assert len(posts)==2 and turns==['Show leads']
                state.update(registration_status='created',registration_error=None)
                await page.locator('#registration-notice').wait_for(state='hidden')
            finally:
                ack.set();await browser.close()
    asyncio.run(run())
