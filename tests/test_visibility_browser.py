"""The one-round-trip visibility check agrees with Playwright's is_visible() (real browser)."""
import asyncio
from playwright.async_api import async_playwright
from app.visibility import visible, any_visible
from app.popups import handle_popups

CASES='''
<div class="t">plain</div>
<div class="t" style="display:none">none</div>
<div class="t" style="visibility:hidden">hidden</div>
<div class="t" style="width:0;height:0;overflow:hidden">zero</div>
<div class="t" style="opacity:0">transparent</div>
<div class="t" style="position:absolute;left:-5000px">offscreen</div>
<div class="t" style="display:contents"><span>child</span></div>
<div class="t" style="display:contents"><span style="display:none">hidden child</span></div>
<details><summary>s</summary><div class="t">closed details</div></details>
<span class="t"></span>
<lead-preview class="t"><div>custom element with block child</div></lead-preview>
<div style="visibility:hidden"><div class="t" style="visibility:visible">visible inside hidden</div></div>
'''

def test_leaving_a_lead_waits_until_its_preview_has_closed():
    """Back-to-back record walkthroughs: a closing preview must not be taken for an open lead."""
    from app.browser import BrowserWorker
    async def run():
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(channel='chrome',headless=True)
            page=await browser.new_page()
            await page.set_content('<lead-preview style="display:block"><i class="ic-circle-chevron-left" style="display:inline-block;width:20px;height:20px"'
                ' onclick="setTimeout(()=>this.parentElement.remove(),400)"></i></lead-preview>')
            w=BrowserWorker();w.page=page
            await w.leave_screen()
            assert await page.locator('lead-preview').count()==0
            await browser.close()
    asyncio.run(run())

def test_single_round_trip_matches_playwright_and_skips_idle_popup_scan():
    async def run():
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(channel='chrome',headless=True)
            page=await browser.new_page()
            await page.set_content(CASES)
            items=page.locator('.t')
            expected=[i for i in range(await items.count()) if await items.nth(i).is_visible()]
            shown=await visible(items)
            assert [await s.evaluate('e=>[...document.querySelectorAll(".t")].indexOf(e)') for s in shown]==expected
            assert await any_visible(items) and not await any_visible(page.locator('[style*="display:none"]'))
            # Nothing open: one in-page check, no clicks.
            assert await handle_popups(page)==[]
            await browser.close()
    asyncio.run(run())
