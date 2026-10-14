import asyncio,json
from app.semantic_knowledge import SemanticKnowledge
from app.conversation_engine import Decision

def knowledge(completion):
    k=SemanticKnowledge(completion=completion);k.ready=True
    k.documents=[{'id':1,'module':'Inventory','section':'Purpose and overview','text':'Tracks available units.','page':3},
                 {'id':2,'module':'Work orders','section':'Purpose and overview','text':'Tracks assigned work.','page':5}]
    async def retrieve(*args,**kwargs):return [(0.8,k.documents[0])]
    k.retrieve=retrieve
    return k

def test_document_inventory_answers_without_any_demo(monkeypatch):
    async def complete(messages,schema,**kw):
        body=json.loads(messages[-1]['content'])
        if 'valid' in schema['properties']:return {'valid':True,'reason':''}
        assert body['handbook_main_module_count']==2
        assert body['handbook_main_modules']==['Inventory','Work orders']
        assert body['selected_demo'] is None
        return {'supported':True,'answer':'There are two documented modules: Inventory and Work orders.',
                'evidence_ids':['doc:1#0','doc:2#0'],'demo_requested':False,'evidence_quotes':[{'source_id':'doc:1#0','quote':'Tracks available units.'},{'source_id':'doc:2#0','quote':'Tracks assigned work.'}]}
    k=knowledge(complete)
    result=asyncio.run(k.answer('What can this product do?',Decision(kind='product'),{}))
    assert result['grounded'] and not result['demo_requested'] and result['mode']=='contextual_handbook_model'

def test_followup_context_is_supplied_to_search_and_answer():
    calls=[]
    history=[{'role':'user','text':'Tell me about available inventory'}]
    async def complete(messages,schema,**kw):
        if 'valid' in schema['properties']:return {'valid':True,'reason':''}
        body=json.loads(messages[-1]['content']);assert body['conversation']==history
        return {'supported':True,'answer':'Inventory tracks available units.','evidence_ids':['doc:1#0'],'demo_requested':False,'evidence_quotes':[{'source_id':'doc:1#0','quote':'Tracks available units.'}]}
    k=knowledge(complete)
    async def retrieve(question,topic=None,**kwargs):calls.append((question,topic));return [(0.8,k.documents[0])]
    k.retrieve=retrieve
    asyncio.run(k.answer('Explain that further',Decision(kind='product'),{},history=history))
    assert calls[0][0]=='Explain that further' and 'available inventory' in calls[1][0]
    assert calls[1][0].startswith('Explain that further\n')


def test_full_inventory_is_derived_from_document_in_page_order():
    async def complete(messages,schema,**kw):
        if 'valid' in schema['properties']:return {'valid':True,'reason':''}
        return {'supported':True,'answer':'Here are the documented modules.',
                'include_module_list':True,'evidence_ids':['catalogue:modules#0'],'demo_requested':False}
    k=knowledge(complete)
    k.documents.reverse()  # Database retrieval order must not reorder the PDF.
    result=asyncio.run(k.answer('Give me the full catalogue',Decision(kind='product'),{}))
    assert result['text'].endswith('- Inventory\n- Work orders')
    assert '(2)' in result['text'] and result['grounded']


def test_specific_module_does_not_receive_whole_product_list():
    async def complete(messages,schema,**kw):
        if 'valid' in schema['properties']:return {'valid':True,'reason':''}
        return {'supported':True,'answer':'Inventory tracks units.',
                'include_module_list':True,'evidence_ids':['doc:1#0'],'demo_requested':False}
    result=asyncio.run(knowledge(complete).answer('What is in Inventory?',Decision(kind='product',topic='Inventory'),{}))
    assert result['text']=='Inventory tracks units.'


def test_inventory_without_generated_introduction_is_a_valid_answer():
    async def complete(messages,schema,**kw):
        assert 'valid' not in schema['properties']
        return {'supported':True,'answer':'','include_module_list':True,
                'evidence_ids':[],'demo_requested':False}
    result=asyncio.run(knowledge(complete).answer('What modules are documented?',Decision(kind='product'),{}))
    assert result['grounded'] and result['text'].endswith('- Inventory\n- Work orders')
    assert result['sources'][0]['id']=='catalogue:modules#0'

def test_invented_source_cannot_be_presented_as_grounded():
    async def complete(*args,**kwargs):return {'supported':True,'answer':'Invented fact','evidence_ids':['not-in-pdf'],'demo_requested':False}
    result=asyncio.run(knowledge(complete).answer('A question',Decision(kind='product'),{}))
    assert not result['grounded'] and result['mode']=='knowledge_unavailable'

