"""Export a self-contained private Kaggle notebook, excluding every test row."""
import ast
import argparse
import base64
import hashlib
import json
import lzma
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/beacon-qwen3-fresh-training'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reuse-data-payload',action='store_true',help='Keep the uploaded data archive; embed the current audited trainer in the notebook')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    files={'train.py':(ROOT/'slm/qwen3/train.py').read_text('utf-8')}
    for name in ('train.jsonl','dev.jsonl','manifest.json'):
        files['data/'+name]=(ROOT/'slm/data/qwen3-v1'/name).read_text('utf-8')
    if args.reuse_data_payload:
        payload=(OUT/'training_source.json.xz').read_bytes()
        previous=json.loads(lzma.decompress(payload))
        assert all(previous[k]==files[k] for k in files if k.startswith('data/')), 'Uploaded data must be unchanged'
    else:
        payload=lzma.compress(json.dumps(files,ensure_ascii=False).encode(),preset=9)
        (OUT/'training_source.json.xz').write_bytes(payload)
    trainer_bytes=files['train.py'].encode('utf-8')
    trainer_sha=hashlib.sha256(trainer_bytes).hexdigest()
    trainer_b64=base64.b64encode(lzma.compress(trainer_bytes)).decode('ascii')
    setup=f'''import os,sys,json,hashlib,base64,lzma,subprocess,zipfile,time
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']='0,1'
os.environ['TOKENIZERS_PARALLELISM']='false'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
WORK=Path('/kaggle/working/beacon_qwen3_fresh');WORK.mkdir(exist_ok=True)
sources=list(Path('/kaggle/input').rglob('training_source.json.xz'))
assert len(sources)==1, 'Attach the private Beacon Qwen3 training dataset containing training_source.json.xz'
payload=sources[0].read_bytes()
assert hashlib.sha256(payload).hexdigest()=={hashlib.sha256(payload).hexdigest()!r}
source_files=json.loads(lzma.decompress(payload))
source_manifest=json.loads(source_files['data/manifest.json'])
for relative,content in source_files.items():
    path=(WORK/relative).resolve()
    assert path.is_relative_to(WORK.resolve())
    raw=content.encode('utf-8')
    if relative in ('data/train.jsonl','data/dev.jsonl'):
        expected=source_manifest['splits'][Path(relative).stem]['sha256']
        if hashlib.sha256(raw).hexdigest()!=expected:
            # Text packaging normalizes Windows CRLF. Restore the original bytes,
            # and require the ORIGINAL hash; never silently change the manifest.
            raw=content.replace('\\r\\n','\\n').replace('\\n','\\r\\n').encode('utf-8')
        assert hashlib.sha256(raw).hexdigest()==expected, 'Dataset bytes failed verification'
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
os.chdir(WORK)
# Versioned trainer override: keep the uploaded data immutable and verify code separately.
trainer_source=lzma.decompress(base64.b64decode({trainer_b64!r}))
assert hashlib.sha256(trainer_source).hexdigest()=={trainer_sha!r}
Path('train.py').write_bytes(trainer_source)
Path('trainer_provenance.json').write_text(json.dumps({{'trainer_sha256':{trainer_sha!r},'data_payload_sha256':hashlib.sha256(payload).hexdigest()}}))
print('Verified trainer SHA256:',{trainer_sha!r},flush=True)
def run(args):subprocess.run(args,check=True)
run([sys.executable,'-m','pip','install','-q','transformers==4.57.1','peft==0.17.1','accelerate==1.11.0','bitsandbytes==0.48.1','safetensors>=0.4.3'])
print('Verified fresh Qwen3 training package. No old adapter or test conversations included.',flush=True)
'''
    preflight="""run([sys.executable,'train.py','--check-only','--out','preflight'])
import torch
assert torch.cuda.is_available(), 'Select a Kaggle GPU before Save & Run All'
print('Kaggle GPU:',torch.cuda.get_device_name(0),flush=True)
assert torch.cuda.device_count()==2, 'Select GPU T4 x2; this notebook trains on both GPUs'
"""
    training="""# New LoRA weights on the pretrained Qwen3 base; never loads a previous adapter.
# Periodic checkpoints are saved. A 9-hour budget exports a PARTIAL result if needed.
run([sys.executable,'-m','torch.distributed.run','--standalone','--nproc_per_node=2','train.py','--out','run','--epochs','1','--lr','5e-5','--grad-accum','8','--wall-hours','9'])
"""
    export="""metadata=json.loads(Path('run/run_metadata.json').read_text())
assert metadata['base_model']=='Qwen/Qwen3-4B-Instruct-2507'
assert metadata['old_adapter_loaded'] is False
assert metadata['training_mode']=='new_adapter_on_pretrained_base'
name='beacon_qwen3_new_adapter.zip' if metadata['completed'] else 'beacon_qwen3_PARTIAL_adapter.zip'
output=Path('/kaggle/working')/name
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
    z.write('trainer_provenance.json','trainer_provenance.json')
    for p in sorted(Path('run/adapter').rglob('*')):
        if p.is_file():z.write(p,str(p.relative_to('run')))
    for p in ['run_metadata.json','data_manifest.json','preflight.json','trainer_state.json']:
        if Path('run',p).exists():z.write(Path('run',p),p)
with zipfile.ZipFile(output) as z:assert z.testzip() is None
print('COMPLETE' if metadata['completed'] else 'PARTIAL - NOT A COMPLETED TRAINING RUN',flush=True)
print('Download:',output,flush=True)
print('Evaluate on the separate local test set and live conversations before using this adapter in Beacon.')
"""
    manifest=json.loads(files['data/manifest.json'])
    cells=[{'cell_type':'markdown','metadata':{},'source':[
        '# Beacon: fresh Qwen3-4B multitask fine-tuning\n',
        f"{manifest['splits']['train']['count']:,} training examples; {manifest['splits']['dev']['count']:,} separate development examples. Predominantly English.\n",
        'A new adapter on Qwen/Qwen3-4B-Instruct-2507. Previous Qwen2.5 adapters are never loaded.\n',
        'Tasks: customer qualification facts, conversation classification, customer updates and demo selection. Application code calculates scores and verifies browser actions.\n',
        '**Private notebook. Enable Internet and a GPU. Use Save Version > Save & Run All for a Kaggle server job that can continue with the laptop closed.**\n',
        'Synthetic examples are not a guarantee of live accuracy. Test conversations are excluded. A time-limited partial run is labelled PARTIAL. The old Hugging Face model is never overwritten.\n']}]
    for code in (setup,preflight,training,export):
        ast.parse(code)
        cells.append({'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':code.splitlines(True)})
    notebook={'nbformat':4,'nbformat_minor':4,'metadata':{'kernelspec':{'name':'python3','display_name':'Python 3'},'language_info':{'name':'python'},'accelerator':'GPU'},'cells':cells}
    path=OUT/'beacon_qwen3_fresh_17446.ipynb';path.write_text(json.dumps(notebook,indent=1),encoding='utf-8')
    result={'notebook':str(path),'notebook_bytes':path.stat().st_size,'compressed_bytes':len(payload),'trainer_sha256':trainer_sha,'test_rows_included':0,'train_examples':manifest['splits']['train']['count']}
    (OUT/'package_manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
