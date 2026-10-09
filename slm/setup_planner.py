"""Install pinned, verified local planner files. No accounts or hosted inference."""
import argparse,hashlib,json,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=[
 ('https://github.com/ggml-org/llama.cpp/releases/download/b11429/llama-b11429-bin-win-cpu-x64.zip',ROOT/'.tools/llama-b11429.zip','1283323272b04cd07905816a597a0da810918102de958f4ff6f7bbaa70ed2efe'),
 ('https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/resolve/f6d5376be1edb4d416d56da11e5397a961aca8ae/Qwen3.5-2B-Q4_K_M.gguf',ROOT/'.models/planner/Qwen3.5-2B-Q4_K_M.gguf','aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223'),
]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(4*1024**2),b''):h.update(chunk)
 return h.hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--model',choices=['2b','4b'],default='4b');args=parser.parse_args()
 name='Qwen3.5-2B';revision='f6d5376be1edb4d416d56da11e5397a961aca8ae'
 if args.model=='4b':
  name='Qwen3-4B-Instruct-2507';revision='a06e946bb6b655725eafa393f4a9745d460374c9'
  FILES[1]=(f'https://huggingface.co/unsloth/{name}-GGUF/resolve/{revision}/{name}-Q4_K_M.gguf',ROOT/f'.models/planner/{name}-Q4_K_M.gguf','3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597')
 for url,path,digest in FILES:
  path.parent.mkdir(parents=True,exist_ok=True)
  if path.exists() and sha(path)==digest:continue
  part=path.with_suffix(path.suffix+'.part');total=0;reported=0
  request=urllib.request.Request(url,headers={'User-Agent':'Beacon-local-setup'})
  with urllib.request.urlopen(request,timeout=60) as r,part.open('wb') as f:
   while chunk:=r.read(1024**2):
    f.write(chunk);total+=len(chunk)
    if total-reported>=100*1024**2:print(path.name,round(total/1024**2),'MiB downloaded',flush=True);reported=total
  if sha(part)!=digest:raise RuntimeError('Checksum mismatch: '+path.name)
  part.replace(path);print('Verified',path.name,flush=True)
 target=ROOT/'.tools/llama-b11429';target.mkdir(exist_ok=True)
 with zipfile.ZipFile(FILES[0][1]) as z:
  for member in z.infolist():
   if not (target/member.filename).resolve().is_relative_to(target.resolve()):raise RuntimeError('Unsafe archive member')
  # Do not replace unchanged DLLs: Windows locks libraries while the planner
  # runs, so a repeat setup must be safe with the installed server active.
  for member in z.infolist():
   destination=target/member.filename
   if member.is_dir():
    destination.mkdir(parents=True,exist_ok=True);continue
   with z.open(member) as source:
    expected=hashlib.sha256(source.read()).hexdigest()
   if destination.is_file() and sha(destination)==expected:continue
   z.extract(member,target)
 (ROOT/'.models/planner/manifest.json').write_text(json.dumps({'model':name,'model_file':FILES[1][1].name,'model_revision':revision,'quantization':'Q4_K_M','model_sha256':FILES[1][2],'runtime':'llama.cpp b11429','runtime_sha256':FILES[0][2]},indent=2))
 print('Planner files verified and ready',flush=True)
if __name__=='__main__':main()
