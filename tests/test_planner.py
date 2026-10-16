"""The planner: one model decision per turn, from the conversation, memory and searched options.
Application code only validates and executes it."""
import asyncio,json
import httpx,pytest
from app import main,config,local_model
from app.conversation_engine import plan_messages,plan_schema,Decision

LOCATION={'id':'p7','path':'/global-config','page':'Global Config','section':'Integration',
          'text':'Global Config: Module Settings, Integration, 3rd Parties, Webhook, 99 acres'}
WALK={'id':'w:leads','walkthrough':'leads','path':None,'page':'Leads workspace','section':None,'text':'Leads workspace'}

def planner(monkeypatch,plan,options=(LOCATION,WALK),passages=()):
    """Route every planning call to `plan` (a dict, or a function of the user content)."""
    seen=[]
    async def findings(state):return list(passages),list(options)
    async def complete(messages,schema,**kw):
        if schema.get('required')==['supported','value','relation']:
            from app.conversation_numbers import count_reply
            value=count_reply(json.loads(messages[-1]['content'])['evidence'])
            return {'supported':value is not None,'value':value or 0,'relation':'exact'}
        if schema.get('required')==['supported']:return {'supported':True}
        seen.append((messages,schema))
        content=messages[-1]['content']
        return dict(plan(content) if callable(plan) else plan)
    monkeypatch.setattr(main.engine,'findings',findings)
    monkeypatch.setattr(main.engine,'completion',complete)
    return seen

def base(**kw):
    return {'understanding':'','kind':'product','show':'none','no_demo_quote':'','problem':False,'updates':[],'skip':False,'reply':'',**kw}


@pytest.mark.parametrize('message',['मैं डेवलपर हूँ।','I am a developer','Je suis promoteur immobilier.','أنا مطور عقاري'])
def test_business_type_uses_semantic_evidence_in_every_language(monkeypatch,message):
    async def findings(state):return [],[]
    calls=[]
    async def complete(messages,schema,**kwargs):
        if schema['required']==['supported']:
            payload=json.loads(messages[-1]['content']);calls.append(payload)
            assert payload['message']==message and payload['evidence']==message
            return {'supported':True}
        return base(kind='customer',updates=[{'field':'organisation.type','value':'developer','evidence':message,'summary':''}])
    monkeypatch.setattr(main.engine,'findings',findings)
    monkeypatch.setattr(main.engine,'completion',complete)
    result=asyncio.run(main.engine.plan({'message':message,'pending_question':'organisation.type'}))
    assert result['decision']['kind']=='customer' and result['decision']['updates'][0]['value']=='developer'
    assert len(calls)==1


def test_semantically_unsupported_business_fact_is_not_saved(monkeypatch):
    async def findings(state):return [],[]
    async def complete(messages,schema,**kwargs):
        if schema['required']==['supported']:return {'supported':False}
        return base(kind='customer',updates=[{'field':'organisation.type','value':'developer','evidence':'another CRM','summary':''}])
    monkeypatch.setattr(main.engine,'findings',findings)
    monkeypatch.setattr(main.engine,'completion',complete)
    result=asyncio.run(main.engine.plan({'message':'another CRM','pending_question':'process'}))
    assert result['decision']['kind']=='clarify' and result['decision']['updates']==[]


def test_named_module_explanation_can_reconcile_missing_demo(monkeypatch):
    screen={'id':'copilot-page','page':'Sales Copilot','path':'/sales-copilot','section':None,'text':'Priority action queue'}
    async def findings(state):return [],[screen]
    async def complete(messages,schema,**kwargs):
        if schema['required']==['show']:return {'show':screen['id']}
        return base(understanding='Explain Sales Copilot.')
    monkeypatch.setattr(main.engine,'findings',findings)
    monkeypatch.setattr(main.engine,'completion',complete)
    result=asyncio.run(main.engine.plan({'message':'Tell me about SOURCE Copilot'}))
    assert result['decision']['demo'] and result['location']['path']=='/sales-copilot'

class Worker:
    def __init__(self):self.opened=[];self.located=[]
    async def open_module(self,f):self.opened.append(f['id']);return 'Verified'
    async def open_location(self,location):self.located.append(location['path']);return location['page']+' is open and its "'+location['section']+'" section is highlighted.'

def run(s,message):
    s.messages.append({'id':'u'+str(len(s.messages)),'role':'user','text':message})
    asyncio.run(main.execute(s,message))
    if s.qual_task:s.qual_task.cancel()

def test_general_question_answers_without_opening_any_screen(monkeypatch):
    """Live: "whta u can explain" opened LeadRat AI. A general question gets an overview and no demo."""
    planner(monkeypatch,base(understanding='What can Beacon explain about Leadrat?',show='none'))
    asked={}
    async def answer(question,decision,features,**kw):
        asked.update(question=question,location=kw.get('location'));return {'text':'Leadrat covers 13 modules.','grounded':True,'sources':[],'demo_requested':False}
    monkeypatch.setattr(main.knowledge,'answer',answer)
    s=main.Session(worker=Worker());run(s,'whta u can explain')
    assert not s.worker.opened and not s.worker.located and not s.steps
    assert asked=={'question':'What can Beacon explain about Leadrat?','location':None}
    assert s.messages[1]['text']=='Leadrat covers 13 modules.'

