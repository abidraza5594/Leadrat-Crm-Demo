"""Reviewed Lead procedures. Guidance is separate from an observed UI result.

Sources are relative to the existing Leadrat CRM repository, not a new CRM.
No generated selector or generated operation is executable.
"""
GUIDES = {}
def guide(key, title, keywords, source, facts, surface='preview'):
    GUIDES[key] = dict(id=key, title=title, keywords=keywords.split('|'), module='leads',
                       path='/leads/manage-leads', source=source, facts=facts, surface=surface)

guide('status','Change lead status','status|stage|change status|update status', 'src/app/features/leads/status-change/status-change.component.html',[
 'Open a lead, then Status. This is the status editor; the status filters on the list only change which leads you see.',
 'Choose a permitted status, then its reason and any required fields. Scheduling statuses ask for appointment details; booking statuses have booking fields. Review the form before updating. This demo stops before saving.'], 'status')
for key, label in [('meeting','meeting'), ('site_visit','site visit')]:
    guide(key,'Schedule a '+label, f'{label}|schedule {label}|{label.replace(" ","")}|appointment {label}',
      'src/app/features/leads/status-change/status-change.component.html; custom-status-change/custom-status-change.component.html',[
      f'Open the lead and its Status tab. Choose Schedule {label.title()} or the corresponding configured scheduling status.',
      'Enter the appointment date and time, then review the available project or property, responsible user, and required notes. The fields depend on the selected status and account configuration. Confirm only after checking the details; this demo does not create an appointment.'], key)
guide('notes','Lead notes','notes|note|remark|comment', 'src/app/features/leads/lead-notes/lead-notes.component.html',[
 'Open a lead and choose Notes. Read the existing notes before adding a new update.',
 'Enter a clear note describing the conversation, requirement or next action, then review it before posting. Editing controls depend on your permissions. The demonstration leaves the note unsaved.'], 'notes')
guide('history','Lead history','history|audit|activity|timeline', 'src/app/features/leads/lead-history/lead-history.component.html',[
 'Open the lead and choose History to review its recorded activity.',
 'Use the visible entries to trace changes and their recorded timing. History is different from Notes: Notes contain written updates; History records CRM events.'], 'history')
guide('documents','Lead documents','document|attachment|upload file', 'src/app/features/leads/leads-document-upload/leads-document-upload.component.html',[
 'Open a lead and choose Document to view its document controls.',
 'Use the displayed file selection and document details, obey the file restrictions shown by the CRM, then review before uploading. Download and deletion are separate actions; this demo does not transfer or remove files.'], 'documents')
guide('reassign','Reassign a lead','reassign|assign lead|owner|ownership|transfer lead', 'src/app/features/leads/individual-reassign/individual-reassign.component.html',[
 'Open the lead Overview and find Assign To. Choose Re-Assign Lead to open the ownership controls.',
 'Choose the permitted primary owner and, when dual ownership is enabled, the secondary owner. Review the selection before confirming. Lead-pool options depend on account configuration. This demonstration does not change ownership.'], 'reassign')
for key, label, source in [('email','Email','leads-email-share'),('whatsapp','WhatsApp','leads-template-share'),('sms','SMS','leads-template-share')]:
    guide(key,'Lead '+label, f'{label.lower()}|{label.lower()} template|send {label.lower()}',f'src/app/features/leads/{source}/{source}.component.html',[
      f'Open a lead and select its {label} action. The account must have communication permission and the appropriate contact details.',
      ('Email may offer SMTP, Brevo or template sharing. Review recipient, sender, CC/BCC where available, template, subject and body.' if key=='email' else
       'WhatsApp may open personal template sharing, integrated chat or an API composer, depending on configuration. Review the number, approved template, variables and preview.' if key=='whatsapp' else
       'Choose the available SMS template and review the recipient and message variables.' )+' Review before Send. No message is sent during this demonstration.'],key)
guide('communication','Lead communication','communication|email and whatsapp|message|template','src/app/features/leads/leads-actions/leads-actions.component.html',[
 'The lead actions include Email, WhatsApp, SMS and calling when permitted and configured.',
 'For written messages, choose the channel, check the recipient and template, review the content, then send when ready. This overview does not send or place a call.'], 'communication')
guide('edit_lead','Edit a lead','edit lead|change phone|correct email|update details','src/app/features/leads/leads-actions/leads-actions.component.html',[
 'Open the lead and select Edit to review its contact and requirement fields.',
 'Change only the intended fields, check the required fields and review before saving. This demo opens the editor without changing the record.'], 'edit_lead')
guide('lead_sources','Where leads come from','source|subsource|sub source|facebook|integration|where leads come','src/app/features/leads/add-lead/add-lead.component.html; src/app/features/global-config/integration/integration-routing.module.ts',[
 'Leads can enter by manual Add Lead, bulk upload, Data conversion or a configured integration. Source and Sub Source record attribution; they do not themselves connect a provider.',
 'The CRM includes Facebook, Google campaign, property portal and webhook integrations. Actual availability and assignment rules depend on Global Configuration. In Add Lead, choose the relevant Source and then an available Sub Source.'], 'lead_sources')
