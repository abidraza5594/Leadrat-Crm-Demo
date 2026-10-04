"""Reproducible held-out evaluation of the published v3 adapter; saves every raw output."""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from slm.prompting import messages, render, parse, rescore
from slm.labels import Qualification

FIELDS = {
    'role':'What is the visitor job role?',
    'seniority':'What is the visitor seniority?',
    'organisation.name':'What is the organisation name?',
    'organisation.type':'What type of organisation is it?',
    'organisation.agents':'How many agents are on the team?',
    'pain_points':'What problems did the visitor state?',
    'current_tooling':'Which tools are currently used?',
    'process':'Is the process manual or CRM based, and is the visitor satisfied?',
    'geography.cities':'Which cities were stated?',
    'geography.countries':'Which countries were stated?',
    'monthly_leads.min':'What is the minimum monthly lead volume?',
    'monthly_leads.max':'What is the maximum monthly lead volume?',
    'lead_sources':'Where do the leads come from?',
    'influence':'What purchase authority does the visitor have?',
    'next_step':'What is the intended timing or next step?',
    'consent':'Did the visitor consent to sales contact?',
    'contact.name':'What contact name was provided?',
    'contact.email':'What contact email was provided?',
    'contact.phone':'What contact phone was provided?',
    'icp_score':'What is the ICP score, or is it unknown?',
    'score_range':'What is the possible ICP score range?',
    'route':'Which follow-up route should be used?',
}

def get(d, path):
    for key in path.split('.'):
        if not isinstance(d, dict) or key not in d: return None
        d=d[key]
    return d

def normalized(v, field):
    if v is None: return None
    if isinstance(v,str): return re.sub(r'\s+',' ',v.strip()).casefold()
    if isinstance(v,list):
        if field=='score_range': return v
        return sorted(set(normalized(s,field) for s in v))
    return v

def fingerprint(r):
    return '\n'.join(t['text'].strip().casefold() for t in r['transcript'] if t['speaker']=='visitor')

