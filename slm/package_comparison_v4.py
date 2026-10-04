import base64,json,lzma
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
files=['app/__init__.py','app/qualification.py','slm/__init__.py','slm/labels.py','slm/prompting.py','slm/evaluate_v3_release.py','slm/compare_v4.py','slm/data/v3/test.jsonl','slm/data/v4/fresh_test.jsonl']
payload={p:(ROOT/p).read_text(encoding='utf-8') if (ROOT/p).exists() else '' for p in files}
encoded=base64.b64encode(lzma.compress(json.dumps(payload).encode())).decode()
cells=[]
def code(s):cells.append({'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':s.splitlines(keepends=True)})
cells.append({'cell_type':'markdown','metadata':{},'source':['# Beacon v4 versus v3 comparison\n','233 preserved comparison conversations plus 60 additional conversations (two per prepared scenario). Both versions use the same full JSON prompt and generation settings. The previous 233 answers remain frozen; this run generates v4 answers and both versions on the 60 additional examples. No training or customer messages are sent.']})
code("%pip -q install transformers==4.57.1 peft==0.17.1 accelerate==1.10.1 bitsandbytes==0.48.1 huggingface_hub pydantic\n")
code("import base64,json,lzma,os,sys,subprocess,hashlib,zipfile\nfrom pathlib import Path\nWORK=Path('/kaggle/working/beacon_comparison');WORK.mkdir(exist_ok=True);os.chdir(WORK)\npayload=json.loads(lzma.decompress(base64.b64decode('"+encoded+"')))\nfor name,content in payload.items():\n p=WORK/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf-8')\nprint('Evaluation files ready. No training.')\n")
release=json.loads((ROOT/'outputs/beacon-training-v4/hf_published_v4.json').read_text())
code("from huggingface_hub import snapshot_download\nrepo='"+release['repo']+"'\nversions="+repr([('slm/runs/kaggle-v4-continued/adapter',release['revision'],release['weights_sha256']),('slm/runs/kaggle/adapter','11f9e096fa656f8d26706ce59debb40fc2e2d904','e23139ba1b61a4912f476120cef8ff6edb8a8a726a0d8c9a9537308cc492ffe3')])+"\nfor target,revision,expected in versions:\n snapshot_download(repo,revision=revision,local_dir=target,allow_patterns=['adapter*','tokenizer*','special_tokens_map.json','added_tokens.json','vocab.json','merges.txt','chat_template.jinja'])\n assert hashlib.sha256((Path(target)/'adapter_model.safetensors').read_bytes()).hexdigest()==expected\n print('Verified version',revision)\n")
code("subprocess.run([sys.executable,'-u','slm/compare_v4.py','--cloud','--batch-size','8'],check=True)\n")
code("folder=WORK/'outputs/beacon-training-v4/comparison'\nassert len((folder/'new.jsonl').read_text().splitlines())==293\nassert len((folder/'old.jsonl').read_text().splitlines())==60\nwith zipfile.ZipFile('/kaggle/working/beacon_v4_comparison.zip','w',zipfile.ZIP_DEFLATED) as z:\n for p in folder.iterdir():\n  if p.is_file():z.write(p,p.name)\nprint('COMPARISON COMPLETE. Download beacon_v4_comparison.zip')\n")
out=ROOT/'outputs/beacon-training-v4/compare_v4_v3.ipynb'
out.write_text(json.dumps({'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'nbformat':4,'nbformat_minor':5}),encoding='utf-8')
print(out)
