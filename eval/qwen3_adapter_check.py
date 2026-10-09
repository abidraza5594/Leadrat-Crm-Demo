"""Recorded inference on the imported Qwen3 adapter; no CRM writes or deployment."""
import argparse,asyncio,collections,hashlib,html,json,random,sys,time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'outputs/qwen3-adapter-check-2026-10-08'
URL='http://127.0.0.1:8016'

def canonical(value):
    if isinstance(value,dict):return {k:canonical(v) for k,v in sorted(value.items())}
    if isinstance(value,list):return sorted((canonical(v) for v in value),key=lambda x:json.dumps(x,sort_keys=True))
    return value

def leaves(value,prefix=''):
    if isinstance(value,dict):
        result={}
        for k,v in value.items():
            if k=='evidence':continue
            result.update(leaves(v,prefix+'.'+k if prefix else k))
        return result
    return {prefix:canonical(value)}

def sample_rows():
    path=ROOT/'slm/data/qwen3-v1/test.jsonl'
    manifest=json.loads((path.parent/'manifest.json').read_text('utf-8'))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['splits']['test']['sha256']
    rows=[json.loads(s) for s in path.read_text('utf-8').splitlines()]
    selected=[];rng=random.Random(20261008)
    for task,count in [('classify',32),('demo_selection',64),('customer_update',24),('qualification',24)]:
        groups=collections.defaultdict(list)
        for row in rows:
            if row['task']==task:groups[row['family']].append(row)
        names=sorted(groups);rng.shuffle(names)
        for name in names:rng.shuffle(groups[name])
        chosen=[]
        while len(chosen)<count:
            for name in names:
                if groups[name] and len(chosen)<count:chosen.append(groups[name].pop())
        selected+=chosen
    return selected

async def infer(client,messages,schema=None,max_tokens=768):
    body={'model':'beacon-qwen3-test','messages':messages,'temperature':0,'seed':20261008,
          'max_tokens':max_tokens,'response_format':{'type':'json_object'},'cache_prompt':True}
    if schema:body['response_format']['schema']=schema
    response=await client.post(URL+'/v1/chat/completions',json=body)
    response.raise_for_status();result=response.json();choice=result['choices'][0]
    text=choice['message']['content']
    if choice.get('finish_reason')=='length':raise ValueError('Output truncated: '+text)
    return text,json.loads(text),result.get('usage',{}),result.get('timings',{})

def save(rows):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'results.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
    summary={}
    for task in dict.fromkeys(r['task'] for r in rows):
        rs=[r for r in rows if r['task']==task]
        summary[task]={'tested':len(rs),'passed':sum(r['passed'] for r in rs),
                       'percent':round(100*sum(r['passed'] for r in rs)/len(rs),1),
                       'errors':sum(bool(r.get('error')) for r in rs),
                       'average_seconds':round(sum(r['seconds'] for r in rs)/len(rs),2)}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    labels={'classify':'Message understanding','demo_selection':'Choosing the right demo',
            'customer_update':'Understanding customer replies','qualification':'Sales customer details',
            'conversation_engine':'Conversation with application logic'}
    content=['<!doctype html><meta charset="utf-8"><title>Beacon model checks</title>',
      '<style>body{font:16px system-ui;margin:32px;color:#19332c}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:12px;text-align:left;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px system-ui}summary{cursor:pointer}.ok{color:#087b36}.bad{color:#b42318}</style>',
      '<h1>Beacon — new model checks</h1><p>8 October 2026. Tests use the downloaded Qwen3 adapter with the local compact Qwen3 model. No live CRM records were changed.</p>',
      '<p>These are reference-answer checks on a selected sample plus previously reported conversation problems. They do not guarantee every customer conversation works. Training questions are excluded from the sample. CRM clicks, audio and full website operation require separate checks.</p>',
      '<table><tr><th>Check</th><th>Questions</th><th>Matched</th><th>Result</th></tr>']
    for task,s in summary.items():content.append(f'<tr><td>{labels[task]}</td><td>{s["tested"]}</td><td>{s["passed"]}</td><td>{s["percent"]}%</td></tr>')
    content.append('</table><h2>Every question and response</h2>')
    for index,row in enumerate(rows,1):
        status='Matched' if row['passed'] else 'Needs review'
        content.append(f'<details><summary class="{"ok" if row["passed"] else "bad"}">{index}. {html.escape(labels[row["task"]])} — {status} — {row["seconds"]} seconds</summary>')
        for label,key in [('Question / conversation','question'),('Expected answer','expected'),('Model answer','actual'),('Checks / error','checks')]:
            val=row.get(key,row.get('error',''))
            if not isinstance(val,str):val=json.dumps(val,indent=2,ensure_ascii=False)
            content.append('<h3>'+label+'</h3><pre>'+html.escape(val)+'</pre>')
        content.append('</details><hr>')
    (OUT/'Beacon_Qwen3_Checks.html').write_text('\n'.join(content),encoding='utf-8')

