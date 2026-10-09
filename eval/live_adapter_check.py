"""Reproducible direct adapter checks; never sends a sales handoff or CRM write."""
import asyncio, json, time, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import httpx
from slm.prompting import messages, parse

CASES=[
 ('complete customer', [('visitor','I am a property developer with 30 sales agents and 2000 new leads per month. We use Excel manually and miss follow-ups. I decide on the CRM purchase and want it within 30 days. I have not agreed to sales contact.')],
  {'organisation.type':'developer','organisation.agents':30,'monthly_leads.min':2000,'monthly_leads.max':2000,'process':'manual','influence':'approver','next_step':'within_30_days','consent':False,'contact.email':None,'contact.phone':None}),
 ('short contextual replies', [('beacon','Are you a brokerage, developer or channel partner?'),('visitor','developer'),('beacon','How many people are on your sales team?'),('visitor','300'),('beacon','Roughly how many new leads do you get in a month?'),('visitor','100k'),('beacon','What do you use to manage leads today?'),('visitor','Excel')],
  {'organisation.type':'developer','organisation.agents':300,'monthly_leads.min':100000,'monthly_leads.max':100000,'process':'manual','consent':False}),
 ('corrected facts', [('visitor','We are a brokerage with 300 sales agents and 5000 monthly leads.'),('visitor','Correction: 30 sales agents and 2000 monthly leads. My name is Demo Person.')],
  {'organisation.type':'brokerage','organisation.agents':30,'monthly_leads.min':2000,'monthly_leads.max':2000,'contact.name':'Demo Person','consent':False}),
 ('withdraw permission', [('visitor','We are a developer. Yes, sales may contact me at demo@example.invalid.'),('visitor','Do not contact me. Remove my email.')],
  {'consent':False,'contact.email':None,'next_step':'declined'}),
 ('question is not a customer fact', [('visitor','How can a developer with 300 agents manage 100k leads? This is just a hypothetical question, not my business.')],
  {'organisation.type':'unknown','organisation.agents':None,'monthly_leads.min':None,'monthly_leads.max':None,'consent':False}),
]

def field(data,path):
 for part in path.split('.'):data=data.get(part) if isinstance(data,dict) else None
 return data

async def run():
 import argparse
 from datetime import datetime,timezone
 parser=argparse.ArgumentParser();parser.add_argument('--output',default='artifacts/live-adapter-check-2026-10-06.json');parser.add_argument('--limit',type=int,default=len(CASES));args=parser.parse_args()
 out=ROOT/args.output
 async with httpx.AsyncClient(timeout=150) as client:
  health=(await client.get('http://127.0.0.1:8012/health')).json()
  release=json.loads((ROOT/'slm/current_release.json').read_text())
  assert health['weights_sha256']==release['weights_sha256']
  report={'started_at':datetime.now(timezone.utc).isoformat(),'health':health,'results':[],'scope':'Direct trained adapter, raw results before application validation; no CRM writes or handoff.'}
  for name,conversation,expected in CASES[:args.limit]:
   turns=[{'turn_id':i+1,'speaker':role,'text':text} for i,(role,text) in enumerate(conversation)]
   row={'case':name,'transcript':turns,'expected':expected}; started=time.monotonic()
   try:
    response=await client.post('http://127.0.0.1:8012/v1/chat/completions',json={'model':'beacon-v4','messages':messages(turns),'max_tokens':900,'temperature':0})
    response.raise_for_status();data=response.json()
    assert data['weights_sha256']==release['weights_sha256']
    row['raw_output']=data['choices'][0]['message']['content']
    q,reason=parse(row['raw_output'],turns);row['parse_reason']=reason
    actual=q.model_dump() if q else {};row['actual']=actual
    row['checks']={path:{'expected':value,'actual':field(actual,path),'passed':q is not None and field(actual,path)==value} for path,value in expected.items()}
    row['passed']=q is not None and reason is None and all(c['passed'] for c in row['checks'].values())
   except Exception as exc:row.update(passed=False,error=type(exc).__name__+': '+str(exc))
   row['seconds']=round(time.monotonic()-started,2);report['results'].append(row)
   out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
   print(json.dumps({k:row[k] for k in ('case','passed','seconds')}),flush=True)
 print('Saved',out,flush=True)

if __name__=='__main__':asyncio.run(run())
