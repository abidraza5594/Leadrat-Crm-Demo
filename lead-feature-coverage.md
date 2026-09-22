# Lead assistant coverage

Source review: 21 September 2026. This is a coverage inventory, not certification of every account-specific workflow. Source retrieval and executable walkthroughs are different capabilities. All source files under `src/app/features/leads` are eligible for the existing local knowledge index; only the action registry below can drive the UI. No account was used to send, save, delete or export customer data.

## Executable registry

| Topic | Actual UI used | Boundary |
|---|---|---|
| Add Lead | Existing Add Lead form and registered fields | Sample name/email only; no save |
| Status, meeting, existing site-visit guide | Lead preview → Status | No save or appointment completion; site-visit matching unchanged |
| Notes | Lead preview → Notes | Highlight input; no post |
| History | Lead preview → History | Read only |
| Documents | Lead preview → Document | No upload/download/delete |
| Reassign | Overview → existing assignment editor | No ownership update |
| WhatsApp + email | Preview action controls | Both-channel overview; no send |
| WhatsApp | Configured personal/integrated/API composer | Recipient and template controls; no Send/Test |
| Email | Configured SMTP/Brevo/template composer | If chooser offered, SMTP; no send |
| Sources | Add Lead → Source | Explains entry and attribution; no field change |
| Bulk upload | Existing upload route | Upload entry only; no file selection/import |
| Advanced filters | Existing filter opener/modal | No filter submission |
| Search, columns, export, date filters, saved filters | Corresponding lead-list controls | Highlight/explain; no export/preferences write |
| Integrations | Global Configuration | Overview only; no account connection or assignment changes |

Ordinary WhatsApp/email phrasing uses direct routing. A follow-up `template` remembers the last communication channel. A combined-channel request gets a combined overview; a subsequent template request defaults to WhatsApp. Explicit new email/WhatsApp wording switches the channel. Generic paraphrases still use the local model and may take longer or misclassify.

## Full Lead source inventory and remaining live coverage

Paths below are relative to `src/app/features/leads/`. Components have both TypeScript and HTML unless noted. Knowledge retrieval includes these components; inclusion alone is not a guarantee of a correct generated answer.

| Source area | Features in scope | Live status |
|---|---|---|
| `manage-leads.component.*` | Visibility, counts, search criteria, status/date filters, grid/card, columns, tracker, selection | List guides above; remaining controls need walkthroughs |
| `add-lead/`, `custom-lead-form/` | Identity/contact, requirements, budget, projects/properties, source/sub-source, owners, campaign/channel partner, notes, configured fields | Existing form guide; custom account layouts need real testing |
| `leads-actions/` | Edit, notes, history, documents, portal link, SMS, email, WhatsApp, call, recordings, delete, restore, permanent delete, claim | Communication/notes/history/documents covered; others knowledge-only |
| `lead-name-section/` | Name preview, flags, converted-from-Data badge, duplicate counts, meeting/visit summaries | Opens preview; other badges knowledge-only |
| `status-change/`, `custom-status-change/` | Standard/custom status transitions, reasons, scheduling fields | Bounded status/scheduling guide; not every transition |
| `lead-appointment/`, `meeting-site-visit-done/` | Appointment information and completion | Knowledge-only; completion is a write |
| `booking-form/` | Booking details | Knowledge-only |
| `individual-reassign/` | Primary/secondary ownership, pool-related controls | Assignment editor guide; no pool mutations |
| `lead-notes/`, `lead-history/`, `leads-document-upload/` | Notes/history/files and permissions | Guides registered |
| `leads-template-share/` | Lead/project/property material sharing, template, variables, recipient | WhatsApp/email guide |
| `leads-email-share/` | SMTP/Brevo, template, sender/recipient, CC/BCC, subject/body | Email compose guide; no delivery |
| `whatsapp-chat/` | Contact selection, integrated messages/composer | Configured WhatsApp guide; not every chat operation |
| `lead-bulk-share/` | Campaign/template API fields, variables, preview, test/send | Single-lead API compose surface only; bulk not automated |
| `whatsapp-chat-bulk/`, `bulk-leads-email-share/` | Bulk integrated chat and email | Knowledge-only |
| `leads-bulk-update/` | Status, primary/secondary assignment, unassign, source, project, agency, channel partner, campaign, WhatsApp/email, auto-dialer, claim, restore/delete | Knowledge-only; never substituted with single-lead actions |
| `bulk-update-status-leads/` | Bulk status form | Knowledge-only |
| `leads-advance-filter/` | Advanced filter fields | Open/highlight guide |
| `matching-properties/`, `matching-properties/properties-share-data/` | Matching properties and sharing | Knowledge-only |
| `duplicate-source-info/`, `duplicate-assign-info/` | Duplicate attribution/assignment details | Knowledge-only |
| `excel-uploaded-status/` | Upload results | Knowledge-only |
| `lead-pool-notification/` | Pool notifications | Knowledge-only |
| `lead-call/`, `auto-dialer/` | Calling and dialer | Knowledge-only; no call initiation |
| Shared `lead-preview/`, `sla-section/` | Overview, tabs, ownership, SLA, UTM, contact/record metadata | Preview and tab guides; SLA-specific flow not automated |
| Shared `bulk-upload/`, `migration-bulk-upload/`, `bulk-operation-tracker/` | Upload/mapping/review, migration, results/tracking | Standard upload entry guide; remaining stages knowledge-only |
| Shared `saved-filter/`, `multi-date-filter/`, list helpers | Saved/date filters and list preferences | Highlight guides |

Lead entry evidence: manual Add Lead, file import, converted Data, configured integrations. Integration source includes Facebook, Google campaign/ad flows, Magicbricks, Housing, 99acres, webhook, JustLead, CommonFloor, Bayut, Dubizzle, Property Finder and Skyloov. Source/Sub Source, campaign, channel partner and UTM describe attribution; their presence does not establish that any provider is connected in the current organisation.

## Verification and limits

Backend regression tests cover the exact reported conversation, channel context, bilingual voice keys and action acknowledgements. Frontend executor fixtures cover communication chooser/template opening, follow-up reuse, dirty/permission guards and non-writing behavior. Angular compilation checks templates/types. These checks do not replace a live test in the user's logged-in Chrome. Hidden controls, missing contact details, disabled integrations, permission restrictions and incompatible lead state stop the guide with an explanation.

Remaining work before claiming complete Lead automation: add and test the knowledge-only workflows above, provider-specific setup substeps and account-specific custom forms/statuses. No statement of 100% live coverage is warranted yet.
