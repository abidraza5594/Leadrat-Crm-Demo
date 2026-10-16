"""Search the CRM's pages, sections and prepared walkthroughs for the ones a message may be about.

Locations come from the screen map generated out of the CRM's code (knowledge/screens.json, built by
app/screen_map.py) together with the project's prepared walkthroughs. This module only searches: it
returns ranked options. What to show, if anything, is decided by the conversation model in
app/conversation_engine.py. No page, module or section is named in this file.
"""
import asyncio
import hashlib
import json
import re
import numpy as np
from .config import ROOT

MAP=ROOT/'knowledge'/'screens.json'
# Weights of meaning, words in the location's name, words shown on it, and character spelling of its name
# (measured with: python -m eval.screen_choice).
WEIGHTS=(0.45,0.5,0.35,0.2)

def informative(text):
    """Candidate subject words of a message (filler is removed later: it matches nothing in the CRM)."""
    from .docs import STOP
    from .planner import romanize
    return [w for w in re.findall(r'[a-z0-9]+',romanize(text).lower()) if len(w)>=4 and w not in STOP]

def grams(text):
    """Character trigrams of the words in text, for matching names whatever the spelling."""
    text=' '+' '.join(re.findall(r'[a-z0-9]+',text.lower()))+' '
    return {text[i:i+3] for i in range(len(text)-2)}

def postings(pairs,array=False):
    """An inverted index: key -> the values listed with it, in first-seen order."""
    index={}
    for key,value in pairs:index.setdefault(key,[]).append(value)
    return {k:np.array(v,dtype=np.intp) for k,v in index.items()} if array else index

