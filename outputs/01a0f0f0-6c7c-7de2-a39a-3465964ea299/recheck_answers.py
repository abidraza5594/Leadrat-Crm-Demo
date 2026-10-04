import asyncio, json, os, sys
from pathlib import Path
ROOT=Path('C:/Leadrat AI/Beacon')
sys.path.insert(0,str(ROOT))
sys.path.append(str(ROOT/'.venv/Lib/site-packages'))
from slm.evaluate_v3_release import score
from app import qualify
rows=[json.loads(l) for l in (ROOT/'outputs/beacon-training-v3/evaluation/predictions.jsonl').read_text(encoding='utf-8').splitlines()]
sources={r['id']:r for r in map(json.loads,(ROOT/'slm/data/v3/test.jsonl').read_text(encoding='utf-8').splitlines())}
async def no_hosted(*a,**k): raise ValueError('Disabled for offline replay')
qualify._hosted=no_hosted
os.environ['QUAL_SLM_URL']='http://offline-replay.invalid'
os.environ['QUAL_SLM_MODEL']='recorded-answer'
os.environ.pop('QUAL_FORCE_INVALID',None)
async def main():
    results=[]
    for r in rows:
        checked=score(sources[r['id']],r['raw'],r['ms'],r['usage'])
        assert checked['checks']==r['checks'],r['id']
        async def recorded(*a,**k): return r['raw']
        qualify._chat=recorded
        session=[{'role':'user' if t['speaker']=='visitor' else 'assistant','text':t['text']} for t in r['transcript']]
        out=await qualify.qualify_session(session)
        q=out['qualification']
        results.append({'id':r['id'],'website_decision':q['route'],'correct':int(q['route']==r['gold']['route']),
            'wrong_sales':int(q['route']=='sales_handoff' and (r['gold']['route']!='sales_handoff' or not r['gold']['consent'])),
            'source':out['source'],'score':q['icp_score'],'range':q['score_range']})
    data={'kind':'Offline replay of actual recorded model answers through website decision handling. No new model generation or live website request.',
          'cases':results,'correct':sum(x['correct'] for x in results),'wrong_sales':sum(x['wrong_sales'] for x in results)}
    (Path(__file__).parent/'answer_recheck.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in data.items() if k!='cases'}))
    print('All 233 original answers rechecked against original expected answers. Cases with wrong sales decision:',[x['id'] for x in results if x['wrong_sales']])
asyncio.run(main())
