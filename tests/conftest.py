"""Offline application contract tests. Model quality is measured separately in eval/context_engine.py."""
import json
import pytest

@pytest.fixture(autouse=True)
def no_hosted_calls(monkeypatch,tmp_path):
    from app import qualify,handoff
    monkeypatch.setenv('BEACON_PREWARM_BROWSER','0')
    monkeypatch.setenv('BEACON_START_LOCAL_MODEL','0')
    monkeypatch.delenv('QUAL_SLM_URL',raising=False)
    monkeypatch.delenv('QUAL_SLM_MODEL',raising=False)
    monkeypatch.setattr(handoff,'OUTBOX',tmp_path/'outbox')

@pytest.fixture(autouse=True)
def isolated_conversation_model(monkeypatch,tmp_path):
    from app import main
    monkeypatch.setenv('BEACON_STATE_PATH',str(tmp_path/'state.sqlite3'))
    monkeypatch.setenv('BEACON_DATABASE_URL','')
    monkeypatch.delenv('BEACON_WARM_KNOWLEDGE',raising=False)
    rows={
        'show leads':{'kind':'product','feature':'leads','topic':'Lead Management','demo':True},
        'show tasks':{'kind':'product','feature':'tasks','topic':'Task','demo':True},
        'show email':{'kind':'product','feature':'email','topic':'Lead Management','demo':True},
        'hi':{'kind':'chat','reply':'Hello! What would you like to explore?'},
        'thank you':{'kind':'chat','reply':'You are welcome.'},
        '20k':{'kind':'customer','updates':[{'field':'monthly_leads','value':20000,'evidence':'20k'}],'reply':'Got it — 20,000 new leads per month.'},
        'How do I add a new lead status or substatus?':{'kind':'product','feature':'unknown','topic':'Global Config','demo':False},
    }
    async def complete(messages,schema,max_tokens):
        message=messages[-1]['content'].split('Latest visitor message:\n')[-1].split('Visitor message to classify: ')[-1]
        if message not in rows:raise AssertionError('No fake model decision supplied for '+message)
        return rows[message]
    monkeypatch.setattr(main.engine,'completion',complete)
    monkeypatch.setattr(main.engine,'topics',['Lead Management','Global Config','Task','Project','Properties','Dashboard','Data Management'])
    yield rows
