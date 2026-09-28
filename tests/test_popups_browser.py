"""Real browser checks of source-shaped popup controls (no CRM writes)."""
import asyncio
import pytest
from playwright.async_api import async_playwright
from app.popups import handle_popups,PopupBlocked

def test_confirmations_never_approve_changes():
    async def run():
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(channel='chrome',headless=True)
            page=await browser.new_page()
            fixtures=[
                ('user-confirmation','<button id="deleteNo" onclick="this.parentElement.remove()">No</button><button id="deleteYes" onclick="window.written=true">Yes</button>'),
                ('user-alert-popup','<h4 onclick="this.parentElement.remove()">Cancel</h4><h4 onclick="window.written=true">Override &amp; Assign</h4>'),
                ('save-changes','<a class="ic-close-secondary" onclick="this.parentElement.remove()">Close</a><button onclick="window.written=true">Discard</button><button onclick="window.written=true">Save</button>'),
                ('user-alert-popup','<button onclick="window.written=true">OK</button>'),
            ]
            for tag,content in fixtures:
                await page.set_content('<script>window.written=false</script><'+tag+' style="display:block">'+content+'</'+tag+'>')
                with pytest.raises(PopupBlocked):await handle_popups(page)
                assert await page.evaluate('window.written') is False
            await browser.close()
    asyncio.run(run())
