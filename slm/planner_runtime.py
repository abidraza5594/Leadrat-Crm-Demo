"""Start a dedicated loopback CPU planner without competing for adapter GPU RAM."""
import json,os,subprocess,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
URL='http://127.0.0.1:8014'
NAME='beacon-planner'

def ready():
    try:
        from app.planner_auth import KEY_FILE
        key=KEY_FILE.read_text('ascii').strip()
        r=httpx.get(URL+'/v1/models',headers={'Authorization':'Bearer '+key},timeout=2);r.raise_for_status()
        names=[m['id'] for m in r.json()['data']]
        props=httpx.get(URL+'/props',headers={'Authorization':'Bearer '+key},timeout=2);props.raise_for_status()
        manifest=json.loads((ROOT/'.models/planner/manifest.json').read_text())
        expected=ROOT/'.models/planner'/manifest['model_file']
        if Path(props.json()['model_path']).resolve()!=expected.resolve():
            raise RuntimeError('Planner is running a different checkpoint; restart its service')
    except (httpx.HTTPError,ValueError,KeyError,OSError):return False
    if names!=[NAME]:raise RuntimeError('Another model is using the planner port')
    return True

def ensure_planner():
    if ready():return
    binary=ROOT/'.tools/llama-b11429/llama-server.exe'
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
    from app.planner_auth import ensure_key
    key_file=ensure_key()
    args=[str(binary),'-m',str(model),'--alias',NAME,'--host','127.0.0.1','--port','8014',
          '-c','4096','-t','4','-tb','8','-b','512','-ub','256','-ngl','0','-np','1',
          '--cache-ram','512','--kv-unified','--cache-idle-slots','--reasoning','off','--no-ui','--api-key-file',str(key_file)]
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
