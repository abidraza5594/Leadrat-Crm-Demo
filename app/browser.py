"""Server-owned isolated Chromium. Only reviewed UI navigation, never model selectors."""
import asyncio
import os
import re
import hashlib
import json
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
from . import config
from .device_location import cached_windows_location, known_location
from .popups import handle_popups, PopupBlocked
from .visibility import VISIBLE_JS, visible

class DemoError(Exception):pass

NAV='a.nav-item,.module-navbar a,[data-ai-nav-route]'
LOGIN_FIELDS='#inpLoginPassword,input[type="password"]'
CLOSE_TIMEOUT=3.0
LOGIN_BLOCKED=re.compile(r'\baccount (?:has been|is) locked\b|\b(?:must|need to|required to) reset (?:your )?password\b|\bpassword reset (?:is )?required\b',re.I)

# One round trip instead of one per matching element: the sidebar has dozens of links and this check
# runs before every screen frame. Same visibility rule as Playwright's is_visible().
SIGNED_IN_SCRIPT='({nav,password})=>{'+VISIBLE_JS+"""
    if([...document.querySelectorAll(password)].some(visible))return false;
    return [...document.querySelectorAll(nav)].some(visible);
}"""
# Operator-supplied test credentials stay in process memory so the hidden browser can sign in
# again when the saved login expires. They are removed from the environment (child processes).
_LOGIN=(os.environ.pop('BEACON_LOGIN_USER','').strip(),os.environ.pop('BEACON_LOGIN_PASSWORD',''))

def has_login_credentials():return all(_LOGIN)

async def device_location():
    return await cached_windows_location() if config.LOCAL_DEVICE_LOCATION else None

