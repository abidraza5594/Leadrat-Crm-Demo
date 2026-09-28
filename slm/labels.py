"""Qualification label schema (beacon.qualification.v1) and the deterministic scoring that completes it.

The SLM reads a (possibly partial) transcript and emits the full object below. Training targets are
built in two steps: the teacher writes the extracted facts with evidence turn ids; `complete()` then
derives the score, range, rationale and route from the approved ICP rules (app/qualification.py), so
no score in the dataset is a guess. At runtime the same function checks the model's arithmetic.

Unknown means null. An empty list means the visitor explicitly said "none".
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.qualification import Facts, qualify

SCHEMA_VERSION = 'beacon.qualification.v1'
Org = Literal['brokerage','developer','channel_partner','other_real_estate','unrelated','unknown']

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Organisation(Strict):
    name: str | None = Field(default=None, max_length=100)
    type: Org = 'unknown'
    agents: int | None = Field(default=None, ge=0)

class Geography(Strict):
    countries: list[str] | None = None
    cities: list[str] | None = None

class Range(Strict):
    min: int | None = Field(default=None, ge=0)
    max: int | None = Field(default=None, ge=0)
    @model_validator(mode='after')
    def ordered(self):
        if self.min is not None and self.max is not None and self.min > self.max: raise ValueError('min > max')
        return self

class Contact(Strict):
    name: str | None = None
    email: str | None = None
    phone: str | None = None

class Extraction(Strict):
    """What the teacher labels and the SLM must read from the transcript."""
    role: str | None = Field(default=None, max_length=80)
    seniority: Literal['owner','executive','manager','individual_contributor','unknown'] = 'unknown'
    organisation: Organisation = Organisation()
    pain_points: list[str] | None = None
    current_tooling: list[str] | None = None
    process: Literal['manual','unsatisfied_crm','satisfied_crm','unknown'] = 'unknown'
    geography: Geography = Geography()
    monthly_leads: Range = Range()
    lead_sources: list[str] | None = None
    influence: Literal['approver','sponsored_evaluator','none','unknown'] = 'unknown'
    next_step: Literal['within_30_days','later','declined','unknown'] = 'unknown'
    consent: bool = False
    contact: Contact = Contact()
    # Field path -> visitor turn ids that establish the value.
    evidence: dict[str, list[int]] = {}

class Rationale(Strict):
    dimension: Literal['organisation','agents','monthly_leads','pain','process','influence','next_step']
    points: int | None
    evidence_turn_ids: list[int] = []

class Qualification(Extraction):
    """Full SLM output: extraction plus the scored, routable part."""
    schema_version: Literal['beacon.qualification.v1'] = SCHEMA_VERSION
    icp_score: int | None = Field(default=None, ge=0, le=100)
    score_range: list[int] = Field(min_length=2, max_length=2)
    score_rationale: list[Rationale]
    route: Literal['sales_handoff','human_review','nurture','graceful_close']

def band_leads(r: Range) -> int | None:
    """One band only: a range spanning bands (e.g. 80-150) stays unknown, as the rules require."""
    if r.min is None: return None
    top = r.min if r.max is None else r.max
    band = lambda n: 3 if n >= 500 else 2 if n >= 100 else 1 if n >= 1 else 0
    return r.min if band(r.min) == band(top) else None

def facts_of(x: Extraction) -> Facts:
    return Facts(
        organisation=None if x.organisation.type == 'unknown' else x.organisation.type,
        agents=x.organisation.agents, monthly_leads=band_leads(x.monthly_leads),
        pain_count=None if x.pain_points is None else len(x.pain_points),
        process=None if x.process == 'unknown' else x.process,
        influence=None if x.influence == 'unknown' else x.influence,
        intent=None if x.next_step == 'unknown' else x.next_step)

def usable_contact(c: Contact) -> bool:
    return bool(c.email or c.phone)

def complete(x: Extraction) -> Qualification:
    f = facts_of(x)
    result = qualify(f, declined=x.next_step == 'declined', consent=x.consent, usable_contact=usable_contact(x.contact))
    points = {
        'organisation': None if f.organisation is None else {'brokerage':20,'developer':20,'channel_partner':20,'other_real_estate':10,'unrelated':0}[f.organisation],
        'agents': None if f.agents is None else 15 if f.agents >= 20 else 10 if f.agents >= 6 else 5 if f.agents else 0,
        'monthly_leads': None if f.monthly_leads is None else 15 if f.monthly_leads >= 500 else 10 if f.monthly_leads >= 100 else 5 if f.monthly_leads else 0,
        'pain': None if f.pain_count is None else min(2, f.pain_count) * 10,
        'process': None if f.process is None else {'manual':10,'unsatisfied_crm':5,'satisfied_crm':0}[f.process],
        'influence': None if f.influence is None else {'approver':10,'sponsored_evaluator':5,'none':0}[f.influence],
        'next_step': None if f.intent is None else {'within_30_days':10,'later':5,'declined':0}[f.intent]}
    source = {'organisation':['organisation.type'],'agents':['organisation.agents'],'monthly_leads':['monthly_leads'],'pain':['pain_points'],
              'process':['process'],'influence':['influence'],'next_step':['next_step']}
    rationale = [Rationale(dimension=d, points=p, evidence_turn_ids=sorted({t for k in source[d] for t in x.evidence.get(k, [])}))
                 for d, p in points.items()]
    return Qualification(**x.model_dump(), icp_score=result['icp_score'], score_range=result['score_range'],
                         score_rationale=rationale, route=result['route'])
