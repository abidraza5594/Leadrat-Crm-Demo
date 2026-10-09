import pytest
from app.conversation_numbers import count_reply

@pytest.mark.parametrize('text,expected',[
 ('20k',20000),('20K',20000),('1.5k',1500),('20,000',20000),
 ('1 lakh',100000),('1,00,000',100000),('we get around 20k leads per month',20000),
 ('50',50),('0',0),('2 million',2000000),('20k/month',20000),
 ('show 20k leads',None),('20-30k',None),('20,00',None),('-30',None),('1.5',None)])
def test_count_formats(text,expected):
 assert count_reply(text)==expected