def score(source, raw, ms, usage):
    parsed, reason=parse(raw,source['transcript'])
    pred=parsed.model_dump() if parsed else None
    gold=source['target']
    checks=[]
    for field,question in FIELDS.items():
        g,p=get(gold,field),get(pred,field)
        correct=pred is not None and normalized(p,field)==normalized(g,field)
        checks.append({'field':field,'question':question,'expected':g,'actual':p,
                       'correct':int(correct),'reference_known':int(g is not None and g!='unknown'),
                       'method':'Normalized text/set equality' if field in ['role','organisation.name','pain_points','current_tooling','geography.cities','geography.countries','lead_sources','contact.name','contact.email','contact.phone'] else 'Exact equality'})
    count=sum(c['correct'] for c in checks)
    return {'id':source['id'],'family':source['family'],'language':source['language'],
            'source':source.get('source'),'transcript':source['transcript'],'prompt_questions':'\n'.join(t['text'] for t in source['transcript'] if t['speaker']=='beacon'),
            'raw':raw,'gold':gold,'pred':pred,'parse_reason':reason,'valid':int(pred is not None),
            'checks':checks,'matched_fields':count,'total_fields':len(checks),'fully_matched':int(count==len(checks)),
            'raw_exact_json_match':int(pred==gold),
            'routing_correct':int(pred is not None and pred['route']==gold['route']),
            'rescored_route':rescore(parsed).route if parsed else None,
            'unsafe_handoff':int(pred is not None and pred['route']=='sales_handoff' and (gold['route']!='sales_handoff' or not gold['consent'])),
            'ms':ms,'usage':usage}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--batch-size',type=int,default=8);ap.add_argument('--limit',type=int);args=ap.parse_args()
    out=ROOT/'outputs/beacon-training-v3/evaluation';out.mkdir(exist_ok=True)
    release=json.loads((out.parent/'hf_published_v3.json').read_text())
    rows=[json.loads(l) for l in (ROOT/'slm/data/v3/test.jsonl').read_text('utf-8').splitlines() if l.strip()]
    train=[json.loads(l) for l in (ROOT/'slm/data/v3/train.jsonl').read_text('utf-8').splitlines() if l.strip()]
    dev=[json.loads(l) for l in (ROOT/'slm/data/v3/dev.jsonl').read_text('utf-8').splitlines() if l.strip()]
    assert not {r['id'] for r in rows}&{r['id'] for r in train+dev}
    assert not {r['family'] for r in rows}&{r['family'] for r in train+dev}
    assert not {fingerprint(r) for r in rows}&{fingerprint(r) for r in train+dev}
    for r in rows: Qualification.model_validate(r['target'])
    if args.limit: rows=rows[:args.limit]
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM,AutoTokenizer,BitsAndBytesConfig
    from peft import PeftModel
    adapter=snapshot_download(release['repo'],revision=release['revision'],allow_patterns=['adapter*','tokenizer*','special_tokens_map.json','added_tokens.json','vocab.json','merges.txt','chat_template.jinja'])
    assert hashlib.sha256((Path(adapter)/'adapter_model.safetensors').read_bytes()).hexdigest()==release['weights_sha256']
    print('Published revision downloaded and verified:',release['revision'],flush=True)
    tok=AutoTokenizer.from_pretrained(adapter,padding_side='left')
    if tok.pad_token_id is None:tok.pad_token=tok.eos_token
    model=AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct',device_map={'':0},
        quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.float16))
    model=PeftModel.from_pretrained(model,adapter).eval()
    model.config.use_cache=True
    torch.cuda.empty_cache()
    print('Model GPU memory MiB:', round(torch.cuda.memory_allocated()/2**20), flush=True)
    outfile=out/('predictions-smoke.jsonl' if args.limit else 'predictions.jsonl')
    existing=[json.loads(l) for l in outfile.read_text('utf-8').splitlines()] if outfile.exists() else []
    done={r['id'] for r in existing}; todo=[r for r in rows if r['id'] not in done]
    print('Loaded on',torch.cuda.get_device_name(0),'pending',len(todo),'batch',args.batch_size,flush=True)
    started=time.time()
    with outfile.open('a',encoding='utf-8') as f:
        for pos in range(0,len(todo),args.batch_size):
            group=todo[pos:pos+args.batch_size]
            prompts=[tok.apply_chat_template(messages(r['transcript']),add_generation_prompt=True,tokenize=False) for r in group]
            batch=tok(prompts,add_special_tokens=False,return_tensors='pt',padding=True).to(0)
            t=time.time()
            with torch.inference_mode():
                generated=model.generate(**batch,max_new_tokens=900,do_sample=False,
                    pad_token_id=tok.pad_token_id,logits_to_keep=1)
            elapsed=time.time()-t
            for r,gen,mask in zip(group,generated,batch['attention_mask']):
                tokens=gen[batch['input_ids'].shape[1]:]
                raw=tok.decode(tokens,skip_special_tokens=True)
                result=score(r,raw,round(elapsed*1000/len(group)),{'input_tokens':int(mask.sum()),'output_tokens':int((tokens!=tok.pad_token_id).sum()),'batch_seconds':round(elapsed,3),'batch_size':len(group)})
                result['revision']=release['revision']
                f.write(json.dumps(result,ensure_ascii=False)+'\n');f.flush();existing.append(result)
            print(f'Completed {len(existing)}/{len(rows)}; batch {elapsed:.1f}s; matched fields {sum(r["matched_fields"] for r in existing)}/{len(existing)*len(FIELDS)}',flush=True)
            # Release temporary generation allocations between batches on small GPUs.
            del generated, batch
            torch.cuda.empty_cache()
    summary={'release':release,'examples':len(existing),'schema_valid':sum(r['valid'] for r in existing),
        'fully_matched':sum(r['fully_matched'] for r in existing),'routing_correct':sum(r['routing_correct'] for r in existing),
        'matched_fields':sum(r['matched_fields'] for r in existing),'total_fields':len(existing)*len(FIELDS),
        'unsafe_handoffs':sum(r['unsafe_handoff'] for r in existing),'fields':FIELDS,
        'test_sha256':hashlib.sha256((ROOT/'slm/data/v3/test.jsonl').read_bytes()).hexdigest(),
        'evaluation_seconds_this_session':round(time.time()-started),'gpu':torch.cuda.get_device_name(0),
        'inference':'NF4 4-bit base, greedy decoding, max_new_tokens=900, left-padded batches',
        'limitations':'Synthetic reference labels, not independently human-reviewed. Text/list equality is conservative and can reject valid paraphrases. Field accuracy includes correct unknown values. Family and exact visitor transcript overlap checks passed; broader template similarity can remain. Results apply to structured qualification, not general chatbot question answering.'}
    (out/('summary-smoke.json' if args.limit else 'summary.json')).write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['fields','limitations']},indent=2),flush=True)

if __name__=='__main__':main()
