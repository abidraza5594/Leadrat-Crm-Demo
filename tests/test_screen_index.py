"""The indexed screen search returns exactly what the original full scans returned."""
import time
import numpy as np
from app.screens import Screens, grams, informative


def scan_matches(s,word):
    g=grams(word);match={}
    for v,vg in s.vocabulary.items():
        score=len(g&vg)/len(g|vg)
        if len(v)>=4 and (v in word or word in v):score=max(score,0.8)
        if score>=0.55:match[v]=score
    return match

def scan_word_match(s,similar,wordsets):
    if not similar:return np.zeros(len(s.entries))
    weights=[s.rarity.get(max(match,key=lambda v:(match[v],-s.rarity.get(v,0.0))),0.0) for match in similar]
    total=sum(weights) or 1.0
    return np.array([sum(w*max((x for v,x in match.items() if v in ws),default=0.0) for w,match in zip(weights,similar))/total for ws in wordsets])

QUERIES=['show leads','How do I add units to a project?','whatsapp integration kaise kare','isme kya hota hai',
    'salse copilt dashbord','webhook 99acres','lead ka status kaise badle','attendence report','bulk uplod','invioce templates',
    'site visit schedule','प्रोजेक्ट दिखाओ','roles and permisions','zzzz qqqq']

def test_indexed_search_equals_full_scan_and_is_faster():
    s=Screens()
    assert len(s.entries)>100
    words=sorted({w for q in QUERIES for w in informative(q)}|set(list(s.vocabulary)[:200]))
    for w in words:assert list(s.matches(w).items())==list(scan_matches(s,w).items())
    for q in QUERIES:
        similar=[m for m in (scan_matches(s,w) for w in informative(q)) if m]
        for sets in (s.words,s.namewords):
            assert np.array_equal(s.word_match(s.similar(q),sets),scan_word_match(s,similar,sets))
        asked=grams(q)
        assert np.array_equal(s.spelling(asked),np.array([len(asked&n)/len(n) if n else 0.0 for n in s.names]))
    s._matches.clear()
    started=time.perf_counter()
    for q in QUERIES:
        s.word_match(s.similar(q),s.words);s.word_match(s.similar(q),s.namewords);s.spelling(grams(q))
    indexed=time.perf_counter()-started
    started=time.perf_counter()
    for q in QUERIES:
        similar=[m for m in (scan_matches(s,w) for w in informative(q)) if m]
        scan_word_match(s,similar,s.words);scan_word_match(s,similar,s.namewords)
        [len(grams(q)&n)/len(n) if n else 0.0 for n in s.names]
    assert indexed*3<time.perf_counter()-started


def test_changing_a_few_screens_re_encodes_only_those(monkeypatch,tmp_path):
    """Editing one walkthrough description used to re-encode all ~2,000 screens at start-up."""
    import asyncio
    from app import screens as module
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'STORE',tmp_path/'.state'/'screen-vectors.npz')
    encoded=[]
    class Encoder:
        fingerprint='test-model'
        def encode(self,texts,**kwargs):
            encoded.extend(texts);return np.array([[float(len(t)),1.0] for t in texts],dtype=np.float32)
    first=Screens();first.entries=first.entries[:50];first.index()
    asyncio.run(first.prepare(Encoder()))
    assert len(encoded)==50
    encoded.clear()
    second=Screens();second.entries=first.entries[:49]+[{**first.entries[49],'text':'A changed screen description'}];second.index()
    asyncio.run(second.prepare(Encoder()))
    assert encoded==['A changed screen description']
    assert np.array_equal(second.vectors[:49],first.vectors[:49]) and second.vectors[49][0]==len('A changed screen description')


def test_a_question_does_not_wait_for_the_screen_index(monkeypatch,tmp_path):
    """Live report: after a restart the first question showed "Exploring your workspace…" for minutes while
    every screen was being re-encoded."""
    import asyncio,threading
    from types import SimpleNamespace
    from app import screens as module
    from app.conversation_engine import ConversationEngine
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'STORE',tmp_path/'.state'/'v.npz')
    release=threading.Event()
    class SlowEncoder:
        def encode(self,texts,**kwargs):
            if isinstance(texts,str):return np.ones(2,dtype=np.float32)
            release.wait(10);return np.ones((len(texts),2),dtype=np.float32)
    async def retrieve(*args,**kwargs):return []
    s=Screens();s.entries=s.entries[:300];s.index()
    engine=ConversationEngine({},[],SimpleNamespace(model=SlowEncoder(),retrieve=retrieve),screens=s)
    async def run():
        _,options=await asyncio.wait_for(engine.findings({'message':'show leads','history':[]}),3)
        assert options and not s.ready  # found by their words while the index builds
        release.set();await s._build
        assert s.ready
    asyncio.run(run())
