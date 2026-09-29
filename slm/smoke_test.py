"""Load the base model + a trained adapter on the local GPU and qualify a few transcripts end to end.

Usage: python slm/smoke_test.py [--adapter slm/runs/kaggle/adapter]
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from slm.prompting import messages, parse, rescore  # noqa: E402

NEW = {  # English transcripts that are not in the training or dev data
    'new: qualified owner': [
        {'turn_id': 1, 'speaker': 'beacon', 'text': 'Hi! Which part of Leadrat would you like to see?'},
        {'turn_id': 2, 'speaker': 'visitor', 'text': 'We run a brokerage in Pune with 18 agents. Our biggest problem is missed follow-ups.'},
        {'turn_id': 3, 'speaker': 'beacon', 'text': 'Roughly how many leads do you get a month?'},
        {'turn_id': 4, 'speaker': 'visitor', 'text': 'Around 400 a month, mostly from MagicBricks and Facebook. Everything is in Excel today.'},
        {'turn_id': 5, 'speaker': 'beacon', 'text': 'Would you like our team to follow up?'},
        {'turn_id': 6, 'speaker': 'visitor', 'text': "Yes, I'm the owner. Call me on +91 90000 04321 next week."}],
    'new: missing volume, no contact': [
        {'turn_id': 1, 'speaker': 'beacon', 'text': 'Hi! What brings you to Leadrat today?'},
        {'turn_id': 2, 'speaker': 'visitor', 'text': "I'm a sales manager at a developer in Hyderabad. We have two projects launching."},
        {'turn_id': 3, 'speaker': 'beacon', 'text': 'How many leads do you handle a month?'},
        {'turn_id': 4, 'speaker': 'visitor', 'text': "Not sure, I'd have to check. Can you show me the lead dashboard?"},
        {'turn_id': 5, 'speaker': 'beacon', 'text': 'Sure. Would you like someone from our team to reach out?'},
        {'turn_id': 6, 'speaker': 'visitor', 'text': 'Not right now, I am just exploring.'}],
}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--adapter', default='slm/runs/kaggle/adapter'); args = ap.parse_args()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    started = time.time()
    tok = AutoTokenizer.from_pretrained(args.adapter)
    base = AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct', device_map={'': 0}, quantization_config=BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_compute_dtype=torch.float16))
    model = PeftModel.from_pretrained(base, args.adapter).eval()
    print(f'loaded in {time.time() - started:.0f}s on {torch.cuda.get_device_name(0)}, VRAM {torch.cuda.memory_allocated() / 2**30:.2f} GiB', flush=True)
    dev = json.loads((ROOT / 'slm' / 'data' / 'dev.jsonl').read_text('utf-8').splitlines()[0])
    for name, transcript, gold in [('dev ' + dev['id'], dev['transcript'], dev['target'])] + [(k, v, None) for k, v in NEW.items()]:
        text = tok.apply_chat_template(messages(transcript), add_generation_prompt=True, tokenize=False)
        ids = tok(text, add_special_tokens=False, return_tensors='pt')['input_ids'].to(0)
        t = time.time()
        with torch.no_grad(): out = model.generate(ids, max_new_tokens=900, do_sample=False, pad_token_id=tok.eos_token_id)
        raw = tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)
        q, reason = parse(raw, transcript)
        print(f'\n== {name}: {time.time() - t:.1f}s, parse: {reason or "ok"}')
        if q is None: print(raw[:800]); continue
        r = rescore(q)
        facts = {'org': q.organisation.model_dump(), 'role': q.role, 'seniority': q.seniority, 'monthly_leads': q.monthly_leads.model_dump(),
                 'lead_sources': q.lead_sources, 'tooling': q.current_tooling, 'cities': q.geography.cities, 'pain_points': q.pain_points,
                 'consent': q.consent, 'contact': q.contact.model_dump(), 'next_step': q.next_step}
        print(json.dumps(facts, ensure_ascii=False))
        print(f'model: score {q.icp_score} range {q.score_range} route {q.route} | rules: score {r.icp_score} range {r.score_range} route {r.route}')
        if gold: print(f'gold:  score {gold["icp_score"]} range {gold["score_range"]} route {gold["route"]}')

if __name__ == '__main__':
    main()
