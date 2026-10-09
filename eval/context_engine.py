"""Real local-model contextual evaluation. No CRM actions or contact delivery."""
import asyncio,json,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.conversation_engine import ConversationEngine
from app.project import FEATURES
from app.semantic_knowledge import SemanticKnowledge
from app import docs
from app.local_model import complete

CASES=[
 ('lead management','how to manage lead in your CRM',{},'product','leads',None),
 ('ungrammatical lead question','explain to we can manage lead',{},'product','leads',None),
 ('hinglish leads','lead manage kaise karte hai',{},'product','leads',None),
 ('data is different','Explain bulk prospect data management',{},'product','unknown',None),
 ('business','i am a developer',{},'customer','unknown',('organisation.type','developer')),
 ('team','300',{'pending_question':'organisation.agents'},'customer','unknown',('organisation.agents',300)),
 ('volume','100k',{'pending_question':'monthly_leads'},'customer','unknown',('monthly_leads',100000)),
 ('manual work','manually',{'pending_question':'pain_points'},'customer','unknown',('pain_points','manually')),
 ('other CRM','another CRM',{'pending_question':'process'},'customer','unknown',('process','another CRM')),
 ('decision maker','me',{'pending_question':'influence'},'customer','unknown',('influence','me')),
 ('timeline','now',{'pending_question':'next_step'},'customer','unknown',('next_step','now')),
 ('correction','Actually 30 people, not 300',{'pending_question':'monthly_leads','customer':{'organisation.agents':300}},'customer','unknown',('organisation.agents',30)),
 ('contextual reference','show that',{'last_feature':'site_visit','history':[{'role':'assistant','text':'We can schedule a site visit from the lead Status tab.'}]},'product','site_visit',None),
 ('accepted offer','yes',{'last_feature':'leads','last_offer':'add_lead'},'product','add_lead',None),
 ('topic switch','show projects',{'pending_question':'monthly_leads'},'product','projects',None),
 ('typo','how to do siteviste schedule',{},'product','site_visit',None),
 ('explain only','just explain leads, do not open anything',{},'product','leads',None),
 ('unsupported','Can you calculate payroll for employees?',{},'product','unknown',None),
 ('greeting','hi',{},'chat','unknown',None),
 ('unclear count','20-30k',{'pending_question':'monthly_leads'},'clarify','unknown',None),
 ('excel problem reply','excels',{'pending_question':'pain_points'},'customer','unknown',('process','excels')),
 ('excel current tool','Excel',{'pending_question':'process'},'customer','unknown',('process','Excel')),
]

async def run():
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');parser.add_argument('--products',action='store_true');parser.add_argument('--cases');parser.add_argument('--output',default='artifacts/context-model-evaluation.json');args=parser.parse_args()
 async def capture(*args,**kwargs):
  raw=await complete(*args,**kwargs)
  print('MODEL_OUTPUT '+json.dumps(raw,ensure_ascii=False),flush=True)
  return raw
 from app.conversation_store import ConversationStore
 store=ConversationStore();await store.start()
 knowledge=SemanticKnowledge(store)
 await knowledge.warm()
 engine=ConversationEngine(FEATURES,sorted({d['module'] for d in docs.load()}),knowledge,completion=capture)
 results=[]
 chosen=[CASES[i] for i in [0,4,5,6,7,8,14]] if args.smoke else ([c for c in CASES if c[3]=='product'] if args.products else CASES)
 if args.cases:chosen=[CASES[int(i)] for i in args.cases.split(',')]
 for i,(name,message,context,kind,feature,fact) in enumerate(chosen):
  base=dict(project='leadrat',session_id='eval-'+str(i),message=message,history=[],customer={},pending_question=None,last_feature=None,last_offer=None)
  base.update(context);t=time.monotonic()
  result=await engine.decide(**base);d=result['decision']
  passed=not result.get('error') and d['kind']==kind and d['feature']==feature
  if fact:passed=passed and any(u['field']==fact[0] and u['value']==fact[1] for u in d['updates'])
  if name=='explain only':passed=passed and not d['demo']
  elif kind=='product' and feature!='unknown':passed=passed and d['demo']
  row={'case':name,'message':message,'passed':passed,'seconds':round(time.monotonic()-t,3),'decision':d,'error':result.get('error'),'answer':result['answer']}
  results.append(row);print(json.dumps({k:row[k] for k in ['case','passed','seconds','error','decision']}),flush=True)
  (ROOT/args.output).write_text(json.dumps(results,indent=2,ensure_ascii=False),'utf8')
 await store.close()
 print('Passed',sum(x['passed'] for x in results),'/',len(results),flush=True)

if __name__=='__main__':asyncio.run(run())
