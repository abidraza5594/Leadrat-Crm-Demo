"""Generate comparison answers using the same prompt/decoding as preserved v3 evaluation."""
import argparse,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from slm.evaluate_v3_release import score,FIELDS
from slm.prompting import messages

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--batch-size',type=int,default=4);ap.add_argument('--limit',type=int);ap.add_argument('--cloud',action='store_true');args=ap.parse_args()
    out=ROOT/'outputs/beacon-training-v4/comparison';out.mkdir(parents=True,exist_ok=True)
    regression=[json.loads(l) for l in (ROOT/'slm/data/v3/test.jsonl').read_text(encoding='utf-8').splitlines()]
    fresh=[json.loads(l) for l in (ROOT/'slm/data/v4/fresh_test.jsonl').read_text(encoding='utf-8').splitlines()]
    # Two deterministic examples per scenario, selected before seeing model answers.
    counts={};selected=[]
    for r in fresh:
        family=r.get('scenario',r['family'])
        # v4 family identifies the scenario; retain up to two per family.
        if counts.get(family,0)<2:selected.append(r);counts[family]=counts.get(family,0)+1
    (out/'fresh_selection.json').write_text(json.dumps({'selected':len(selected),'families':counts},indent=2))
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM,BitsAndBytesConfig
    from peft import PeftModel
    torch.set_num_threads(4)
    new=ROOT/'slm/runs/kaggle-v4-continued/adapter';old=ROOT/'slm/runs/kaggle/adapter'
    releases=[('new',new,regression+selected),('old',old,selected)]
    tok=AutoTokenizer.from_pretrained(new,padding_side='left')
    if tok.pad_token_id is None:tok.pad_token=tok.eos_token
    print('Loading cached base model',flush=True)
    base=AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct',device_map={'':0},local_files_only=not args.cloud,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.float16))
    model=PeftModel.from_pretrained(base,new,adapter_name='new').eval()
    model.load_adapter(old,adapter_name='old');model.config.use_cache=True
    for name,adapter,rows in releases:
        model.set_adapter(name)
        if args.limit:rows=rows[:args.limit]
        file=out/(name+('-smoke' if args.limit else '')+'.jsonl')
        existing=[json.loads(l) for l in file.read_text(encoding='utf-8').splitlines()] if file.exists() else []
        sha=hashlib.sha256((adapter/'adapter_model.safetensors').read_bytes()).hexdigest()
        assert all(r['weights_sha256']==sha for r in existing)
        done={r['id'] for r in existing};todo=[r for r in rows if r['id'] not in done]
        print(name,'pending',len(todo),'gpu',torch.cuda.get_device_name(0),flush=True)
        with file.open('a',encoding='utf-8') as f:
            for pos in range(0,len(todo),args.batch_size):
                group=todo[pos:pos+args.batch_size]
                prompts=[tok.apply_chat_template(messages(r['transcript']),add_generation_prompt=True,tokenize=False) for r in group]
                batch=tok(prompts,add_special_tokens=False,return_tensors='pt',padding=True).to(0)
                t=time.time()
                with torch.inference_mode():
                    gen=model.generate(**batch,max_new_tokens=900,do_sample=False,pad_token_id=tok.pad_token_id,logits_to_keep=1)
                seconds=time.time()-t
                for r,tokens,mask in zip(group,gen,batch['attention_mask']):
                    tokens=tokens[batch['input_ids'].shape[1]:];raw=tok.decode(tokens,skip_special_tokens=True)
                    result=score(r,raw,round(seconds*1000/len(group)),{'batch_size':len(group),'batch_seconds':seconds})
                    result.update(weights_sha256=sha,version=name,dataset='regression' if r['id'] in {x['id'] for x in regression} else 'fresh')
                    f.write(json.dumps(result,ensure_ascii=False)+'\n');f.flush();existing.append(result)
                print(name,len(existing),'/',len(rows),'batch seconds',round(seconds,1),flush=True)
                del gen,batch;torch.cuda.empty_cache()

if __name__=='__main__':main()
