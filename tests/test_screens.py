"""The screen map is generated from the CRM code; locations are chosen by meaning, not by names in Beacon."""
import asyncio,json
import numpy as np
from app.screens import Screens

class Encoder:
    """Bag-of-letters vectors: enough to rank candidates deterministically without the real model."""
    def encode(self,texts,**kwargs):
        def one(t):
            v=np.zeros(26,dtype=np.float32)
            for c in t.lower():
                if 'a'<=c<='z':v[ord(c)-97]+=1
            return v/max(np.linalg.norm(v),1e-9)
        return one(texts) if isinstance(texts,str) else np.array([one(t) for t in texts])

def screens(tmp_path):
    entries=[{'id':'p0','path':'/global-config','page':'Global Config','section':None,'text':'Global Config: Module Settings, Integration'},
             {'id':'p1','path':'/global-config','page':'Global Config','section':'Integration','text':'Global Config › Integration'},
             {'id':'p2','path':'/attendance','page':'Attendance','section':None,'text':'Attendance: Clock In'},
             {'id':'p3','path':'https://elsewhere.example/x','page':'Bad','section':None,'text':'Bad'}]
    path=tmp_path/'screens.json';path.write_text(json.dumps({'entries':entries}))
    return Screens(path)

def test_only_in_app_paths_are_navigable(tmp_path):
    assert {e['path'] for e in screens(tmp_path).entries}=={'/global-config','/attendance'}

def test_generated_map_covers_the_crm():
    from app.screens import MAP
    data=json.loads(MAP.read_text('utf8'))
    paths={e['path'] for e in data['entries']}
    assert data['pages']>=100 and all(p.startswith('/') for p in paths)
    assert not any(p.startswith('/login') for p in paths)

def test_words_shown_on_a_screen_are_found_whatever_the_spelling():
    """Live report: "weebhook" / "let me about webhook" opened Leadrat AI, though Webhook is an
    integration card on Global Config. Words on the screen count, typed apart, together or misspelled."""
    s=Screens()
    for question,page in [('weebhook','Global Config'),('let me about webhook','Global Config'),('99acres kaise connect kare','Global Config')]:
        scores=s.content_match(question)
        assert s.entries[int(scores.argmax())]['page'].startswith(page),question

def test_search_returns_ranked_options_including_walkthroughs(tmp_path,monkeypatch):
    """The search only finds options (pages, sections, walkthroughs); it never decides."""
    import app.screens as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    s=screens(tmp_path);s.include({'leads':{'title':'Leads workspace','intent_description':'Leads list','facts':['Manage leads.']}})
    async def run():
        await s.prepare(Encoder())
        return await s.candidates(Encoder(),'attendance clock in')
    ranked=asyncio.run(run())
    assert ranked[0][1]['path']=='/attendance' and any(e.get('walkthrough')=='leads' for _,e,_ in ranked)
    assert not hasattr(module,'decisive') and not hasattr(s,'choose')
