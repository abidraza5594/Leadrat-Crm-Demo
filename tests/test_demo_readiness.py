import asyncio
import pytest

from app.browser import BrowserWorker,LOGIN_BLOCKED,LOGIN_FIELDS,NAV



def test_password_help_is_not_a_lockout_error():
    assert not LOGIN_BLOCKED.search('Click here to reset your password')
    assert LOGIN_BLOCKED.search('Your account has been locked')
    assert LOGIN_BLOCKED.search('You must reset your password')

def test_auth_requires_visible_workspace_without_login_form():
    from playwright.async_api import async_playwright
    hidden={'nav':'display:none','password':'visibility:hidden'}
    cases=[([False],[],False),([True],[True],False),([False,True],[False],True),([],[],False)]
    async def run():
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(channel='chrome',headless=True)
            page=await browser.new_page();worker=BrowserWorker();worker.page=page
            results=[]
            for nav,password,_ in cases:
                await page.set_content(''.join('<a class="nav-item" style="'+('' if v else hidden['nav'])+'">Leads</a>' for v in nav)
                    +''.join('<input type="password" style="'+('' if v else hidden['password'])+'">' for v in password))
                results.append(await worker.authenticated())
            await browser.close()
            return results
    assert asyncio.run(run())==[expected for *_,expected in cases]
