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

def test_model_chooses_among_candidates_or_none(tmp_path,monkeypatch):
    import app.screens as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    s=screens(tmp_path);calls=[]
    async def completion(messages,schema,**kwargs):
        payload=json.loads(messages[-1]['content']);calls.append((payload,schema))
        return {'option':'p1' if 'integration' in payload['latest_message'] else 'none'}
    async def run():
        await s.prepare(Encoder())
        found=await s.choose(completion,Encoder(),'what is integration',[{'role':'user','text':'hi'}])
        assert found['id']=='p1'
        assert await s.choose(completion,Encoder(),'tell me a joke',[]) is None
    asyncio.run(run())
    payload,schema=calls[0]
    assert 'none' in schema['properties']['option']['enum'] and payload['conversation']==[{'role':'user','text':'hi'}]

def test_generated_map_covers_the_crm():
    from app.screens import MAP
    data=json.loads(MAP.read_text('utf8'))
    paths={e['path'] for e in data['entries']}
    assert data['pages']>=100 and all(p.startswith('/') for p in paths)
    assert not any(p.startswith('/login') for p in paths)
