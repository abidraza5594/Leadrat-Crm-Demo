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
    release_file = ROOT / 'slm/current_release.json'
    release=json.loads(release_file.read_text('utf-8')) if release_file.exists() else {}
    if release.get('status') == 'retired' or release.get('runtime') == 'llamacpp':
        raise SystemExit('The Qwen2.5 training pipeline is retired. Prepare the new Qwen3-4B training run; do not reload the old adapter.')
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True); parser.add_argument('--epochs', type=float, default=2)
    parser.add_argument('--max-len', type=int, default=3072); parser.add_argument('--lr', type=float, default=5e-5)
    parser.add_argument('--grad-accum', type=int, default=16)
    parser.add_argument('--format', choices=['full', 'facts'], default='full', help='facts: the model extracts, the rules score')
    parser.add_argument('--lang', default=None, help='train/evaluate only on this language code, e.g. en')
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'slm' / 'data' / 'v3', help='Directory containing train.jsonl and dev.jsonl')
    parser.add_argument('--check-only', action='store_true', help='Validate data and token lengths without loading or training model weights')
    parser.add_argument('--init-adapter', type=Path, help='Continue training existing adapter weights; optimizer/scheduler start fresh')
    parser.add_argument('--fresh-adapter', action='store_true', help='Explicit opt-in to initialize new adapter weights instead of continuing the latest published adapter')
    args = parser.parse_args()
    if args.fresh_adapter and args.init_adapter:
        parser.error('--fresh-adapter and --init-adapter are mutually exclusive')
    parent_revision = None
    if not args.init_adapter and not args.fresh_adapter:
        from huggingface_hub import HfApi, snapshot_download
        repo = 'abidansari5594/beacon-qualification-qwen2.5-1.5b-qlora'
        info = HfApi().model_info(repo, files_metadata=True)
        args.init_adapter = Path(snapshot_download(repo, revision=info.sha, allow_patterns=[
            'adapter*', 'tokenizer*', 'vocab.json', 'merges.txt', 'special_tokens_map.json', 'added_tokens.json', 'chat_template.jinja']))
        expected = next(s.lfs.sha256 for s in info.siblings if s.rfilename == 'adapter_model.safetensors')
        if hashlib.sha256((args.init_adapter/'adapter_model.safetensors').read_bytes()).hexdigest() != expected:
            raise ValueError('Published adapter hash mismatch')
        parent_revision = {'repo': repo, 'revision': info.sha}
        print('Latest published parent:', info.sha, flush=True)
    started = time.time()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments
    from peft import LoraConfig, PeftModel, get_peft_model, get_peft_model_state_dict, prepare_model_for_kbit_training
    import transformers, peft, bitsandbytes
    random.seed(SEED); torch.manual_seed(SEED)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    parent = None
    if args.init_adapter:
        config = json.loads((args.init_adapter / 'adapter_config.json').read_text('utf-8'))
        if config['base_model_name_or_path'] != BASE or config['peft_type'] != 'LORA':
            raise ValueError('Parent adapter must be a LoRA adapter for ' + BASE)
        if args.init_adapter.resolve() == (out / 'adapter').resolve():
            raise ValueError('Output must not overwrite the parent adapter')
        weights = args.init_adapter / 'adapter_model.safetensors'
        if not weights.is_file(): raise ValueError('Missing parent adapter_model.safetensors')
        parent = {'path':str(args.init_adapter), 'weights_sha256':hashlib.sha256(weights.read_bytes()).hexdigest(),
                  'config_sha256':hashlib.sha256((args.init_adapter / 'adapter_config.json').read_bytes()).hexdigest(),
                  'optimizer_state_restored':False}
        print('CONTINUATION: loading existing adapter weights; optimizer/scheduler start fresh. Parent SHA256: ' + parent['weights_sha256'], flush=True)
    tokenizer_kwargs = {}
    if args.init_adapter and int(transformers.__version__.split('.')[0]) < 5:
        tokenizer_config = json.loads((args.init_adapter / 'tokenizer_config.json').read_text('utf-8'))
        extra = tokenizer_config.get('extra_special_tokens')
        if isinstance(extra, list):
            # Transformers 5 saves this as a list; Transformers 4 expects a mapping.
            # Keep the same special tokens and the original tokenizer vocabulary.
            tokenizer_kwargs = {'extra_special_tokens': {}, 'additional_special_tokens': extra}
    tok = AutoTokenizer.from_pretrained(str(args.init_adapter) if args.init_adapter else BASE, **tokenizer_kwargs)

    def encode(row):
        msgs = facts_messages(row['transcript']) if args.format == 'facts' else messages(row['transcript'])
        prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
        prompt = tok(prompt, add_special_tokens=False)['input_ids']
        answer = tok((facts_target_text if args.format == 'facts' else target_text)(row['target']) + tok.eos_token, add_special_tokens=False)['input_ids']
        if len(prompt) + len(answer) > args.max_len:
            raise ValueError(f"{row['id']}: {len(prompt)+len(answer)} tokens exceeds --max-len {args.max_len}; increase max-len, do not truncate the JSON target")
        return {'input_ids': prompt + answer, 'labels': [-100] * len(prompt) + answer}

    keep = lambda rows: [r for r in rows if args.lang is None or r.get('language') == args.lang]
    train_rows = keep(load(args.data_dir / 'train.jsonl'))
    dev_rows = keep(load(args.data_dir / 'dev.jsonl'))
    if not train_rows or not dev_rows:
        raise ValueError('Training and development sets must both contain examples after language filtering')
    if {r['id'] for r in train_rows} & {r['id'] for r in dev_rows} or {r['family'] for r in train_rows} & {r['family'] for r in dev_rows}:
        raise ValueError('Train/dev overlap in IDs or scenario families')
    train = [encode(r) for r in train_rows]
    dev = [encode(r) for r in dev_rows]
    lengths = sorted(len(x['input_ids']) for x in train)
    truncated = sum(len(x['input_ids']) >= args.max_len for x in train)
    print(f'train {len(train)} dev {len(dev)} tokens p50 {lengths[len(lengths)//2]} p95 {lengths[int(.95*len(lengths))]} max {lengths[-1]} truncated {truncated}', flush=True)
    if args.check_only:
        print('Preflight passed; no training performed.', flush=True)
        return
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required for this QLoRA run. Enable a GPU in Kaggle settings.')
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
    model.config.use_cache = False
    if args.init_adapter:
        model = PeftModel.from_pretrained(model, str(args.init_adapter), is_trainable=True)
        # Fail closed if the saved weights were not actually restored before training.
        from safetensors.torch import load_file
        saved = load_file(str(args.init_adapter / 'adapter_model.safetensors'), device='cpu')
        loaded = get_peft_model_state_dict(model)
        if set(saved) != set(loaded): raise ValueError('Parent adapter tensor keys differ after load')
        for key, value in saved.items():
            if not torch.equal(value, loaded[key].detach().cpu().to(value.dtype)):
                raise ValueError('Parent adapter weights did not restore exactly: ' + key)
        if not any(p.requires_grad for p in model.parameters()): raise ValueError('Adapter is frozen')
        print(f'CONTINUATION VERIFIED: {len(saved)} saved adapter tensors restored exactly; adapter is trainable.', flush=True)
        del saved, loaded
    else:
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
    data = {n: hashlib.sha256((args.data_dir / f'{n}.jsonl').read_bytes()).hexdigest() for n in ['train', 'dev']}
    meta = {'base_model': BASE, 'licence': 'Apache-2.0', 'method': 'QLoRA NF4 r16 a32, batch 1 x grad-accum ' + str(args.grad_accum),
            'format': args.format, 'lang': args.lang, 'data_dir': str(args.data_dir), 'epochs': args.epochs, 'max_len': args.max_len, 'seed': SEED, 'train_examples': len(train), 'dev_examples': len(dev),
            'training_mode':'continue_adapter' if parent else 'fresh_adapter', 'parent_adapter':parent, 'parent_repository':parent_revision,
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
