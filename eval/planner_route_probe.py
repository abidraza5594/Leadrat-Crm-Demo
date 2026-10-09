"""Bounded real-model classification check; no browser actions."""
import asyncio,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.local_model import complete
from app.project import FEATURES
from app.conversation_engine import QUESTIONS
from eval.context_engine import CASES

async def run():
 schema={'type':'object','properties':{'kind':{'type':'string','enum':['product','customer','clarify','chat','repeat','stop','decline']},'feature':{'type':'string','enum':['unknown',*FEATURES]},'demo':{'type':'boolean'}},'required':['kind','feature','demo'],'additionalProperties':False}
 system='You classify the LATEST visitor message in a CRM product demo conversation. Reply with the JSON decision only. Customer means information ABOUT THE VISITOR, including short answers to the pending question. Product means asking ABOUT CRM FEATURES, even during a pending question. Questions about managing leads select leads; bulk datasets select unknown. A product request normally needs demo=true unless the visitor asks only for explanation. Non-product uses feature=unknown and demo=false. Ambiguous number ranges use clarify. Never invent a feature. Available features: '+json.dumps({k:v['title'] for k,v in FEATURES.items()})
 for name,msg,ctx,kind,feature,fact in CASES:
  t=time.monotonic()
  context={'question':QUESTIONS.get(ctx.get('pending_question')),'previous_feature':ctx.get('last_feature'),'offered_feature':ctx.get('last_offer'),'history':ctx.get('history',[]),'latest_visitor_message':msg}
  try:r=await complete([{'role':'system','content':system},{'role':'user','content':json.dumps(context)}],schema,max_tokens=80)
  except Exception as e:r={'error':type(e).__name__}
  print(json.dumps({'case':name,'result':r,'pass':r.get('kind')==kind and r.get('feature')==feature,'seconds':round(time.monotonic()-t,2)}),flush=True)
if __name__=='__main__':asyncio.run(run())
