import asyncio
import pytest
from app.planner import small_talk
from app.planner import plan
from app.browser import BrowserWorker,LOGIN_BLOCKED,LOGIN_FIELDS,NAV

@pytest.mark.parametrize('message',['Hi, what can you show me today?','Hello Beacon! What can we explore today?','How can you help me?','What can you show?'])
def test_natural_demo_introduction(message):
    assert 'Leads' in small_talk(message)

def test_greeting_does_not_swallow_a_real_request():
    assert small_talk('Hi, delete all leads') is None
    assert small_talk('Hello, show projects') is None
    assert small_talk('Hi, what can you show me about pricing?') is None

def test_password_help_is_not_a_lockout_error():
    assert not LOGIN_BLOCKED.search('Click here to reset your password')
    assert LOGIN_BLOCKED.search('Your account has been locked')
    assert LOGIN_BLOCKED.search('You must reset your password')

class Locator:
    def __init__(self,visible):self.visible=visible
    async def count(self):return len(self.visible)
    def nth(self,i):return Locator([self.visible[i]])
    async def is_visible(self):return self.visible[0]

class Page:
    url='https://crm.example.com/'
    def __init__(self,nav,password):self.nav,self.password=nav,password
    def is_closed(self):return False
    def locator(self,selector):return Locator(self.nav if selector==NAV else self.password)

@pytest.mark.parametrize('nav,password,expected',[([False],[],False),([True],[True],False),([False,True],[False],True)])
def test_auth_requires_visible_workspace_without_login_form(nav,password,expected):
    worker=BrowserWorker();worker.page=Page(nav,password)
    assert asyncio.run(worker.authenticated()) is expected

@pytest.mark.parametrize('question,feature',[
    ('How do I add a new lead status or substatus?','unknown'),
    ('Why is Offplan data different from the Project module?','unknown'),
    ('How do I bulk upload inventory?','unknown'),
    ('Where can I see who changed the lead owner or status?','history'),
    ('Can I link a task to a lead or project?','tasks'),
])
def test_handbook_questions_do_not_open_similar_wrong_screens(question,feature):
    selected,source=asyncio.run(plan(question,None))
    assert selected.feature==feature and source in {'reviewed_scope','reviewed_handbook'}
    assert selected.demo is (feature!='unknown')

def test_unmapped_question_still_reaches_handbook_when_model_unavailable(monkeypatch):
    from app import planner
    async def unavailable(*args):raise ValueError('unavailable')
    monkeypatch.setattr(planner,'classify',unavailable)
    selected,source=asyncio.run(plan('Why is the organisation field locked?',None))
    assert selected.feature=='unknown' and not selected.demo
