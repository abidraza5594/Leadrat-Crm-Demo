"""A local-only secret shared by the backend and private inference process."""
import os,secrets
from pathlib import Path

KEY_FILE=Path(__file__).resolve().parents[1]/'.state/planner.key'

def ensure_key():
    KEY_FILE.parent.mkdir(parents=True,exist_ok=True)
    try:
        with KEY_FILE.open('x',encoding='ascii') as f:f.write(secrets.token_urlsafe(48))
    except FileExistsError:pass
    if len(KEY_FILE.read_text('ascii').strip())<32:raise RuntimeError('Invalid local planner key file')
    return KEY_FILE

def headers():
    # Never send this secret to a configured external endpoint.
    from urllib.parse import urlsplit
    from . import config
    if urlsplit(config.PLANNER_MODEL_URL).hostname not in {'127.0.0.1','localhost','::1'}:
        raise ValueError('The conversation model must be a loopback endpoint')
    return {'Authorization':'Bearer '+KEY_FILE.read_text('ascii').strip()}