async def main():
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int);args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    headers={'Authorization':'Bearer '+(ROOT/'.state/qwen3-evaluation.key').read_text('ascii')}
    async with httpx.AsyncClient(headers=headers,timeout=httpx.Timeout(180,connect=5)) as client:
        adapters=(await client.get(URL+'/lora-adapters')).json()
        expected=ROOT/'slm/runs/qwen3-17k-2026-10-08/adapter-f32.gguf'
        assert len(adapters)==1 and Path(adapters[0]['path']).resolve()==expected.resolve() and adapters[0]['scale']==1
        (OUT/'loaded_adapter.json').write_text(json.dumps(adapters,indent=2),encoding='utf-8')
        chosen=sample_rows()
        if args.limit:chosen=chosen[:args.limit]
        (OUT/'selected_cases.json').write_text(json.dumps(chosen,indent=2,ensure_ascii=False),encoding='utf-8')
        results=[]
        for sample in chosen:
            expected=json.loads(sample['messages'][-1]['content']);messages=sample['messages'][:-1]
            schema=None;marker='Return only a JSON object matching this schema: '
            if marker in messages[0]['content']:schema=json.loads(messages[0]['content'].split(marker)[-1])
            started=time.monotonic();raw='';actual=None;error=None;checks={}
            try:
                raw,actual,usage,timings=await infer(client,messages,schema)
                checks['reference_match']=canonical(actual)==canonical(expected)
                if sample['task']=='qualification':
                    from slm.labels import Extraction,complete
                    predicted=Extraction.model_validate(actual);reference=Extraction.model_validate(expected)
                    checks['same_follow_up_decision']=complete(predicted).route==complete(reference).route
                    a,b=leaves(actual),leaves(expected)
                    checks['matching_fields']=sum(a.get(k)==v for k,v in b.items());checks['total_fields']=len(b)
                    checks['different_fields']=[k for k,v in b.items() if a.get(k)!=v]
                    checks['customer_fields_match']=not checks['different_fields']
                elif sample['task']=='customer_update':
                    visitor=messages[-1]['content'].split('Latest visitor message:\n')[-1]
                    checks['evidence_in_visitor']=all(u['evidence'] in visitor for u in actual['updates'])
                passed=checks['reference_match']
            except Exception as exc:error=type(exc).__name__+': '+str(exc);passed=False
            row={'id':sample['id'],'task':sample['task'],'family':sample['family'],'language':sample['language'],
                 'question':messages[-1]['content'],'expected':expected,'actual':actual,'raw':raw,'checks':checks,
                 'passed':passed,'error':error,'seconds':round(time.monotonic()-started,3)}
            results.append(row);save(results)
            print(json.dumps({'done':len(results),'total':len(chosen),'task':row['task'],'passed':passed,'seconds':row['seconds'],'error':error}),flush=True)
        if not args.limit:
            from eval.context_engine import CASES
            from app.conversation_engine import ConversationEngine
            from app.semantic_knowledge import SemanticKnowledge
            from app.project import FEATURES
            from app import docs
            knowledge=SemanticKnowledge();await knowledge.warm()
            async def completion(messages,schema,max_tokens=240):
                messages=[dict(m) for m in messages]
                messages[0]['content']+='\nReturn only a JSON object matching this schema: '+json.dumps(schema,separators=(',',':'))
                return (await infer(client,messages,schema,max_tokens))[1]
            engine=ConversationEngine(FEATURES,sorted({d['module'] for d in docs.load()}),knowledge,completion=completion)
            for index,(name,message,context,kind,feature,fact) in enumerate(CASES):
                state=dict(session_id='qwen3-eval-'+str(index),message=message,history=[],customer={},pending_question=None,last_feature=None,last_offer=None)
                state.update(context);started=time.monotonic();result=await engine.decide(**state);d=result['decision']
                checks={'kind':d['kind']==kind,'feature':d['feature']==feature,'no_error':not result.get('error')}
                if fact:checks['fact']=any(u['field']==fact[0] and u['value']==fact[1] for u in d['updates'])
                if name=='explain only':checks['no_demo']=not d['demo']
                elif kind=='product' and feature!='unknown':checks['demo_requested']=d['demo']
                row={'id':name,'task':'conversation_engine','question':json.dumps(state,ensure_ascii=False),
                     'expected':{'kind':kind,'feature':feature,'fact':fact},'actual':result,'checks':checks,
                     'passed':all(checks.values()),'error':result.get('error'),'seconds':round(time.monotonic()-started,3)}
                results.append(row);save(results);print(json.dumps({'conversation':name,'passed':row['passed'],'seconds':row['seconds']}),flush=True)
        print('COMPLETE '+str(OUT/'summary.json'),flush=True)

if __name__=='__main__':asyncio.run(main())
