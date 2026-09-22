import pytest

from app.intents import fast_guide_intent


@pytest.mark.parametrize('message,kind,module', [
    ('how to add lead', 'lead', None),
    ('HOW TO ADD A NEW LEAD?', 'lead', None),
    ('Please create a lead', 'lead', None),
    ('lead add karna kaise hai', 'lead', None),
    ('लीड कैसे बनाते हैं', 'lead', None),
    ('Lead form samjhao', 'lead', None),
    ('full CRM tour', 'crm', None),
    ('pura CRM samjhao', 'crm', None),
    ('CRM kaise use karte hain', 'crm', None),
    ('Reports kaise use karte hai live dikhao', 'module', 'reports'),
    ('Show me the dashboard', 'module', 'dashboard'),
    ('Team ka demo dikhao', 'module', 'teams'),
])
def test_clear_requests(message, kind, module):
    guide = fast_guide_intent(message)
    assert guide and (guide.kind, guide.module) == (kind, module)


@pytest.mark.parametrize('message', [
    "Don't show the lead form", 'lead demo nahi chahiye', 'लीड मत बनाओ',
    'what is a lead source?', 'how to add lead source', 'lead source kaise use kare',
    'delete this lead', 'add lead and send email', 'save a new lead',
    'how to update a lead', 'show projects and properties', 'hello',
    'how to add lead notes', 'how to add lead documents',
])
def test_ambiguous_negative_or_write_requests_do_not_launch_fast_tour(message):
    assert fast_guide_intent(message) is None
