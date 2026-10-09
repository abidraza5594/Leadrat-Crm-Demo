import hashlib
import ast
import base64
import lzma
import json
from pathlib import Path
import pytest
from slm.qwen3.train import BASE,REVISION,encode,read_data,native_bf16

ROOT=Path(__file__).resolve().parents[1]

def test_t4_never_uses_emulated_bf16():
    class Cuda:
        def __init__(self,major):self.major=major
        def get_device_capability(self,index):return (self.major,5)
        def is_bf16_supported(self,including_emulation=True):return including_emulation or self.major>=8
    assert native_bf16(Cuda(7)) is False
    assert native_bf16(Cuda(8)) is True

def test_new_multitask_dataset_contracts():
    manifest,data=read_data(ROOT/'slm/data/qwen3-v1')
    assert manifest['base_model']==BASE and manifest['base_revision']==REVISION
    assert manifest['old_adapter_loaded'] is False
    assert len(data['train'])>=17000
    assert {r['task'] for r in data['train']}=={'qualification','classify','demo_selection','customer_update'}
    for row in data['train']+data['dev']:
        answer=json.loads(row['messages'][-1]['content'])
        if row['task']=='demo_selection':
            assert set(answer)=={'feature','no_demo_quote'}
            assert answer['feature']=='unknown' or answer['feature'].startswith('knowledge:') or answer['feature'] in manifest['capabilities']
            assert not answer['no_demo_quote'] or answer['no_demo_quote'] in row['messages'][-2]['content']
        if row['task']=='customer_update':
            visitor=row['messages'][-2]['content'].split('Latest visitor message:\n',1)[1]
            for u in answer['updates']:assert u['evidence'] in visitor
        if row['task']=='qualification':
            assert 'icp_score' not in answer and 'route' not in answer

class Tokenizer:
    def apply_chat_template(self,messages,add_generation_prompt,tokenize):
        return [1,2,3] if add_generation_prompt else [1,2,3,4,5]

def test_only_answer_tokens_receive_loss_and_no_silent_truncation():
    row={'id':'sample','messages':[{'role':'system','content':'x'},{'role':'user','content':'y'},{'role':'assistant','content':'{}'}]}
    assert encode(Tokenizer(),row,5)['labels']==[-100,-100,-100,4,5]
    with pytest.raises(ValueError,match='never truncate'):encode(Tokenizer(),row,4)

def test_retired_runtime_does_not_start_process(monkeypatch,tmp_path):
    from slm import local_runtime
    (tmp_path/'slm').mkdir();(tmp_path/'slm/current_release.json').write_text('{"status":"retired"}')
    monkeypatch.setattr(local_runtime,'ROOT',tmp_path)
    def forbidden(*args,**kwargs):raise AssertionError('Retired model should never start or make a health request')
    monkeypatch.setattr(local_runtime.subprocess,'Popen',forbidden)
    monkeypatch.setattr(local_runtime.httpx,'get',forbidden)
    local_runtime.ensure_local_model()

def test_packaged_data_restores_original_hashes_on_linux():
    payload=ROOT/'outputs/beacon-qwen3-fresh-training/training_source.json.xz'
    files=json.loads(lzma.decompress(payload.read_bytes()))
    assert set(files)=={'train.py','data/train.jsonl','data/dev.jsonl','data/manifest.json'}
    manifest=json.loads(files['data/manifest.json'])
    for split in ('train','dev'):
        content=files[f'data/{split}.jsonl'];raw=content.encode('utf-8')
        expected=manifest['splits'][split]['sha256']
        if hashlib.sha256(raw).hexdigest()!=expected:
            raw=content.replace('\r\n','\n').replace('\n','\r\n').encode('utf-8')
        assert hashlib.sha256(raw).hexdigest()==expected
        assert raw==(ROOT/f'slm/data/qwen3-v1/{split}.jsonl').read_bytes()

def test_notebook_embeds_current_verified_trainer():
    notebook=json.loads((ROOT/'outputs/beacon-qwen3-fresh-training/beacon_qwen3_fresh_17446.ipynb').read_text('utf-8'))
    setup=''.join(notebook['cells'][1]['source'])
    tree=ast.parse(setup)
    assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='trainer_source' for t in n.targets))
    source=lzma.decompress(base64.b64decode(ast.literal_eval(assignment.value.args[0].args[0])))
    assert source==(ROOT/'slm/qwen3/train.py').read_text('utf-8').encode('utf-8')
    assert hashlib.sha256(source).hexdigest() in setup
