import asyncio
import pytest

from app.browser import BrowserWorker,LOGIN_BLOCKED,LOGIN_FIELDS,NAV



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
