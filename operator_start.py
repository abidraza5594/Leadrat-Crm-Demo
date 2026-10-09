"""Start Beacon. Settings and test secrets come from .env; only a missing required value is asked for.

A value typed at a prompt stays in process memory only. Credentials stay in memory so the hidden
browser can sign in again when the saved login expires.
"""
import argparse
import getpass
import os
import threading
import time
import webbrowser
from pathlib import Path
import httpx
import uvicorn
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parent
SITE='http://localhost:8011'

def open_site_when_ready():
    for _ in range(120):
        try:
            if httpx.get('http://127.0.0.1:8010/api/health',timeout=1).status_code==200:
                webbrowser.open(SITE);return
        except httpx.HTTPError:pass
        time.sleep(0.5)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-browser',action='store_true',help='do not open the test website')
    args=parser.parse_args()
    load_dotenv(ROOT/'.env')
    os.environ.setdefault('BEACON_PREWARM_BROWSER','1')
    os.environ.setdefault('BEACON_WARM_KNOWLEDGE','1')
    provider=os.environ.setdefault('PLANNER_PROVIDER','local').strip().lower()
    if provider!='local':raise SystemExit('Beacon uses local models only. Set PLANNER_PROVIDER=local.')
    os.environ['BEACON_START_LOCAL_MODEL']='1'
    print('Starting Beacon; local models will load in the background...',flush=True)
    saved_login=Path(os.getenv('BEACON_BROWSER_STATE',ROOT/'.browser'/'crm-state.json')).is_file()
    if not (os.getenv('BEACON_LOGIN_USER','').strip() and os.getenv('BEACON_LOGIN_PASSWORD')) and not saved_login:
        user=input('Test CRM username (put BEACON_LOGIN_USER/PASSWORD in .env to skip; blank to sign in with login.ps1): ').strip()
        if user:
            os.environ['BEACON_LOGIN_USER']=user
            os.environ['BEACON_LOGIN_PASSWORD']=getpass.getpass('Test CRM password: ')
    login='test credentials' if os.getenv('BEACON_LOGIN_USER','').strip() and os.getenv('BEACON_LOGIN_PASSWORD') else 'saved login' if saved_login else 'not configured (run .\\login.ps1)'
    print(f'Planner: {provider} | CRM sign-in: {login} | Website: {SITE}')
    if not args.no_browser:threading.Thread(target=open_site_when_ready,daemon=True).start()
    uvicorn.run('app.main:app',host='127.0.0.1',port=8010,access_log=False)
