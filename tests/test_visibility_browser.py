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

BULK_PAGE='''<div class="ag-header-select-all" style="display:inline-block;width:18px;height:18px"><input type="checkbox" style="pointer-events:none"></div>
<div id="bar" hidden><span>10</span><span>Leads Selected</span>
<button class="btn-bulk-black" onclick="window.ran='status'">Bulk Update Status</button>
<button class="btn-bulk-black" onclick="window.ran='reassign'">Reassign Leads</button>
<button id="moreActionsDropdown" class="btn-bulk-black" onclick="openMenu()">More Actions</button></div>
<script>
document.querySelector('.ag-header-select-all').addEventListener('click',()=>{const i=document.querySelector('.ag-header-select-all input');i.checked=!i.checked;document.getElementById('bar').hidden=!i.checked;});
function openMenu(){const c=document.createElement('bs-dropdown-container');c.innerHTML='<button class="btn-bulk-black" onclick="window.ran=1">Bulk WhatsApp</button><button class="btn-bulk-black" onclick="window.ran=2">Bulk Delete</button>';document.body.append(c);}
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelector('bs-dropdown-container')?.remove();});
</script>'''

def test_bulk_walkthrough_points_at_the_action_the_model_chose_and_never_runs_it():
    """Live reports: "bulk lead delete" did not show the select-all, bar and More Actions flow, and "bulk
    assignment" highlighted Bulk Update Status. Which action is meant is now the conversation model's choice
    among the labels read from the page; the walkthrough only shows it."""
    from app.browser import BrowserWorker
    from app.lead_browser import walkthrough
    from app.project import FEATURES
    highlighted="()=>[...document.querySelectorAll('.btn-bulk-black')].filter(b=>b.style.getPropertyPriority('background')==='important').map(b=>b.textContent.trim())"
    async def run():
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(channel='chrome',headless=True)
            page=await browser.new_page()
            offered=[]
            for chosen,expected in [('Bulk Delete','Bulk Delete is highlighted'),('Reassign Leads',"I've highlighted Reassign Leads"),(None,'opened More Actions to show the rest')]:
                await page.set_content(BULK_PAGE)
                w=BrowserWorker();w.page=page
                async def choose(labels,chosen=chosen):
                    offered.append(labels)
                    if chosen is None:raise TimeoutError('model unavailable')
                    return chosen
                w.choose_control=choose
                said=await walkthrough(w,FEATURES['bulk_update'])
                assert expected in said
                assert await page.evaluate(highlighted)==([chosen] if chosen else [])
                assert bool(await page.locator('bs-dropdown-container').count())==(chosen!='Reassign Leads')
                assert await page.evaluate('window.ran') is None  # nothing was run
                await w.leave_screen()
                assert await page.evaluate("()=>!document.querySelector('.ag-header-select-all input').checked && !document.querySelector('bs-dropdown-container')")
            assert offered[0]==['Bulk Update Status','Reassign Leads','Bulk WhatsApp','Bulk Delete']
            await browser.close()
    asyncio.run(run())

def test_endless_decorations_are_held_still_and_transitions_still_run():
    """Live report: the demo lagged. Endless CSS animations kept the hidden CRM browser repainting."""
    from app.browser import STILL_DECORATIONS
    async def run():
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(channel='chrome',headless=True)
            context=await browser.new_context();await context.add_init_script(STILL_DECORATIONS)
            page=await context.new_page()
            await page.set_content('<style>@keyframes blink{50%{opacity:0}} .blink{animation:blink 1s infinite}'
                                   '.slide{transition:opacity 5s} .slide.go{opacity:0}</style><h6 class="blink">Breached</h6><div class="slide">x</div>')
            await page.evaluate("document.querySelector('.slide').classList.add('go')")
            await page.wait_for_timeout(1600)
            states=await page.evaluate("()=>document.getAnimations().map(a=>[a.effect.target.className,a.playState,a.currentTime])")
            assert ['blink','paused',0] in states  # held at its first, visible frame
            assert any(c=='slide go' and s=='running' for c,s,_ in states)  # a finite transition is untouched
            await browser.close()
    asyncio.run(run())
