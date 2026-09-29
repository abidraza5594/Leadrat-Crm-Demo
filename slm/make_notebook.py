"""Writes slm/train_colab.ipynb (kept as code so the notebook is reviewable in diffs)."""
import json
from pathlib import Path

CELLS = [
('md', """# Beacon qualification SLM — raw data → QLoRA adapter → evaluation table

Runs end to end on one free **Colab T4** session. Base model: `Qwen/Qwen2.5-1.5B-Instruct` (Apache-2.0).
1. Upload `beacon.zip` (create it locally with `git archive -o beacon.zip HEAD`).
2. Runtime → Change runtime type → **T4 GPU**. Run all cells.

Outputs: `slm/runs/colab/adapter/`, `slm/results/B.json`, `slm/results/C.json`, `slm/runs/colab/run_metadata.json` (peak VRAM, wall-clock, versions, data hashes).
System A (hosted model) is run locally with `python slm/evaluate.py run --system A --backend openai`, then `table` merges all three."""),
('code', """import time, os, sys, json, subprocess
NOTEBOOK_STARTED = time.time()
from google.colab import files
if not os.path.exists('beacon'):
    up = files.upload()                      # choose beacon.zip
    subprocess.run(['unzip', '-q', next(iter(up)), '-d', 'beacon'], check=True)
os.chdir('beacon'); sys.path.insert(0, os.getcwd())
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'transformers', 'peft', 'bitsandbytes', 'accelerate', 'pydantic'], check=True)
subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', '-q', 'torchao'], check=False)  # Colab's preinstalled torchao is too old for peft
print(subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv'], capture_output=True, text=True).stdout)"""),
('md', "## 1. Raw data → dataset (teacher scripts reproduce the raw batches; build.py validates, scores, splits)"),
('code', """import glob
for script in sorted(glob.glob('slm/teacher/gen*.py'), key=lambda p: int(''.join(filter(str.isdigit, os.path.basename(p))))):
    subprocess.run([sys.executable, os.path.basename(script)], cwd='slm/teacher', check=True)
print(subprocess.run([sys.executable, 'slm/build.py'], capture_output=True, text=True).stdout[:1500])
stats = json.load(open('slm/data/stats.json')); print(stats['split_sizes'], stats['sha256'])"""),
('md', "## 2. QLoRA fine-tune (NF4, rank 16, alpha 32, batch 1 × grad-accum 16; loss on the JSON answer only)"),
('code', """import torch
subprocess.run([sys.executable, 'slm/train.py', '--out', 'slm/runs/colab', '--epochs', '2'], check=True)
meta = json.load(open('slm/runs/colab/run_metadata.json'))
print({k: meta[k] for k in ['train_seconds', 'total_seconds', 'peak_vram_gib', 'gpu']})"""),
('md', "## 3. Evaluate B (few-shot base) and C (fine-tuned) on the frozen hand-labelled set"),
('code', """EVAL = 'slm/eval/eval_set.jsonl' if os.path.exists('slm/eval/eval_set.jsonl') else 'slm/data/dev.jsonl'
print('evaluating on', EVAL, '(dev.jsonl = teacher labels: development numbers only)' if 'dev' in EVAL else '')
for system, extra in [('B', []), ('C', ['--adapter', 'slm/runs/colab/adapter'])]:
    subprocess.run([sys.executable, 'slm/evaluate.py', 'run', '--system', system, '--backend', 'hf', '--eval', EVAL, '--gpu-hourly', '0'] + extra, check=True)
print(subprocess.run([sys.executable, 'slm/evaluate.py', 'table'], capture_output=True, text=True).stdout)"""),
('md', "## 4. Download the adapter, results and run metadata"),
('code', """meta['notebook_seconds'] = round(time.time() - NOTEBOOK_STARTED); meta['eval_file'] = EVAL
json.dump(meta, open('slm/runs/colab/run_metadata.json', 'w'), indent=1)
subprocess.run(['zip', '-qr', 'beacon_run.zip', 'slm/runs/colab/adapter', 'slm/runs/colab/run_metadata.json', 'slm/results'], check=True)
files.download('beacon_run.zip')"""),
]

def main():
    nb = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {'accelerator': 'GPU', 'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}},
          'cells': [{'cell_type': 'markdown' if kind == 'md' else 'code', 'metadata': {}, 'source': src.splitlines(keepends=True),
                     **({} if kind == 'md' else {'execution_count': None, 'outputs': []})} for kind, src in CELLS]}
    out = Path(__file__).with_name('train_colab.ipynb'); out.write_text(json.dumps(nb, indent=1), 'utf-8'); print('wrote', out)

if __name__ == '__main__':
    main()
