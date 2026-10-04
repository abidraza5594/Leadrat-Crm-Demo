import json
from pathlib import Path
from slm.evaluate_v3_release import score, normalized, FIELDS

def test_invalid_output_cannot_pass_unknown_fields():
    source=json.loads(Path('slm/data/v3/test.jsonl').read_text('utf-8').splitlines()[0])
    result=score(source,'not JSON',1,{})
    assert result['matched_fields']==0
    assert result['valid']==0 and result['fully_matched']==0

def test_reference_output_passes_all_fields():
    source=json.loads(Path('slm/data/v3/test.jsonl').read_text('utf-8').splitlines()[0])
    result=score(source,json.dumps(source['target']),1,{})
    assert result['matched_fields']==len(FIELDS)
    assert result['fully_matched']==1

def test_null_and_empty_and_range_order_are_distinct():
    assert normalized(None,'pain_points') != normalized([],'pain_points')
    assert normalized([20,40],'score_range') != normalized([40,20],'score_range')
    assert normalized(['Excel',' Email '],'current_tooling') == normalized(['email','excel'],'current_tooling')
