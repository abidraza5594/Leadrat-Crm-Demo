from slm.labels import Extraction, complete, band_leads, Range

def label(**kw):
    base=dict(organisation={'type':'brokerage','agents':25},monthly_leads={'min':600,'max':600},pain_points=['missed follow-ups','no reports'],
              process='manual',influence='approver',next_step='within_30_days',consent=True,contact={'email':'a@example.com'})
    base.update(kw);return complete(Extraction(**base))

def test_design_doc_worked_examples():
    full=label()
    assert full.icp_score==100 and full.route=='sales_handoff'
    low=label(organisation={'type':'developer','agents':3},monthly_leads={'min':50,'max':50},pain_points=['slow follow-up'],
              process='satisfied_crm',influence='none',next_step='declined',consent=False,contact={})
    assert low.icp_score==40 and low.route=='graceful_close'
    unknown=label(monthly_leads={'min':None,'max':None})
    assert unknown.icp_score is None and unknown.score_range==[85,100] and unknown.route=='human_review'

def test_no_consent_or_contact_is_not_a_handoff():
    assert label(consent=False).route=='nurture'
    assert label(contact={}).route=='nurture'

def test_ranges_spanning_bands_stay_unknown():
    assert band_leads(Range(min=80,max=150)) is None and band_leads(Range(min=200,max=400))==200
