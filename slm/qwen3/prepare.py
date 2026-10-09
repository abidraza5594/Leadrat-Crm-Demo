"""Build auditable multitask chats; preserve previous source datasets unchanged.

Synthetic development/test templates are separate from training templates.
They are NOT independent real-customer accuracy benchmarks.
"""
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from app import docs
from app.project import FEATURES,PROJECT
from app.semantic_knowledge import SemanticKnowledge
from app.conversation_engine import (classification_dialogue,dialogue,product_contract,
    KIND_SCHEMA,FACT_SCHEMA,FACT_SYSTEM,QUESTIONS)
from slm.prompting import facts_messages,facts_target_text,parse_facts

OUT=ROOT/'slm/data/qwen3-v1'
SEED=20261008
BASE='Qwen/Qwen3-4B-Instruct-2507'
REVISION='cdbee75f17c01a7cc42f958dc650907174af0554'

# Each phrase identifies one reviewed capability, not an executable click.
PHRASES={
 'leads':['manage leads in the CRM','work with my enquiries','see the sales pipeline','open the lead list','organise sales prospects','lead manage kaise kare'],
 'add_lead':['add a new lead','create one enquiry','enter a new prospect','register a new lead','make a new enquiry record','naya lead add karna hai'],
 'lead_sources':['see where a lead came from','check enquiry sources','inspect lead attribution','review source and campaign details','find the origin of an enquiry','lead ka source dekhna hai'],
 'bulk_upload':['import leads from a spreadsheet','upload active leads in bulk','add leads using an Excel file','import a CSV into Leads','load multiple enquiries into Leads','bulk leads upload kaise kare'],
 'projects':['view property development projects','open the Projects workspace','browse the project list','look through project records','explore real estate projects','projects dikhao'],
 'tasks':['view follow-up tasks','open the Tasks workspace','manage assigned tasks','see my pending task list','review task records','tasks kaise dekhe'],
 'properties':['browse the property inventory','open the Properties workspace','see available properties','view property records','explore the property list','properties dikhao'],
 'dashboard':['view the CRM dashboard','see the dashboard overview','open sales dashboard','check the dashboard summary','explore dashboard indicators','dashboard dikhao'],
 'communication':['review communication options for a lead','see lead communication channels','explore how to contact a lead','view the lead communication controls','understand available contact channels','lead communication options dikhao'],
 'status':['change a lead status','update the sales stage','modify the lead substatus','move a lead to another status','set the lifecycle stage for a lead','lead status change kaise kare'],
 'meeting':['schedule a meeting with a lead','arrange a customer meeting','set up a meeting appointment','book a meeting time for a prospect','plan a meeting for this enquiry','meeting schedule karna hai'],
 'site_visit':['schedule a site visit','arrange a property visit','set a site-visit appointment','plan a visit to the project','fix a date for a site visit','sitevisite schedule karna hai'],
 'notes':['add a note to a lead','write a lead note','view notes on the enquiry','record a note against a prospect','review the lead notes section','lead me note add karo'],
 'history':['review lead activity history','see previous lead activities','inspect the enquiry timeline','read the lead history','track earlier activities on a lead','lead history dikhao'],
 'documents':['attach a document to a lead','view lead documents','upload a file against an enquiry','review attached lead files','manage the documents on a lead','lead documents dikhao'],
 'reassign':['reassign a lead to another agent','change the lead owner','transfer ownership of an enquiry','allocate this lead to a colleague','move a lead to another salesperson','lead dusre agent ko assign karo'],
 'email':['send an email to a lead','write a lead email','open the email composer for an enquiry','email a prospect from the CRM','compose a customer email','lead ko email kaise bheje'],
 'whatsapp':['open WhatsApp for a lead','contact a lead through WhatsApp','use the lead WhatsApp action','message this prospect on WhatsApp','start WhatsApp from lead details','lead ko WhatsApp karo'],
 'sms':['send an SMS to a lead','text a prospect by SMS','open the lead SMS composer','use SMS for an enquiry','compose a customer SMS','lead ko SMS bhejna hai'],
 'edit_lead':['edit lead information','update an enquiry record','modify the lead contact details','correct details on an existing lead','change information in a lead','lead details edit kaise kare'],
 'search':['search for a lead','find a particular enquiry','locate a lead by name','look up a prospect in Leads','use lead search','lead search kaise kare'],
 'filters':['filter leads by multiple conditions','open advanced lead filters','narrow the lead list with filters','apply advanced filters to enquiries','use lead filtering controls','lead filter lagana hai'],
 'columns':['change visible lead columns','customise the lead table columns','choose columns in the lead list','reorder the displayed lead columns','manage lead column visibility','lead columns change karna hai'],
 'date_filter':['filter leads by a date range','use the lead date filter','show leads within selected dates','set a date interval for the lead list','narrow enquiries by date','date ke hisab se lead filter karo'],
 'saved_filters':['save a lead filter','reuse a saved filter','open saved lead filters','store a lead filter preset','apply a previously saved lead filter','saved filters dikhao'],
 'export':['export leads to a file','download the lead list','save lead records as an export','use the lead export option','extract leads into a spreadsheet','leads export kaise kare'],
 'bulk_update':['update several selected leads','apply bulk actions to leads','change selected leads together','perform a bulk lead update','use actions on multiple leads','multiple lead bulk update karo'],
 'matching':['find properties matching a lead','view matching properties for an enquiry','match inventory to a prospect','see suitable properties for this lead','use the property matching section','lead ke matching properties dikhao'],
 'duplicates':['check duplicate leads','inspect duplicate enquiries','find repeated lead records','review possible duplicate prospects','open duplicate lead controls','duplicate leads kaise dekhe'],
 'booking':['view the lead booking section','record a booking against a lead','open booking details for an enquiry','inspect a lead booking','use the booking workflow for a lead','lead booking kaise kare'],
 'appointment_done':['mark an appointment completed','complete a scheduled appointment','update the completed meeting outcome','record completion of a site visit','finish an appointment on a lead','appointment complete mark karo'],
 'call':['call a lead from the CRM','open the lead calling action','dial a prospect','make a phone call to an enquiry','use the call control on a lead','lead ko call kaise kare'],
 'archive':['delete or restore a lead','archive an enquiry','open deleted lead restoration','remove a lead record','recover a deleted lead','lead delete restore kaise kare'],
 'lead_pool':['view the unassigned lead pool','claim a lead from the pool','open the lead pool','pick an unassigned enquiry','see lead pool claiming options','lead pool se lead claim karo'],
 'flags':['flag a lead','set a flag on an enquiry','review lead flags','mark a prospect using a flag','open the lead flag options','lead flag kaise kare'],
 'lead_details':['view the lead overview','open details of one lead','inspect an enquiry overview','review information on a particular lead','see a prospect detail screen','lead overview dikhao'],
 'whatsapp_api':['use WhatsApp API templates','send an approved WhatsApp template','view WhatsApp business API templates','open template messaging through WhatsApp API','choose a WhatsApp API message template','WhatsApp API template kaise use kare'],
 'whatsapp_chat':['open integrated WhatsApp chat','see the CRM WhatsApp inbox','use the integrated WhatsApp conversation','view WhatsApp chat inside the CRM','access the built-in WhatsApp chat','integrated WhatsApp chat dikhao'],
}

