import asyncio,json
import httpx,pytest
from slm import planner_runtime,local_runtime
from app import config,planner_auth,qualify,main

@pytest.fixture
def release(monkeypatch,tmp_path):
    monkeypatch.setattr(planner_runtime,'ROOT',tmp_path)
    folder=tmp_path/'.models/planner';folder.mkdir(parents=True)
    (folder/'manifest.json').write_text(json.dumps({'model_file':'base.gguf'}))
    return {'status':'active','runtime':'llamacpp','model_alias':'beacon-qwen3-17k',
            'gguf_adapter':'slm/runs/new/adapter.gguf','release_id':'test-release','weights_sha256':'verified'}

@pytest.mark.parametrize('adapters', [[],[{'path':'old.gguf','scale':1}],[{'path':'slm/runs/new/adapter.gguf','scale':0}]])
def test_missing_old_or_disabled_adapter_is_rejected(release,adapters):
    with pytest.raises(RuntimeError,match='adapter'):
        planner_runtime.verify_identity(['beacon-qwen3-17k'],{'model_path':str(planner_runtime.ROOT/'.models/planner/base.gguf')},adapters,release)

def test_loaded_current_adapter_is_verified(release):
    assert planner_runtime.verify_identity(['beacon-qwen3-17k'],
      {'model_path':str(planner_runtime.ROOT/'.models/planner/base.gguf')},
      [{'path':str(planner_runtime.ROOT/release['gguf_adapter']),'scale':1}],release)

def test_shared_runtime_never_starts_old_transformers_server(monkeypatch,tmp_path):
    folder=tmp_path/'slm';folder.mkdir();(folder/'current_release.json').write_text('{"runtime":"llamacpp","status":"active"}')
    monkeypatch.setattr(local_runtime,'ROOT',tmp_path)
    def fail(*args,**kwargs):raise AssertionError('Old service must not start')
    monkeypatch.setattr(local_runtime.subprocess,'Popen',fail)
    local_runtime.ensure_local_model()

@pytest.mark.parametrize('module_name',['slm.train','slm.continue_latest'])
def test_active_qwen3_keeps_old_training_disabled(monkeypatch,tmp_path,module_name):
    import importlib
    module=importlib.import_module(module_name)
    folder=tmp_path/'slm';folder.mkdir();(folder/'current_release.json').write_text('{"runtime":"llamacpp","status":"active"}')
    monkeypatch.setattr(module,'ROOT',tmp_path)
    with pytest.raises(SystemExit,match='Qwen3'):module.main()

def test_qualification_uses_shared_auth_and_schema(monkeypatch,tmp_path):
    key=tmp_path/'key';key.write_text('z'*48);monkeypatch.setattr(planner_auth,'KEY_FILE',key)
    monkeypatch.setattr(config,'PLANNER_BACKEND','llamacpp')
    monkeypatch.setattr(config,'PLANNER_MODEL_URL','http://127.0.0.1:8014')
    def respond(request):
        assert request.headers['authorization']=='Bearer '+'z'*48
        body=json.loads(request.content)
        assert body['model']=='beacon-qwen3-17k'
        assert body['response_format']['schema']==qualify.extraction_schema()
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]})
    real=httpx.AsyncClient;monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(respond),**kw))
    assert asyncio.run(qualify._chat('http://127.0.0.1:8014/v1','beacon-qwen3-17k',[]))=='{}'

def test_health_does_not_mark_base_only_server_ready(monkeypatch,release):
    monkeypatch.setattr(config,'PLANNER_BACKEND','llamacpp');monkeypatch.setattr(config,'PLANNER_MODEL','beacon-qwen3-17k')
    monkeypatch.setattr(planner_runtime,'active_release',lambda:release)
    from app import local_model
    monkeypatch.setattr(local_model,'request_headers',lambda:{})
    def respond(request):
        data={'/v1/models':{'data':[{'id':'beacon-qwen3-17k'}]},'/props':{'model_path':str(planner_runtime.ROOT/'.models/planner/base.gguf')},'/lora-adapters':[]}
        return httpx.Response(200,json=data[request.url.path])
    real=httpx.AsyncClient;monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(respond),**kw))
    result=asyncio.run(main.health())
    assert not result['model_available'] and not result['trained_adapter_active']
