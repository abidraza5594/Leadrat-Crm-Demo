import asyncio,json
import pytest
from app import main,handoff
from slm.labels import Extraction,complete

@pytest.mark.parametrize('message', ['There are 1,000-plus.', "I'm telling you, 1,000-plus.", 'एक हज़ार से ज़्यादा लोग हैं।'])
def test_count_bound_is_preserved_and_next_question_is_asked(monkeypatch,message):
    async def findings(state):return [],[]
    async def completion(messages,schema,**kwargs):
        if schema.get('required')==['supported','value','relation']:
            payload=json.loads(messages[-1]['content'])
            assert payload['message']==message and 'sales team' in payload['pending_question']
            return {'supported':True,'value':1000,'relation':'at_least'}
        return {'kind':'customer','updates':[{'field':'organisation.agents','value':'1000-plus','evidence':message}]}
    monkeypatch.setattr(main.engine,'findings',findings)
    monkeypatch.setattr(main.engine,'completion',completion)
    async def run():
        s=main.Session(pending_discovery='organisation.agents',discovery_answers={'organisation.type':'developer'},discovery_asked=['organisation.type','organisation.agents'])
        s.messages.append({'id':'u1','role':'user','text':message})
        await main.execute(s,message)
        assert s.discovery_answers['organisation.agents']==1000
        assert s.discovery_answers['organisation.agents.relation']=='at_least'
        assert s.pending_discovery=='monthly_leads'
        assert any('1,000+' in m['text'] for m in s.messages if m['role']=='assistant')
        q=main.accepted_qualification(s,{'source':'slm','qualification':complete(Extraction()).model_dump()})
        assert q['organisation']['agents'] is None  # Never claim an exact headcount.
        assert q['count_details']['organisation.agents']['relation']=='at_least'
        assert handoff.brief(s.id,q,[])['count_details']==q['count_details']
        if s.qual_task:
            s.qual_task.cancel();await asyncio.gather(s.qual_task,return_exceptions=True)
    asyncio.run(run())


def test_unrelated_sentence_does_not_turn_one_into_team_size(monkeypatch):
    message='One person who leans back and does.'
    async def findings(state):return [],[]
    async def completion(messages,schema,**kwargs):
        if schema.get('required')==['supported','value','relation']:
            return {'supported':False,'value':0,'relation':'exact'}
        return {'kind':'customer','updates':[{'field':'organisation.agents','value':'one','evidence':'One'}]}
    monkeypatch.setattr(main.engine,'findings',findings)
    monkeypatch.setattr(main.engine,'completion',completion)
    result=asyncio.run(main.engine.plan({'message':message,'pending_question':'organisation.agents'}))
    assert result['decision']['updates']==[] and result['decision']['kind']=='clarify'
