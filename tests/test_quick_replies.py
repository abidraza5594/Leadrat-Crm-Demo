import asyncio
from app import main
from app.quick_replies import for_question

def test_options_follow_session_question_and_do_not_grant_consent():
    s=main.Session(pending_discovery='organisation.type')
    options=s.snapshot()['quick_replies']['options']
    assert [o['label'] for o in options]==['Developer','Brokerage','Channel partner']
    assert not s.discovery_answers
    s.pending_discovery='consent'
    assert len(s.snapshot()['quick_replies']['options'])==2
    assert 'consent' not in s.discovery_answers
    s.opted_out=True
    assert s.snapshot()['quick_replies'] is None
    s.opted_out=False;s.lead_draft={'phase':'name'}
    assert s.snapshot()['quick_replies'] is None
    assert for_question(None) is None

def test_click_answers_use_the_normal_conversation_and_advance(isolated_conversation_model):
    developer=for_question('organisation.type')['options'][0]['message']
    team=for_question('organisation.agents')['options'][2]['message']
    isolated_conversation_model[developer]={'kind':'customer','updates':[{'field':'organisation.type','value':'developer','evidence':'developer'}]}
    isolated_conversation_model[team]={'kind':'customer','updates':[{'field':'organisation.agents','value':25,'evidence':'25'}]}
    async def run():
        s=main.Session(voice_enabled=False,pending_discovery='organisation.type',discovery_asked=['organisation.type'])
        await main.execute(s,developer)
        assert s.discovery_answers['organisation.type']=='developer'
        assert s.snapshot()['quick_replies']['question']=='organisation.agents'
        await main.execute(s,team)
        assert s.discovery_answers['organisation.agents']==25
        assert s.snapshot()['quick_replies']['question']=='monthly_leads'
        assert not s.steps
        if s.qual_task:s.qual_task.cancel()
    asyncio.run(run())
