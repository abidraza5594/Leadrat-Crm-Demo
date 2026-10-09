import asyncio
import pytest
from app import main
from app.qualify import rules_extract,transcript_of








def test_count_context_in_sales_fallback():
 rows=[{'role':'assistant','text':'How many people are on your sales team?'},{'role':'user','text':'50'},
 {'role':'assistant','text':'Roughly how many new leads do you get in a month?'},{'role':'user','text':'20k'}]
 q=rules_extract(transcript_of(rows))
 assert q.organisation.agents==50 and q.monthly_leads.min==20000
 assert q.evidence['monthly_leads']==[4]

def test_assistant_number_does_not_become_customer_fact():
 q=rules_extract(transcript_of([{'role':'assistant','text':'Our sample has 20k leads'},{'role':'user','text':'ok'}]))
 assert q.monthly_leads.min is None

@pytest.mark.parametrize('text,n',[('20k leads',20000),('20,000 leads',20000),('1 lakh leads',100000)])
def test_explicit_sales_counts(text,n):
 q=rules_extract(transcript_of([{'role':'user','text':text}]))
 assert q.monthly_leads.min==n

@pytest.mark.parametrize('text,expected',[('twenty thousand',20000),('two lakh',200000),('one million',1000000)])
def test_spoken_counts(text,expected):
 from app.conversation_numbers import count_reply
 assert count_reply(text)==expected
