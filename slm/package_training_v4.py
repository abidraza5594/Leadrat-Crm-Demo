"""Small self-contained Kaggle notebook: regenerate and hash-check the reviewed local data."""
import base64,hashlib,io,json,zipfile,lzma
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/beacon-training-v4'
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    files=['app/__init__.py','app/qualification.py','slm/__init__.py','slm/labels.py','slm/prompting.py','slm/build.py','slm/train.py','slm/prepare_v4.py','slm/data/v3/train.jsonl','slm/data/v3/dev.jsonl','slm/data/v4/manifest.json']
    blob=lzma.compress(json.dumps({f:(ROOT/f).read_text('utf-8') for f in files},ensure_ascii=False).encode('utf-8'),preset=9)
    (OUT/'beacon_v4_training_source.json.xz').write_bytes(blob)
    setup=f'''import os,sys,json,hashlib,base64,zipfile,lzma,subprocess,time,random
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']='0'
os.environ['TOKENIZERS_PARALLELISM']='false'
STARTED=time.time()
WORK=Path('/kaggle/working/beacon_v4_continue');WORK.mkdir(exist_ok=True)
payload=base64.b64decode({base64.b64encode(blob).decode()!r})
assert hashlib.sha256(payload).hexdigest()=={hashlib.sha256(blob).hexdigest()!r}
for rel,content in json.loads(lzma.decompress(payload)).items():
    dest=(WORK/rel).resolve()
    assert dest.is_relative_to(WORK.resolve())
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content,encoding='utf-8')
os.chdir(WORK);sys.path.insert(0,str(WORK))
def run(args): subprocess.run(args,check=True)
run([sys.executable,'-m','pip','install','-q','transformers==4.57.1','peft==0.17.1','accelerate','bitsandbytes==0.48.1','safetensors','pydantic>=2,<3'])
print('Training source verified. No evaluation conversations included.')
'''
    data='''from slm.prepare_v4 import make,CASES,read
manifest=json.loads(Path('slm/data/v4/manifest.json').read_text())
splits={}
for split,number in [('train',260),('dev',12)]:
    items=read(Path(f'slm/data/v3/{split}.jsonl'))+[make(c,j,split) for c in CASES for j in range(number)]
    random.Random(20261001).shuffle(items)
    p=Path(f'slm/data/v4/{split}.jsonl')
    p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\\n' for r in items),encoding='utf-8')
    assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['splits'][split]['sha256']
    splits[split]=items
    print(split,len(items),'data hash verified',flush=True)
assert len(splits['train'])==10611
assert not {r['family'] for r in splits['train']} & {r['family'] for r in splits['dev']}
'''
    parent='''from huggingface_hub import HfApi,snapshot_download
import shutil
PARENT_REPO='abidansari5594/beacon-qualification-qwen2.5-1.5b-qlora'
info=HfApi().model_info(PARENT_REPO,files_metadata=True)
PARENT_REVISION=info.sha
PARENT_SHA=next(s.lfs.sha256 for s in info.siblings if s.rfilename=='adapter_model.safetensors')
assert PARENT_SHA=='e23139ba1b61a4912f476120cef8ff6edb8a8a726a0d8c9a9537308cc492ffe3','Published weights changed. Review parent before continuing.'
download=Path(snapshot_download(PARENT_REPO,revision=PARENT_REVISION,allow_patterns=['adapter*','tokenizer*','vocab.json','merges.txt','special_tokens_map.json','added_tokens.json','chat_template.jinja']))
shutil.copytree(download,WORK/'parent_adapter',dirs_exist_ok=True)
assert hashlib.sha256((WORK/'parent_adapter/adapter_model.safetensors').read_bytes()).hexdigest()==PARENT_SHA
print('CONTINUING EXISTING TRAINED ADAPTER:',PARENT_REVISION,flush=True)
print('Verified parent weights:',PARENT_SHA,flush=True)
ARGS=['--out','slm/runs/kaggle-v4-continued','--data-dir','slm/data/v4','--init-adapter','parent_adapter','--format','full','--lr','2e-5','--max-len','3072','--epochs','1','--grad-accum','16']
run([sys.executable,'slm/train.py',*ARGS,'--check-only'])
'''
    train="run([sys.executable,'slm/train.py',*ARGS])\n"
    save='''run_dir=Path('slm/runs/kaggle-v4-continued')
meta=json.loads((run_dir/'run_metadata.json').read_text())
assert meta['training_mode']=='continue_adapter'
assert meta['parent_adapter']['weights_sha256']==PARENT_SHA
assert meta['train_examples']==10611 and meta['dev_examples']==716
meta.update(parent_repo=PARENT_REPO,parent_revision=PARENT_REVISION,notebook_seconds=round(time.time()-STARTED),test_status='Not yet evaluated. Compare with the preserved baseline before publication.')
(run_dir/'run_metadata.json').write_text(json.dumps(meta,indent=2))
output=Path('/kaggle/working/beacon_v4_continued_adapter.zip')
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted((run_dir/'adapter').rglob('*')):
        if p.is_file():z.write(p,str(p.relative_to(run_dir)))
    z.write(run_dir/'run_metadata.json','run_metadata.json')
    z.write('slm/data/v4/manifest.json','data_manifest.json')
with zipfile.ZipFile(output) as z:assert z.testzip() is None
print('TRAINING COMPLETE. Download:',output,flush=True)
print('Parent adapter preserved. New adapter needs evaluation before replacing the published model.')
'''
    cells=[{'cell_type':'markdown','metadata':{},'source':['# Beacon v4: continue latest trained adapter on 10,611 conversations\n','7,800 new controlled examples plus 2,811 previous training examples. 716 development examples. One additional pass at a conservative learning rate. Existing adapter weights are restored and verified; this is not training from scratch.\n','Run with GPU and Internet through **Save Version > Save & Run All** so training continues on Kaggle even when the laptop is closed. Tests stay separate.']}]
    for s in [setup,data,parent,train,save]:cells.append({'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':s.splitlines(True)})
    notebook={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'name':'python3','display_name':'Python 3'},'language_info':{'name':'python'},'accelerator':'GPU'},'cells':cells}
    p=OUT/'beacon_v4_continue_10611.ipynb';p.write_text(json.dumps(notebook,indent=1),'utf-8')
    assert p.stat().st_size<1000000,'Notebook must fit Kaggle import limit'
    print(json.dumps({'notebook':str(p),'bytes':p.stat().st_size,'bundle_bytes':len(blob),'test_data_included':False}))
if __name__=='__main__':main()
