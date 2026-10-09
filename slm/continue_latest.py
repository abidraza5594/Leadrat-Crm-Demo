"""Continue the current Hugging Face adapter, resolving main anew for every run.

Example: python slm/continue_latest.py --out slm/runs/next --data-dir slm/data/v3 --epochs 2
"""
import hashlib
import json
import json
import subprocess
import sys
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download

ROOT = Path(__file__).resolve().parents[1]
REPO = 'abidansari5594/beacon-qualification-qwen2.5-1.5b-qlora'

def main():
    release_file = ROOT / 'slm/current_release.json'
    release=json.loads(release_file.read_text('utf-8')) if release_file.exists() else {}
    if release.get('status') == 'retired' or release.get('runtime') == 'llamacpp':
        raise SystemExit('Old adapter continuation is disabled. The next training run must use Qwen3-4B with a new adapter.')
    if '--init-adapter' in sys.argv or '--format' in sys.argv:
        raise SystemExit('This entrypoint always loads the current published adapter and uses its full format.')
    info=HfApi().model_info(REPO,files_metadata=True)
    weights=next(s for s in info.siblings if s.rfilename=='adapter_model.safetensors')
    path=Path(snapshot_download(REPO,revision=info.sha,allow_patterns=['adapter*','tokenizer*','vocab.json','merges.txt','special_tokens_map.json','added_tokens.json','chat_template.jinja']))
    assert hashlib.sha256((path/'adapter_model.safetensors').read_bytes()).hexdigest()==weights.lfs.sha256
    print('Continuing current Hugging Face revision:',info.sha,flush=True)
    command=[sys.executable,str(ROOT/'slm/train.py'),'--init-adapter',str(path),'--format','full','--lr','5e-5','--max-len','3072',*sys.argv[1:]]
    subprocess.run(command,cwd=ROOT,check=True)

if __name__=='__main__': main()
