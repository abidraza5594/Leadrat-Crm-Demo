import os
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
CRM_URL = os.getenv('CRM_URL', 'http://localhost:4200').rstrip('/')
CRM_ORIGIN = '{0.scheme}://{0.netloc}'.format(urlsplit(CRM_URL))
SANDBOX_CONFIRMED = os.getenv('SANDBOX_CONFIRMED', 'false').lower() == 'true'
ORIGINS = set(os.getenv('BEACON_ORIGINS', 'http://localhost:8010,http://localhost:8011,http://127.0.0.1:8010,http://127.0.0.1:8011').split(','))
# The demo browser is hidden by default; visitors see it only inside the website popup.
HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'
LOCAL_DEVICE_LOCATION = os.getenv('LOCAL_DEVICE_LOCATION', 'false').lower() == 'true'
# Saved CRM login (cookies + localStorage) reused by each new hidden browser. Contains auth tokens; never commit it.
BROWSER_STATE = Path(os.getenv('BEACON_BROWSER_STATE', ROOT / '.browser' / 'crm-state.json'))
TTS_URL = os.getenv('TTS_URL', '').rstrip('/')
TTS_VOICE = os.getenv('TTS_VOICE', 'af_heart')
TTS_PROVIDER = os.getenv('TTS_PROVIDER','local' if TTS_URL else 'browser')
STT_PROVIDER = os.getenv('STT_PROVIDER', 'soniox')
PROVIDER = os.getenv('PLANNER_PROVIDER','local').strip().lower()
if PROVIDER not in {'local','deepseek'}:raise ValueError('PLANNER_PROVIDER must be local or deepseek')
# Hosted conversation model (OpenAI-compatible API). The key stays in .env; it is never logged.
DEEPSEEK_URL = os.getenv('DEEPSEEK_URL','https://api.deepseek.com').rstrip('/')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL','deepseek-flash')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY','').strip()
if PROVIDER=='deepseek' and not DEEPSEEK_API_KEY:raise ValueError('PLANNER_PROVIDER=deepseek needs DEEPSEEK_API_KEY in .env')
LOCAL_MODEL_URL = os.getenv('LOCAL_MODEL_URL', 'http://127.0.0.1:8012').rstrip('/')
LOCAL_CHAT_MODEL = os.getenv('LOCAL_CHAT_MODEL', 'beacon-qwen3-17k')
PLANNER_MODEL_URL = os.getenv('PLANNER_MODEL_URL', LOCAL_MODEL_URL).rstrip('/')
PLANNER_MODEL = os.getenv('PLANNER_MODEL', LOCAL_CHAT_MODEL)
PLANNER_BACKEND = os.getenv('PLANNER_BACKEND','transformers')
