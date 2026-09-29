"""Standalone inference for the Beacon qualification adapter.

pip install "transformers>=4.45" peft accelerate huggingface_hub   (add bitsandbytes for --4bit)
python inference.py transcript.json [--4bit]

transcript.json is a list of turns: [{"turn_id": 1, "speaker": "beacon"|"visitor", "text": "..."}, ...]
Prints the model's beacon.qualification.v1 JSON. Re-derive icp_score, score_range and route from the extracted
facts with your own rules before acting on them (see the model card).
"""
import argparse
import json
import re
import sys

from huggingface_hub import hf_hub_download

REPO = 'abidansari5594/beacon-qualification-qwen2.5-1.5b-qlora'
BASE = 'Qwen/Qwen2.5-1.5B-Instruct'

def render(transcript):
    return '\n'.join(f"[{t['turn_id']}] {t['speaker'].upper()}: {t['text']}" for t in transcript)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('transcript'); ap.add_argument('--4bit', dest='four_bit', action='store_true')
    args = ap.parse_args()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    system = open(hf_hub_download(REPO, 'system_prompt.txt'), encoding='utf-8').read().strip()
    kwargs = {'device_map': 'auto', 'dtype': torch.float16 if torch.cuda.is_available() else torch.float32}
    if args.four_bit:
        from transformers import BitsAndBytesConfig
        kwargs['quantization_config'] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_compute_dtype=torch.float16)
    tok = AutoTokenizer.from_pretrained(REPO)
    model = PeftModel.from_pretrained(AutoModelForCausalLM.from_pretrained(BASE, **kwargs), REPO).eval()
    transcript = json.load(open(args.transcript, encoding='utf-8'))
    msgs = [{'role': 'system', 'content': system}, {'role': 'user', 'content': render(transcript)}]
    text = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    ids = tok(text, add_special_tokens=False, return_tensors='pt')['input_ids'].to(model.device)
    with torch.no_grad():
        out = model.generate(ids, max_new_tokens=900, do_sample=False, pad_token_id=tok.eos_token_id)
    raw = tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)
    match = re.search(r'\{.*\}', raw, re.S)
    if not match: sys.exit('no JSON in model output:\n' + raw)
    print(json.dumps(json.loads(match.group(0)), indent=1, ensure_ascii=False))

if __name__ == '__main__':
    main()
