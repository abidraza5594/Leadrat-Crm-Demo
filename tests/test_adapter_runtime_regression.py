"""Replay real synthetic adapter outputs; not a live model accuracy test."""
import asyncio
import json
from pathlib import Path
import pytest
from app import qualify

CASES=json.loads((Path(__file__).parent/'fixtures/adapter_fp16_regression.json').read_text())

@pytest.mark.parametrize('case',CASES,ids=[c['case'] for c in CASES])
def test_actual_adapter_output_is_validated_before_customer_result(monkeypatch,case):
    monkeypatch.setenv('QUAL_SLM_URL','http://local.invalid/v1')
    monkeypatch.setenv('QUAL_SLM_MODEL','beacon-v4')
    monkeypatch.setenv('QUAL_SLM_FORMAT','full')
    calls=[]
    async def chat(*args,**kwargs):
        calls.append(1)
        return case['raw_output']
    monkeypatch.setattr(qualify,'_chat',chat)
    transcript=[{'role':'user' if t['speaker']=='visitor' else 'assistant','text':t['text']} for t in case['transcript']]
    result=asyncio.run(qualify.qualify_session(transcript))
    assert result['source']=='slm' and len(calls)==1
    for path,expected in case['expected'].items():
        actual=result['qualification']
        for part in path.split('.'):actual=actual[part]
        assert actual==expected,(path,actual,expected)
    assert result['qualification']['route']!='sales_handoff'
