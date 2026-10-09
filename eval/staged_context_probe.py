"""Probe a staged prompt without changing the live application."""
import asyncio,json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from app.project import FEATURES
ROUTE='''Read the conversation and identify what the visitor is doing. Output only A, B or C.
A = asking about a product, requesting a demonstration, or accepting an offered demonstration.
B = describing their own business or answering a business question, including a short answer.
C = a greeting, thanks, unclear message, stopping, repeating or declining contact.'''
FACTS='''Extract facts from the visitor's CURRENT reply in the conversation. Do not answer the visitor.
Return only JSON: {"updates":[{"field":"FIELD","value":VALUE,"evidence":"exact words from current reply"}]}.
Fields: organisation.type (brokerage/developer/channel_partner), organisation.agents (integer), monthly_leads (integer), pain_points (text), process (text), influence (text), next_step (text), consent (boolean), contact (boolean).
Interpret the reply using the last question. 100k means 100000. A correction replaces the old value. Never invent facts. Evidence must be copied exactly from current reply. If nothing is stated return {"updates":[]}.'''
PRODUCT='''Choose the product feature that best matches the visitor's CURRENT request in this conversation. Return JSON only: {"feature":"ID","demo":true}. Use exactly one listed ID, or unknown when unsupported. demo is false only if the visitor explicitly asks not to open/show anything. Use the previous feature or offered demo for references such as "show that" or "yes".
Features: '''+json.dumps({k:f['title'] for k,f in FEATURES.items()})
CASES=[('manage leads','how to manage lead in your CRM','none','A','leads'),('business','i am a developer','none','B','organisation.type'),('team','300','How many people are on your sales team?','B','organisation.agents'),('volume','100k','Roughly how many new leads do you get in a month?','B','monthly_leads'),('manual','manually','What is the biggest problem with how you handle leads today?','B','pain_points'),('CRM','another CRM','What do you use to manage leads today?','B','process'),('switch','show projects','How many monthly leads do you get?','A','projects')]
async def run():
 out=[]
 async with httpx.AsyncClient(timeout=25) as c:
  async def ask(system,user,tokens):
   r=await c.post('http://127.0.0.1:8012/v1/chat/completions',json={'model':'qwen2.5-1.5b-instruct','messages':[{'role':'system','content':system},{'role':'user','content':user}],'max_tokens':tokens,'temperature':0});r.raise_for_status();return r.json()['choices'][0]['message']['content']
  for name,message,pending,expected,field in CASES:
   user='Last question: '+pending+'\nCurrent visitor reply: '+message;t=time.monotonic()
   route=await ask(ROUTE,user,5)
   detail=await ask(FACTS if expected=='B' else PRODUCT,user,100)
   row={'case':name,'expected_route':expected,'route':route,'detail':detail,'seconds':round(time.monotonic()-t,2)};out.append(row);print(json.dumps(row),flush=True)
   Path('artifacts/staged-context-probe.json').write_text(json.dumps(out,indent=2),encoding='utf8')
asyncio.run(run())
