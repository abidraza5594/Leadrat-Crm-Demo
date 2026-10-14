"""Evaluate (and tune) how Beacon picks the CRM screen for a question.

Each case is a visitor message, optional earlier messages, and the screens that would be correct (paths
from knowledge/screens.json, or w:<walkthrough>). No model call is made: a decision taken from the
retrieval evidence alone must be right; when the evidence is not decisive the model chooses among the
options, which counts as recoverable if a correct screen is among the top three.

    python -m eval.screen_choice            # score the current settings
    python -m eval.screen_choice --tune     # search weights and thresholds
"""
import argparse
import asyncio
import itertools
import sys

CASES=[
 ('what is sale copilote',[],{'/sales-copilot'}),
 ('what is sale copilot',[],{'/sales-copilot'}),
 ('le me about sale copilot',[],{'/sales-copilot'}),
 ('tell me about sales copilot',[],{'/sales-copilot'}),
 ('salse copilt kya hai',[],{'/sales-copilot'}),
 ('can you show me all reports available',[],{'/reports/leads/status-report'}),
 ('i am takling about reports modeule',['can you show me all reports available'],{'/reports/leads/status-report'}),
 ('can you open lead status report',[],{'/reports/leads/status-report'}),
 ('reports me source wise leads kaha dekhu',[],{'/reports/leads/source-report'}),
 ('weebhook',[],{'/global-config'}),
 ('let me about webhook',[],{'/global-config'}),
 ('what about webhook',['kya ham facebook integrate kar sakte hai kya ?'],{'/global-config'}),
 ('99acres kaise connect kare',[],{'/global-config'}),
 ('99 acres kaise connect kare',[],{'/global-config'}),
 ('what is integration',[],{'/global-config'}),
 ('globel confeg ke bare me batao',[],{'/global-config'}),
 ('kya facebook interrate kar sakte hai',[],{'/global-config/facebook','/global-config'}),
 ('kya ham facebook integrate kar sakte hai kya ?',['kya facebook interrate kar sakte hai'],{'/global-config/facebook','/global-config'}),
 ('facebook se leads kaise aate hai',[],{'/global-config/facebook','/global-config','w:lead_sources'}),
 ('lead status kaise add kare',[],{'/global-config/manage-status'}),
 ('auto lead assignment kaise set kare',[],{'/global-config/auto-lead-assignment'}),
 ('whatsapp templates kaha hai',[],{'/global-config/templates','w:whatsapp_api'}),
 ('naya user kaise add kare team me',[],{'/teams/add-user','/teams/manage-user'}),
 ('attendance dikhao',[],{'/attendance'}),
 ('chatgpt se connect kaise kare',[],{'/leadrat-ai/connect-assistant','/leadrat-ai/overview'}),
 ('temm me about AI',[],{'/leadrat-ai/overview','/leadrat-ai/connect-assistant'}),
 ('listing management explain karo',[],{'/listing/manage-listing','/global-config/listing-management'}),
 ('data import kaise karte hai',[],{'/data/bulk-upload','w:bulk_upload','/data/manage-data'}),
 ('dashboard explain karo',[],{'w:dashboard','/dashboard/overview','/dashboard/stats','/dashboard/metrics'}),
 ('show me leads',[],{'w:leads','/leads/manage-leads'}),
 ('projects dikhao',[],{'w:projects','/projects/manage-projects'}),
 ('tasks kaha dekhu',[],{'w:tasks','/task/manage-task'}),
]

def key(entry):return 'w:'+entry['walkthrough'] if entry.get('walkthrough') else entry['path']

async def prepare():
    sys.path.insert(0,'.')
    from app.semantic_knowledge import SemanticKnowledge
    from app.screens import Screens
    from app.project import FEATURES,PROJECT
    knowledge=SemanticKnowledge(project=PROJECT['id'],directory=PROJECT['knowledge_dir']);await knowledge.warm()
    screens=Screens();screens.include(FEATURES);await screens.prepare(knowledge.model)
    prepared=[]
    for message,earlier,expected in CASES:
        # The same handbook steering as the conversation engine.
        hits=await knowledge.retrieve(message if screens.distinctive(message) else '\n'.join([message,*reversed(earlier)]))
        top=[doc for _,doc in hits[:3]]
        if len({doc['module'] for doc in top})!=1:top=[]
        areas=[a for m in dict.fromkeys(doc['module'] for doc in top) for a in knowledge.anchors(m)]
        weight=screens.coverage(message,[doc['text'] for doc in top]) if top else 0.0
        prepared.append((message,earlier,expected,areas,weight))
    return knowledge,screens,prepared

async def score(knowledge,screens,prepared,verbose=False):
    from app import screens as module
    right=wrong=recoverable=lost=0
    for message,earlier,expected,areas,weight in prepared:
        ranked=await screens.candidates(knowledge.model,message,areas=areas,context='\n'.join(reversed(earlier)),area_weight=weight)
        pick=module.decisive(ranked)
        if pick is not None:
            ok=key(pick) in expected;right+=ok;wrong+=not ok
            outcome=('right' if ok else 'WRONG')+' (no model call): '+key(pick)
        else:
            ok=any(key(e) in expected for _,e,_ in ranked[:3]);recoverable+=ok;lost+=not ok
            outcome=('model chooses, correct in top 3' if ok else 'MODEL CANNOT RECOVER')+': '+', '.join(key(e) for _,e,_ in ranked[:3])
        if verbose:print(f'{message!r:52} {outcome}')
    return right,wrong,recoverable,lost

async def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tune',action='store_true');args=parser.parse_args()
    from app import screens as module
    knowledge,screens,prepared=await prepare()
    if args.tune:
        best=None
        for weights in itertools.product((0.45,0.55,0.65),(0.3,0.4,0.5),(0.25,0.35,0.45),(0.0,0.1,0.2,0.3)):
            for clear,words in itertools.product((0.05,0.08,0.11),(0.3,)):
                module.WEIGHTS,module.CLEAR_LEAD,module.WORDS_LEAD=weights,clear,words
                right,wrong,recoverable,lost=await score(knowledge,screens,prepared)
                # A wrong screen opened without asking is the worst outcome; an unrecoverable choice next.
                value=(right+0.7*recoverable)-3*wrong-1*lost
                if best is None or value>best[0]:best=(value,weights,clear,words,(right,wrong,recoverable,lost))
        value,weights,clear,words,counts=best
        print(f'best: WEIGHTS={weights} CLEAR_LEAD={clear} WORDS_LEAD={words}  right={counts[0]} wrong={counts[1]} recoverable={counts[2]} lost={counts[3]}')
        module.WEIGHTS,module.CLEAR_LEAD,module.WORDS_LEAD=weights,clear,words
    right,wrong,recoverable,lost=await score(knowledge,screens,prepared,verbose=True)
    print(f'\n{len(prepared)} cases: {right} right without a model call, {wrong} wrong without a model call, '
          f'{recoverable} left to the model with a correct option, {lost} the model cannot get right')

if __name__=='__main__':asyncio.run(main())
