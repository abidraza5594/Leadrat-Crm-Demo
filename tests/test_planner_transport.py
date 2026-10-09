import asyncio,json
import httpx,pytest
from app import local_model,config,planner_auth

def test_private_planner_contract_and_truncation(monkeypatch,tmp_path):
    key=tmp_path/'key';key.write_text('a'*48)
    monkeypatch.setattr(planner_auth,'KEY_FILE',key)
    monkeypatch.setattr(config,'PLANNER_BACKEND','llamacpp')
    monkeypatch.setattr(config,'PLANNER_MODEL_URL','http://127.0.0.1:8014')
    monkeypatch.setattr(config,'PLANNER_MODEL','beacon-planner')
    schema={'type':'object','properties':{'ok':{'type':'boolean'}}}
    def respond(request):
        assert request.headers['authorization']=='Bearer '+'a'*48
        body=json.loads(request.content)
        assert body['response_format']['schema']==schema
        assert 'schema:' in body['messages'][0]['content']
        return httpx.Response(200,json={'choices':[{'finish_reason':'length','message':{'content':'{"ok":true}'}}]})
    real=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:real(transport=httpx.MockTransport(respond),**kwargs))
    with pytest.raises(ValueError,match='truncated'):
        asyncio.run(local_model.complete([{'role':'system','content':'Classify.'}],schema))

def test_key_is_not_sent_to_external_endpoint(monkeypatch):
    monkeypatch.setattr(config,'PLANNER_BACKEND','llamacpp')
    monkeypatch.setattr(config,'PLANNER_MODEL_URL','https://external.invalid')
    with pytest.raises(ValueError,match='loopback'):local_model.request_headers()


def test_adapter_does_not_send_customer_transcript_to_external_endpoint():
    from app.qualify import _chat
    with pytest.raises(ValueError,match='must be local'):
        asyncio.run(_chat('https://external.invalid/v1','beacon-v4',[]))

def test_count_correction_and_ambiguous_range():
    from app.conversation_engine import convert_updates,UnclearCount
    update={'field':'organisation.agents','value':'30','evidence':'Actually 30 people, not 300'}
    assert convert_updates({'updates':[update]})['updates'][0]=={'field':'organisation.agents','value':30,'evidence':'30'}
    with pytest.raises(UnclearCount):
        convert_updates({'updates':[{'field':'monthly_leads','value':'20-30k','evidence':'20-30k'}]})
