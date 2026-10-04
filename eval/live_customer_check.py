"""A synthetic customer turn through the running app; no consent or delivery."""
import asyncio
import json
import time
from pathlib import Path
import httpx

async def main():
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8010',timeout=30) as c:
        r=await c.post('/api/sessions',json={'parent_origin':'http://localhost:8011','voice':False})
        r.raise_for_status();s=r.json();url='/api/sessions/'+s['session_id'] if 'session_id' in s else '/api/sessions/'+s['id']
        headers={'x-beacon-token':s['token']}
        question='My name is Ravi. We are a brokerage with 12 agents and 300 leads per month. We use Excel manually and miss follow-ups. I have not agreed to sales contact.'
        try:
            r=await c.post(url+'/turn',headers=headers,json={'message':question,'request_id':'acceptance-live-customer-01'})
            r.raise_for_status()
            deadline=time.monotonic()+65
            while time.monotonic()<deadline:
                r=await c.get(url,headers=headers);r.raise_for_status();state=r.json()
                if state['qualification'].get('scorer') in ('hosted','slm','rules'): break
                await asyncio.sleep(1)
            q=state['qualification']
            checks={'name':q.get('contact',{}).get('name')=='Ravi',
                    'agents':q.get('organisation',{}).get('agents')==12,
                    'leads':q.get('monthly_leads',{}).get('min')==300,
                    'consent':q.get('consent') is False,
                    'no_delivery':state.get('handoff_status')=='not_requested',
                    'hosted_used':q.get('scorer')=='hosted'}
            Path('artifacts/live-customer-check-2026-10-01.json').write_text(json.dumps({'question':question,'qualification':q,'checks':checks},indent=2),encoding='utf-8')
            print(json.dumps(checks))
        finally: await c.delete(url,headers=headers)

if __name__=='__main__':asyncio.run(main())
