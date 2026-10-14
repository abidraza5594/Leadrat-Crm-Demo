"""Exercise the CRM duplicate modal boundary with real browser events, no CRM writes."""
import asyncio
from types import SimpleNamespace
import pytest
from playwright.async_api import async_playwright
from app import lead_creation

def test_duplicate_cancel_then_corrected_save():
    async def run():
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(channel='chrome',headless=True)
            page=await browser.new_page();posts=[]
            async def route(r):
                if '/api/v1/lead' in r.request.url:
                    posts.append(r.request.post_data)
                    await r.fulfill(json={'succeeded':True,'data':'12345678-1234-1234-1234-123456789abc'})
                else:await r.fulfill(content_type='text/html',body='''
                    <button onclick="if(!window.corrected){document.querySelector('user-alert-popup').hidden=false}else{fetch('/api/v1/lead',{method:'POST',body:'corrected'}).then(()=>location.href='/leads/manage-leads')}">Save</button>
                    <user-alert-popup hidden><h3>Duplicate Lead Detected!</h3>
                    <h4 onclick="this.parentElement.hidden=true">Cancel</h4>
                    <h4 onclick="fetch('/api/v1/lead',{method:'POST',body:'BAD DUPLICATE'})">Proceed With Adding</h4></user-alert-popup>''')
            await page.route('http://crm.test/**',route)
            await page.goto('http://crm.test/leads/add-lead')
            async def check_popups():pass
            worker=SimpleNamespace(page=page,lock=asyncio.Lock(),check_popups=check_popups,demo_form_signature='old')
            try:
                with pytest.raises(lead_creation.LeadNotSaved) as caught:
                    await lead_creation.save(worker,{'name':'Duplicate QA'})
                assert caught.value.code=='duplicate' and posts==[]
                assert not await page.locator('user-alert-popup').is_visible()
                await page.evaluate('window.corrected=true')
                data={'name':'Corrected QA'}
                await lead_creation.save(worker,data)
                assert len(posts)==1 and data['created_id']=='12345678-1234-1234-1234-123456789abc'
            finally:await browser.close()
    asyncio.run(run())
