"""Source-reviewed popup policy; an OK label is not evidence of a safe action."""
import re
from .visibility import VISIBLE_JS, visible

class PopupBlocked(Exception):pass

# Every popup handled below is one of these containers or sits inside a .modal-content. One in-page check
# answers the common case (nothing open) before every walkthrough step, instead of several round trips.
ANY_POPUP='()=>{'+VISIBLE_JS+"return [...document.querySelectorAll('user-confirmation,user-alert-popup,save-changes,.modal-content')].some(visible);}"

async def handle_popups(page):
    handled=[]
    if not await page.evaluate(ANY_POPUP):return handled
    for _ in range(4):
        visible_popups=await visible(page.locator('user-confirmation,user-alert-popup,save-changes'))
        if not visible_popups:
            # This exact account-configuration notice closes with modalRef.hide()
            # in leads-actions; a generic OK elsewhere may approve a mutation.
            notices=await visible(page.locator('.modal-content').filter(has=page.get_by_role('button',name='Ok, Got it',exact=True)))
            if len(notices)==1:
                await notices[0].get_by_role('button',name='Ok, Got it',exact=True).click()
                raise PopupBlocked('The CRM says this communication option needs account setup or administrator access. I closed the notice; no message was sent.')
            return handled
        popup=visible_popups[-1]
        tag=await popup.evaluate('el=>el.tagName.toLowerCase()')
        if tag=='save-changes':
            close=popup.locator('a.ic-close-secondary')
            if await close.count()==1:await close.click()
            raise PopupBlocked('The CRM asked about unsaved changes. I kept the changes and stopped navigation; I did not save or discard them.')
        cancel=popup.locator('#deleteNo') if tag=='user-confirmation' else popup.get_by_text(re.compile(r'^\s*(cancel|no|stay|go back)\s*$',re.I))
        choices=await visible(cancel)
        if len(choices)!=1:raise PopupBlocked('A CRM confirmation needs review. I did not click its confirmation button.')
        await choices[0].click()
        # Do not retry the original operation: a confirmation can guard a write.
        raise PopupBlocked('The CRM requested confirmation. I cancelled that pending operation; no save, send, delete or ownership confirmation was approved.')
    raise PopupBlocked('Multiple CRM popups are blocking the screen. The demo stopped safely.')
