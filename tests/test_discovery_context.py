import asyncio
from app import main,planner,docs






def test_rules_extract_reads_discovery_answers():
 from app.qualify import rules_extract
 turns=[{'speaker':'beacon','turn_id':1,'text':'What is the biggest problem with how you handle leads today?'},
  {'speaker':'visitor','turn_id':2,'text':'excels'},
  {'speaker':'beacon','turn_id':3,'text':'Would you like someone from Leadrat to contact you? If yes, share an email or phone number.'},
  {'speaker':'visitor','turn_id':4,'text':'yes'},
  {'speaker':'beacon','turn_id':5,'text':'Would you be the one deciding on a CRM, or evaluating it for someone else?'},
  {'speaker':'visitor','turn_id':6,'text':'i decide'},
  {'speaker':'beacon','turn_id':7,'text':'When would you want a new CRM running: within the next month, or later?'},
  {'speaker':'visitor','turn_id':8,'text':'next month'}]
 x=rules_extract(turns)
 assert x.pain_points==['excels'] and x.current_tooling==['Excel'] and x.process=='manual' and x.consent is True
 assert x.influence=='approver' and x.next_step=='within_30_days'
