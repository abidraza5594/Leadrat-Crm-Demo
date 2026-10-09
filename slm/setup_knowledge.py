"""Verified small CPU embedding artifacts; run explicitly during setup."""
import hashlib,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVISION='e8f8c211226b894fcb81acc59f3b34ba3efd5f42'
FILES={
 'onnx/model_quint8_avx2.onnx':'98a01d88b7de996cdea58c32ca71208c09968d143798814b2ea09d3439dc334f',
 'tokenizer.json':'2c3387be76557bd40970cec13153b3bbf80407865484b209e655e5e4729076b8',
}
def verify(path,digest):
    if not path.is_file():return False
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024**2),b''):h.update(chunk)
    return h.hexdigest()==digest
def main():
    folder=ROOT/'.models/knowledge';folder.mkdir(parents=True,exist_ok=True)
    for remote,digest in FILES.items():
        path=folder/Path(remote).name
        if verify(path,digest):continue
        url=f'https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/resolve/{REVISION}/{remote}'
        part=path.with_suffix('.part')
        with urllib.request.urlopen(url,timeout=60) as response,part.open('wb') as out:
            while chunk:=response.read(1024**2):out.write(chunk)
        if not verify(part,digest):raise RuntimeError('Embedding artifact checksum mismatch')
        part.replace(path);print('Verified',path.name,flush=True)
if __name__=='__main__':main()
