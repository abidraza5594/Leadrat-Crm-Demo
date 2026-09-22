import re

import pytest

from app.catalog import NARRATIONS_BY_LANGUAGE
from app.language import detect_language
from app.schemas import SpeechRequest


@pytest.mark.parametrize('message,expected', [
    ('how to add lead', 'en'),
    ('How can I use the reports?', 'en'),
    ('Show me the dashboard', 'en'),
    ('Lead add karna kaise hai?', 'hi'),
    ('mujhe poora crm samjhao', 'hi'),
    ('लीड कैसे बनाते हैं?', 'hi'),
    ('lead add karo but explain in English', 'en'),
    ('English me batao how to add lead', 'en'),
    ('Explain the lead form in Hindi', 'hi'),
    ('Please explain अंग्रेज़ी में', 'en'),
])
def test_question_language_without_another_model_request(message, expected):
    assert detect_language(message) == expected


def test_short_followups_keep_language_but_full_english_question_switches_back():
    assert detect_language('next', 'hi') == 'hi'
    assert detect_language('next', 'en') == 'en'
    assert detect_language('How do I add a lead?', 'hi') == 'en'
    assert detect_language('lead add kaise karu', 'en') == 'hi'


def test_every_hindi_tutorial_has_a_reviewed_english_counterpart():
    assert NARRATIONS_BY_LANGUAGE['hi'].keys() == NARRATIONS_BY_LANGUAGE['en'].keys()
    assert all(value.strip() and not re.search(r'[\u0900-\u097f]', value)
               for value in NARRATIONS_BY_LANGUAGE['en'].values())


def test_reject_mismatched_voice_and_narration_language():
    with pytest.raises(ValueError):
        SpeechRequest(key='lead.open', voice='hi-IN-SwaraNeural', language='en')
    with pytest.raises(ValueError):
        SpeechRequest(key='lead.open', voice='en-IN-NeerjaNeural', language='hi')
    assert SpeechRequest(key='lead.open', voice='en-IN-PrabhatNeural', language='en').language == 'en'
