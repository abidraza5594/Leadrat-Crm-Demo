"""Reviewed selectors for the hosted CRM. No model-supplied selectors or mutations."""
import re
from .browser import DemoError
from . import guide

async def visible(locator):
    return [locator.nth(i) for i in range(await locator.count()) if await locator.nth(i).is_visible()]

async def one(locator, description, click=False):
    from .popups import handle_popups,PopupBlocked
    try:await handle_popups(locator.page)
    except PopupBlocked as exc:raise DemoError(str(exc))
    try:await locator.first.wait_for(state='visible',timeout=6000)
    except Exception:
        try:await handle_popups(locator.page)
        except PopupBlocked as exc:raise DemoError(str(exc))
        raise DemoError(description+' is not available in this account or lead state.')
    items=await visible(locator)
    if len(items)!=1:raise DemoError(description+' could not be identified uniquely. The demo stopped.')
    target=items[0]
    if await target.evaluate("el=>!!el.closest('[aria-disabled=true],.pe-none')"):
        raise DemoError(description+' is disabled for this record.')
    if click:
        await guide.click(target,'Click '+description)
        try:await handle_popups(locator.page)
        except PopupBlocked as exc:raise DemoError(str(exc))
    else:await guide.point(target,'Here: '+description)
    return target

async def walkthrough(worker, feature):
    key=feature['id'];page=worker.page
    if key in {'add_lead','bulk_upload','lead_sources'}:
        await worker.open_feature({**feature,'id':'add_lead' if key=='lead_sources' else key})
        if key=='lead_sources':
            await one(page.locator('ng-select[formcontrolname="leadSource"]'),'Lead source')
            return 'The Source control on Add Lead is visible.'
        return 'The requested form is visible.'
    list_controls={
        'search':'#search-dropdown input', 'columns':'.show-hide-gray ng-select',
        'date_filter':'multi-date-filter', 'saved_filters':'#saved-filter',
        'bulk_update':'.ag-header-select-all', 'duplicates':'lead-name-section [title^="Total Duplicates"]',
    }
    async with worker.lock:
        if key in list_controls:
            targets=await visible(page.locator(list_controls[key]))
            if not targets:raise DemoError(feature['title']+' has no visible control in this list. '+feature['facts'][0])
            # Read-only highlight of a representative control; never selects rows or duplicates.
            await guide.point(targets[0],'Here: '+feature['title'])
            return 'The relevant list control is highlighted. No list preference or record was changed.'
        if key=='export':
            await one(page.get_by_text(re.compile(r'^\s*Export\s*$',re.I)), 'Export control')
            return 'The Export entry is highlighted; no export was started.'
        if key=='filters':
            await one(page.locator('manage-leads').get_by_text(re.compile(r'^\s*Filter\s*$',re.I)),'Lead filter',True)
            await one(page.locator('leads-advance-filter'),'Advanced filters')
            return 'The advanced filter form is open.'
        preview=page.locator('lead-preview')
        if not await preview.count():
            rows=page.locator('lead-name-section .header-6.text-secondary')
            try:await rows.first.wait_for(state='visible',timeout=10000)
            except Exception:raise DemoError('No visible lead is available for a record walkthrough. '+feature['facts'][0])
            choices=await visible(rows)
            if not choices:raise DemoError('No visible lead is available.')
            await guide.click(choices[0],'Open a lead from the list')
        await one(preview,'Lead preview')
        tab={'status':'Status','meeting':'Status','site_visit':'Status','booking':'Status',
             'appointment_done':'Status','notes':'Notes','history':'History','documents':'Document'}.get(key,'Overview')
        await one(preview.locator('.nav-item').filter(has_text=re.compile(r'^\s*'+tab+r'\s*$')),'Lead '+tab+' tab',True)
        if key in {'status','meeting','site_visit','booking','appointment_done'}:
            root=preview.locator('status-change,custom-status-change')
            await one(root,'Status editor')
            if key in {'meeting','site_visit'}:
                label='meeting' if key=='meeting' else 'site visit'
                option=root.locator('label').filter(has_text=re.compile(r'^\s*(schedule '+label+'|'+label+r' scheduled)\s*$',re.I))
                await one(option,'Schedule '+label,True)
                await one(root.locator('[formcontrolname="scheduledDate"],[formcontrolname="ScheduledDate"]'),'Appointment date and time')
                await worker.remember_demo_form()
                return 'The scheduling option and appointment date/time field are visible. The selection is unsaved.'
            return 'The lead status editor is visible. No status has been saved.'
        roots={'notes':'lead-notes','history':'lead-history','documents':'leads-document-upload','reassign':'individual-reassign'}
        if key in roots:
            root=preview.locator(roots[key]);await one(root,feature['title'])
            if key=='reassign':
                await one(root.get_by_role('button',name=re.compile(r'^(Re-Assign|Assign) Lead$',re.I)),'Reassign lead',True)
                await one(root.locator('ng-select').first,'Owner selection')
            return feature['title']+' controls are visible.'
        if key in {'email','whatsapp','sms','edit_lead','whatsapp_chat','whatsapp_api'}:
            channel='whatsapp' if key.startswith('whatsapp') else key
            selector={'email':'#clkMailLead','whatsapp':'#clkWhatsappLead','sms':'#clkSMS','edit_lead':'[title="Edit"]'}[channel]
            await one(preview.locator('leads-actions '+selector),feature['title']+' action',True)
            if key=='edit_lead':
                await one(page.locator('add-lead,custom-lead-form'),'Lead editor')
            else:
                roots='leads-template-share,leads-email-share,whatsapp-chat,lead-bulk-share'
                chooser=page.locator('img[src$="smtp-email.svg"],img[src$="brevo.svg"]' if key=='email' else 'img[src$="personal-whatsapp.svg"],img[src$="whatsapp-chat.svg"],img[src$="whatsapp-API.svg"]')
                possible=page.locator(roots).or_(chooser).or_(page.get_by_text(re.compile('There is no email ID associated')))
                try:await possible.first.wait_for(state='visible',timeout=6000)
                except Exception:pass
                for attempt in range(4):
                    missing=page.locator('.modal-content').filter(has_text='There is no email ID associated with')
                    if not await missing.count():break
                    await one(missing.get_by_text(re.compile(r'^\s*Cancel\s*$',re.I)),'Missing-email message Cancel',True)
                    if attempt==3:
                        # Demonstrate the prerequisite instead of repeatedly asking
                        # the visitor what to do or pretending a composer is open.
                        if not await preview.count():
                            rows=await visible(page.locator('lead-name-section .header-6.text-secondary'))
                            if not rows:raise DemoError('The checked sample leads have no email address. Edit Lead is required before email can be demonstrated.')
                            await guide.click(rows[0],'Open a lead from the list')
                        await one(preview.locator('leads-actions [title="Edit"]'),'Edit lead to add an email address',True)
                        await one(page.locator('input[formcontrolname="email"]'),'Lead email address field')
                        return 'Email prerequisite: the checked sample leads have no email address, so I opened Edit Lead and highlighted Email. Enter a valid address and save before using Email. I have not entered or saved an address, and the email composer has not been opened.'
                    if attempt==0 and getattr(worker,'notify',None):
                        worker.notify('This sample lead has no email address. I will check another available test lead to show the email composer; I will not add a made-up address.')
                    next_lead=preview.locator('[title="Next Lead"]:visible').first
                    if await next_lead.count() and not await next_lead.evaluate("el=>!!el.closest('.pe-none')"):
                        await one(next_lead,'Next available test lead',True)
                    else:
                        # Some hosted versions close the underlying preview together
                        # with the missing-email notice; don't wait for a vanished close icon.
                        if await preview.count():
                            closer=preview.locator('.ic-circle-chevron-left:visible').first
                            if await closer.count():await one(closer,'Close lead preview',True)
                            else:raise DemoError('This lead has no email address, and another sample cannot be selected from this preview. Update its email through Edit Lead before sending.')
                        candidates=await visible(page.locator('lead-name-section .header-6.text-secondary'))
                        if len(candidates)<=attempt+1:
                            raise DemoError('No other visible test lead is available to demonstrate email. The current lead needs a valid email address through Edit Lead. No customer data was changed.')
                        await guide.click(candidates[attempt+1],'Open another lead from the list')
                    await one(preview.locator('leads-actions #clkMailLead'),'Email action on the next lead',True)
                    try:await possible.first.wait_for(state='visible',timeout=6000)
                    except Exception:pass
                if await visible(chooser):
                    choices=(['smtp-email.svg','brevo.svg'] if key=='email' else
                             ['whatsapp-chat.svg'] if key=='whatsapp_chat' else
                             ['whatsapp-API.svg'] if key=='whatsapp_api' else
                             ['personal-whatsapp.svg','whatsapp-chat.svg','whatsapp-API.svg'])
                    chosen=None
                    for filename in choices:
                        candidate=page.locator('img[src$="'+filename+'"]')
                        if len(await visible(candidate))==1:chosen=(filename,candidate);break
                    if chosen is None:raise DemoError('The requested communication provider is not available in this account. No different provider was silently substituted.')
                    label={'smtp-email.svg':'SMTP email','brevo.svg':'Brevo email','personal-whatsapp.svg':'Personal WhatsApp template sharing','whatsapp-chat.svg':'Integrated WhatsApp chat','whatsapp-API.svg':'WhatsApp API templates'}[chosen[0]]
                    if getattr(worker,'notify',None):worker.notify('I am opening '+label+'. The available choices depend on this account configuration.')
                    await one(chosen[1],label,True)
                await one(page.locator(roots),'Configured message composer')
            return feature['title']+' form is visible; nothing was submitted.'
        # These topics have a source-backed explanation and a preview, not a completed nested demo.
        return 'The lead Overview is visible. The specific '+feature['title'].lower()+' operation has not been opened or executed.'
