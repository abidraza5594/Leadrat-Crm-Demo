"""Transparent rules fallback. A trained/evaluated SLM is NOT installed."""
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class Facts(BaseModel):
    model_config=ConfigDict(extra='forbid')
    organisation: Literal['brokerage','developer','channel_partner','other_real_estate','unrelated'] | None=None
    agents:int|None=Field(default=None,ge=0)
    monthly_leads:int|None=Field(default=None,ge=0)
    pain_count:int|None=Field(default=None,ge=0)
    process:Literal['manual','unsatisfied_crm','satisfied_crm']|None=None
    influence:Literal['approver','sponsored_evaluator','none']|None=None
    intent:Literal['within_30_days','later','declined']|None=None

def qualify(f:Facts, declined:bool=False, consent:bool=False, usable_contact:bool=False)->dict:
    values=[None if f.organisation is None else {'brokerage':20,'developer':20,'channel_partner':20,'other_real_estate':10,'unrelated':0}[f.organisation],
      None if f.agents is None else 15 if f.agents>=20 else 10 if f.agents>=6 else 5 if f.agents else 0,
      None if f.monthly_leads is None else 15 if f.monthly_leads>=500 else 10 if f.monthly_leads>=100 else 5 if f.monthly_leads else 0,
      None if f.pain_count is None else min(2,f.pain_count)*10,
      None if f.process is None else {'manual':10,'unsatisfied_crm':5,'satisfied_crm':0}[f.process],
      None if f.influence is None else {'approver':10,'sponsored_evaluator':5,'none':0}[f.influence],
      None if f.intent is None else {'within_30_days':10,'later':5,'declined':0}[f.intent]]
    lower=sum(v for v in values if v is not None)
    upper=lower+sum(mx for v,mx in zip(values,[20,15,15,20,10,10,10]) if v is None)
    score=lower if None not in values else None
    route='human_review' if score is None else 'sales_handoff' if score>=70 else 'nurture' if score>=40 else 'graceful_close'
    if route=='sales_handoff' and not(consent and usable_contact and f.intent=='within_30_days'):route='nurture'
    if declined or f.intent=='declined':route='graceful_close'
    return {'icp_score':score,'score_range':[lower,upper],'route':route,'scorer':'rules_fallback','model_status':'not_evaluated',
        'handoff_allowed':False,'reason':'Customer extraction is not yet available. Automatic handoff is not permitted for this preliminary result.'}
