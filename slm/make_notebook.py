"""Writes slm/train_colab.ipynb (kept as code so the notebook is reviewable in diffs)."""
import json
from pathlib import Path

CELLS = [
('md', """# Beacon qualification SLM — raw data → QLoRA adapter → evaluation table

Runs end to end on one free **Colab T4** session. Base model: `Qwen/Qwen2.5-1.5B-Instruct` (Apache-2.0).
1. Upload `beacon.zip` (create it locally with `git archive -o beacon.zip HEAD`).
2. Runtime → Change runtime type → **T4 GPU**. Run all cells.

Outputs: `adapter/`, `slm/results/B.json`, `slm/results/C.json`, `run_metadata.json` (peak VRAM, wall-clock, versions, data hashes).
System A (hosted model) is run locally with `python slm/evaluate.py run --system A --backend openai`, then `table` merges all three."""),
('code', """import time, os, sys, json, subprocess
NOTEBOOK_STARTED = time.time()
from google.colab import files
if not os.path.exists('beacon'):
    up = files.upload()                      # choose beacon.zip
    subprocess.run(['unzip', '-q', next(iter(up)), '-d', 'beacon'], check=True)
os.chdir('beacon'); sys.path.insert(0, os.getcwd())
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'transformers', 'peft', 'bitsandbytes', 'accelerate', 'pydantic'], check=True)
print(subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv'], capture_output=True, text=True).stdout)"""),
('md', "## 1. Raw data → dataset (teacher scripts reproduce the raw batches; build.py validates, scores, splits)"),
('code', """import glob
for script in sorted(glob.glob('slm/teacher/gen*.py'), key=lambda p: int(''.join(filter(str.isdigit, os.path.basename(p))))):
    subprocess.run([sys.executable, os.path.basename(script)], cwd='slm/teacher', check=True)
print(subprocess.run([sys.executable, 'slm/build.py'], capture_output=True, text=True).stdout[:1500])
stats = json.load(open('slm/data/stats.json')); print(stats['split_sizes'], stats['sha256'])"""),
('md', "## 2. Tokenise: loss only on the JSON answer (prompt tokens masked)"),
('code', """import torch, random
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from slm.prompting import messages, target_text
BASE = 'Qwen/Qwen2.5-1.5B-Instruct'; SEED = 20260928; MAX_LEN = 2048
random.seed(SEED); torch.manual_seed(SEED)
tok = AutoTokenizer.from_pretrained(BASE)
def load(path): return [json.loads(l) for l in open(path, encoding='utf-8') if l.strip()]
def encode(row):
    prompt = tok.apply_chat_template(messages(row['transcript']), add_generation_prompt=True, tokenize=True)
    answer = tok(target_text(row['target']) + tok.eos_token, add_special_tokens=False)['input_ids']
    ids = (prompt + answer)[:MAX_LEN]
    labels = ([-100] * len(prompt) + answer)[:MAX_LEN]
    return {'input_ids': ids, 'labels': labels}
train = [encode(r) for r in load('slm/data/train.jsonl')]; dev = [encode(r) for r in load('slm/data/dev.jsonl')]
lengths = sorted(len(x['input_ids']) for x in train)
print('train', len(train), 'dev', len(dev), 'tokens p50/p95/max', lengths[len(lengths)//2], lengths[int(.95*len(lengths))], lengths[-1])
def collate(batch):
    n = max(len(x['input_ids']) for x in batch); pad = tok.pad_token_id or tok.eos_token_id
    return {'input_ids': torch.tensor([x['input_ids'] + [pad] * (n - len(x['input_ids'])) for x in batch]),
            'attention_mask': torch.tensor([[1] * len(x['input_ids']) + [0] * (n - len(x['input_ids'])) for x in batch]),
            'labels': torch.tensor([x['labels'] + [-100] * (n - len(x['labels'])) for x in batch])}"""),
('md', "## 3. QLoRA (NF4, rank 16, alpha 32, batch 1 × grad-accum 16)"),
('code', """torch.cuda.reset_peak_memory_stats()
model = AutoModelForCausalLM.from_pretrained(BASE, device_map='auto', quantization_config=BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True))
model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type='CAUSAL_LM',
    target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj']))
model.print_trainable_parameters()
args = TrainingArguments(output_dir='checkpoints', per_device_train_batch_size=1, per_device_eval_batch_size=1,
    gradient_accumulation_steps=16, num_train_epochs=2, learning_rate=2e-4, warmup_ratio=0.05, lr_scheduler_type='cosine',
    fp16=True, logging_steps=10, eval_strategy='epoch', save_strategy='epoch', save_total_limit=1, seed=SEED, report_to=[])
trainer = Trainer(model=model, args=args, train_dataset=train, eval_dataset=dev, data_collator=collate)
TRAIN_STARTED = time.time(); result = trainer.train(); TRAIN_SECONDS = time.time() - TRAIN_STARTED
model.save_pretrained('adapter'); tok.save_pretrained('adapter')
PEAK_GIB = torch.cuda.max_memory_allocated() / 2**30
print('train seconds', round(TRAIN_SECONDS), 'peak VRAM GiB', round(PEAK_GIB, 2), result.metrics)"""),
('md', "## 4. Evaluate B (few-shot base) and C (fine-tuned) on the frozen hand-labelled set"),
('code', """del model, trainer; torch.cuda.empty_cache()
EVAL = 'slm/eval/eval_set.jsonl' if os.path.exists('slm/eval/eval_set.jsonl') else 'slm/data/dev.jsonl'
print('evaluating on', EVAL, '(dev.jsonl = teacher labels: development numbers only)' if 'dev' in EVAL else '')
for system, extra in [('B', []), ('C', ['--adapter', 'adapter'])]:
    subprocess.run([sys.executable, 'slm/evaluate.py', 'run', '--system', system, '--backend', 'hf', '--eval', EVAL, '--gpu-hourly', '0'] + extra, check=True)
print(subprocess.run([sys.executable, 'slm/evaluate.py', 'table'], capture_output=True, text=True).stdout)"""),
('md', "## 5. Run metadata (peak VRAM, wall-clock, versions, data hashes)"),
('code', """import transformers, peft, bitsandbytes, platform
meta = {'base_model': BASE, 'licence': 'Apache-2.0', 'seed': SEED, 'max_len': MAX_LEN, 'train_seconds': round(TRAIN_SECONDS),
        'notebook_seconds': round(time.time() - NOTEBOOK_STARTED), 'peak_vram_gib': round(PEAK_GIB, 2),
        'gpu': torch.cuda.get_device_name(0), 'versions': {'torch': torch.__version__, 'transformers': transformers.__version__,
        'peft': peft.__version__, 'bitsandbytes': bitsandbytes.__version__, 'python': platform.python_version()},
        'data_sha256': stats['sha256'], 'eval_file': EVAL, 'train_metrics': result.metrics}
json.dump(meta, open('run_metadata.json', 'w'), indent=1); print(json.dumps(meta, indent=1))
subprocess.run(['zip', '-qr', 'beacon_run.zip', 'adapter', 'slm/results', 'run_metadata.json'], check=True)
files.download('beacon_run.zip')"""),
]

def main():
    nb = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {'accelerator': 'GPU', 'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}},
          'cells': [{'cell_type': 'markdown' if kind == 'md' else 'code', 'metadata': {}, 'source': src.splitlines(keepends=True),
                     **({} if kind == 'md' else {'execution_count': None, 'outputs': []})} for kind, src in CELLS]}
    out = Path(__file__).with_name('train_colab.ipynb'); out.write_text(json.dumps(nb, indent=1), 'utf-8'); print('wrote', out)

if __name__ == '__main__':
    main()
