import asyncio
import pytest
from app import main
@pytest.mark.parametrize('question,feature',[
 ('how i can add lead','add_lead'),
 ('how to add bulk lead','bulk_upload'),
 ('how to bulk delete leads','bulk_update'),
 ('how to delete multiple leads','bulk_update'),
])
def test_lead_answer_follows_selected_capability(question,feature,isolated_conversation_model):
 isolated_conversation_model[question]={'kind':'product','feature':feature,'topic':'Lead Management','demo':True}
 result=asyncio.run(main.engine.decide(session_id='routing-test',message=question,history=[],customer={}))
 assert result['decision']['feature']==feature
 assert result['answer']['grounded'] and 'masters Defines' not in result['answer']['text']
