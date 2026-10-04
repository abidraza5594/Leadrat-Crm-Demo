"""Verify downloaded continuation, publish it and preserve the previous release."""
import hashlib,json,shutil,zipfile
from pathlib import Path
from dotenv import dotenv_values
from huggingface_hub import HfApi

ROOT=Path(__file__).resolve().parents[1]
REPO='abidansari5594/beacon-qualification-qwen2.5-1.5b-qlora'
OUT=ROOT/'outputs/beacon-training-v4'
RUN=ROOT/'slm/runs/kaggle-v4-continued'
PARENT='e23139ba1b61a4912f476120cef8ff6edb8a8a726a0d8c9a9537308cc492ffe3'

def main():
    OUT.mkdir(parents=True,exist_ok=True);RUN.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(Path.home()/'Downloads/beacon_v4_continued_adapter.zip') as z:
        assert z.testzip() is None
        for member in z.infolist():
            target=(RUN/member.filename).resolve()
            assert target.is_relative_to(RUN.resolve())
        z.extractall(RUN)
    meta=json.loads((RUN/'run_metadata.json').read_text())
    assert meta['training_mode']=='continue_adapter' and meta['train_examples']==10611
    assert meta['parent_adapter']['weights_sha256']==PARENT and meta['train_metrics']['epoch']==1
    assert meta['log_history'][-1]['step']==664 and meta['format']=='full'
    weights=RUN/'adapter/adapter_model.safetensors'
    sha=hashlib.sha256(weights.read_bytes()).hexdigest();assert sha!=PARENT
    api=HfApi(token=dotenv_values(ROOT/'.env').get('HF_TOKEN'))
    assert api.whoami()['name']=='abidansari5594'
    before=api.model_info(REPO,files_metadata=True)
    remote=next(f for f in before.siblings if f.rfilename=='adapter_model.safetensors').lfs.sha256
    assert remote in (PARENT,sha), 'Repository changed unexpectedly'
    stage=OUT/'hf-v4-release';stage.mkdir(exist_ok=True)
    for p in (RUN/'adapter').iterdir():
        if p.is_file() and p.name!='README.md':shutil.copy2(p,stage/p.name)
    for name in ['run_metadata.json','data_manifest.json']:shutil.copy2(RUN/name,stage/name)
    from slm.prompting import SYSTEM
    (stage/'system_prompt.txt').write_text(SYSTEM,encoding='utf-8')
    (stage/'README.md').write_text(f'''---
base_model: Qwen/Qwen2.5-1.5B-Instruct
library_name: peft
pipeline_tag: text-generation
license: apache-2.0
language: [en, hi]
tags: [lora, qlora, information-extraction, lead-qualification]
---

# Beacon qualification adapter

Current weights: **v4 continuation, 1 October 2026**.

Continued the previous v3 adapter on 10,611 synthetic conversations, including 7,800 additional controlled examples. All 664 steps completed. This extracts customer qualification JSON, not general CRM feature answers.

Parent weights SHA256: `{PARENT}`. Current weights SHA256: `{sha}`.
Parent revision: `{meta['parent_revision']}`. All 392 adapter tensors were restored before training. Optimizer and scheduler started fresh. One additional epoch, learning rate 0.00002, 716 development conversations.

## Evaluation status

Published at the owner's request before the new comparison is complete. V4 evaluation is pending. Existing files under `eval/` describe the previous release and must not be interpreted as v4 performance. Lower training loss does not establish better answers or readiness for customers.

## Use and continued training

Load Qwen/Qwen2.5-1.5B-Instruct, then this repository with PeftModel.from_pretrained. Use `system_prompt.txt` and `inference.py` for the full beacon.qualification.v1 JSON format. Recompute score and routing using the approved rules before any follow-up action.

For further training, resolve the current main revision and load this adapter with is_trainable=True. Do not initialise a new adapter. Previous weights remain available in repository history. The live Beacon website is a separate deployment and is not switched by this upload.
''',encoding='utf-8')
    (stage/'eval').mkdir(exist_ok=True)
    (stage/'eval/README.md').write_text('Historical v3 results. V4 comparison is pending. Do not attribute historical metrics to current v4 weights.\n',encoding='utf-8')
    old=json.loads((ROOT/'slm/current_release.json').read_text())
    baseline=OUT/'previous_release.json'
    if not baseline.exists():baseline.write_text(json.dumps(old,indent=2))
    commit=api.upload_folder(repo_id=REPO,folder_path=str(stage),parent_commit=before.sha,
        commit_message='Publish v4 continued adapter: 10611 conversations, evaluation pending')
    after=api.model_info(REPO,revision=commit.oid,files_metadata=True)
    assert next(f for f in after.siblings if f.rfilename=='adapter_model.safetensors').lfs.sha256==sha
    result={'repo':REPO,'previous_revision':before.sha,'revision':commit.oid,'weights_sha256':sha,
        'commit_url':str(commit.commit_url),'remote_hash_verified':True,'local_adapter':'slm/runs/kaggle-v4-continued/adapter',
        'training_entrypoint':'slm/continue_latest.py','evaluation_status':'pending','live_qualification_endpoint_configured':False,
        'comparison_baseline':'slm/results_history/2026-09-30-baseline.json'}
    (OUT/'hf_published_v4.json').write_text(json.dumps(result,indent=2))
    (ROOT/'slm/current_release.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
