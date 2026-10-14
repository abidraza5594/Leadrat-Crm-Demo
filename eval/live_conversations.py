"""Replay real visitor conversations through the full Beacon turn logic with the configured model.

The CRM browser is replaced by a recorder, so no screen is opened; everything else is live: retrieval,
the planning call, grounded answers, discovery and memory. Each turn prints what Beacon decided and said.

    python -m eval.live_conversations
"""
import asyncio
import sys
import time

CONVERSATIONS={
 'overview and reports':['whta u can explain','can you show me all reports available','can you open lead status report',
     'me lead status nahi lead report ke ander status ki bat kar rha hu'],
 'discovery':['dasboar explain karo','i am developer','600','10k','excels','i am not using any tools','follow up miss ho jate hai',
     'me','now','9999999999','no thatks','nothing'],
 'integrations and follow-ups':['what is sale copilote','what about webhook','isme kya hota hai','kya ham facebook integrate kar sakte hai kya ?',
     '99acres kaise connect kare','chatgpt se connect kaise kare'],
 'screens and manners':['hello','naya user kaise add kare team me','org ka logo kaise change kare','show me leads',
     "explain lead status but don't open any screen",'thank you'],
}

class Recorder:
    """Stands in for the CRM browser: records what would be opened."""
    def __init__(self):self.events=[]
    async def open_module(self,f):self.events.append('walkthrough '+f['id']);return f['title']+' (would open)'
    async def open_location(self,location):
        self.events.append('screen '+location['path']+(' › '+location['section'] if location.get('section') else ''))
        return location['page']+' is open'+(' and its "'+location['section']+'" section is highlighted.' if location.get('section') else '.')
    async def signed_in(self):return True

async def main(names):
    sys.path.insert(0,'.')
    from app import main as app,docs,config
    from app.project import PROJECT
    print('model:',config.PROVIDER,config.DEEPSEEK_MODEL if config.PROVIDER=='deepseek' else config.PLANNER_MODEL,flush=True)
    await app.knowledge.warm();await app.screens.prepare(app.knowledge.model)
    app.engine.topics=sorted({c['module'] for c in docs.load(PROJECT['knowledge_dir'])})
    for name,turns in CONVERSATIONS.items():
        if names and name not in names:continue
        print(f'\n===== {name} =====',flush=True)
        worker=Recorder();s=app.Session(worker=worker);app.sessions[s.id]=s
        s.say('Welcome to Beacon.')
        for message in turns:
            s.messages.append({'id':'u'+str(len(s.messages)),'role':'user','text':message});before=len(s.messages);events=len(worker.events)
            s.turn_started=time.monotonic();s.timings.append({})
            started=time.monotonic();await app.execute(s,message);took=time.monotonic()-started
            d=s.last_decision or {}
            print(f'\nYOU: {message}   [{took:.1f}s | {d.get("kind")} | understood: {d.get("understanding","")[:90]}]',flush=True)
            for e in worker.events[events:]:print('  >> '+e,flush=True)
            for m in s.messages[before:]:print('  BEACON: '+m['text'].replace('\n',' | ')[:330],flush=True)
        if s.qual_task:s.qual_task.cancel()
        app.sessions.pop(s.id,None)

if __name__=='__main__':asyncio.run(main(sys.argv[1:]))
