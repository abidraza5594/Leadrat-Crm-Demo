"""Source-reviewed popup policy; an OK label is not evidence of a safe action."""
import re

class PopupBlocked(Exception):pass

async def handle_popups(page):
    handled=[]
    for _ in range(4):
        containers=page.locator('user-confirmation,user-alert-popup,save-changes')
        visible=[containers.nth(i) for i in range(await containers.count()) if await containers.nth(i).is_visible()]
        if not visible:
            # This exact account-configuration notice closes with modalRef.hide()
            # in leads-actions; a generic OK elsewhere may approve a mutation.
            notices=page.locator('.modal-content').filter(has=page.get_by_role('button',name='Ok, Got it',exact=True))
            notices=[notices.nth(i) for i in range(await notices.count()) if await notices.nth(i).is_visible()]
            if len(notices)==1:
                await notices[0].get_by_role('button',name='Ok, Got it',exact=True).click()
                raise PopupBlocked('The CRM says this communication option needs account setup or administrator access. I closed the notice; no message was sent.')
            return handled
        popup=visible[-1]
        tag=await popup.evaluate('el=>el.tagName.toLowerCase()')
        if tag=='save-changes':
            close=popup.locator('a.ic-close-secondary')
            if await close.count()==1:await close.click()
            raise PopupBlocked('The CRM asked about unsaved changes. I kept the changes and stopped navigation; I did not save or discard them.')
        cancel=popup.locator('#deleteNo') if tag=='user-confirmation' else popup.get_by_text(re.compile(r'^\s*(cancel|no|stay|go back)\s*$',re.I))
        choices=[cancel.nth(i) for i in range(await cancel.count()) if await cancel.nth(i).is_visible()]
        if len(choices)!=1:raise PopupBlocked('A CRM confirmation needs review. I did not click its confirmation button.')
        await choices[0].click()
        # Do not retry the original operation: a confirmation can guard a write.
        raise PopupBlocked('The CRM requested confirmation. I cancelled that pending operation; no save, send, delete or ownership confirmation was approved.')
    raise PopupBlocked('Multiple CRM popups are blocking the screen. The demo stopped safely.')
