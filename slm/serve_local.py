"""Loopback-only Qwen service: current release for qualification, base for CRM guidance."""
import os
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
import hashlib
import json
import threading
import time
from contextlib import nullcontext
from pathlib import Path
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
RELEASE = json.loads((ROOT / 'slm/current_release.json').read_text())
ADAPTER = (ROOT / RELEASE['local_adapter']).resolve()
assert ADAPTER.is_relative_to(ROOT / 'slm/runs')
SHA = hashlib.sha256((ADAPTER / 'adapter_model.safetensors').read_bytes()).hexdigest()
assert SHA == RELEASE['weights_sha256'], 'Current adapter hash mismatch'
QUAL_MODEL = 'beacon-v4'
BASE_MODEL = 'qwen2.5-1.5b-instruct'
app = FastAPI()
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost'])
lock = threading.Lock()
slots = threading.BoundedSemaphore(2)
model = tokenizer = None
precision = 'loading'

class Message(BaseModel):
    role: str
    content: str = Field(max_length=40000)

class Request(BaseModel):
    model: str
    messages: list[Message] = Field(min_length=1, max_length=30)
    max_tokens: int = Field(default=900, ge=1, le=1000)
    temperature: float = 0

def load():
    global model, tokenizer, precision
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU is required for this local service')
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER, local_files_only=True)
    if tokenizer.pad_token_id is None: tokenizer.pad_token = tokenizer.eos_token
    free_bytes, _ = torch.cuda.mem_get_info()
    precision = 'float16' if free_bytes >= 3.6 * 1024**3 else 'nf4-float16'
    options = {} if precision == 'float16' else {'quantization_config':BitsAndBytesConfig(
        load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.float16)}
    print('GPU mode:', precision, 'free MiB', round(free_bytes/2**20), flush=True)
    base = AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct', local_files_only=True,
        device_map={'': 0}, torch_dtype=torch.float16, attn_implementation='sdpa', **options)
    model = PeftModel.from_pretrained(base, ADAPTER, local_files_only=True, autocast_adapter_dtype=False).eval()
    model.config.use_cache = True
    torch.cuda.empty_cache()
    print('Beacon local model ready:', QUAL_MODEL, SHA, flush=True)

@app.get('/health')
def health():
    return {'ready': model is not None, 'qualification_model': QUAL_MODEL, 'base_model': BASE_MODEL,
            'weights_sha256': SHA, 'revision': RELEASE['revision'], 'precision':precision, 'external_llm_calls': False}

@app.post('/v1/chat/completions')
def completion(body: Request):
    if body.model not in (QUAL_MODEL, BASE_MODEL): raise HTTPException(400, 'Unknown model')
    if model is None: raise HTTPException(503, 'Model is loading')
    if any(m.role not in ('system', 'user', 'assistant') for m in body.messages):
        raise HTTPException(400, 'Invalid message role')
    if not slots.acquire(blocking=False): raise HTTPException(429, 'Local model is busy')
    try:
        with lock:
            # Windows OpenMP settings must also be applied in the inference worker.
            torch.set_num_threads(4)
            started = time.monotonic()
            print('Starting generation:', body.model, 'limit', body.max_tokens, flush=True)
            prompt = tokenizer.apply_chat_template([m.model_dump() for m in body.messages],
                tokenize=False, add_generation_prompt=True)
            batch = tokenizer(prompt, add_special_tokens=False, return_tensors='pt').to(0)
            print('Prompt tokens:', batch['input_ids'].shape[1], flush=True)
            if batch['input_ids'].shape[1] + body.max_tokens > 4096:
                raise HTTPException(413, 'Conversation is too long for the local model')
            adapter_context = nullcontext() if body.model == QUAL_MODEL else model.disable_adapter()
            with adapter_context, torch.inference_mode():
                output = model.generate(**batch, max_new_tokens=body.max_tokens, do_sample=False,
                    pad_token_id=tokenizer.pad_token_id, logits_to_keep=1, max_time=120)
            content = tokenizer.decode(output[0, batch['input_ids'].shape[1]:], skip_special_tokens=True)
            print('Generation complete:', body.model, 'tokens', output.shape[1]-batch['input_ids'].shape[1],
                  'seconds', round(time.monotonic()-started, 2), flush=True)
            del output, batch
            return {'model': body.model, 'weights_sha256': SHA if body.model == QUAL_MODEL else None,
                    'choices': [{'message': {'role': 'assistant', 'content': content}}]}
    finally:
        slots.release()

if __name__ == '__main__':
    load()
    uvicorn.run(app, host='127.0.0.1', port=8012, access_log=False)
