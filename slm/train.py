"""QLoRA fine-tune of Qwen2.5-1.5B-Instruct on the Beacon qualification data (shared by the Colab notebook and local runs).

Usage: python slm/train.py --out slm/runs/<name> [--epochs 2] [--max-len 2048]
Loss is computed on the JSON answer only (prompt tokens masked). Writes the adapter and run_metadata.json
(peak VRAM, wall-clock, GPU, library versions, data hashes, training metrics).
"""
import argparse
import hashlib
import json
import platform
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from slm.prompting import messages, target_text, facts_messages, facts_target_text  # noqa: E402

BASE = 'Qwen/Qwen2.5-1.5B-Instruct'
SEED = 20260928

def load(path):
    return [json.loads(l) for l in Path(path).read_text('utf-8').splitlines() if l.strip()]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True); parser.add_argument('--epochs', type=float, default=2)
    parser.add_argument('--max-len', type=int, default=2048); parser.add_argument('--lr', type=float, default=2e-4)
    parser.add_argument('--grad-accum', type=int, default=16)
    parser.add_argument('--format', choices=['full', 'facts'], default='full', help='facts: the model extracts, the rules score')
    parser.add_argument('--lang', default=None, help='train/evaluate only on this language code, e.g. en')
    args = parser.parse_args()
    started = time.time()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    import transformers, peft, bitsandbytes
    random.seed(SEED); torch.manual_seed(SEED)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(BASE)

    def encode(row):
        msgs = facts_messages(row['transcript']) if args.format == 'facts' else messages(row['transcript'])
        prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
        prompt = tok(prompt, add_special_tokens=False)['input_ids']
        answer = tok((facts_target_text if args.format == 'facts' else target_text)(row['target']) + tok.eos_token, add_special_tokens=False)['input_ids']
        return {'input_ids': (prompt + answer)[:args.max_len], 'labels': ([-100] * len(prompt) + answer)[:args.max_len]}

    keep = lambda rows: [r for r in rows if args.lang is None or r.get('language') == args.lang]
    train = [encode(r) for r in keep(load(ROOT / 'slm' / 'data' / 'train.jsonl'))]
    dev = [encode(r) for r in keep(load(ROOT / 'slm' / 'data' / 'dev.jsonl'))]
    lengths = sorted(len(x['input_ids']) for x in train)
    truncated = sum(len(x['input_ids']) >= args.max_len for x in train)
    print(f'train {len(train)} dev {len(dev)} tokens p50 {lengths[len(lengths)//2]} p95 {lengths[int(.95*len(lengths))]} max {lengths[-1]} truncated {truncated}', flush=True)
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id

    def collate(batch):
        n = max(len(x['input_ids']) for x in batch)
        return {'input_ids': torch.tensor([x['input_ids'] + [pad] * (n - len(x['input_ids'])) for x in batch]),
                'attention_mask': torch.tensor([[1] * len(x['input_ids']) + [0] * (n - len(x['input_ids'])) for x in batch]),
                'labels': torch.tensor([x['labels'] + [-100] * (n - len(x['labels'])) for x in batch])}

    torch.cuda.reset_peak_memory_stats()
    model = AutoModelForCausalLM.from_pretrained(BASE, device_map={'': 0}, torch_dtype=torch.float16, quantization_config=BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True))
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type='CAUSAL_LM',
        target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj']))
    model.print_trainable_parameters()
    training = TrainingArguments(output_dir=str(out / 'checkpoints'), per_device_train_batch_size=1, per_device_eval_batch_size=1,
        gradient_accumulation_steps=args.grad_accum, num_train_epochs=args.epochs, learning_rate=args.lr, warmup_steps=max(1, round(0.05 * args.epochs * len(train) / args.grad_accum)),
        lr_scheduler_type='cosine', fp16=True, logging_steps=5, eval_strategy='epoch', save_strategy='epoch', save_total_limit=1,
        seed=SEED, report_to=[], dataloader_pin_memory=False)
    trainer = Trainer(model=model, args=training, train_dataset=train, eval_dataset=dev, data_collator=collate)
    train_started = time.time(); result = trainer.train(); train_seconds = time.time() - train_started
    model.save_pretrained(out / 'adapter'); tok.save_pretrained(out / 'adapter')
    data = {n: hashlib.sha256((ROOT / 'slm' / 'data' / f'{n}.jsonl').read_bytes()).hexdigest() for n in ['train', 'dev']}
    meta = {'base_model': BASE, 'licence': 'Apache-2.0', 'method': 'QLoRA NF4 r16 a32, batch 1 x grad-accum ' + str(args.grad_accum),
            'format': args.format, 'lang': args.lang, 'epochs': args.epochs, 'max_len': args.max_len, 'seed': SEED, 'train_examples': len(train), 'dev_examples': len(dev),
            'train_seconds': round(train_seconds), 'total_seconds': round(time.time() - started),
            'peak_vram_gib': round(torch.cuda.max_memory_allocated() / 2**30, 2), 'peak_reserved_gib': round(torch.cuda.max_memory_reserved() / 2**30, 2),
            'gpu': torch.cuda.get_device_name(0), 'platform': platform.platform(),
            'versions': {'python': platform.python_version(), 'torch': torch.__version__, 'transformers': transformers.__version__,
                         'peft': peft.__version__, 'bitsandbytes': bitsandbytes.__version__},
            'data_sha256': data, 'train_metrics': result.metrics, 'log_history': trainer.state.log_history}
    (out / 'run_metadata.json').write_text(json.dumps(meta, indent=1), 'utf-8')
    print(json.dumps({k: v for k, v in meta.items() if k != 'log_history'}, indent=1))

if __name__ == '__main__':
    main()
