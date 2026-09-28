"""Credentials stay in process memory only, so the hidden browser can sign in again when the saved login expires."""
import getpass
import os
import uvicorn
import argparse
import httpx

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--openai',action='store_true')
    args=parser.parse_args()
    if args.openai:
        os.environ['OPENAI_API_KEY']=getpass.getpass('Temporary OpenAI API key (memory only): ').strip()
        os.environ['PLANNER_PROVIDER']='openai'
        os.environ['OPENAI_MODEL']='gpt-6-luna'
        try:
            result=httpx.get('https://api.openai.com/v1/models/gpt-6-luna',headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']},timeout=15)
            print('Luna model access:',result.status_code)
            if result.status_code!=200:raise SystemExit('Requested model access could not be verified. No model was substituted.')
        except httpx.HTTPError:raise SystemExit('Model access check failed; retry when connectivity is available.')
    os.environ['BEACON_LOGIN_USER']=input('Test CRM username (blank to use the login saved by login.ps1): ').strip()
    if os.environ['BEACON_LOGIN_USER']:
        os.environ['BEACON_LOGIN_PASSWORD']=getpass.getpass('Test CRM password: ')
    uvicorn.run('app.main:app',host='127.0.0.1',port=8010,access_log=False)