for key,title,keywords,source,facts in [
 ('search','Find a lead','search|find lead|phone search','manage-leads', ['Use the lead search box and its criteria selector. Choose the appropriate criterion, then enter the value to find a matching record.', 'Search changes the displayed results, not the lead details.']),
 ('filters','Advanced lead filters','filter|advanced filter','leads-advance-filter/leads-advance-filter',['Open Filter on the lead list. Select criteria such as the available owner, source or status fields.', 'Review the criteria and apply them to narrow the list. Clear or reset them when you need the wider list again.']),
 ('columns','Manage lead columns','column|grid fields','manage-leads',['Manage Columns controls which fields appear in the lead grid.', 'Review the available fields and select the columns useful to your work. This demo shows the control without changing saved preferences.']),
 ('date_filter','Lead date filters','date filter|date range','manage-leads',['Use the date filter on the lead list. Check the selected date criterion before choosing a period.', 'Created date and appointment date answer different questions. Review the range before applying it.']),
 ('saved_filters','Saved lead filters','saved filter|save filter','manage-leads',['Saved Filters lets you reuse a list-filter configuration.', 'Review its criteria before applying or setting a default. Saving a filter changes a preference, not the customer records.']),
 ('export','Export leads','export|download leads','manage-leads',['The list Export control is available only with the required permissions and organisation settings.', 'Review the list scope and active filters before exporting. The demo points out the control without downloading customer data.']),
 ('bulk_update','Bulk lead actions','bulk update|multiple leads|bulk status|bulk assign|bulk email|bulk whatsapp','leads-bulk-update/leads-bulk-update',['Select the intended rows in the lead list to reveal the available bulk actions. Verify the selection count and scope before choosing an action.', 'Depending on permissions, bulk actions include status, assignment, source, project, agency, campaign and communication. Each has its own review controls. The demo shows the selection entry without changing multiple records.']),
 ('matching','Matching properties','matching properties|match property','matching-properties/matching-properties',['Matching Properties compares the lead requirements with available property records.', 'Review the suggested properties and their fit before using the sharing controls. Sharing is separate from viewing a match; this demo does not send property material.']),
 ('duplicates','Duplicate leads','duplicate|duplicate source|duplicate assignment','duplicate-source-info/duplicate-source-info',['The lead list may show duplicate counts and duplicate-version badges for records with duplicate information.', 'Review the linked attribution and assignment details before deciding what to do. A duplicate badge alone does not authorise merging or deleting a record.']),
 ('booking','Lead booking','booking|booked|book property','booking-form/booking-form',['Booking-related lead statuses expose booking details according to the configured workflow.', 'Review the booked-under name, booking date, agreement value and available project, property or unit fields. Required details vary. This demo does not confirm a booking.']),
 ('appointment_done','Complete an appointment','meeting done|visit done|complete meeting|complete visit','meeting-site-visit-done/meeting-site-visit-done',['The CRM separates scheduling an appointment from recording a meeting or site visit as done.', 'Open the relevant lead appointment workflow, verify the appointment and fill the required completion details before confirming. This demo does not mark an appointment complete.']),
 ('call','Lead calling','call lead|dialer|dialler|call recording','lead-call/lead-call',['The lead actions include calling and, when available, call recordings. Calling choices depend on the configured communication service.', 'Review the contact and calling option before connecting. Auto-dialer is a separate flow. This demo does not start a call or play a customer recording.']),
 ('archive','Delete or restore leads','delete lead|restore|archive|permanent delete','leads-actions/leads-actions',['Active leads and archived leads have different actions. Delete, Restore and Permanent Delete are permission-gated and may be restricted by lead state.', 'Review the exact record and consequences before confirming. This guide explains these controls but does not click a destructive or restoring action.']),
 ('lead_pool','Lead pool and claim','lead pool|claim|unassigned','individual-reassign/individual-reassign',['Lead Pool can expose Claim Lead and assignment options when the feature and permissions are enabled.', 'Claiming, moving to Unassigned and reassigning change ownership or pool membership. Review the record and desired owner before confirming; none is executed in this demo.']),
 ('flags','Lead flags','flag|tag lead','lead-name-section/lead-name-section',['Lead flags appear on the list and in the lead preview when available.', 'They help identify marked leads. Editing flags depends on permissions and lead state; this demonstration only shows the preview.']),
 ('lead_details','Lead overview','overview|utm|sla|lead details|campaign|channel partner','manage-leads',['Open a lead to review its Overview, ownership and enquiry details. Available metadata can include source, campaign, UTM and activity information.', 'The account configuration determines which fields and SLA information appear. The demo does not infer missing attribution or interpret private customer data.']),
]: guide(key,title,keywords,'src/app/features/leads/'+source+'.component.html',facts,key)

GUIDES['add_lead']=dict(id='add_lead',title='Add a lead',module='leads',path='/leads/add-lead',keywords=['add lead','new lead','create lead'],source='src/app/features/leads/add-lead/add-lead.component.html',surface='add_lead',facts=[
 'Choose Add Lead from the Leads list. Enter the customer name and contact details, then review Source, Sub Source and Assign To.',
 'Complete the applicable enquiry requirements: budget, location, property type, project or property and other configured fields. Review the additional information and notes, then check required fields before Save. This demo leaves the form unsaved.'])

for key,title,keywords in [('whatsapp_api','WhatsApp API templates',['whatsapp api','whatsapp api template']),('whatsapp_chat','Integrated WhatsApp chat',['whatsapp chat','integrated whatsapp'])]:
    GUIDES[key]={**GUIDES['whatsapp'],'id':key,'title':title,'keywords':keywords,'surface':key}
