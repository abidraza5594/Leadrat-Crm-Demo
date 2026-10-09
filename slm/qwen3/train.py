"""Kaggle QLoRA run: a NEW adapter on the pinned pretrained Qwen3 base.

No old adapter download/load, hosted LLM, publication, or live deployment.
"""
import argparse
import hashlib
import json
import math
import os
import platform
import random
import time
from pathlib import Path

BASE='Qwen/Qwen3-4B-Instruct-2507'
REVISION='cdbee75f17c01a7cc42f958dc650907174af0554'

def native_bf16(cuda,device=0):
    # PyTorch's default permits software emulation, which is very slow on T4.
    return cuda.get_device_capability(device)[0]>=8 and cuda.is_bf16_supported(including_emulation=False)

def read_data(directory):
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_text('utf-8'))
    if manifest['base_model']!=BASE or manifest['base_revision']!=REVISION or manifest['old_adapter_loaded']:
        raise ValueError('Wrong base model or adapter provenance')
    result={};prompts=set();families=set()
    for split in ('train','dev'):
        p=directory/f'{split}.jsonl'
        if hashlib.sha256(p.read_bytes()).hexdigest()!=manifest['splits'][split]['sha256']:
            raise ValueError('Dataset checksum mismatch: '+split)
        rows=[json.loads(line) for line in p.read_text('utf-8').splitlines() if line.strip()]
        if len(rows)!=manifest['splits'][split]['count']:raise ValueError('Wrong split size')
        current_prompts=set();current_families=set()
        for row in rows:
            msgs=row['messages']
            if [m['role'] for m in msgs]!=['system','user','assistant']:raise ValueError('Expected one supervised response')
            if not isinstance(json.loads(msgs[-1]['content']),dict):raise ValueError('Target must be a JSON object')
            fp=hashlib.sha256(json.dumps(msgs[:-1],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            if fp in prompts or fp in current_prompts:raise ValueError('Duplicate or leaking prompt')
            current_prompts.add(fp);current_families.add(row['family'])
        if current_families&families:raise ValueError('Train/dev family overlap')
        prompts.update(current_prompts);families.update(current_families);result[split]=rows
    return manifest,result

def encode(tokenizer,row,max_length):
    prefix=tokenizer.apply_chat_template(row['messages'][:-1],add_generation_prompt=True,tokenize=True)
    full=tokenizer.apply_chat_template(row['messages'],add_generation_prompt=False,tokenize=True)
    # Transformers 5 returns BatchEncoding by default; 4.x returns token IDs.
    if not isinstance(prefix,list):prefix=prefix['input_ids']
    if not isinstance(full,list):full=full['input_ids']
    if full[:len(prefix)]!=prefix:raise ValueError('Chat-template prefix mismatch: '+row['id'])
    if len(full)>max_length:raise ValueError(f"{row['id']}: {len(full)} tokens exceeds {max_length}; never truncate targets")
    if len(full)<=len(prefix):raise ValueError('No supervised target tokens')
    return {'input_ids':full,'labels':[-100]*len(prefix)+full[len(prefix):]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=Path('data'))
    p.add_argument('--out',type=Path,default=Path('run'))
    p.add_argument('--max-length',type=int,default=4096)
    p.add_argument('--epochs',type=float,default=1)
    p.add_argument('--lr',type=float,default=5e-5)
    p.add_argument('--grad-accum',type=int,default=16)
    p.add_argument('--check-only',action='store_true')
    p.add_argument('--wall-hours',type=float,default=9)
    args=p.parse_args()
    local_rank=int(os.environ.get('LOCAL_RANK','0'))
    rank=int(os.environ.get('RANK','0'))
    world_size=int(os.environ.get('WORLD_SIZE','1'))
    if args.epochs<=0 or args.grad_accum<1 or args.wall_hours<=0:raise ValueError('Invalid training settings')
    manifest,rows=read_data(args.data)
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION,trust_remote_code=False)
    tokenizer.pad_token=tokenizer.eos_token;tokenizer.padding_side='right'
    encoded={};lengths={}
    for split,rs in rows.items():
        encoded[split]=[encode(tokenizer,r,args.max_length) for r in rs]
        sizes=sorted(len(x['input_ids']) for x in encoded[split])
        lengths[split]={'count':len(sizes),'min':sizes[0],'median':sizes[len(sizes)//2],
            'p95':sizes[int(len(sizes)*.95)],'max':sizes[-1],'total_tokens':sum(sizes)}
    args.out.mkdir(parents=True,exist_ok=True)
    preflight={'base_model':BASE,'base_revision':REVISION,'lengths':lengths,'prompt_tokens_masked':True,
        'targets_truncated':0,'old_adapter_loaded':False,'dataset_hashes':{s:manifest['splits'][s]['sha256'] for s in encoded}}
    if rank==0:
        (args.out/'preflight.json').write_text(json.dumps(preflight,indent=2),encoding='utf-8')
        print(json.dumps(preflight,indent=2),flush=True)
    if args.check_only:return
    if (args.out/'adapter').exists() or list(args.out.glob('checkpoint-*')):
        raise ValueError('Output has previous weights. Choose a fresh run directory; no silent resume/overwrite.')
    import torch
    import transformers
    import peft
    import bitsandbytes
    from transformers import AutoModelForCausalLM,BitsAndBytesConfig,Trainer,TrainingArguments,TrainerCallback
    from peft import LoraConfig,get_peft_model,prepare_model_for_kbit_training
    if not torch.cuda.is_available():raise RuntimeError('Enable a Kaggle GPU before running')
    torch.cuda.set_device(local_rank)
    if torch.cuda.get_device_properties(local_rank).total_memory<14*1024**3:raise RuntimeError('Use a Kaggle GPU with at least 14 GiB VRAM')
    random.seed(manifest['seed']);torch.manual_seed(manifest['seed'])
    bf16=native_bf16(torch.cuda,local_rank);dtype=torch.bfloat16 if bf16 else torch.float16
    precision={'compute_dtype':str(dtype),'gpu_capability':torch.cuda.get_device_capability(local_rank),'native_bf16':bf16,'gpu_count':world_size,'effective_batch_size':world_size*args.grad_accum}
    print(f'Rank {rank} GPU precision: '+json.dumps(precision),flush=True)
    started=time.monotonic();torch.cuda.reset_peak_memory_stats()
    model=AutoModelForCausalLM.from_pretrained(BASE,revision=REVISION,trust_remote_code=False,
        device_map={'':local_rank},torch_dtype=dtype,attn_implementation='sdpa',
        quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
            bnb_4bit_compute_dtype=dtype,bnb_4bit_use_double_quant=True))
    model=prepare_model_for_kbit_training(model,use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={'use_reentrant':False})
    model.config.use_cache=False
    model=get_peft_model(model,LoraConfig(r=16,lora_alpha=32,lora_dropout=.05,bias='none',
        task_type='CAUSAL_LM',target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj']))
    model.print_trainable_parameters()
    print('FRESH QWEN3 ADAPTER: no Qwen2.5 weights or previous adapters loaded.',flush=True)
    def collate(batch):
        width=math.ceil(max(len(x['input_ids']) for x in batch)/8)*8
        return {'input_ids':torch.tensor([x['input_ids']+[tokenizer.pad_token_id]*(width-len(x['input_ids'])) for x in batch]),
            'attention_mask':torch.tensor([[1]*len(x['input_ids'])+[0]*(width-len(x['input_ids'])) for x in batch]),
            'labels':torch.tensor([x['labels']+[-100]*(width-len(x['labels'])) for x in batch])}
    class Budget(TrainerCallback):
        stopped=False
        def on_step_end(self,args,state,control,**kwargs):
            stop=torch.tensor(int(time.monotonic()-started>args_wall_seconds),device=local_rank)
            if torch.distributed.is_initialized():
                torch.distributed.all_reduce(stop,op=torch.distributed.ReduceOp.MAX)
            if stop.item():
                self.stopped=True;control.should_save=True;control.should_training_stop=True
            return control
    args_wall_seconds=args.wall_hours*3600
    budget=Budget()
    settings=TrainingArguments(output_dir=str(args.out),per_device_train_batch_size=1,per_device_eval_batch_size=1,
        gradient_accumulation_steps=args.grad_accum,num_train_epochs=args.epochs,learning_rate=args.lr,
        warmup_ratio=.05,lr_scheduler_type='cosine',fp16=not bf16,bf16=bf16,optim='paged_adamw_8bit',
        gradient_checkpointing=True,gradient_checkpointing_kwargs={'use_reentrant':False},max_grad_norm=.3,
        logging_steps=5,eval_strategy='no',save_strategy='steps',save_steps=100,save_total_limit=2,
        seed=manifest['seed'],data_seed=manifest['seed'],report_to=[],dataloader_pin_memory=True,
        dataloader_num_workers=0,remove_unused_columns=False,ddp_find_unused_parameters=False)
    trainer=Trainer(model=model,args=settings,train_dataset=encoded['train'],eval_dataset=encoded['dev'],data_collator=collate,callbacks=[budget])
    result=trainer.train()
    trainer.accelerator.wait_for_everyone()
    if not trainer.is_world_process_zero():return
    model.save_pretrained(args.out/'adapter',safe_serialization=True);tokenizer.save_pretrained(args.out/'adapter')
    trainer.save_state()
    complete=not budget.stopped and (trainer.state.epoch or 0)>=args.epochs-.001
    weights=args.out/'adapter/adapter_model.safetensors'
    config=json.loads((args.out/'adapter/adapter_config.json').read_text('utf-8'))
    if config['base_model_name_or_path']!=BASE:raise RuntimeError('Output adapter has wrong base model')
    meta={**preflight,**precision,'training_mode':'new_adapter_on_pretrained_base','completed':complete,
        'stopped_for_time_budget':budget.stopped,'epochs_requested':args.epochs,'epochs_completed':trainer.state.epoch,
        'global_steps':trainer.state.global_step,'train_metrics':result.metrics,'gpu':torch.cuda.get_device_name(0),
        'wall_seconds':round(time.monotonic()-started),'peak_vram_gib':round(torch.cuda.max_memory_allocated()/2**30,2),
        'weights_sha256':hashlib.sha256(weights.read_bytes()).hexdigest(),
        'versions':{'python':platform.python_version(),'torch':torch.__version__,'transformers':transformers.__version__,
            'peft':peft.__version__,'bitsandbytes':bitsandbytes.__version__},
        'validation':'Training loss only. No live accuracy claim; independent evaluation required before deployment.'}
    (args.out/'run_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    (args.out/'data_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(meta,indent=2),flush=True)
    print('TRAINING COMPLETE' if complete else 'PARTIAL TRAINING SAVED: time budget reached; do not call this a completed run.',flush=True)

if __name__=='__main__':main()