def test_unverified_claim_is_rewritten_before_delivery():
    drafts=[]
    async def complete(messages,schema,**kw):
        if 'valid' in schema['properties']:
            bad='unlimited' in json.loads(messages[-1]['content'])['answer']
            return {'valid':not bad,'reason':'Unlimited capacity is not documented' if bad else ''}
        payload=json.loads(messages[-1]['content']);drafts.append(payload)
        text='Inventory supports unlimited units.' if len(drafts)==1 else 'Inventory tracks available units.'
        return {'supported':True,'answer':text,'evidence_ids':['doc:1#0'],'demo_requested':False,'evidence_quotes':[{'source_id':'doc:1#0','quote':'Tracks available units.'}]}
    result=asyncio.run(knowledge(complete).answer('What can inventory do?',Decision(kind='product'),{}))
    assert result['text']=='Inventory tracks available units.' and result['generation_attempts']==2
    assert 'Unlimited' in drafts[1]['revision_needed']['unsupported_claims']

def test_verifier_outage_does_not_publish_unchecked_draft():
    async def complete(messages,schema,**kw):
        if 'valid' in schema['properties']:raise TimeoutError()
        return {'supported':True,'answer':'Potential draft','evidence_ids':['doc:1#0'],'demo_requested':False,'evidence_quotes':[{'source_id':'doc:1#0','quote':'Tracks available units.'}]}
    result=asyncio.run(knowledge(complete).answer('A question',Decision(kind='product'),{}))
    assert not result['grounded'] and result['error']=='TimeoutError'

def test_support_playbook_is_used_only_when_the_model_judges_a_reported_problem():
    playbook={'id':7,'module':'Inventory','section':'Troubleshooting matrix','text':'Check permissions before concluding units are missing.','page':4}
    seen=[]
    async def complete(messages,schema,**kw):
        if 'valid' in schema['properties']:return {'valid':True,'reason':''}
        seen.append({r['id'].split('#')[0] for r in json.loads(messages[-1]['content'])['references']})
        return {'supported':True,'answer':'Inventory tracks available units.','evidence_ids':['doc:1#0'],'demo_requested':False}
    k=knowledge(complete)
    async def retrieve(*args,**kwargs):return [(0.9,playbook),(0.8,k.documents[0])]
    k.retrieve=retrieve
    asyncio.run(k.answer('What does inventory do?',Decision(kind='product'),{}))
    asyncio.run(k.answer('Why are units not showing in inventory?',Decision(kind='product',problem=True),{}))
    assert 'doc:7' not in seen[0] and 'doc:1' in seen[0]
    assert 'doc:7' in seen[1]

def test_retrieval_fuses_meaning_and_exact_terms_and_reads_handbook_anchors():
    import numpy as np
    k=SemanticKnowledge();k.ready=True
    k.documents=[{'id':1,'module':'Org Profile','section':'Purpose and overview','page':25,
                  'text':'Stores organisation identity. Navigation anchor Org Profile / Organisation Profile Module boundary Org Profile is metadata.'},
                 {'id':2,'module':'Task','section':'Feature catalogue','page':21,'text':'Task creation assigns work items.'}]
    class Model:
        def encode(self,text,**kw):return np.array([1.0,0.0]) if isinstance(text,str) else np.array([[0.0,1.0],[1.0,0.0]])
    k.model=Model();k.vectors=np.array([[0.0,1.0],[1.0,0.0]])
    # Meaning prefers the Task chunk; the exact term "logo"-free question about organisation identity is found by BM25.
    hits=asyncio.run(k.retrieve('organisation identity'))
    assert {d['module'] for _,d in hits}=={'Org Profile','Task'} and hits[0][1]['module']=='Org Profile'
    assert k.anchors('Org Profile')==['Org Profile','Organisation Profile'] and k.anchors('Task')==[]

def test_failed_answer_about_a_shown_screen_falls_back_to_the_screen_itself():
    """Live: "Answer did not pass source checking" / "Empty generated answer" left the visitor with
    "I could not finish checking the handbook". The screen being shown is a source in its own right."""
    location={'id':'p9','path':'/global-config/facebook','page':'Global Config › Facebook','section':None,
              'text':'Global Config › Facebook: Facebook, Add Account, Login With Facebook, Ad Accounts, Lead Forms, Connect Now'}
    async def complete(messages,schema,**kw):
        if 'valid' in schema['properties']:return {'valid':False,'reason':'Unsupported claim'}
        return {'supported':True,'answer':'Facebook shows campaign analytics.','evidence_ids':['screen:p9#0'],'demo_requested':False,'include_module_list':False}
    result=asyncio.run(knowledge(complete).answer('kya facebook integrate kar sakte hai',Decision(kind='product'),{},location=location))
    assert result['grounded'] and result['mode']=='screen_text'
    assert result['text'].startswith('This is the Global Config › Facebook screen in Leadrat, which shows Facebook, Add Account, Login With Facebook')
    assert 'analytics' not in result['text']
