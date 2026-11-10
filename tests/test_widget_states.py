"""Widget states that must clear themselves (real browser, stubbed API, no CRM)."""
import asyncio
import mimetypes
from pathlib import Path
from playwright.async_api import async_playwright


def test_form_closes_once_registered_and_step_card_clears_the_screen():
    """Live report: after a reconnect the details form stayed open although the visitor was registered, and
    the "What Beacon is doing" card stayed over the live CRM after the demo had finished."""
    async def run():
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(channel='chrome',headless=True)
            page=await browser.new_page(viewport={'width':1440,'height':900})
            await page.add_init_script("localStorage.setItem('beacon.voice','off')")
            turns=[]
            state={'id':'1','token':'test','status':'ready','busy':False,'messages':[],'steps':[],
                   'registration_required':True,'registration_status':'needed','registration_accepted':False,'registration_error':None}
            async def route(r):
                path=r.request.url.split('http://localhost:9876')[-1].split('?')[0]
                if path.startswith('/api/'):
                    if path.endswith('/screen') or r.request.method=='DELETE':await r.fulfill(status=204);return
                    if path.endswith('/visitor'):
                        # The server accepts the details, but the reply never arrives intact.
                        state.update(registration_status='created',registration_accepted=True)
                        await r.fulfill(status=502,json={'detail':'Bad gateway'});return
                    if path.endswith('/turn'):
                        turns.append(r.request.post_data_json['message']);await r.fulfill(status=202,json={'accepted':True});return
                    await r.fulfill(json=state);return
                f=Path('web')/path.lstrip('/')
                await r.fulfill(content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream',body=f.read_bytes())
            await page.route('http://localhost:9876/**',route)
            await page.goto('http://localhost:9876/widget.html')
            await page.locator('#message').fill('Show leads');await page.locator('#send').click()
            await page.locator('#visitor-form').wait_for(state='visible')
            await page.locator('[name=name]').fill('Visitor QA');await page.locator('[name=email]').fill('qa@example.invalid')
            await page.locator('#visitor-phone').fill('9876543210')
            await page.locator('#visitor-form button[type=submit]').click()
            await page.locator('#visitor-form').wait_for(state='hidden',timeout=5000)
            for _ in range(40):
                if turns:break
                await asyncio.sleep(.05)
            assert turns==['Show leads']
            state.update(steps=[{'title':'Bulk lead actions','status':'running','detail':'Opening'}])
            await page.locator('#activity').wait_for(state='visible')
            await page.wait_for_timeout(7000)
            assert await page.locator('#activity').is_visible()  # still working: the card stays
            state.update(steps=[{'title':'Bulk lead actions','status':'verified','detail':'Done'}])
            await page.wait_for_function("document.querySelector('#steps li')?.className==='step-verified'")
            await page.locator('#activity').wait_for(state='hidden',timeout=8000)
            await browser.close()
    asyncio.run(run())
