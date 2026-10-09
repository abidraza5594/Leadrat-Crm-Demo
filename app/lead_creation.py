"""Confirmed single-lead creation through the reviewed CRM form."""
import re
from urllib.parse import urlsplit
from .browser import DemoError

CONFIRM={'yes','confirm','confirm create','yes create lead','create it','haan','haan save karo'}
CANCEL={'no','cancel','cancel lead','stop','nahi','mat karo'}

async def begin(s):
    s.lead_draft={'phase':'name'}
    s.pending_discovery=None;s.offer=None
    s.say('Let us create a lead here. What is the customer’s full name?')

async def handle(s,message):
    d=s.lead_draft
    if not d:return False
    text=message.strip();low=text.lower().rstrip('.!')
    if low in CANCEL:
        s.lead_draft=None
        s.say('Lead creation cancelled. No additional Save will be attempted.')
        return True
    if d['phase'] in {'submitted','done'}:
        s.say('This creation request has already been submitted. Check the Leads list before starting another, to avoid a duplicate.')
        return True
    if d['phase']=='name':
        name=re.sub(r'^name\s*:\s*','',text,flags=re.I)
        if len(name)>75 or not re.fullmatch(r"[^\W\d_][\w .'-]*",name) or re.search(r'\b(show|open|how|delete|save|ignore)\b',name,re.I):
            s.say('Please give only the customer’s name, or say cancel to leave lead creation.');return True
        d['name']=name;d['phase']='phone'
        s.say('What is their phone number, including country code—for example +91 followed by the number?');return True
    if d['phase']=='phone':
        phone=re.sub(r'[\s()-]','',text)
        if not re.fullmatch(r'\+[1-9]\d{6,14}',phone):
            s.say('Please include + and the country code. I will not guess the country or number.');return True
        d['phone']=phone;d['phase']='email'
        s.say('What is their email address? Say skip if you do not have it.');return True
    if d['phase']=='email':
        if low not in {'skip','none','no email','nahi'} and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',text):
            s.say('Please give a valid email address, or say skip.');return True
        d['email']='' if low in {'skip','none','no email','nahi'} else text
        defaults=await prepare(s.worker,d)
        d['signature']=await s.worker.form_signature();d['phase']='review'
        s.say(f"Ready to create: {d['name']}; phone {d['phone']}; email {d['email'] or 'not provided'}. {defaults} Please check the form. Say confirm create to save, or cancel.")
        return True
    if low not in CONFIRM:
        s.say('Please check the displayed details, then say confirm create or cancel. To change the details, cancel and start Add Lead again.');return True
    if not await s.worker.signed_in():raise DemoError('CRM sign-in expired. The lead was not submitted.')
    if await s.worker.form_signature()!=d['signature']:
        s.say('The form changed after your review. Please cancel and start again so the correct details can be confirmed.');return True
    # Mark before the first write. Timeouts and repeat messages never resubmit.
    d['phase']='submitted'
    s.say('Saving the lead now. I will verify the result in the Leads list.')
    try:
        result=await save(s.worker,d)
        d['phase']='done';s.say(result)
        s.lead_draft=None
    except Exception:
        s.say('I could not verify whether the CRM saved the lead. I will not retry Save automatically. Please check the Leads list for this name and phone before trying again.')
    return True

async def prepare(worker,d):
    from . import config
    if not config.SANDBOX_CONFIRMED:raise DemoError('Lead creation is enabled only in the configured test CRM.')
    page=worker.page
    if '/leads/add-lead' not in page.url:raise DemoError('Open Add Lead again before entering the details.')
    async with worker.lock:
        await worker.check_popups()
        await page.locator('input[formcontrolname="name"]').fill(d['name'])
        phone=page.locator('ngx-mat-intl-tel-input[formcontrolname="contactNo"]')
        await phone.locator('input[type="tel"]').fill(d['phone'])
        await phone.locator('input[type="tel"]').press('Tab')
        d['national_phone']=await phone.locator('input[type="tel"]').input_value()
        await page.locator('input[formcontrolname="email"]').fill(d['email'])
        if 'ng-invalid' in (await phone.get_attribute('class') or ''):
            raise DemoError('The CRM rejected that phone number. Cancel and start again with a valid number.')
        await worker.remember_demo_form()
        source=page.locator('ng-select[formcontrolname="leadSource"] .ng-value-label')
        source_text=await source.inner_text() if await source.count()==1 else 'as displayed'
        return 'Source: '+source_text+'. Other form defaults remain as displayed.'

async def save(worker,d):
    page=worker.page
    async with worker.lock:
        await worker.check_popups()
        button=page.get_by_role('button',name='Save',exact=True)
        if await button.count()!=1 or not await button.is_enabled():raise DemoError('Save is not available.')
        # Match the observed create endpoint, not an unrelated 200 response.
        async with page.expect_response(lambda r:r.request.method=='POST'
                and urlsplit(r.url).path.rstrip('/')=='/api/v1/lead',timeout=25000) as pending:
            await button.click()
        response=await pending.value
        result=await response.json()
        if not response.ok or result.get('succeeded') is not True:
            return 'The CRM did not accept this lead. Please review the validation message on the form before starting a corrected request.'
        record_id=result.get('data')
        if not isinstance(record_id,str) or not re.fullmatch(r'[0-9a-fA-F-]{36}',record_id):
            raise DemoError('CRM returned an unexpected creation result.')
        d['created_id']=record_id
        worker.demo_form_signature=None
        try:await page.wait_for_url('**/leads/manage-leads*',timeout=10000)
        except Exception:return 'Lead created: '+d['name']+'. The CRM confirmed the new record, but the list has not refreshed yet.'
        return 'Lead created: '+d['name']+'. The CRM confirmed the new record and the Leads list is open.'
