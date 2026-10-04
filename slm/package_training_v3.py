"""Package the current continuation trainer and train/dev data for Kaggle.

The held-out test split and credentials are never included.
Use slm/train_kaggle.ipynb with the resulting dataset ZIP.
"""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'app/__init__.py', 'app/qualification.py', 'slm/__init__.py',
    'slm/labels.py', 'slm/prompting.py', 'slm/train.py',
    'slm/data/v3/train.jsonl', 'slm/data/v3/dev.jsonl', 'slm/data/v3/manifest.json',
]

def main():
    output = ROOT / 'outputs/beacon-training-v3/beacon_training_v3.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {name: (ROOT / name).read_bytes() for name in FILES}
    manifest = {'purpose': 'training only; test excluded; continues latest published adapter',
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()}}
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in payload.items(): z.writestr(name, data)
        z.writestr('bundle_manifest.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert set(z.namelist()) == set(FILES) | {'bundle_manifest.json'}
    print(output)

if __name__ == '__main__':
    main()