class BrowserWorker:
    def __init__(self):
        self.pw=None;self.browser=None;self.context=None;self.page=None
        self.lock=asyncio.Lock()
        self.closed=False
        self.native_popup=None
        self.demo_form_signature=None
        # Operator-facing reason when automatic sign-in did not complete; never includes field values.
        self.login_problem=None
        self.state_mtime=0.0
        self.checkpoint=None
        self.preview_row_id=None
        self.walkthrough_feature=None
        self.location_section=None
        self.crashed=False
        self.failure_event=asyncio.Event()
        self.on_failure=None
        self._checkpoint_document=None
        # A frame captured while the browser waited for its visitor; the first screen request returns it
        # at once, and every later request captures live.
        self.ready_frame=None

    def signal_failure(self):
        if self.closed:return
        self.failure_event.set()
        if self.on_failure:self.on_failure()

    def frame_navigated(self,frame):
        if frame==self.page.main_frame and urlsplit(frame.url).path.startswith('/login') and self.checkpoint:
            self.signal_failure()

    def page_crashed(self,*args):
        self.crashed=True
        self.signal_failure()

    async def screen_fingerprint(self):
        # Compare locally, without storing customer text or sending it to the model.
        text=await self.page.locator('body').inner_text()
        return hashlib.sha256((text+await self.form_signature()).encode()).hexdigest()

    async def remember_checkpoint(self):
        if not await self.authenticated():return
        parsed=urlsplit(self.page.url)
        if '{0.scheme}://{0.netloc}'.format(parsed)!=config.CRM_ORIGIN:return
        values=[]
        if self.demo_form_signature and self.demo_form_signature==await self.form_signature():
            values=await self.page.locator('input[formcontrolname],textarea[formcontrolname]').evaluate_all(
                "els=>els.filter(e=>e.type!=='password' && !['radio','checkbox','file','hidden'].includes(e.type)).map(e=>({name:e.getAttribute('formcontrolname'),value:e.value})).filter(e=>e.value).slice(0,40)")
        self.checkpoint={'url':self.page.url,'row_id':self.preview_row_id,
            'feature':self.walkthrough_feature,'section':self.location_section,'fields':values,
            'scroll':await self.page.evaluate('({x:scrollX,y:scrollY})')}
        self.checkpoint['fingerprint']=await self.screen_fingerprint()
        if self._checkpoint_document:
            try:await self._checkpoint_document.dispose()
            except Exception:pass
        self._checkpoint_document=await self.page.evaluate_handle('document')

    async def restore_checkpoint(self):
        point=self.checkpoint
        if not point:return
        parsed=urlsplit(point['url'])
        if '{0.scheme}://{0.netloc}'.format(parsed)!=config.CRM_ORIGIN or parsed.path.startswith('/login'):
            raise DemoError('Invalid saved demo location.')
        same_document=False
        if self._checkpoint_document:
            try:same_document=await self._checkpoint_document.evaluate('d=>d===document')
            except Exception:pass
        same_url=self.page.url==point['url']
        if same_url and same_document and await self.signed_in():
            await self.check_popups()
            if self.preview_row_id==point.get('row_id') and point.get('fingerprint')==await self.screen_fingerprint():
                await self.page.evaluate('p=>scrollTo(p.x,p.y)',point['scroll'])
                return  # Verified screen survived the timeout; no reload or repeated click.
        # A fresh document at the saved URL can be restored directly. A partial,
        # changed document must be reset before replaying reviewed navigation.
        if not same_url or same_document:
            await self.page.goto(point['url'],wait_until='domcontentloaded',timeout=30000)
        await self.settle(timeout=8000)
        if not await self.signed_in():raise DemoError('CRM sign-in expired again.')
        if urlsplit(self.page.url).path!=parsed.path:raise DemoError('The previous page is no longer available.')
        if point.get('row_id'):
            # AG Grid's getRowId uses the CRM record ID; never substitute the first lead.
            selected=self.page.locator('[row-id='+json.dumps(point['row_id'])+']').filter(has=self.page.locator('lead-name-section'))
            try:await selected.first.wait_for(state='visible',timeout=8000)
            except Exception:raise DemoError('The previous lead is not visible after sign-in. I did not open a different lead.')
            if await selected.count()!=1:raise DemoError('The previous lead could not be identified uniquely.')
            await selected.locator('lead-name-section .header-6.text-secondary').click()
            self.preview_row_id=point['row_id']
        if point.get('feature'):
            from .lead_browser import walkthrough
            await walkthrough(self,point['feature'])
        for item in point.get('fields',[]):
            # Fixed formcontrolname values captured from this page, escaped as CSS strings.
            field=self.page.locator('[formcontrolname='+json.dumps(item['name'])+']')
            if await field.count()!=1 or not await field.is_visible():raise DemoError('The previous form fields could not be restored.')
            await field.fill(item['value'])
        if point.get('fields'):await self.remember_demo_form()
        if point.get('section'):
            section=self.page.get_by_text(point['section'],exact=True)
            if await section.count():await section.first.scroll_into_view_if_needed()
        else:await self.page.evaluate('p=>scrollTo(p.x,p.y)',point['scroll'])

    async def form_signature(self):
        values=await self.page.locator('input,textarea,select,ng-select').evaluate_all("els=>els.map(el=>[el.tagName,el.getAttribute('formcontrolname'),el.value,el.checked,el.tagName==='NG-SELECT'?el.innerText:''])")
        return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()

    async def remember_demo_form(self):
        self.demo_form_signature=await self.form_signature()

    async def dismiss_native(self,dialog):
        self.native_popup=dialog.type
        await dialog.dismiss()

    async def check_popups(self):
        if self.native_popup:
            self.native_popup=None
            raise DemoError('The CRM displayed a browser dialog. I dismissed it and stopped the pending step without approving a change.')
        try:await handle_popups(self.page)
        except PopupBlocked as exc:raise DemoError(str(exc))

    async def start(self,headless=None):
        self.closed=False
        self.crashed=False
        self.failure_event.clear()
        headless=config.HEADLESS if headless is None else headless
        self.pw=await async_playwright().start()
        # Hidden by default: the visitor sees this browser only as frames inside the website popup.
        self.browser=await self.pw.chromium.launch(headless=headless,channel='chrome',args=['--disable-notifications','--mute-audio'])
        options={'viewport':{'width':1280,'height':800},'accept_downloads':False}
        if headless:
            # The CRM records the browser name at login; report ordinary Chrome, not "HeadlessChrome".
            options['user_agent']=f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self.browser.version} Safari/537.36'
        try:
            self.state_mtime=config.BROWSER_STATE.stat().st_mtime if config.BROWSER_STATE.is_file() else 0.0
            self.context=await self.browser.new_context(**options,storage_state=config.BROWSER_STATE if self.state_mtime else None)
        except Exception:
            # An unreadable saved login must not block the demo; it is replaced after the next sign-in.
            self.state_mtime=0.0
            self.context=await self.browser.new_context(**options)
        # Permissions do not fabricate coordinates. Actual device geolocation may require operator approval.
        await self.context.grant_permissions(['geolocation'],origin=config.CRM_ORIGIN)
        if config.LOCAL_DEVICE_LOCATION and known_location():await self.context.set_geolocation(known_location())
        await self.context.route('**/*',self.guard)
        self.page=await self.context.new_page()
        self.page.set_default_timeout(8000)
        self.page.on('dialog',self.dismiss_native)
        self.page.on('crash',self.page_crashed)
        self.page.on('close',lambda *args:self.signal_failure())
        self.page.on('framenavigated',self.frame_navigated)
        self.browser.on('disconnected',lambda *args:self.signal_failure())
        self.context.on('page',lambda page: asyncio.create_task(page.close()) if page!=self.page else None)
        # With a saved login, open the app itself (it lands on Leads); the CRM sends an invalid login to /login.
        target=config.CRM_ORIGIN+'/' if self.state_mtime else config.CRM_URL
        if self.checkpoint and self.state_mtime:
            saved=urlsplit(self.checkpoint['url'])
            if '{0.scheme}://{0.netloc}'.format(saved)==config.CRM_ORIGIN and not saved.path.startswith('/login'):
                target=self.checkpoint['url']
        await self.page.goto(target,wait_until='domcontentloaded',timeout=60000)
        await self.settle()
        if await self.signed_in():await self.save_state()
        elif has_login_credentials():await self.login()
        else:self.login_problem='No saved CRM login was found and no test credentials were supplied.'

    async def settle(self,timeout=25000):
        # Continue when usable UI arrives, not after a fixed saved-token grace period.
        either=self.page.locator(NAV).first.or_(self.page.locator(LOGIN_FIELDS).first)
        try:await either.first.wait_for(state='visible',timeout=timeout)
        except Exception:return

    async def login(self):
        """One sign-in attempt with the operator's test credentials; returns True when the CRM opens."""
        page=self.page;username,password=_LOGIN
        self.login_problem=None
        if '/login' not in urlsplit(page.url).path:
            await page.goto(config.CRM_URL,wait_until='domcontentloaded',timeout=60000);await self.settle()
        try:await page.locator(LOGIN_FIELDS).first.wait_for(state='visible',timeout=20000)
        except Exception:
            self.login_problem='The CRM login form did not appear.';return False
        location=await device_location()
        if location:await self.context.set_geolocation(location)
        try:
            user=page.locator('#inpLoginName,input[formcontrolname="username"],input[formcontrolname="userName"],input[name="username"]')
            if await user.count()==0:user=page.locator('input[type="text"]')
            await user.first.fill(username)
            await page.locator(LOGIN_FIELDS).first.fill(password)
            button=page.get_by_role('button',name=re.compile(r'^(log\s*in|sign\s*in)$',re.I))
            if await button.count()==0:button=page.locator('h4.btn-accent-green-xl').filter(has_text=re.compile(r'log\s*in',re.I))
            await button.first.click()
        except Exception:
            # Never log field values or raw errors that could contain records.
            self.login_problem='The CRM login form could not be filled.';return False
        # DOM readiness follows the CRM response. No half-second polling delay.
        try:
            outcome=await page.wait_for_function("""({nav,password})=>{
                const visible=e=>!!(e && e.getClientRects().length && getComputedStyle(e).visibility!=='hidden');
                const text=document.body?.innerText || '';
                if(location.pathname.includes('two-factor'))return 'mfa';
                if(/Location permission is required/i.test(text))return 'location';
                if(/account (?:has been|is) locked|(?:must|need to|required to) reset (?:your )?password|password reset (?:is )?required/i.test(text))return 'blocked';
                if(!location.pathname.startsWith('/login') && ![...document.querySelectorAll(password)].some(visible) && [...document.querySelectorAll(nav)].some(visible))return 'ready';
                return false;
            }""",arg={'nav':NAV,'password':LOGIN_FIELDS},timeout=20000,polling='raf')
            result=await outcome.json_value();await outcome.dispose()
            if result=='ready':
                await self.save_state();return True
            if result=='mfa':self.login_problem='The CRM asked for two-factor verification. Sign in once with login.ps1.';return False
            if result=='location':self.login_problem='The CRM requires device location. Enable Windows Location Services (LOCAL_DEVICE_LOCATION=true) or sign in once with login.ps1.';return False
            if result=='blocked':self.login_problem='The CRM refused the sign-in (account locked or password reset required).';return False
        except Exception:pass
        self.login_problem='Automatic sign-in did not complete. Check the test credentials or sign in once with login.ps1.'
        return False

    async def save_state(self):
        """Persist the CRM login so the next hidden browser starts signed in."""
        try:
            config.BROWSER_STATE.parent.mkdir(exist_ok=True)
            temporary=config.BROWSER_STATE.with_suffix('.tmp')
            await self.context.storage_state(path=temporary)
            os.replace(temporary,config.BROWSER_STATE)
            self.state_mtime=config.BROWSER_STATE.stat().st_mtime
        except Exception:pass

    async def adopt_saved_login(self):
        """Pick up a login the operator completed with login.ps1 while this session waited."""
        try:
            mtime=config.BROWSER_STATE.stat().st_mtime
            if mtime<=self.state_mtime:return False
            self.state_mtime=mtime
            data=json.loads(config.BROWSER_STATE.read_text('utf-8'))
        except (OSError,ValueError):return False
        async with self.lock:
            if data.get('cookies'):await self.context.add_cookies(data['cookies'])
            if '{0.scheme}://{0.netloc}'.format(urlsplit(self.page.url))!=config.CRM_ORIGIN:
                await self.page.goto(config.CRM_URL,wait_until='domcontentloaded',timeout=60000)
            for origin in data.get('origins',[]):
                if origin.get('origin')==config.CRM_ORIGIN:
                    await self.page.evaluate("items=>{for(const i of items)localStorage.setItem(i.name,i.value)}",origin.get('localStorage',[]))
            await self.page.goto(config.CRM_ORIGIN+'/',wait_until='domcontentloaded',timeout=60000)
            await self.settle()
        return await self.signed_in()

    def alive(self):
        return bool(not self.crashed and self.page and not self.page.is_closed() and self.browser and self.browser.is_connected())

    async def guard(self,route):
        request=route.request
        # A navigation may never leave the designated CRM origin, including redirects.
        if self.page and request.is_navigation_request() and request.frame==self.page.main_frame:
            if '{0.scheme}://{0.netloc}'.format(urlsplit(request.url))!=config.CRM_ORIGIN:
                await route.abort();return
        await route.continue_()

    async def authenticated(self):
        """True/False when known; None while a navigation makes the page briefly unreadable."""
        if not self.page or self.page.is_closed():return False
        if urlsplit(self.page.url).path.startswith('/login'):return False
        try:return bool(await self.page.evaluate(SIGNED_IN_SCRIPT,{'nav':NAV,'password':LOGIN_FIELDS}))
        except Exception:return None

    async def signed_in(self):
        for _ in range(8):
            result=await self.authenticated()
            if result is not None:return result
            await asyncio.sleep(0.25)
        return False

    async def prepare_frame(self):
        try:self.ready_frame=await self.capture()
        except Exception:self.ready_frame=None

    async def screenshot(self):
        frame,self.ready_frame=self.ready_frame,None
        if frame and config.SANDBOX_CONFIRMED and self.alive():return frame
        return await self.capture()

    async def capture(self):
        if not config.SANDBOX_CONFIRMED or not await self.authenticated():return None
        # Screenshots are read-only and must not wait behind the entire action sequence.
        # No login pixels, raw DOM or customer records sent to the language model.
        # caret='initial' avoids injecting a hide-caret stylesheet into the CRM on every frame.
        return await self.page.screenshot(type='jpeg',quality=70,timeout=5000,caret='initial',animations='allow')

    async def leave_screen(self):
        """Close reviewed demo dialogs before changing screens; never touch an operator's unsaved input."""
        page=self.page
        await self.check_popups()
        # Never leave an operator-entered dirty form or dismiss its confirmation.
        own_changes=self.demo_form_signature is not None and self.demo_form_signature==await self.form_signature()
        if await page.locator('form.ng-dirty').count() and not own_changes:raise DemoError('An unsaved form contains input outside this walkthrough. I kept it intact; close it before starting another demo.')
        # Close only reviewed, unchanged demo dialogs before changing screens.
        for selector in ['leads-template-share .ic-close-secondary','leads-email-share .ic-close-secondary','leads-advance-filter .ic-close-secondary']:
            controls=page.locator(selector)
            if await controls.count()==1 and await controls.is_visible():await controls.click()
        # This CRM version exposes Cancel on the advanced-filter sheet rather
        # than the older close icon. Leaving the sheet open blocks navigation.
        filters=page.locator('leads-advance-filter')
        if await filters.count()==1 and await filters.is_visible():
            cancel=filters.get_by_text(re.compile(r'^\s*Cancel\s*$',re.I))
            if await cancel.count()==1 and await cancel.is_visible():await cancel.click()
        no_email=page.locator('.modal-content').filter(has_text='There is no email ID associated with')
        if await no_email.count()==1:
            cancel=no_email.get_by_text(re.compile(r'^\s*Cancel\s*$'))
            if await cancel.count()==1:await cancel.click()
        preview=page.locator('lead-preview')
        if await preview.count():
            back=preview.locator('.ic-circle-chevron-left').first
            if await back.is_visible():
                await back.click()
                # The closing preview stays in the page briefly; the next walkthrough would take it for
                # an open lead, skip choosing one and then miss its tabs.
                try:await preview.first.wait_for(state='hidden',timeout=5000)
                except Exception:pass
        if own_changes:
            discard=page.locator('save-changes').get_by_role('button',name=re.compile(r'^Discard$',re.I))
            if await discard.count()==1 and await discard.is_visible():await discard.click()
        await self.check_popups()
        return own_changes

    async def open_location(self,location):
        """Open a page from the screen map generated out of the CRM code and highlight the chosen section."""
        if not config.SANDBOX_CONFIRMED:raise DemoError('A test-data sandbox must be configured before showing CRM screens.')
        if not await self.signed_in():raise DemoError("The demo browser is not signed in to the test CRM yet, so I can't show this screen.")
        path=location['path']
        if not path.startswith('/') or '://' in path:raise DemoError('That screen location is not valid.')
        async with self.lock:
            await self.leave_screen()
            self.preview_row_id=None;self.walkthrough_feature=None;self.location_section=location.get('section')
            page=self.page
            if urlsplit(page.url).path.rstrip('/')!=path.rstrip('/'):
                # In-app navigation through the CRM's own router, the same as following one of its links.
                await page.evaluate("p=>{history.pushState(null,'',p);dispatchEvent(new PopStateEvent('popstate',{state:null}))}",path)
                # The address changes at once; let the router render and apply its guards before checking it.
                try:await page.wait_for_load_state('networkidle',timeout=6000)
                except Exception:pass
                if urlsplit(page.url).path.rstrip('/')!=path.rstrip('/'):
                    await page.goto(config.CRM_ORIGIN+path,wait_until='domcontentloaded',timeout=30000)
                    await self.settle()
                if urlsplit(page.url).path.rstrip('/')!=path.rstrip('/'):
                    raise DemoError(location['page']+' is not available for this account, so the CRM opened another page.')
            if await page.get_by_text(re.compile('access denied|not authorized',re.I)).count():raise DemoError('The CRM denied access to this screen.')
            if not await self.signed_in():raise DemoError('The CRM session expired. The demo stopped.')
            self.demo_form_signature=None
            section=location.get('section')
            # Said to the visitor after the page was verified: "Leads › Manage Leads" reads as "the Manage Leads page".
            name=location['page'].split(' › ')[-1]
            name='the '+name+('' if name.lower().endswith('page') else ' page')
            if not section:return "I've opened "+name+' for you.'
            target=page.get_by_text(section,exact=True)
            try:await target.first.wait_for(state='visible',timeout=6000)
            except Exception:return "I've opened "+name+', but its "'+section+"\" section isn't shown for this account."
            for element in (await visible(target))[:1]:
                await element.scroll_into_view_if_needed()
                await element.evaluate("el => { el.style.outline='3px solid #18aa83'; el.style.outlineOffset='4px'; }")
            return "I've opened "+name+' and highlighted its "'+section+'" section.'

    async def open_module(self,feature):
        if not config.SANDBOX_CONFIRMED:raise DemoError('A test-data sandbox must be configured before showing CRM screens.')
        if not await self.signed_in():raise DemoError("The demo browser is not signed in to the test CRM yet, so I can't show this screen.")
        module=feature['module']
        label={'task':'Tasks','properties':'Properties'}.get(module,module.title())
        async with self.lock:
            page=self.page
            own_changes=await self.leave_screen()
            self.preview_row_id=None;self.walkthrough_feature=None;self.location_section=None
            if module=='leads' and urlsplit(page.url).path.rstrip('/')=='/leads/manage-leads':
                listing=page.locator('manage-leads')
                if await listing.count()==1 and await listing.is_visible():
                    self.demo_form_signature=None
                    return 'Leads is already open. The visible workspace was verified.'
            choices=[page.locator('a.nav-item').filter(has_text=re.compile(r'^\s*'+re.escape(label)+r'\s*$',re.I)),
                page.locator('.module-navbar a').filter(has_text=re.compile(r'^\s*'+re.escape(label)+r'\s*$',re.I)),
                page.locator(f'[data-ai-nav-route="{module}"]')]
            # The authenticated shell can appear before the tenant's module menu finishes loading.
            try:await choices[0].or_(choices[1]).or_(choices[2]).first.wait_for(state='visible',timeout=8000)
            except Exception:pass
            target=None
            for candidate in choices:
                for element in await visible(candidate):
                    if await element.get_attribute('aria-disabled')!='true':target=element;break
                if target is not None:break
            if target is None:raise DemoError(f'{label} is not visible or permitted in this sandbox account.')
            await target.click()
            # /leads/add-lead also starts with /leads; wait for the actual list
            # before trying to open another control from its toolbar.
            await page.wait_for_url(lambda url:(urlsplit(str(url)).path.rstrip('/')=='/leads/manage-leads'
                if module=='leads' else urlsplit(str(url)).path.startswith('/'+module)),timeout=20000)
            if await page.get_by_text(re.compile('access denied|not authorized',re.I)).count():raise DemoError('The CRM denied access to this screen.')
            if not await self.signed_in():raise DemoError('The CRM session expired. The demo stopped.')
            self.demo_form_signature=None
            return f'{label} is open. The visible module navigation and destination were verified.'

    async def open_feature(self,feature):
        if feature['id'] not in {'add_lead','bulk_upload'}:return []
        async with self.lock:
            page=self.page
            pattern=r'^\s*(add\s+(new\s+)?lead|new\s+lead)\s*$' if feature['id']=='add_lead' else r'^\s*(bulk\s+upload|import\s+leads)\s*$'
            # Fixed allowed button names, never generic model-supplied click selectors.
            candidates=page.get_by_role('button',name=re.compile(pattern,re.I)).or_(page.get_by_role('link',name=re.compile(pattern,re.I)))
            if feature['id']=='add_lead':
                # The sidebar flyout can also show Add Lead while the pointer is over Leads.
                # Prefer the reviewed main-toolbar control instead of conflating two valid entries.
                primary=page.locator('.btn-left-dropdown').filter(has_text=re.compile(pattern,re.I))
                try:await primary.first.wait_for(state='visible',timeout=8000)
                except Exception:pass
                if await primary.count()==1 and await primary.is_visible():candidates=primary
            elif await candidates.count()==0:
                dropdown=page.locator('.btn-right-dropdown ng-select')
                with_timeout=dropdown.first
                try:await with_timeout.wait_for(state='visible',timeout=8000)
                except Exception:raise DemoError('The bulk-upload menu is not available in this account.')
                if await dropdown.count()==1 and await dropdown.is_visible():
                    await dropdown.click()
                    candidates=page.get_by_role('option',name=re.compile(r'bulk\s+upload',re.I))
            # Angular may expose the route before permissions and controls finish rendering.
            try:await candidates.first.wait_for(state='visible',timeout=10000)
            except Exception:raise DemoError('The expected entry control did not become visible. No alternate action was attempted.')
            shown=await visible(candidates)
            if len(shown)!=1:raise DemoError('The expected entry control is not uniquely visible. No alternate action was attempted.')
            await shown[0].click()
            if feature['id']=='add_lead':
                await page.locator('input[formcontrolname="name"],input[formcontrolname="firstName"]').first.wait_for(state='visible',timeout=20000)
                fields=page.locator('input[formcontrolname="name"],input[formcontrolname="firstName"],input[formcontrolname="email"]')
                labels=[]
                for i in range(min(await fields.count(),8)):
                    field=fields.nth(i)
                    if await field.is_visible():
                        # UI highlighting only; no form values read or written.
                        await field.scroll_into_view_if_needed()
                        labels.append({'name':'Customer name','firstName':'Customer name','email':'Email'}.get(await field.get_attribute('formcontrolname'),'Contact field'))
                return labels
            await page.wait_for_url('**/leads/bulk-upload*',timeout=10000)
            return []

    async def reopen(self):
        """Replace a crashed browser, retaining this visitor's verified checkpoint."""
        await self.close()
        await self.start()

    async def close(self,save=True):
        self.closed=True
        # Keep tokens the CRM refreshed during this session for the next hidden browser.
        # A retired idle browser skips this: its replacement may already hold newer tokens.
        from contextlib import suppress
        with suppress(Exception):
            async with asyncio.timeout(CLOSE_TIMEOUT):
                if save and self.context and await self.authenticated():await self.save_state()
        # A failed page/state operation must never strand the Chromium process
        # or its Playwright transport after the session ends.
        for resource,method in ((self.context,'close'),(self.browser,'close'),(self.pw,'stop')):
            if resource:
                with suppress(Exception):
                    async with asyncio.timeout(CLOSE_TIMEOUT):await getattr(resource,method)()
        self.context=self.browser=self.pw=None
