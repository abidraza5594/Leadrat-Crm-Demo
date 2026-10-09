"""Start the current release once and verify it before starting the website backend."""
import json
import os
import subprocess
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]

def ensure_local_model():
    expected = json.loads((ROOT / 'slm/current_release.json').read_text())['weights_sha256']
    url = os.getenv('LOCAL_MODEL_URL', 'http://127.0.0.1:8012').rstrip('/')
    def ready():
        try:
            r = httpx.get(url + '/health', timeout=2)
            r.raise_for_status()
            data = r.json()
        except (httpx.HTTPError, ValueError): return False
        if data.get('weights_sha256') != expected:
            raise RuntimeError('A different model is using the local model port; restart that Beacon model service.')
        return data.get('ready', False)
    if ready(): return
    if url != 'http://127.0.0.1:8012':
        raise RuntimeError('Configured local model endpoint is unavailable')
    python = ROOT / '.venv-train/Scripts/python.exe'
    if not python.is_file(): raise RuntimeError('Beacon training environment is missing')
    env = dict(os.environ)
    # Keep the training environment's CUDA torch ahead of the web server's
    # CPU-only embedding dependencies. The latter supplies shared web packages.
    env['PYTHONPATH'] = os.pathsep.join([str(ROOT), str(ROOT / '.venv-train/Lib/site-packages'), str(ROOT / '.venv/Lib/site-packages')])
    env['HF_HUB_OFFLINE'] = env['TRANSFORMERS_OFFLINE'] = '1'
    logs = ROOT / 'artifacts'; logs.mkdir(exist_ok=True)
    with (logs / 'local-model.stdout.log').open('a', encoding='utf8') as stdout, (logs / 'local-model.stderr.log').open('a', encoding='utf8') as stderr:
        process = subprocess.Popen([str(python), 'slm/serve_local.py'], cwd=ROOT, env=env,
            stdout=stdout, stderr=stderr, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        if ready(): return
        if process.poll() is not None: raise RuntimeError('Local model startup failed; see artifacts/local-model.stderr.log')
        time.sleep(1)
    raise RuntimeError('Local model is still loading; see artifacts/local-model.stdout.log')