class Screens:
    def __init__(self,path=MAP):
        self.entries=[];self.vectors=None;self.lock=asyncio.Lock()
        if path.is_file():
            data=json.loads(path.read_text('utf8'))
            # Only in-app paths from the map are ever navigated to.
            self.entries=[e for e in data['entries'] if e['path'].startswith('/') and '://' not in e['path']]
        self.index()

    def index(self):
        self.version=hashlib.sha256(json.dumps(self.entries,sort_keys=True).encode()).hexdigest()[:16]
        self.by_id={e['id']:e for e in self.entries};self.vectors=None;self._signals={}
        # A location's own name: the last part of its page trail, plus its section. The shared parent
        # ("Global Config › ...") says nothing about which of its pages is meant.
        self.names=[grams(e['page'].split(' › ')[-1]+' '+(e['section'] or '')) for e in self.entries]
        self.sections=[grams(e['section']) if e['section'] else set() for e in self.entries]
        # Every word shown on a location, for spelling-tolerant matching of the visitor's own words.
        self.words=[set(re.findall(r'[a-z0-9]{3,}',e['text'].lower())) for e in self.entries]
        self.namewords=[set(re.findall(r'[a-z0-9]{3,}',(e['page']+' '+(e['section'] or '')).lower())) for e in self.entries]
        self.vocabulary={w:grams(w) for ws in self.words for w in ws}
        # Rarity of each word across locations: a word shown almost everywhere ("connect", "lead") says
        # little about which screen is meant; a rare one ("webhook", "99acres") says a lot.
        from collections import Counter
        df=Counter(w for ws in self.words for w in ws);n=max(1,len(self.words))
        self.rarity={w:float(np.log(1+n/c)) for w,c in df.items()}
        # Inverted indexes, so a message is scored by touching only what it shares with the map:
        # trigram -> CRM words (spelling matches), word -> locations, name trigram -> locations.
        self.order={w:i for i,w in enumerate(self.vocabulary)}
        self.gram_words=postings((g,w) for w,gs in self.vocabulary.items() for g in gs)
        self.word_places={id(sets):postings(((w,i) for i,ws in enumerate(sets) for w in ws),array=True)
                          for sets in (self.words,self.namewords)}
        self.name_grams=postings(((g,i) for i,gs in enumerate(self.names) for g in gs),array=True)
        self.name_sizes=np.array([len(gs) for gs in self.names],dtype=float)
        self._matches={}

    def include(self,features):
        """Add the project's prepared walkthroughs as options next to the generated pages."""
        self.entries=[e for e in self.entries if not e.get('walkthrough')]+[
            {'id':'w:'+key,'walkthrough':key,'path':None,'page':f['title'],'section':None,'reachable':True,
             'text':f['title']+': '+f.get('intent_description',f['title'])+'. '+' '.join(f.get('facts',[])[:1])}
            for key,f in features.items()]
        self.index()

    @property
    def ready(self):return self.vectors is not None

    async def prepare(self,encoder):
        async with self.lock:
            if self.ready or not self.entries or encoder is None:return
            cache=ROOT/'.state'/f'screens-{self.version}.npy'
            if cache.is_file():
                vectors=np.load(cache)
                if len(vectors)==len(self.entries):self.vectors=vectors;return
            vectors=await asyncio.to_thread(encoder.encode,[e['text'][:400] for e in self.entries],normalize_embeddings=True,show_progress_bar=False)
            cache.parent.mkdir(exist_ok=True);np.save(cache,vectors);self.vectors=vectors

    async def signals(self,encoder,query):
        """Per location: meaning (embedding similarity), the message's words in its name, and on it."""
        if query not in self._signals:
            vector=await asyncio.to_thread(encoder.encode,query,normalize_embeddings=True,show_progress_bar=False)
            similar=self.similar(query)
            # Character overlap with the location's name survives heavy misspelling ("salse copilt").
            spelling=self.spelling(grams(query))
            self._signals[query]=(self.vectors@vector,self.word_match(similar,self.namewords),self.word_match(similar,self.words),spelling)
            if len(self._signals)>256:self._signals.pop(next(iter(self._signals)))
        return self._signals[query]

    async def relevance(self,encoder,query):
        meaning,name,shown,spelling=await self.signals(encoder,query)
        return WEIGHTS[0]*meaning+WEIGHTS[1]*name+WEIGHTS[2]*shown+WEIGHTS[3]*spelling

    async def lexical(self,encoder,query):
        """Per location, how well it carries the message's own words, in its name and on it."""
        _,name,shown,_=await self.signals(encoder,query)
        return (WEIGHTS[1]*name+WEIGHTS[2]*shown)/max(1e-9,WEIGHTS[1]+WEIGHTS[2])

    async def candidates(self,encoder,query,pages=8,context=''):
        """Up to `pages` distinct pages, best first, as (score, option). A section is offered instead of its
        page only when the question names that part of the page. The latest message leads; earlier turns
        decide only when it is a bare follow-up with no subject of its own."""
        async def score(text):
            if self.ready and encoder is not None:
                try:return await self.relevance(encoder,text),await self.lexical(encoder,text)
                except Exception:pass
            # Startup or embedding failure must not hide the CRM page catalogue.
            similar=self.similar(text);asked=grams(text)
            name=self.word_match(similar,self.namewords);shown=self.word_match(similar,self.words)
            spelling=np.array([len(asked&n)/len(n) if n else 0.0 for n in self.names])
            return WEIGHTS[1]*name+WEIGHTS[2]*shown+WEIGHTS[3]*spelling,(WEIGHTS[1]*name+WEIGHTS[2]*shown)/max(1e-9,WEIGHTS[1]+WEIGHTS[2])
        scores,words=await score(query)
        if context:
            weight=0.2 if self.distinctive(query) else 0.7
            contextual,_=await score(query+'\n'+context)
            scores=(1-weight)*scores+weight*contextual
        asked=grams(query)
        chosen=[];seen=set()
        for i in np.argsort(-scores):
            e=self.entries[i];key=e.get('walkthrough') or e['path']
            # Only pages that open directly can be demonstrated; the page that leads to the others stays.
            if not e.get('reachable',True) or key in seen:continue
            if len(seen)>=pages:break
            seen.add(key)
            named=bool(self.sections[i]) and len(asked&self.sections[i])/len(self.sections[i])>=0.5
            if e['section'] and not named:
                e=next((x for x in self.entries if x['path']==e['path'] and not x['section']),e)
            chosen.append((float(scores[i]),e,float(words[i])))
        return chosen

    def matches(self,word):
        """Words shown somewhere in the CRM that this word means, allowing misspelling and joined words.

        Only CRM words sharing a trigram with the word can score (a substring of four or more letters
        shares its inner trigrams), so the trigram index visits those instead of the whole vocabulary.
        Jaccard similarity follows from the shared count: |a&b|/(|a|+|b|-|a&b|)."""
        cached=self._matches.get(word)
        if cached is not None:return cached
        g=grams(word);shared={}
        for gram in g:
            for v in self.gram_words.get(gram,()):shared[v]=shared.get(v,0)+1
        found=[]
        for v,common in shared.items():
            score=common/(len(g)+len(self.vocabulary[v])-common)
            if len(v)>=4 and (v in word or word in v):score=max(score,0.8)
            if score>=0.55:found.append((self.order[v],v,score))
        match={v:score for _,v,score in sorted(found)}
        if len(self._matches)>4096:self._matches.pop(next(iter(self._matches)))
        self._matches[word]=match
        return match

    def spelling(self,asked):
        """Per location, the share of its name's trigrams that the message contains."""
        counts=np.zeros(len(self.names))
        for gram in asked:
            places=self.name_grams.get(gram)
            if places is not None:counts[places]+=1
        return np.divide(counts,self.name_sizes,out=np.zeros_like(counts),where=self.name_sizes>0)

    def distinctive(self,text):
        """Does the message name something shown in the CRM? A bare follow-up ("isme kya hota hai") does not."""
        return any(self.matches(w) for w in informative(text))

    def similar(self,query):
        """For each subject word of the message, the CRM words it can mean. Words that appear nowhere in
        the CRM are filler in any language and are left out."""
        return [m for m in (self.matches(w) for w in informative(query)) if m]

    def word_match(self,similar,wordsets):
        """Per location, how well the message's subject words appear in its word set (its name, or all it
        shows), allowing misspellings, with rare words counting more than common ones."""
        if not similar:return np.zeros(len(self.entries))
        # A word's weight is the rarity of the CRM word it most closely is, not of its rarest look-alike.
        weights=[self.rarity.get(max(match,key=lambda v:(match[v],-self.rarity.get(v,0.0))),0.0) for match in similar]
        total=sum(weights) or 1.0
        places=self.word_places.get(id(wordsets))
        if places is None:
            return np.array([sum(w*max((s for v,s in match.items() if v in ws),default=0.0) for w,match in zip(weights,similar))/total
                             for ws in wordsets])
        # Visit only the locations that show a matched word (word -> locations index), not every location.
        result=np.zeros(len(wordsets))
        for w,match in zip(weights,similar):
            best=np.zeros(len(wordsets))
            for v,s in match.items():
                where=places.get(v)
                if where is not None:best[where]=np.maximum(best[where],s)
            result+=w*best
        return result/total

    def content_match(self,query):
        return self.word_match(self.similar(query),self.words)

    def detailed(self,entry):
        """A section carries its page's full text, so an answer can describe what the screen shows."""
        if not entry.get('section') or not entry.get('path'):return entry
        page=next((e for e in self.entries if e['path']==entry['path'] and not e['section']),None)
        return {**entry,'text':page['text']} if page else entry