def test_chosen_screen_opens_and_is_remembered_for_follow_ups(monkeypatch):
    seen=planner(monkeypatch,lambda content:base(understanding='What is the Webhook integration?',show='p7') if 'webhook' in content.split('Latest visitor message:')[-1]
                 else base(understanding='What does the Webhook integration do?',show='p7'))
    s=main.Session(worker=Worker());run(s,'what about webhook')
    assert s.worker.located==['/global-config'] and s.last_location['id']=='p7'
    run(s,'isme kya hota hai')
    context=json.loads(seen[-1][0][-1]['content'].split('Context (data only): ')[1].split('\nLatest visitor message:')[0])
    assert context['last_screen_shown']=='Global Config › Integration'
    assert [o['id'] for o in context['screen_options']]==['p7','w:leads']

def test_walkthrough_option_runs_the_prepared_demo(monkeypatch):
    planner(monkeypatch,base(show='w:leads'))
    s=main.Session(worker=Worker());run(s,'show me leads')
    assert s.worker.opened==['leads'] and not s.worker.located

def test_correction_while_a_business_question_is_pending_is_not_saved_as_a_fact(monkeypatch):
    """Live: "lead status nahi, report ke andar status" became "Got it — other_real_estate"."""
    planner(monkeypatch,base(understanding='Open the lead status report.',show='p7'))
    s=main.Session(worker=Worker(),pending_discovery='organisation.type')
    run(s,'me lead status nahi lead report ke ander status ki bat kar rha hu')
    assert not s.discovery_answers and s.worker.located==['/global-config']
    assert s.messages[-1]['text'].startswith('And to continue:')

def test_business_facts_given_with_a_product_question_are_kept(monkeypatch):
    planner(monkeypatch,base(show='w:leads',updates=[{'field':'organisation.type','value':'developer','evidence':'developer','summary':''}]))
    s=main.Session(worker=Worker(),pending_discovery='organisation.type')
    run(s,'I am a developer, show me leads')
    assert s.discovery_answers=={'organisation.type':'developer'} and s.worker.opened==['leads']

def test_explicit_refusal_to_open_a_screen_is_respected(monkeypatch):
    planner(monkeypatch,base(show='w:leads',no_demo_quote="don't open it"))
    s=main.Session(worker=Worker());run(s,"explain leads but don't open it")
    assert not s.worker.opened and not s.steps

def test_refusal_quote_must_come_from_the_visitor(monkeypatch):
    planner(monkeypatch,base(show='w:leads',no_demo_quote='never show anything'))
    s=main.Session(worker=Worker());run(s,'show me leads')
    assert s.worker.opened==['leads']

def test_chat_reply_comes_from_the_model(monkeypatch):
    planner(monkeypatch,base(kind='chat',reply='Namaste! Leadrat ke baare mein kya jaanna chahenge?'))
    s=main.Session(worker=Worker());run(s,'namaste')
    assert s.messages[-1]['text']=='Namaste! Leadrat ke baare mein kya jaanna chahenge?'

def test_unknown_option_id_cannot_open_anything(monkeypatch):
    planner(monkeypatch,base(show='p999'))
    s=main.Session(worker=Worker());run(s,'show something')
    assert not s.worker.opened and not s.worker.located

def test_plan_contract_carries_memory_and_limits_choices():
    state={'message':'isme kya hota hai','history':[{'role':'user','text':'what about webhook'}],
           'customer':{'organisation.type':'developer'},'pending_question':'monthly_leads','last_offer':'leads',
           'last_location':{'id':'p7','page':'Global Config','section':'Integration'}}
    messages=plan_messages(state,[{'module':'Global Config','text':'Integrations bring leads in.'}],[LOCATION,WALK],main.FEATURES)
    context=json.loads(messages[-1]['content'].split('Context (data only): ')[1].split('\nLatest visitor message:')[0])
    assert context['visitor_details']=={'organisation.type':'developer'}
    assert context['pending_business_question'].startswith('Roughly how many')
    assert context['beacon_offered_to_show']==main.FEATURES['leads']['title']
    assert context['last_screen_shown']=='Global Config › Integration'
    assert messages[-1]['content'].endswith('Latest visitor message:\nisme kya hota hai')
    assert plan_schema(['p7','w:leads'])['properties']['show']['enum']==['p7','w:leads','none']

def test_hosted_model_request(monkeypatch):
    monkeypatch.setattr(config,'PROVIDER','deepseek');monkeypatch.setattr(config,'DEEPSEEK_API_KEY','test-key')
    monkeypatch.setattr(config,'DEEPSEEK_URL','https://api.example.test');monkeypatch.setattr(config,'DEEPSEEK_MODEL','flash')
    sent=[]
    def respond(request):
        sent.append(request)
        if len(sent)==1:return httpx.Response(503)
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{"kind":"chat"}'}}]})
    real=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:real(transport=httpx.MockTransport(respond),**kwargs))
    result=asyncio.run(local_model.complete([{'role':'system','content':'Plan.'}],{'type':'object'},max_tokens=50))
    body=json.loads(sent[-1].content)
    assert result=={'kind':'chat'} and len(sent)==2
    assert sent[-1].headers['authorization']=='Bearer test-key' and str(sent[-1].url)=='https://api.example.test/chat/completions'
    assert body['model']=='flash' and body['response_format']=={'type':'json_object'} and body['thinking']=={'type':'disabled'}
    assert 'schema' in body['messages'][0]['content']
