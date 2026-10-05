import asyncio
import pytest
from app.planner import plan
from app.docs import answer
@pytest.mark.parametrize('question,feature',[
 ('how i can add lead','add_lead'),
 ('how to add bulk lead','bulk_upload'),
 ('how to bulk delete leads','bulk_update'),
 ('how to delete multiple leads','bulk_update'),
])
def test_natural_lead_questions(question,feature):
 p,_=asyncio.run(plan(question,None))
 assert p.feature==feature and p.demo
 a=asyncio.run(answer(question))
 assert a['mode'] in {'reviewed_handbook','reviewed_screen_guide'}
 assert 'masters Defines' not in a['text']