def compact(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
def digest(value):return hashlib.sha256(compact(value).encode()).hexdigest()

def with_schema(messages,schema):
    result=[dict(m) for m in messages]
    result[0]['content']+='\nReturn only a JSON object matching this schema: '+json.dumps(schema,separators=(',',':'))
    return result

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    knowledge=SemanticKnowledge(directory=PROJECT['knowledge_dir'])
    knowledge.documents=docs.load(PROJECT['knowledge_dir'])
    topics=sorted({d['module'] for d in knowledge.documents})
    instruction,product_schema,virtual=product_contract(FEATURES,topics,knowledge)
    if set(PHRASES)!=set(FEATURES):raise ValueError('Every reviewed capability needs training phrases')
    sets={s:[] for s in ['train','dev','test']}; seen={}; duplicates=Counter()
    def add(split,task,prompt,answer,family,language='en'):
        fingerprint=digest(prompt)
        if fingerprint in seen:
            old_split,old_answer=seen[fingerprint]
            if compact(answer)!=old_answer:raise ValueError('Conflicting labels for one prompt')
            if old_split!=split:raise ValueError('Cross-split prompt leakage')
            duplicates[task]+=1;return
        seen[fingerprint]=(split,compact(answer))
        sets[split].append({'id':task+'-'+fingerprint[:20],'task':task,'family':family,
            'language':language,'messages':prompt+[{'role':'assistant','content':compact(answer)}]})
    def state(message,pending=None,last=None,offer=None,history=None):
        return {'message':message,'pending_question':pending,'last_feature':last,'last_offer':offer,
                'history':history or [],'customer':{}}
    def kind(split,s,label,family,language='en'):
        add(split,'classify',with_schema(classification_dialogue(s),KIND_SCHEMA),{'kind':label},family,language)
    def product(split,s,feature,family,quote='',language='en'):
        kind(split,s,'PRODUCT_QUESTION',family,language)
        add(split,'demo_selection',with_schema(dialogue(s,instruction),product_schema),
            {'feature':feature,'no_demo_quote':quote},family,language)
    def fact(split,s,updates,family,skip=False):
        kind(split,s,'CUSTOMER_FACT',family)
        for u in updates:
            if u['evidence'] not in s['message']:raise ValueError('Evidence is not verbatim')
        add(split,'customer_update',with_schema(dialogue(s,FACT_SYSTEM),FACT_SCHEMA),{'updates':updates,'skip':skip},family)

    # Reuse labels, not weights. Score is calculated in application code, never learned arithmetic.
    source_hashes={}
    for split,source in [('train','train'),('dev','dev'),('test','fresh_test')]:
        p=ROOT/f'slm/data/v4/{source}.jsonl';source_hashes[source]=hashlib.sha256(p.read_bytes()).hexdigest()
        for line in p.read_text('utf-8').splitlines():
            r=json.loads(line);answer=json.loads(facts_target_text(r['target']))
            _,error=parse_facts(compact(answer),r['transcript'])
            if error:raise ValueError(f"{r['id']}: {error}")
            add(split,'qualification',facts_messages(r['transcript']),answer,'historical/'+r['family'],r['language'])

    # Phrase families, including the Hinglish examples, are held in separate splits.
    for feature,phrases in PHRASES.items():
        for i,phrase in enumerate(phrases):
            split='train' if i in (0,1,2,5) else 'dev' if i==3 else 'test'
            language='hinglish' if i==5 else 'en';family=f'feature/{feature}/phrase-{i}'
            wrappers=['Can you help me {}?','Please show me how to {}.','I want to {}.'] if i!=5 else ['{}','please {}']
            for wrapper in wrappers:
                msg=wrapper.format(phrase)
                for pending in [None,'monthly_leads','influence']:
                    s=state(msg,pending,last='projects' if feature!='projects' else 'leads')
                    product(split,s,feature,family,language=language)
                quote='do not open anything' if split=='train' else 'no screen please' if split=='dev' else 'do not show the demo'
                product(split,state(msg+' '+quote),feature,family,quote,language)

    # Disjoint numeric ranges across splits; boundary values and shorthand are explicit.
    values={'train':list(range(1,81))+[99,100,299,300,499,500,999,1000,10000,20000,100000],
            'dev':[81,83,97,101,301,501,11000,21000],
            'test':[82,84,98,102,302,502,12000,22000]}
    for split,numbers in values.items():
        for field,noun in [('organisation.agents','people on our sales team'),('monthly_leads','new leads per month')]:
            for n in numbers:
                forms=[str(n),format(n,',')]
                if n>=1000 and n%1000==0:forms.append(str(n//1000)+'k')
                for value in dict.fromkeys(forms):
                    phrases=([value,f'We have {value} {noun}.',f'Actually {value} {noun}, not {n+9}.',f'{value} {noun}'] if split=='train'
                        else [f'The correct number is {value} {noun}.',f'Update that to {value} {noun}.'] if split=='dev'
                        else [f'Please record {value} {noun}.',f'I meant {value} {noun}, not {n+11}.'])
                    for msg in phrases:
                        update={'field':field,'value':value,'evidence':value}
                        fact(split,state(msg,field),[update],f'count/{split}/{field}/{n}')
                        if msg!=value:
                            pending='monthly_leads' if field=='organisation.agents' else 'organisation.agents'
                            fact(split,state(msg,pending,history=[{'role':'assistant','content':QUESTIONS[pending]}]),[update],f'count/{split}/{field}/{n}')

    texts={
      'organisation.type':[['developer','brokerage','channel partner'],['We are a developer','We are a brokerage','We are a channel partner'],['My business is a developer','My business is a brokerage','My business is a channel partner']],
      'pain_points':[['We miss follow-ups','Agents forget to call leads','Reporting takes too long','We lose leads','I cannot track agent activity','Duplicate enquiries waste time'],['Follow-up calls are getting missed','The team misses appointments'],['Leads wait too long for a reply','We struggle to assign enquiries']],
      'process':[['Excel','excels','spreadsheets','WhatsApp','another CRM','manually','Excel and WhatsApp'],['We currently work in spreadsheets','Our team uses another CRM'],['Everything is managed in Excel today','We use a different CRM at present']],
      'influence':[['me','I decide','I approve the purchase','My manager decides','I am evaluating for my boss'],['I am the final approver','Our director signs off'],['The purchase decision is mine','My employer will choose']],
      'next_step':[['now','right away','within a month','next week','later','next year','as soon as possible'],['Within the coming three weeks','In six months'],['We need it immediately','Not until next quarter']],
      'consent':[['yes','Yes, you may contact me','Please have sales call me'],['Yes, I agree to a sales call'],['I give permission for the sales team to call']],
      'contact':[['buyer@example.com','+1 202-555-0101'],['person@example.org'],['demo@example.net']],
    }
    for field,groups in texts.items():
        for split,group in zip(sets,groups):
            for msg in group:
                value=('true' if field in ('consent','contact') else msg.split()[-1] if field=='organisation.type' else msg)
                if field=='organisation.type':value='channel_partner' if 'channel partner' in msg else 'developer' if 'developer' in msg else 'brokerage'
                for last in [None,'leads','projects','site_visit']:
                    fact(split,state(msg,field,last=last),[{'field':field,'value':value,'evidence':msg}],f'text/{split}/{field}/{digest(msg)[:8]}')
    for split,group in zip(sets,[['Excel','excels','WhatsApp','spreadsheets'],['We use Excel for everything'],['Our process is still in spreadsheets']]):
        for msg in group:fact(split,state(msg,'pain_points'),[{'field':'process','value':msg,'evidence':msg}],f'tool-not-pain/{split}/{msg}')

    for split,phrases in zip(sets,[['yes','show that','please show it'],['yes, show me that one'],['go ahead and display it']]):
        for msg in phrases:
            for feature in FEATURES:
                for pending in [None,'monthly_leads']:
                    # An explicit pending business question outranks the demo offer for bare yes.
                    if pending and msg=='yes':continue
                    s=state(msg,pending,last=feature,offer=feature if pending is None else None)
                    product(split,s,feature,f'context/{split}/{msg}')

    special={
      'GREETING':[['hello','hi there','namaste'],['good morning'],['hey, good afternoon']],
      'THANKS':[['thanks','thank you','that helps'],['many thanks'],['appreciate your help']],
      'REPEAT':[['repeat that','say that again'],['please repeat your previous answer'],['could you explain the last answer again']],
      'STOP':[['stop the demo','pause the walkthrough'],['stop showing the screen'],['please halt this demonstration']],
      'DECLINE_CONTACT':[['do not contact me','no sales calls','I withdraw permission to contact me'],['please do not call or email me'],['I refuse any sales follow-up']],
      'UNCLEAR':[['???','asdfg','hmmm'],['qzxw'],['...what...']],
    }
    for label,groups in special.items():
        for split,group in zip(sets,groups):
            for msg in group:
                for pending in [None,*QUESTIONS]:kind(split,state(msg,pending),label,f'special/{split}/{label}/{msg}')
    for split,msgs in zip(sets,[['skip this question','I do not want to answer'],['Can we skip this one?'],['Please leave this question unanswered']]):
        for msg in msgs:
            for field in QUESTIONS:fact(split,state(msg,field),[],f'skip/{split}/{msg}',skip=True)
    for split,msgs in zip(sets,[['I do not know','not sure'],['I am not certain of that'],['I cannot give an exact answer']]):
        for msg in msgs:
            for field in QUESTIONS:fact(split,state(msg,field),[],f'unknown/{split}/{msg}')
    for split,msgs in zip(sets,[['run payroll','calculate my income tax','book a flight'],['configure employee salaries'],['trade stocks for me']]):
        for msg in msgs:product(split,state('Can you '+msg+'?'),'unknown',f'unsupported/{split}/{msg}')
    if 'knowledge:Data Management' in virtual:
        for split,phrase in zip(sets,['manage raw prospect datasets before conversion','validate and segment raw prospect data','explain the Data Management module']):
            product(split,state('How do I '+phrase+'?'),'knowledge:Data Management',f'data-management/{split}')

    manifests={}
    for split,rows in sets.items():
        random.Random(SEED).shuffle(rows)
        p=OUT/f'{split}.jsonl';p.write_text(''.join(compact(r)+'\n' for r in rows),encoding='utf-8')
        manifests[split]={'count':len(rows),'tasks':dict(Counter(r['task'] for r in rows)),
            'languages':dict(Counter(r['language'] for r in rows)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    families={s:{r['family'] for r in rs} for s,rs in sets.items()}
    if families['train']&families['dev'] or families['train']&families['test'] or families['dev']&families['test']:raise ValueError('Family overlap')
    manifest={'created':'2026-10-08','base_model':BASE,'base_revision':REVISION,'training_mode':'new_adapter_on_pretrained_base',
        'old_adapter_loaded':False,'qualification_format':'facts','seed':SEED,'splits':manifests,
        'source_sha256':source_hashes,'deduplicated':dict(duplicates),'capabilities':list(FEATURES),
        'limitations':'Synthetic, controlled examples; shared task semantics and number patterns. No exact prompt or phrase-family overlap across splits. Historical test is a regression set. Not an independently reviewed real-customer accuracy benchmark. More examples do not guarantee correct UI actions.',
        'deployment':'Training does not deploy to Beacon or overwrite a Hugging Face model. Evaluate fresh conversations, field fidelity and live demo selection before deployment.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))
    return manifest

if __name__=='__main__':build()
