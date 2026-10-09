"""Start and verify the shared local Qwen3 conversation/qualification runtime."""
import json,os,subprocess,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
URL='http://127.0.0.1:8014'
NAME='beacon-planner'

def active_release():
    release=json.loads((ROOT/'slm/current_release.json').read_text())
    return release if release.get('runtime')=='llamacpp' and release.get('status')=='active' else None

def adapter_path(release):
    path=(ROOT/release['gguf_adapter']).resolve()
    if not path.is_relative_to((ROOT/'slm/runs').resolve()):
        raise RuntimeError('Invalid adapter path')
    return path

def verify_identity(names,props,adapters,release=None):
    manifest=json.loads((ROOT/'.models/planner/manifest.json').read_text())
    expected=ROOT/'.models/planner'/manifest['model_file']
    if Path(props['model_path']).resolve()!=expected.resolve():
        raise RuntimeError('A different base model is running; restart its service')
    if names!=[release['model_alias'] if release else NAME]:
        raise RuntimeError('A different model is using the planner port; restart its service')
    if release:
        if len(adapters)!=1 or Path(adapters[0]['path']).resolve()!=adapter_path(release) or adapters[0]['scale']!=1:
            raise RuntimeError('The current trained adapter is not loaded at full strength')
    elif adapters:
        raise RuntimeError('An unexpected adapter is loaded')
    return True

def ready():
    try:
        from app.planner_auth import KEY_FILE
        key=KEY_FILE.read_text('ascii').strip()
        r=httpx.get(URL+'/v1/models',headers={'Authorization':'Bearer '+key},timeout=2);r.raise_for_status()
        names=[m['id'] for m in r.json()['data']]
        props=httpx.get(URL+'/props',headers={'Authorization':'Bearer '+key},timeout=2);props.raise_for_status()
        adapters=httpx.get(URL+'/lora-adapters',headers={'Authorization':'Bearer '+key},timeout=2);adapters.raise_for_status()
        verify_identity(names,props.json(),adapters.json(),active_release())
    except (httpx.HTTPError,ValueError,KeyError,OSError):return False
    return True

def ensure_planner():
    if ready():return
    release=active_release()
    binary=ROOT/('.tools/llama-b11429-cuda/llama-server.exe' if release else '.tools/llama-b11429/llama-server.exe')
    manifest=ROOT/'.models/planner/manifest.json'
    if not manifest.is_file():raise RuntimeError('Run python slm/setup_planner.py first')
    metadata=json.loads(manifest.read_text())
    model=(manifest.parent/metadata['model_file']).resolve()
    if not model.is_relative_to(manifest.parent.resolve()):raise RuntimeError('Invalid model path')
    if not all(p.is_file() for p in (binary,model,manifest)):
        raise RuntimeError('Local conversation model is missing. Run python slm/setup_planner.py.')
    from slm.setup_planner import sha
    if sha(model)!=metadata['model_sha256']:
        raise RuntimeError('Conversation model checksum mismatch')
    if release:
        adapter=adapter_path(release)
        if not adapter.is_file() or sha(adapter)!=release['gguf_sha256']:
            raise RuntimeError('Trained adapter missing or checksum mismatch')
    from app.planner_auth import ensure_key
    key_file=ensure_key()
    args=[str(binary),'-m',str(model),'--alias',release['model_alias'] if release else NAME,'--host','127.0.0.1','--port','8014',
          '-c','4096','-t','4','-tb','8','-b','256','-ub','128','-ngl','99' if release else '0','-np','1',
          # Host-memory prompt cache: each turn alternates between a few fixed system prompts
          # (classify, route, answer, check, scoring); restoring their prefix skips ~1-2 s of prompt work.
          '--cache-ram',os.getenv('BEACON_PROMPT_CACHE_MB','512'),'--reasoning','off','--no-ui','--api-key-file',str(key_file)]
    if release:args+=['--lora',str(adapter),'-fa','on','-ctk','q8_0','-ctv','q8_0']
    logs=ROOT/'artifacts';logs.mkdir(exist_ok=True)
    with (logs/'planner.stdout.log').open('a',encoding='utf8') as out,(logs/'planner.stderr.log').open('a',encoding='utf8') as err:
        process=subprocess.Popen(args,cwd=ROOT,stdout=out,stderr=err,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        if ready():return
        if process.poll() is not None:raise RuntimeError('Conversation runtime failed; see artifacts/planner.stderr.log')
        time.sleep(.5)
    raise RuntimeError('Conversation model startup timed out')

if __name__=='__main__':ensure_planner();print('Local conversation model ready')
