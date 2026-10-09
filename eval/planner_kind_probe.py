import asyncio,json,sys,time,httpx
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.local_model import complete
from app.conversation_engine import QUESTIONS
from eval.context_engine import CASES
async def run():
 schema={'type':'object','properties':{'kind':{'type':'string','enum':['PRODUCT_QUESTION','CUSTOMER_FACT','UNCLEAR','GREETING','REPEAT','STOP','DECLINE_CONTACT']}},'required':['kind'],'additionalProperties':False}
 system='Examples: After asking about current tools, reply spreadsheets is CUSTOMER_FACT. After asking about timing, reply as soon as possible is CUSTOMER_FACT. A request to display the earlier topic is PRODUCT_QUESTION. Classify the latest visitor message only. PRODUCT_QUESTION: asks how the software works or requests/accepts a demo. CUSTOMER_FACT: states information about themselves or answers our previous business question. UNCLEAR: cannot understand. GREETING: hello or thanks. REPEAT: asks to repeat. STOP: stop demo. DECLINE_CONTACT: refuses sales contact. Do not answer the visitor. The visitor may interrupt a business question with a product question.'
 mapping={'PRODUCT_QUESTION':'product','CUSTOMER_FACT':'customer','UNCLEAR':'clarify','GREETING':'chat','REPEAT':'repeat','STOP':'stop','DECLINE_CONTACT':'decline'}
 for name,msg,ctx,kind,feature,fact in CASES:
  question=QUESTIONS.get(ctx.get('pending_question')) or ('Shall I show '+ctx['last_offer']+'?' if ctx.get('last_offer') else 'Ask me about the CRM.')
  t=time.monotonic()
  try:r=await complete([{'role':'system','content':system},{'role':'user','content':'Previous assistant question (context only): '+question+'\nVisitor message to classify: '+msg}],schema,max_tokens=35)
  except Exception as e:r={'error':type(e).__name__}
  print(json.dumps({'case':name,'result':r,'pass':mapping.get(r.get('kind'))==kind,'seconds':round(time.monotonic()-t,2)}),flush=True)
if __name__=='__main__':asyncio.run(run())
