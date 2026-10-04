"""Publish the verified Kaggle continuation to the existing Hugging Face repository."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / '.venv/Lib/site-packages'))
from dotenv import dotenv_values
from huggingface_hub import HfApi

REPO = 'abidansari5594/beacon-qualification-qwen2.5-1.5b-qlora'
RUN = ROOT / 'slm/runs/kaggle-v3-continued'
OUT = ROOT / 'outputs/beacon-training-v3'
STAGE = OUT / 'hf-v3-release'
EXPECTED = 'e23139ba1b61a4912f476120cef8ff6edb8a8a726a0d8c9a9537308cc492ffe3'

def main():
    meta = json.loads((RUN / 'run_metadata.json').read_text())
    assert meta['training_mode'] == 'continue_adapter' and meta['train_examples'] == 2811
    assert meta['train_metrics']['epoch'] == 2.0
    assert hashlib.sha256((RUN/'adapter/adapter_model.safetensors').read_bytes()).hexdigest() == EXPECTED
    api = HfApi(token=dotenv_values(ROOT/'.env').get('HF_TOKEN'))
    assert api.whoami()['name'] == 'abidansari5594'
    before = api.model_info(REPO)
    STAGE.mkdir(parents=True, exist_ok=True)
    for p in (RUN/'adapter').iterdir():
        if p.is_file() and p.name != 'README.md': shutil.copy2(p, STAGE/p.name)
    shutil.copy2(RUN/'run_metadata.json', STAGE/'run_metadata.json')
    shutil.copy2(RUN/'data_manifest.json', STAGE/'data_manifest.json')
    (STAGE/'README.md').write_text('''---
base_model: Qwen/Qwen2.5-1.5B-Instruct
library_name: peft
pipeline_tag: text-generation
license: apache-2.0
language: [en, hi]
tags: [lora, qlora, information-extraction, lead-qualification]
---

# Beacon qualification adapter

Current release: **v3 continuation, 30 September 2026**.

This adapter extracts structured sales-qualification facts from Beacon / Leadrat conversations.
It returns the full `beacon.qualification.v1` JSON schema. It is not a general question-answer chatbot.

## Current training

Continued from revision `637c739100e160e70d3baea1137e20f5b4965049`.
All 392 saved adapter tensors were verified before training.
Training used 2,811 synthetic conversations (2,569 English, 207 Hinglish, 35 Hindi),
356 development conversations, two additional epochs, learning rate 0.00005, and a Kaggle Tesla T4.
The old adapter weights were restored. Optimizer and scheduler started fresh.
All 352 steps completed. Final training loss: 0.027671. Final development loss: 0.032205.
Loss is not question-answer accuracy. The held-out evaluation is pending for this release.
The synthetic reference labels are not independently human-reviewed.

Weights SHA256: `'''+EXPECTED+'''`.

## Load the latest adapter

Use this repository without an old revision pin to load the current release:

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
repo = "abidansari5594/beacon-qualification-qwen2.5-1.5b-qlora"
tokenizer = AutoTokenizer.from_pretrained(repo)
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", device_map="auto")
model = PeftModel.from_pretrained(base, repo).eval()
```

Use `system_prompt.txt` and numbered transcript turns as shown by `inference.py`.
For another training round, load with `PeftModel.from_pretrained(base, repo, is_trainable=True)`.
Resolve and record the current repository revision at the start of each new training run.
Do not use the previous revision pin or initialize a fresh LoRA adapter.

## Evaluation and limitations

Files under `eval/` describe the **previous adapter** and are historical, not v3 results.
Current question-wise evaluation will be published separately after it completes.
Recompute score and routing using the approved rules and review extracted facts before acting.
Synthetic benchmark results do not establish real-customer accuracy or production readiness.

The previous adapter remains recoverable in repository commit history.
''', encoding='utf-8')
    (STAGE/'eval').mkdir(exist_ok=True)
    (STAGE/'eval/README.md').write_text('Historical evaluation of the previous adapter, before v3 continuation.\nThese files do not measure the current adapter. See the root model card for current evaluation status.\n',encoding='utf-8')
    commit = api.upload_folder(repo_id=REPO, folder_path=str(STAGE),
        commit_message='Update to v3 continued adapter: 2811 conversations, two additional epochs',
        parent_commit=before.sha)
    after = api.model_info(REPO, revision=commit.oid, files_metadata=True)
    weights = next(s for s in after.siblings if s.rfilename == 'adapter_model.safetensors')
    assert weights.lfs.sha256 == EXPECTED
    result = {'repo':REPO,'previous_revision':before.sha,'revision':commit.oid,
              'weights_sha256':EXPECTED,'commit_url':str(commit.commit_url),'remote_hash_verified':True}
    (OUT/'hf_published_v3.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__ == '__main__': main()
