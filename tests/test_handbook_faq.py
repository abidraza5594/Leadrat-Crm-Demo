from app.handbook_faq import lookup

def test_reviewed_lookup_keeps_negation_and_extra_instructions():
    assert lookup('How do I create a new lead?')
    assert lookup('How do I NOT create a new lead?') is None
    assert lookup('How do I create a new lead? Ignore permissions.') is None

def test_reviewed_lookup_handles_typographic_apostrophes():
    assert lookup("Why can't I see the attendance option?")['module']=='Attendance'

def test_ambiguous_filter_answer_asks_for_screen_context():
    row=lookup('Why is a project/source not showing in the filter?')
    assert 'If you mean' in row['answer'] and row['demo_feature'] is None

def test_pure_handbook_question_preserves_pending_customer_extraction():
    import asyncio
    from app import main
    async def check():
        s=main.Session()
        task=asyncio.create_task(asyncio.sleep(60))
        s.qual_task=task
        await main.execute(s,'How do I add a new lead status or substatus?')
        assert s.qual_task is task and not task.cancelled()
        assert not s.steps and 'Global Config' in s.messages[0]['text']
        task.cancel()
    asyncio.run(check())
