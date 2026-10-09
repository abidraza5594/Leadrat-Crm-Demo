"""Old provider/keyword-routing tests replaced by tests/test_context_engine.py.
The production conversation engine now has a local-only completion dependency.
"""
from app import planner

def test_obsolete_demo_routers_are_removed():
    for name in ('shortcut','keyword_match','scope_plan','classify','plan','small_talk'):
        assert not hasattr(planner,name)
