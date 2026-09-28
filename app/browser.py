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
from . import guide

class DemoError(Exception):pass

NAV='a.nav-item,.module-navbar a,[data-ai-nav-route]'
LOGIN_FIELDS='#inpLoginPassword,input[type="password"]'
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
        self.context.on('page',lambda page: asyncio.create_task(page.close()) if page!=self.page else None)
        # With a saved login, open the app itself (it lands on Leads); the CRM sends an invalid login to /login.
        await self.page.goto(config.CRM_ORIGIN+'/' if self.state_mtime else config.CRM_URL,wait_until='domcontentloaded',timeout=60000)
        await self.settle()
        if await self.signed_in():await self.save_state()
        elif has_login_credentials():await self.login()
        else:self.login_problem='No saved CRM login was found and no test credentials were supplied.'

    async def settle(self,timeout=25000):
        # Wait for either the app or the login form. The hosted CRM can render the form for a few
        # seconds before its guard redirects (or refreshes) a saved login, so keep waiting for the app then.
        either=self.page.locator(NAV).first.or_(self.page.locator(LOGIN_FIELDS).first)
        try:await either.first.wait_for(state='visible',timeout=timeout)
        except Exception:return
        if self.state_mtime and not await self.page.locator(NAV).count():
            try:await self.page.locator(NAV).first.wait_for(state='visible',timeout=10000)
            except Exception:pass

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
        location_banner=page.get_by_text(re.compile(r'Location permission is required',re.I))
        for _ in range(40):
            await asyncio.sleep(0.5)
            if await self.authenticated():
                await self.save_state();return True
            path=urlsplit(page.url).path
            if 'two-factor' in path:
                self.login_problem='The CRM asked for two-factor verification. Sign in once with login.ps1.';return False
            try:
                if await location_banner.count():
                    self.login_problem='The CRM requires device location. Enable Windows Location Services (LOCAL_DEVICE_LOCATION=true) or sign in once with login.ps1.';return False
                if await page.get_by_text(re.compile(r'Account (has been|is) locked|reset your password',re.I)).count():
                    self.login_problem='The CRM refused the sign-in (account locked or password reset required).';return False
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
        return bool(self.page and not self.page.is_closed() and self.browser and self.browser.is_connected())

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
        try:return await self.page.locator(NAV).count()>0
        except Exception:return None

    async def signed_in(self):
        for _ in range(8):
            result=await self.authenticated()
            if result is not None:return result
            await asyncio.sleep(0.25)
        return False

    async def screenshot(self):
        if not config.SANDBOX_CONFIRMED or not await self.authenticated():return None
        # Screenshots are read-only and must not wait behind the entire action sequence.
        # No login pixels, raw DOM or customer records sent to the language model.
        # caret='initial' avoids injecting a hide-caret stylesheet into the CRM on every frame.
        return await self.page.screenshot(type='jpeg',quality=70,timeout=5000,caret='initial',animations='allow')

    async def open_module(self,feature):
        if not config.SANDBOX_CONFIRMED:raise DemoError('A test-data sandbox must be configured before showing CRM screens.')
        if not await self.signed_in():raise DemoError("The demo browser is not signed in to the test CRM yet, so I can't show this screen.")
        module=feature['module']
        label={'task':'Tasks','properties':'Properties'}.get(module,module.title())
        async with self.lock:
            page=self.page
            await self.check_popups()
            # Never leave an operator-entered dirty form or dismiss its confirmation.
            own_changes=self.demo_form_signature is not None and self.demo_form_signature==await self.form_signature()
            if await page.locator('form.ng-dirty').count() and not own_changes:raise DemoError('An unsaved form contains input outside this walkthrough. I kept it intact; close it before starting another demo.')
            # Close only reviewed, unchanged demo dialogs before changing screens.
            for selector in ['leads-template-share .ic-close-secondary','leads-email-share .ic-close-secondary','leads-advance-filter .ic-close-secondary']:
                controls=page.locator(selector)
                if await controls.count()==1 and await controls.is_visible():await controls.click()
            no_email=page.locator('.modal-content').filter(has_text='There is no email ID associated with')
            if await no_email.count()==1:
                cancel=no_email.get_by_text(re.compile(r'^\s*Cancel\s*$'))
                if await cancel.count()==1:await cancel.click()
            preview=page.locator('lead-preview')
            if await preview.count():
                back=preview.locator('.ic-circle-chevron-left').first
                if await back.is_visible():await back.click()
            if own_changes:
                discard=page.locator('save-changes').get_by_role('button',name=re.compile(r'^Discard$',re.I))
                if await discard.count()==1 and await discard.is_visible():await discard.click()
            await self.check_popups()
            choices=[page.locator('a.nav-item').filter(has_text=re.compile(r'^\s*'+re.escape(label)+r'\s*$',re.I)),
                page.locator('.module-navbar a').filter(has_text=re.compile(r'^\s*'+re.escape(label)+r'\s*$',re.I)),
                page.locator(f'[data-ai-nav-route="{module}"]')]
            target=None
            for candidate in choices:
                for i in range(await candidate.count()):
                    element=candidate.nth(i)
                    if await element.is_visible() and await element.get_attribute('aria-disabled')!='true':target=element;break
                if target is not None:break
            if target is None:raise DemoError(f'{label} is not visible or permitted in this sandbox account.')
            await guide.click(target,f'Click {label} in the left menu')
            await page.wait_for_url(lambda url:urlsplit(str(url)).path.startswith('/'+module),timeout=12000)
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
                    await guide.click(dropdown,'Open the menu next to Add Lead')
                    candidates=page.get_by_role('option',name=re.compile(r'bulk\s+upload',re.I))
            # Angular may expose the route before permissions and controls finish rendering.
            try:await candidates.first.wait_for(state='visible',timeout=10000)
            except Exception:raise DemoError('The expected entry control did not become visible. No alternate action was attempted.')
            visible=[candidates.nth(i) for i in range(await candidates.count()) if await candidates.nth(i).is_visible()]
            if len(visible)!=1:raise DemoError('The expected entry control is not uniquely visible. No alternate action was attempted.')
            await guide.click(visible[0],'Click Add Lead' if feature['id']=='add_lead' else 'Choose Bulk Upload')
            if feature['id']=='add_lead':
                await page.locator('input[formcontrolname="name"],input[formcontrolname="firstName"]').first.wait_for(state='visible',timeout=10000)
                fields=page.locator('input[formcontrolname="name"],input[formcontrolname="firstName"],input[formcontrolname="email"]')
                labels=[]
                for i in range(min(await fields.count(),8)):
                    field=fields.nth(i)
                    if await field.is_visible():
                        # UI highlighting only; no form values read or written.
                        labels.append({'name':'Customer name','firstName':'Customer name','email':'Email'}.get(await field.get_attribute('formcontrolname'),'Contact field'))
                        await guide.point(field,'This is the '+labels[-1]+' field')
                return labels
            await page.wait_for_url('**/leads/bulk-upload*',timeout=10000)
            return []

    async def close(self):
        self.closed=True
        # Keep tokens the CRM refreshed during this session for the next hidden browser.
        if self.context and await self.authenticated():await self.save_state()
        if self.context:await self.context.close()
        if self.browser:await self.browser.close()
        if self.pw:await self.pw.stop()
