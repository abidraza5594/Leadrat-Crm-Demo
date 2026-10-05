"""Reviewed handbook wording, separate from model-generated customer extraction."""
import hashlib
import json
import re
from functools import lru_cache
from .config import ROOT

def normalize(text):
    return re.sub(r'[^a-z0-9]+',' ',text.lower().replace('\u2019', "'").replace('\u2018', "'")).strip()

@lru_cache(maxsize=1)
def entries():
    path=ROOT/'knowledge/handbook-faq.json'
    if not path.is_file():return {}
    data=json.loads(path.read_text(encoding='utf8'))
    installed=list((ROOT/'knowledge/docs').glob('*.pdf'))
    if not any(hashlib.sha256(p.read_bytes()).hexdigest()==data['source_sha256'] for p in installed):return {}
    return {normalize(item['question']):item for item in data['items']}

def lookup(question):
    # Exact wording after punctuation/case normalization only. Negation, extra
    # instructions and different wording must go through normal retrieval.
    key=normalize(question)
    aliases={
        'how i can add lead':'how do i create a new lead',
        'how can i add a lead':'how do i create a new lead',
        'how to add lead':'how do i create a new lead',
        'how to add a lead':'how do i create a new lead',
    }
    return entries().get(aliases.get(key,key))
