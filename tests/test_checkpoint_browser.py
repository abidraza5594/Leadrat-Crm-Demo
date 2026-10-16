"""Checkpoint reuse against real DOM navigation, with no remote CRM calls."""
import asyncio
import pytest
from playwright.async_api import async_playwright
from app.browser import BrowserWorker,DemoError
from app import config


def test_checkpoint_reuses_only_verified_unchanged_screen(monkeypatch):
    origin='https://checkpoint.invalid'
    monkeypatch.setattr(config,'CRM_ORIGIN',origin)
    async def run():
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(channel='chrome',headless=False)
            try:
                page=await browser.new_page();loads=[]
                async def fixture(route):
                    loads.append(route.request.url)
                    await route.fulfill(content_type='text/html',body='<a class="nav-item">Leads</a><p id="screen">Notes</p><input formcontrolname="name"><div style="height:2000px"></div>')
                await page.route('**/*',fixture)
                await page.goto(origin+'/leads')
                w=BrowserWorker();w.page=page;w.browser=browser
                await page.evaluate('scrollTo(0,200)')
                await w.remember_checkpoint()
                await page.evaluate('scrollTo(0,600)')
                await w.restore_checkpoint()
                assert len(loads)==1 and await page.evaluate('scrollY')==200
                # A partially changed screen may not claim to be the old checkpoint.
                await page.locator('#screen').evaluate("e=>e.textContent='Wrong screen'")
                await w.restore_checkpoint()
                assert len(loads)==2 and await page.locator('#screen').inner_text()=='Notes'
                # A replacement document already at the destination needs no second reload.
                await w.remember_checkpoint()
                await page.reload()
                await w.restore_checkpoint()
                assert len(loads)==3
                # Fingerprints cannot permit an out-of-tenant destination.
                w.checkpoint['url']='https://elsewhere.invalid/leads'
                with pytest.raises(DemoError,match='Invalid saved'):await w.restore_checkpoint()
                assert len(loads)==3
            finally:await browser.close()
    asyncio.run(run())
