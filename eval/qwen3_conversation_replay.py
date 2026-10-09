"""State-carrying model replay, without browser actions or sales contact."""
import asyncio,json,sys,time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from eval.qwen3_adapter_check import infer,OUT,URL
from app.conversation_engine import ConversationEngine,QUESTIONS
from app.semantic_knowledge import SemanticKnowledge
from app.project import FEATURES
from app import docs

async def main():
    headers={'Authorization':'Bearer '+(ROOT/'.state/qwen3-evaluation.key').read_text('ascii')}
    knowledge=SemanticKnowledge();await knowledge.warm()
    async with httpx.AsyncClient(headers=headers,timeout=180) as client:
        async def complete(messages,schema,max_tokens=240):
            messages=[dict(m) for m in messages]
            messages[0]['content']+='\nReturn only a JSON object matching this schema: '+json.dumps(schema,separators=(',',':'))
            return (await infer(client,messages,schema,max_tokens))[1]
        engine=ConversationEngine(FEATURES,sorted({d['module'] for d in docs.load()}),knowledge,completion=complete)
        state=dict(session_id='continuous-model-replay',history=[],customer={},pending_question=None,last_feature=None,last_offer=None)
        # Fixed business-question order represents the conversation, not a live UI.
        turns=[
          ('i am a developer','customer','unknown',('organisation.type','developer')),
          ('300','customer','unknown',('organisation.agents',300)),
          ('100k','customer','unknown',('monthly_leads',100000)),
          ('manually','customer','unknown',('pain_points','manually')),
          ('another CRM','customer','unknown',('process','another CRM')),
          ('me','customer','unknown',('influence','me')),
          ('now','customer','unknown',('next_step','now')),
          ('how to manage lead in your CRM','product','leads',None),
          ('how to do siteviste schedule','product','site_visit',None),
          ('show that','product','site_visit',None),
          ('Actually 30 people, not 300','customer','unknown',('organisation.agents',30)),
          ('show projects','product','projects',None),
          ('just explain leads, do not open anything','product','leads',None),
        ]
        rows=[]
        async def record(name,message,context,kind,feature,fact=None):
            started=time.monotonic();given=json.loads(json.dumps(context))
            result=await engine.decide(message=message,**context);d=result['decision']
            checks={'kind':d['kind']==kind,'feature':d['feature']==feature,'no_error':not result.get('error')}
            if fact:checks['fact']=any(u['field']==fact[0] and u['value']==fact[1] for u in d['updates'])
            if 'do not open anything' in message:checks['no_demo']=not d['demo']
            row=dict(name=name,message=message,context=given,expected=dict(kind=kind,feature=feature,fact=fact),actual=result,checks=checks,passed=all(checks.values()),seconds=round(time.monotonic()-started,3))
            rows.append(row)
            (OUT/'conversation_replay.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),'utf-8')
            print(json.dumps(dict(name=name,passed=row['passed'],seconds=row['seconds'])),flush=True)
            return d
        for index,(message,kind,feature,fact) in enumerate(turns,1):
            d=await record('continuous turn '+str(index),message,state,kind,feature,fact)
            for u in d['updates']:state['customer'][u['field']]=u['value']
            if d['kind']=='product' and d['feature']!='unknown':state['last_feature']=d['feature']
            if d['kind']=='customer':state['pending_question']=next((k for k in list(QUESTIONS)[:7] if k not in state['customer']),None)
            # No fabricated browser-success messages in the replay history.
            reply=QUESTIONS.get(state['pending_question']) or d.get('reply') or ('Discussing '+d['feature'] if d['kind']=='product' else 'Thank you.')
            state['history']=(state['history']+[{'role':'user','text':message},{'role':'assistant','text':reply}])[-8:]
        targeted=[
          ('wrong pending field','Please record 12k new leads per month.','organisation.agents','customer','unknown',('monthly_leads',12000)),
          ('email intent','I want to compose a customer email.','influence','product','email',None),
          ('lead history','I want to track earlier activities on a lead.','influence','product','history',None),
          ('whatsapp intent','Please show me how to start WhatsApp from lead details.',None,'product','whatsapp',None),
          ('immediate timeline','We need it immediately','next_step','customer','unknown',None),
          ('pain case preservation','Leads wait too long for a reply','pain_points','customer','unknown',None),
        ]
        for name,message,pending,kind,feature,fact in targeted:
            context=dict(session_id='targeted-'+name,history=[],customer={},pending_question=pending,last_feature=None,last_offer=None)
            await record(name,message,context,kind,feature,fact)
        summary=dict(scope='13 connected model turns, then 6 diagnostic cases selected after initial failures; no CRM clicks, browser, voice or persistent database tested',tested=len(rows),passed=sum(r['passed'] for r in rows),failed=[r['name'] for r in rows if not r['passed']])
        (OUT/'conversation_replay_summary.json').write_text(json.dumps(summary,indent=2),'utf-8')
        print(json.dumps(summary),flush=True)

if __name__=='__main__':asyncio.run(main())
