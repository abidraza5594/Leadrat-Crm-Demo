"""Real adapter replay of the recorded synthetic live conversation.

The accepted ledger is supplied from the verified test conversation. This
isolates extractor/validation behavior; it is not a new browser or planner test.
"""
import asyncio,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import main,qualify

async def run():
    report=json.loads((ROOT/'artifacts/live-context-final-acceptance.json').read_text('utf8'))
    messages=[];fact_ids={}
    facts={'I am a developer':('organisation.type','developer'),'23':('organisation.agents',23),
           '20k':('monthly_leads',20000),'excels':('process','excels'),
           'We miss follow-ups':('pain_points','We miss follow-ups'),'me':('influence','me'),
           'now':('next_step','now'),'No, do not contact me':('consent',False)}
    answers={}
    for row in report['turns']:
        message=row['question'];identity='u'+str(len(messages)+1)
        messages.append({'id':identity,'role':'user','text':message,
                         'kind':'product_question' if row['steps'] else 'customer_answer'})
        if message in facts:
            field,value=facts[message];answers[field]=value
            fact_ids[field]={'message_id':identity,'quote':message}
        for reply in row['replies']:
            # Keep actual questions needed to interpret short visitor answers.
            kind=None if reply.rstrip().endswith('?') else 'product_answer' if row['steps'] else 'customer_ack'
            messages.append({'id':'a'+str(len(messages)+1),'role':'assistant','text':reply,'kind':kind})
    raw=[];original=qualify._chat
    async def capture(*args,**kwargs):
        value=await original(*args,**kwargs);raw.append(value);return value
    qualify._chat=capture
    started=time.monotonic();result=await qualify.qualify_session(messages)
    s=main.Session(messages=messages,discovery_answers=answers,fact_evidence=fact_ids,opted_out=True)
    q=main.accepted_qualification(s,result)
    checks={'actual_adapter_used':result['source']=='slm','team':q['organisation']['agents']==23,
            'leads':q['monthly_leads']['min']==20000,'problem':q['pain_points']==['We miss follow-ups'],
            'tool':q['process']=='manual','decision_maker':q['influence']=='approver',
            'no_contact':q['consent'] is False and q['route']=='graceful_close'}
    output={'scope':__doc__,'seconds':round(time.monotonic()-started,3),'transcript':qualify.transcript_of(messages),
            'raw_outputs':raw,'result':result,'accepted_qualification':q,'checks':checks}
    (ROOT/'artifacts/live-qualification-filtered-replay.json').write_text(json.dumps(output,indent=2),'utf8')
    print(json.dumps({'seconds':output['seconds'],'checks':checks,'attempts':result['attempts']}),flush=True)

if __name__=='__main__':asyncio.run(run())
