"""Speed paths: prepared speech, early speech for checked answers, and non-blocking session close."""
import asyncio,json
from app import config,voice
from app.voice import VoiceCache,warm_phrases
from app.conversation_engine import Decision
from app.semantic_knowledge import SemanticKnowledge


def fake_edge(monkeypatch,calls):
    import edge_tts
    class Fake:
        def __init__(self,text,*args,**kwargs):calls.append(text)
        async def stream(self):yield {'type':'audio','data':b'mp3'}
    monkeypatch.setattr(config,'TTS_PROVIDER','edge')
    monkeypatch.setattr(edge_tts,'Communicate',Fake)


def test_fixed_phrases_are_synthesised_once_kept_on_disk_and_served_instantly(monkeypatch,tmp_path):
    calls=[];fake_edge(monkeypatch,calls)
    monkeypatch.setattr(voice,'PHRASES',{});monkeypatch.setattr(voice,'PHRASE_DIR',tmp_path)
    async def run():
        await warm_phrases(['Welcome to Beacon!','Welcome to Beacon!','What else would you like to see?'])
        assert sorted(calls)==['Welcome to Beacon!','What else would you like to see?']
        assert len(list(tmp_path.glob('*.mp3')))==2
        # A restarted server reads the files instead of synthesising again.
        voice.PHRASES.clear();await warm_phrases(['Welcome to Beacon!'])
        assert len(calls)==2 and voice.PHRASES
        cache=VoiceCache()
        assert b''.join([c async for c in cache.stream('Welcome to Beacon!')])==b'mp3' and len(calls)==2
        cache.close()
    asyncio.run(run())


def test_every_fixed_reply_is_prepared(monkeypatch):
    from app import main
    phrases=set(main.fixed_phrases())
    for text in (main.WELCOME,main.offer_text('leads'),main.CONTACT_QUESTION,main.reask(main.DISCOVERY[0][1])):
        assert set(main.speech_parts(text))<=phrases


def test_draft_speech_starts_before_the_source_check_and_unchecked_text_is_not_returned():
    order=[]
    async def complete(messages,schema,**kw):
        if 'valid' in schema['properties']:
            order.append('check');return {'valid':False,'reason':'Unsupported claim'}
        order.append('draft');return {'supported':True,'answer':'Inventory tracks units and prices.','evidence_ids':['doc:1#0'],'demo_requested':False}
    k=SemanticKnowledge(completion=complete);k.ready=True
    k.documents=[{'id':1,'module':'Inventory','section':'Purpose and overview','text':'Tracks available units.','page':3}]
    async def retrieve(*args,**kwargs):return [(0.8,k.documents[0])]
    k.retrieve=retrieve
    result=asyncio.run(k.answer('What is inventory?',Decision(kind='product',topic='Inventory'),{},on_draft=lambda text:order.append('speech:'+text)))
    assert order[:3]==['draft','speech:Inventory tracks units and prices.','check']
    assert 'prices' not in result['text'] and not result['grounded']


def test_prepared_frame_is_served_once_and_refreshing_it_captures_live(monkeypatch):
    from app.browser import BrowserWorker
    monkeypatch.setattr(config,'SANDBOX_CONFIRMED',True)
    async def run():
        w=BrowserWorker();shots=[]
        async def capture():shots.append(len(shots));return b'frame%d'%len(shots)
        w.capture=capture;w.alive=lambda:True
        await w.prepare_frame();await w.prepare_frame()
        assert w.ready_frame==b'frame2'  # a refresh captures again instead of keeping the old frame
        assert await w.screenshot()==b'frame2' and w.ready_frame is None
        assert await w.screenshot()==b'frame3'
    asyncio.run(run())


def test_unchanged_state_and_frame_are_answered_without_a_body(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    class Worker:
        login_problem=None
        async def signed_in(self):return True
        async def authenticated(self):return True
        async def adopt_saved_login(self):return False
        def alive(self):return True
        async def screenshot(self):return b'jpeg-bytes'
        async def close(self):pass
    async def boot(s):s.worker=Worker();s.status='ready'
    async def nothing():pass
    monkeypatch.setattr(main,'boot',boot);monkeypatch.setattr(main,'warm_up',nothing)
    with TestClient(main.app) as client:
        r=client.post('/api/sessions',json={'parent_origin':'http://localhost:8011'});s=r.json()
        h={'X-Beacon-Token':s['token']};path='/api/sessions/'+s['id']
        for suffix in ('','/screen'):
            first=client.get(path+suffix,headers=h)
            assert first.status_code==200 and first.headers['etag']
            again=client.get(path+suffix,headers={**h,'If-None-Match':first.headers['etag']})
            assert again.status_code==304 and again.content==b''
        assert client.get(path,headers=h).json()['id']==s['id']
        main.sessions[s['id']].say('Something new.')
        assert client.get(path,headers={**h,'If-None-Match':first.headers['etag']}).status_code==200
        client.delete(path,headers=h)


def test_ending_a_session_does_not_wait_for_chrome_to_close(monkeypatch):
    from app import main
    async def run():
        release=asyncio.Event();closed=[]
        class Slow:
            async def close(self):await release.wait();closed.append(True)
        monkeypatch.setattr(main,'sessions',{})
        s=main.Session();s.worker=Slow();main.sessions[s.id]=s
        await asyncio.wait_for(main.close(s),0.5)
        assert s.id not in main.sessions and not closed
        release.set()
        await asyncio.wait(list(main.teardowns),timeout=1)
        assert closed==[True]
    asyncio.run(run())
