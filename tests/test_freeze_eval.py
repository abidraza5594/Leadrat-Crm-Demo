import json
import pytest
from slm import freeze_eval

def test_freeze_needs_100_and_locks(tmp_path, monkeypatch):
    monkeypatch.setattr(freeze_eval,'EVAL',tmp_path)
    turns=[{'turn_id':1,'speaker':'beacon','text':'Hi'},{'turn_id':2,'speaker':'visitor','text':'We are a brokerage'}]
    (tmp_path/'pool.jsonl').write_text(''.join(json.dumps({'id':f'e-{i}','transcript':turns})+'\n' for i in range(101)))
    label={'organisation':{'type':'brokerage'},'evidence':{'organisation.type':[2]}}
    write=lambda n:(tmp_path/'hand_labels.jsonl').write_text(''.join(json.dumps({'id':f'e-{i}','status':'labelled','label':label,'labeller':'A'})+'\n' for i in range(n)))
    write(99)
    with pytest.raises(SystemExit,match='at least 100'):freeze_eval.main()
    write(101); freeze_eval.main()
    manifest=json.loads((tmp_path/'FROZEN.json').read_text())
    assert manifest['examples']==101 and manifest['sha256']['eval_set.jsonl']
    with pytest.raises(SystemExit,match='Already frozen'):freeze_eval.main()
